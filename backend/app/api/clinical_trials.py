"""
Clinical Trials API Router
Handles clinical trial data from ClinicalTrials.gov
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
import logging
import httpx
from datetime import datetime, timedelta
from dotenv import load_dotenv
from app.adapters.ollama.client import OllamaClient
from app.db.connection import get_clinical_trials_cache_collection
import hashlib

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/clinical-trials", tags=["clinical-trials"])

# Ollama is local-first and does not require an API key. The client remains
# lazy so importing the router has no network side effect.
ollama_client: Optional[OllamaClient] = None

# In-memory cache for translated trials
# Key: (condition, page, page_size) -> Value: cached response with timestamp
_trials_cache = {}
_translation_cache = {}  # Key: text hash -> {translation, timestamp}
CACHE_TTL = 3600  # Cache for 1 hour


async def get_persistent_cache(cache_key: str) -> Optional[Dict[str, Any]]:
    """Read a shared cache entry; unit tests and cold starts may have no DB."""
    try:
        entry = await get_clinical_trials_cache_collection().find_one({"cache_key": cache_key})
    except Exception:
        return None
    if not entry or entry.get("fresh_until", datetime.min) <= datetime.now():
        return None
    return entry.get("data")


async def get_persistent_stale_cache(cache_key: str) -> Optional[Dict[str, Any]]:
    """Read a recently expired entry for bounded provider-outage fallback."""
    try:
        entry = await get_clinical_trials_cache_collection().find_one({"cache_key": cache_key})
    except Exception:
        return None
    if not entry or entry.get("expires_at", datetime.min) <= datetime.now():
        return None
    return entry.get("data")


async def set_persistent_cache(cache_key: str, data: Any) -> None:
    """Write a bounded shared cache entry without making the provider path fail."""
    try:
        now = datetime.now()
        await get_clinical_trials_cache_collection().update_one(
            {"cache_key": cache_key},
            {
                "$set": {
                    "cache_key": cache_key,
                    "data": data,
                    "updated_at": now,
                    "fresh_until": now + timedelta(seconds=CACHE_TTL),
                    "expires_at": now + timedelta(seconds=CACHE_TTL * 2),
                }
            },
            upsert=True,
        )
    except Exception:
        logger.debug("Clinical-trial cache persistence unavailable", exc_info=True)


def get_ollama_client() -> OllamaClient:
    """Return the single local client used only for faithful translation."""
    global ollama_client
    if ollama_client is None:
        ollama_client = OllamaClient()
    return ollama_client


# ==================== Cache Helper Functions ====================

def get_text_hash(text: str) -> str:
    """Generate hash for text to use as cache key"""
    return hashlib.md5(text.encode()).hexdigest()


def get_cache_key(
    condition: str,
    page: int,
    page_size: int,
    status: Optional[str] = None,
) -> str:
    """Generate cache key for trial list"""
    return f"{condition}:{status or 'all'}:{page}:{page_size}"


def is_cache_valid(timestamp: float) -> bool:
    """Check if cache is still valid"""
    return (datetime.now().timestamp() - timestamp) < CACHE_TTL


def get_cached_trials(
    condition: str,
    page: int,
    page_size: int,
    status: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Get cached trial list if available and valid"""
    cache_key = get_cache_key(condition, page, page_size, status)
    if cache_key in _trials_cache:
        cached_data = _trials_cache[cache_key]
        if is_cache_valid(cached_data["timestamp"]):
            logger.info(f"Cache hit for trials: {cache_key}")
            return cached_data["data"]
        logger.info(f"Cache expired for trials: {cache_key}")
    return None


def get_stale_cached_trials(
    condition: str,
    page: int,
    page_size: int,
    status: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Return the last provider response for bounded outage fallback."""
    cached_data = _trials_cache.get(get_cache_key(condition, page, page_size, status))
    return cached_data["data"] if cached_data else None


def set_cached_trials(
    condition: str,
    page: int,
    page_size: int,
    data: Dict[str, Any],
    status: Optional[str] = None,
):
    """Cache trial list data"""
    cache_key = get_cache_key(condition, page, page_size, status)
    _trials_cache[cache_key] = {
        "data": data,
        "timestamp": datetime.now().timestamp()
    }
    logger.info(f"Cached trials: {cache_key}")


def get_cached_translation(text: str) -> Optional[str]:
    """Get cached translation if available"""
    text_hash = get_text_hash(text)
    if text_hash in _translation_cache:
        cached = _translation_cache[text_hash]
        if is_cache_valid(cached["timestamp"]):
            logger.info("Translation cache hit")
            return cached["translation"]
        del _translation_cache[text_hash]
    return None


def set_cached_translation(text: str, translation: str):
    """Cache translation"""
    text_hash = get_text_hash(text)
    _translation_cache[text_hash] = {
        "translation": translation,
        "timestamp": datetime.now().timestamp(),
    }


# ==================== Request/Response Models ====================

class ClinicalTrialListRequest(BaseModel):
    """Request for clinical trial list"""
    condition: str = Field(default="kidney", description="Medical condition to search")
    page: int = Field(default=1, ge=1, description="Page number")
    page_size: int = Field(default=10, ge=1, le=50, description="Results per page")
    status: Optional[str] = Field(default=None, description="Study status filter")


class ClinicalTrialDetailRequest(BaseModel):
    """Request for source-backed clinical trial detail and faithful translation."""
    nct_id: str = Field(..., description="NCT ID of the trial")
    language: str = Field(default="ko", pattern="^(ko|en)$", description="Translation language")


# ==================== Helper Functions ====================

async def fetch_clinical_trials(
    condition: str = "kidney",
    page: int = 1,
    page_size: int = 10,
    status: Optional[str] = None
) -> Dict[str, Any]:
    """
    Fetch clinical trials from ClinicalTrials.gov API

    API Documentation: https://clinicaltrials.gov/api/v2/studies
    """
    try:
        base_url = "https://clinicaltrials.gov/api/v2/studies"

        # Build query parameters
        # API v2 uses query.term for keyword search
        query_parts = [f"AREA[Condition]{condition}"]
        if status:
            query_parts.append(f"AREA[OverallStatus]{status}")

        base_params = {
            "query.term": " AND ".join(query_parts),
            "pageSize": page_size,
            "format": "json",
            "sort": "LastUpdatePostDate:desc"  # Sort by last update date, newest first
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            # ClinicalTrials.gov v2 uses an opaque nextPageToken rather than
            # offset pagination. Walk pages in order so a requested page can
            # be resolved even when its token was not previously cached.
            data: Dict[str, Any] = {}
            next_page_token: Optional[str] = None
            resolved_page = 0
            total_count: Optional[int] = None
            for requested_page in range(1, page + 1):
                params = dict(base_params)
                if requested_page == 1:
                    params["countTotal"] = "true"
                elif next_page_token:
                    params["pageToken"] = next_page_token
                else:
                    break

                response = await client.get(base_url, params=params)
                response.raise_for_status()
                data = response.json()
                resolved_page = requested_page
                if requested_page == 1:
                    total_count = data.get("totalCount")
                next_page_token = data.get("nextPageToken")

            if resolved_page != page:
                raise HTTPException(status_code=404, detail="Clinical trial page is not available")
            if total_count is not None:
                data["totalCount"] = total_count

            return data

    except HTTPException:
        raise
    except httpx.HTTPError as e:
        logger.error(f"HTTP error fetching clinical trials: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch clinical trials: {str(e)}")
    except Exception as e:
        logger.error(f"Error fetching clinical trials: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


async def fetch_trial_detail(nct_id: str) -> Dict[str, Any]:
    """
    Fetch detailed information for a specific clinical trial
    """
    try:
        url = f"https://clinicaltrials.gov/api/v2/studies/{nct_id}"

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, params={"format": "json"})
            response.raise_for_status()
            data = response.json()

            return data

    except httpx.HTTPError as e:
        logger.error(f"HTTP error fetching trial detail: {e}")
        raise HTTPException(status_code=404, detail=f"Trial not found: {nct_id}")
    except Exception as e:
        logger.error(f"Error fetching trial detail: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


async def translate_to_korean(text: str) -> str:
    """
    Translate English text to Korean using local Ollama with caching
    """
    if not text or len(text.strip()) == 0:
        return text

    # Mongo is the shared cache; the process cache remains a fast local tier.
    persistent_key = f"translation:{get_text_hash(text)}"
    cached = await get_persistent_cache(persistent_key)
    if cached:
        set_cached_translation(text, cached)
        return cached
    cached = get_cached_translation(text)
    if cached:
        return cached

    try:
        client = get_ollama_client()
        if client is None:
            return text

        response = await client.chat.completions.create(
            model="qwen3.6:27b-mlx",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Translate the supplied ClinicalTrials.gov field from English to Korean "
                        "faithfully. Do not summarize, infer, interpret, recommend, add clinical "
                        "significance, or omit information. Preserve identifiers, numbers and "
                        "uncertainty. Output only the translation."
                    ),
                },
                {"role": "user", "content": text}
            ],
            temperature=0.0,
            max_tokens=2000
        )
        translation = response.choices[0].message.content.strip()

        # Cache the translation
        set_cached_translation(text, translation)
        await set_persistent_cache(persistent_key, translation)

        return translation
    except Exception:
        logger.error("Faithful clinical-trial translation failed", exc_info=True)
        return text  # Return original text if translation fails


async def parse_trial_data(study: Dict[str, Any], translate: bool = False) -> Dict[str, Any]:
    """
    Parse and structure clinical trial data from API response
    """
    try:
        protocol = study.get("protocolSection", {})
        identification = protocol.get("identificationModule", {})
        status = protocol.get("statusModule", {})
        description = protocol.get("descriptionModule", {})
        conditions = protocol.get("conditionsModule", {})
        design = protocol.get("designModule", {})
        eligibility = protocol.get("eligibilityModule", {})
        contacts = protocol.get("contactsModule", {})

        # Extract raw data
        title = identification.get("briefTitle", "")
        official_title = identification.get("officialTitle", "")
        brief_summary = description.get("briefSummary", "")
        detailed_description = description.get("detailedDescription", "")
        eligibility_criteria = eligibility.get("eligibilityCriteria", "")
        study_type = design.get("studyType", "")
        overall_status = status.get("overallStatus", "")
        condition_names = conditions.get("conditions", [])

        # Translate if requested
        if translate:
            title = await translate_to_korean(title)
            if official_title:
                official_title = await translate_to_korean(official_title)
            if brief_summary:
                brief_summary = await translate_to_korean(brief_summary)
            if detailed_description:
                detailed_description = await translate_to_korean(detailed_description)
            if eligibility_criteria:
                eligibility_criteria = await translate_to_korean(eligibility_criteria)
            if study_type:
                study_type = await translate_to_korean(study_type)
            if overall_status:
                overall_status = await translate_to_korean(overall_status)
            condition_names = [await translate_to_korean(item) for item in condition_names]

        return {
            "nctId": identification.get("nctId", ""),
            "title": title,
            "officialTitle": official_title,
            "status": overall_status,
            "phase": design.get("phases", ["N/A"])[0] if design.get("phases") else "N/A",
            "studyType": study_type,
            "briefSummary": brief_summary,
            "detailedDescription": detailed_description,
            "conditions": condition_names,
            "enrollment": design.get("enrollmentInfo", {}).get("count", 0),
            "startDate": status.get("startDateStruct", {}).get("date", ""),
            "completionDate": status.get("completionDateStruct", {}).get("date", ""),
            "lastUpdateDate": status.get("lastUpdatePostDateStruct", {}).get("date", ""),
            "sponsor": protocol.get("sponsorCollaboratorsModule", {}).get("leadSponsor", {}).get("name", ""),
            "locations": contacts.get("locations", []),
            "eligibilityCriteria": eligibility_criteria,
            "sex": eligibility.get("sex", ""),
            "minimumAge": eligibility.get("minimumAge", ""),
            "maximumAge": eligibility.get("maximumAge", ""),
        }

    except Exception as e:
        logger.error(f"Error parsing trial data: {e}", exc_info=True)
        return {}


# ==================== API Endpoints ====================

@router.post("/list")
async def get_clinical_trials(request: ClinicalTrialListRequest) -> Dict[str, Any]:
    """
    Get list of clinical trials filtered by condition (default: kidney)

    Returns:
        - List of trials with basic information (cached for performance)
        - Total count
        - Pagination info
    """
    try:
        logger.info(f"Clinical trials list request: condition={request.condition}, page={request.page}")

        # Check the shared Mongo cache first, then the process-local tier.
        cache_key = get_cache_key(
            request.condition, request.page, request.page_size, request.status
        )
        persistent_response = await get_persistent_cache(cache_key)
        if persistent_response:
            set_cached_trials(
                request.condition,
                request.page,
                request.page_size,
                persistent_response,
                request.status,
            )
            return persistent_response

        cached_response = get_cached_trials(
            request.condition, request.page, request.page_size, request.status
        )
        if cached_response:
            logger.info("Returning cached clinical trials")
            return cached_response

        # Fetch data from ClinicalTrials.gov
        data = await fetch_clinical_trials(
            condition=request.condition,
            page=request.page,
            page_size=request.page_size,
            status=request.status
        )

        # Keep the list path provider-backed and latency-bounded. Translating
        # every field of every study here makes a page of ten trials fan out
        # into dozens of sequential 27B-model calls, leaving the UI spinner
        # visible for minutes. The list card can render the authoritative
        # ClinicalTrials.gov text directly; the detail endpoint performs the
        # Field-by-field translation is deferred until the user selects a trial.
        studies = data.get("studies", [])
        trials = []

        for study in studies:
            trial = await parse_trial_data(study, translate=False)
            if trial:
                trials.append(trial)

        # Get total count
        total_count = data.get("totalCount", len(trials))

        response = {
            "status": "success",
            "trials": trials,
            "total": total_count,
            "page": request.page,
            "pageSize": request.page_size,
            "totalPages": (total_count + request.page_size - 1) // request.page_size
        }

        # Cache the response
        set_cached_trials(
            request.condition,
            request.page,
            request.page_size,
            response,
            request.status,
        )
        await set_persistent_cache(cache_key, response)

        return response

    except Exception as e:
        stale_response = await get_persistent_stale_cache(
            get_cache_key(request.condition, request.page, request.page_size, request.status)
        )
        if stale_response is None:
            stale_response = get_stale_cached_trials(
            request.condition, request.page, request.page_size, request.status
            )
        if stale_response is not None:
            logger.warning("ClinicalTrials provider failed; returning stale cached response", exc_info=True)
            return {**stale_response, "stale": True}
        logger.error(f"Error in get_clinical_trials: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/detail")
async def get_trial_detail(request: ClinicalTrialDetailRequest) -> Dict[str, Any]:
    """
    Return ClinicalTrials.gov source fields and an optional faithful translation.

    Returns:
        - Original source fields
        - Faithful field-by-field translation, without interpretation
        - Source URL and medical disclaimer
    """
    try:
        logger.info(f"Clinical trial detail request: {request.nct_id}")

        # Fetch trial detail
        data = await fetch_trial_detail(request.nct_id)

        # Preserve the provider text and translate the same fields separately.
        study = data.get("protocolSection", {})
        source_trial = await parse_trial_data({"protocolSection": study}, translate=False)
        translated_trial = (
            await parse_trial_data({"protocolSection": study}, translate=True)
            if request.language == "ko"
            else source_trial
        )

        return {
            "status": "success",
            "trial": source_trial,
            "translation": translated_trial,
            "source": {
                "provider": "ClinicalTrials.gov",
                "url": f"https://clinicaltrials.gov/study/{request.nct_id}",
            },
            "informationOnly": True,
            "disclaimer": (
                "공개 임상시험 정보를 제공하며 개인의 적합성, 참여 자격, 치료 효과를 "
                "판단하거나 추천하지 않습니다. 참여 여부는 담당 의료진 및 시험기관과 상담하세요."
            ),
            "retrievedAt": datetime.now().isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Clinical-trial detail request failed", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search")
async def search_trials(
    condition: str = Query(default="kidney", description="Medical condition to search"),
    status: Optional[str] = Query(default=None, description="Study status filter"),
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=10, ge=1, le=50, description="Results per page")
) -> Dict[str, Any]:
    """
    Search clinical trials (GET endpoint for easy testing)
    """
    request = ClinicalTrialListRequest(
        condition=condition,
        page=page,
        page_size=page_size,
        status=status
    )
    return await get_clinical_trials(request)


# ==================== Health Check ====================

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Test ClinicalTrials.gov API connectivity
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get("https://clinicaltrials.gov/api/v2/stats/size")
            api_status = "connected" if response.status_code == 200 else "error"

        return {
            "status": "healthy",
            "service": "clinical_trials_api",
            "clinicalTrialsGov": api_status,
            "detailContract": "source_and_faithful_translation_only",
        }
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return {
            "status": "degraded",
            "service": "clinical_trials_api",
            "error": str(e)
        }
