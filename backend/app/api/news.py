"""
News API Router
Handles kidney/health-related news from multiple sources:
1. GNews API (free tier: 100 requests/day)
2. RSS Feeds (unlimited, no API key required)
3. NewsData.io (fallback, 200 requests/day)
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import logging
import httpx
from datetime import datetime
import os
from dotenv import load_dotenv
import hashlib
import asyncio
import xml.etree.ElementTree as ET
from app.api.dependencies import require_admin
from app.db.connection import db
from app.config import settings
from jose import JWTError, jwt

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/news", tags=["news"])

# API Configuration
GNEWS_API_KEY = os.getenv("GNEWS_API_KEY", "")
GNEWS_BASE_URL = "https://gnews.io/api/v4/search"

NEWSDATA_API_KEY = os.getenv("NEWSDATA_API_KEY", "")
NEWSDATA_BASE_URL = "https://newsdata.io/api/1/news"

# RSS Feed URLs - Health/Kidney related
RSS_FEEDS = {
    "en": [
        # Medical News Today
        "https://www.medicalnewstoday.com/rss",
        # ScienceDaily Health
        "https://www.sciencedaily.com/rss/health_medicine.xml",
        # NIH News
        "https://www.nih.gov/rss/news_releases.xml",
        # WebMD Health News
        "https://rssfeeds.webmd.com/rss/rss.aspx?RSSSource=RSS_PUBLIC",
    ],
    "ko": [
        # Korean Health News RSS feeds
        "https://news.google.com/rss/search?q=%EC%8B%A0%EC%9E%A5+%EA%B1%B4%EA%B0%95&hl=ko&gl=KR&ceid=KR:ko",
        "https://news.google.com/rss/search?q=%EB%A7%8C%EC%84%B1%EC%8B%A0%EC%9E%A5%EC%A7%88%ED%99%98&hl=ko&gl=KR&ceid=KR:ko",
    ]
}

# In-memory cache for news
_news_cache: Dict[str, Dict[str, Any]] = {}
CACHE_TTL = 6 * 3600  # Cache for 6 hours


# ==================== Cache Helper Functions ====================

def get_cache_key(source: str, language: str, page: int) -> str:
    """Generate cache key for news query"""
    return f"{source}:{language}:{page}"


def is_cache_valid(timestamp: float) -> bool:
    """Check if cache is still valid"""
    return (datetime.now().timestamp() - timestamp) < CACHE_TTL


def get_cached_news(source: str, language: str, page: int) -> Optional[Dict[str, Any]]:
    """Get cached news if available and valid"""
    cache_key = get_cache_key(source, language, page)
    if cache_key in _news_cache:
        cached_data = _news_cache[cache_key]
        if is_cache_valid(cached_data["timestamp"]):
            logger.info(f"Cache hit for news: {cache_key}")
            return cached_data["data"]
        else:
            del _news_cache[cache_key]
            logger.info(f"Cache expired for news: {cache_key}")
    return None


def set_cached_news(source: str, language: str, page: int, data: Dict[str, Any]):
    """Cache news data"""
    cache_key = get_cache_key(source, language, page)
    _news_cache[cache_key] = {
        "data": data,
        "timestamp": datetime.now().timestamp()
    }
    logger.info(f"Cached news: {cache_key}")


def _optional_request_user_id(request: Request) -> str | None:
    """Read an optional bearer subject on this intentionally public route."""
    state_user_id = getattr(getattr(request, "state", None), "user_id", None)
    if state_user_id:
        return str(state_user_id)
    authorization = request.headers.get("Authorization", "")
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            return None
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        user_id = payload.get("user_id")
        return str(user_id) if user_id else None
    except (ValueError, JWTError, TypeError):
        return None


# ==================== Request/Response Models ====================

class NewsRequest(BaseModel):
    """Request model for news search"""
    query: str = Field(default="kidney disease", description="Search query")
    language: str = Field(default="en", description="Language code (ko, en)")
    page: int = Field(default=1, ge=1, description="Page number")
    page_size: int = Field(default=10, ge=1, le=50, description="Results per page")
    source: str = Field(default="auto", description="News source: auto, gnews, rss, newsdata")


class NewsArticle(BaseModel):
    """Single news article"""
    id: str
    title: str
    titleOriginal: Optional[str] = None  # Original title (for translation feature)
    description: Optional[str] = None
    descriptionOriginal: Optional[str] = None  # Original description
    content: Optional[str] = None
    source: str
    sourceIcon: Optional[str] = None
    pubDate: str
    time: str  # Relative time like "2 hours ago"
    image: Optional[str] = None
    link: str
    category: Optional[List[str]] = None
    language: str = "en"  # Article language


class NewsResponse(BaseModel):
    """Response model for news list"""
    articles: List[NewsArticle]
    totalResults: int
    status: str
    nextPage: Optional[str] = None
    cached: bool = False
    sourceUsed: str = "unknown"  # Which source was used


# ==================== Helper Functions ====================

def format_relative_time(pub_date: str, language: str = "en") -> str:
    """Convert publication date to relative time string"""
    try:
        # Try various date formats
        dt = None
        for fmt in [
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%d %H:%M:%S",
            "%a, %d %b %Y %H:%M:%S %z",
            "%a, %d %b %Y %H:%M:%S GMT",
            "%Y-%m-%d",
        ]:
            try:
                dt = datetime.strptime(pub_date.split("+")[0].strip(), fmt.replace(" %z", ""))
                break
            except ValueError:
                continue

        if not dt:
            return pub_date

        now = datetime.now()
        diff = now - dt

        if language == "ko":
            if diff.days == 0:
                hours = diff.seconds // 3600
                if hours == 0:
                    minutes = diff.seconds // 60
                    return f"{minutes}분 전" if minutes > 0 else "방금 전"
                return f"{hours}시간 전"
            elif diff.days == 1:
                return "1일 전"
            elif diff.days < 7:
                return f"{diff.days}일 전"
            elif diff.days < 30:
                weeks = diff.days // 7
                return f"{weeks}주 전"
            else:
                months = diff.days // 30
                return f"{months}개월 전"
        else:
            if diff.days == 0:
                hours = diff.seconds // 3600
                if hours == 0:
                    minutes = diff.seconds // 60
                    return f"{minutes}m ago" if minutes > 0 else "just now"
                return f"{hours}h ago"
            elif diff.days == 1:
                return "1 day ago"
            elif diff.days < 7:
                return f"{diff.days} days ago"
            elif diff.days < 30:
                weeks = diff.days // 7
                return f"{weeks}w ago"
            else:
                months = diff.days // 30
                return f"{months}mo ago"

    except Exception:
        return pub_date


def generate_article_id(article: Dict[str, Any]) -> str:
    """Generate unique ID for article"""
    unique_str = f"{article.get('title', '')}{article.get('pubDate', '')}{article.get('source', '')}"
    return hashlib.md5(unique_str.encode()).hexdigest()[:12]


# ==================== RSS Feed Parser ====================

async def fetch_rss_feed(url: str, timeout: float = 10.0) -> List[Dict[str, Any]]:
    """Fetch and parse an RSS feed"""
    articles = []

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(url, follow_redirects=True)

        if response.status_code != 200:
            logger.warning(f"RSS feed {url} returned status {response.status_code}")
            return []

        # Parse XML
        root = ET.fromstring(response.text)

        # Handle different RSS formats
        items = root.findall(".//item") or root.findall(".//{http://www.w3.org/2005/Atom}entry")

        for item in items[:15]:  # Limit to 15 per feed
            # Standard RSS
            title = item.findtext("title") or item.findtext("{http://www.w3.org/2005/Atom}title") or ""
            description = item.findtext("description") or item.findtext("{http://www.w3.org/2005/Atom}summary") or ""
            link = item.findtext("link") or ""

            # Try to get link from Atom format
            if not link:
                link_elem = item.find("{http://www.w3.org/2005/Atom}link")
                if link_elem is not None:
                    link = link_elem.get("href", "")

            pub_date = item.findtext("pubDate") or item.findtext("{http://www.w3.org/2005/Atom}published") or ""

            # Get source
            source = item.findtext("source") or ""
            if not source:
                # Try to extract from URL
                from urllib.parse import urlparse
                parsed = urlparse(url)
                source = parsed.netloc.replace("www.", "").replace("rss.", "")

            # Get image (if available)
            image = None
            media_content = item.find("{http://search.yahoo.com/mrss/}content")
            if media_content is not None:
                image = media_content.get("url")

            enclosure = item.find("enclosure")
            if enclosure is not None and not image:
                if enclosure.get("type", "").startswith("image"):
                    image = enclosure.get("url")

            if title:
                articles.append({
                    "title": title.strip(),
                    "description": description.strip()[:500] if description else None,
                    "link": link.strip(),
                    "pubDate": pub_date,
                    "source": source,
                    "image": image,
                })

    except ET.ParseError as e:
        logger.warning(f"XML parse error for {url}: {e}")
    except Exception as e:
        logger.warning(f"Error fetching RSS {url}: {e}")

    return articles


async def fetch_all_rss_feeds(language: str = "en") -> List[NewsArticle]:
    """Fetch news from all RSS feeds for a language"""
    feeds = RSS_FEEDS.get(language, RSS_FEEDS["en"])

    # Fetch all feeds concurrently
    tasks = [fetch_rss_feed(url) for url in feeds]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    all_articles = []
    for result in results:
        if isinstance(result, list):
            all_articles.extend(result)

    # Convert to NewsArticle and deduplicate
    seen_titles = set()
    news_articles = []

    for article in all_articles:
        title = article.get("title", "")
        if title and title not in seen_titles:
            seen_titles.add(title)
            news_articles.append(NewsArticle(
                id=generate_article_id(article),
                title=title,
                titleOriginal=title,
                description=article.get("description"),
                descriptionOriginal=article.get("description"),
                source=article.get("source", "RSS"),
                pubDate=article.get("pubDate", ""),
                time=format_relative_time(article.get("pubDate", ""), language),
                image=article.get("image"),
                link=article.get("link", "#"),
                language=language,
            ))

    # Sort by date (newest first)
    news_articles.sort(key=lambda x: x.pubDate, reverse=True)

    return news_articles[:20]  # Return top 20


# ==================== GNews API ====================

async def fetch_gnews(query: str, language: str = "en", max_results: int = 10) -> List[NewsArticle]:
    """Fetch news from GNews API"""
    if not GNEWS_API_KEY:
        logger.warning("GNEWS_API_KEY not set")
        return []

    try:
        # GNews language codes
        lang_map = {"ko": "ko", "en": "en"}
        country_map = {"ko": "kr", "en": "us"}

        params = {
            "apikey": GNEWS_API_KEY,
            "q": query,
            "lang": lang_map.get(language, "en"),
            "country": country_map.get(language, "us"),
            "max": max_results,
            "in": "title,description",
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(GNEWS_BASE_URL, params=params)

        if response.status_code != 200:
            logger.error(f"GNews API error: {response.status_code}")
            return []

        data = response.json()
        articles = []

        for item in data.get("articles", []):
            articles.append(NewsArticle(
                id=generate_article_id({"title": item.get("title", ""), "pubDate": item.get("publishedAt", ""), "source": item.get("source", {}).get("name", "")}),
                title=item.get("title", ""),
                titleOriginal=item.get("title"),
                description=item.get("description"),
                descriptionOriginal=item.get("description"),
                content=item.get("content"),
                source=item.get("source", {}).get("name", "Unknown"),
                sourceIcon=None,
                pubDate=item.get("publishedAt", ""),
                time=format_relative_time(item.get("publishedAt", ""), language),
                image=item.get("image"),
                link=item.get("url", "#"),
                language=language,
            ))

        return articles

    except Exception as e:
        logger.error(f"GNews API error: {e}")
        return []


# ==================== NewsData.io API ====================

async def fetch_newsdata(query: str, language: str = "en", page_size: int = 10) -> List[NewsArticle]:
    """Fetch news from NewsData.io API"""
    if not NEWSDATA_API_KEY:
        logger.warning("NEWSDATA_API_KEY not set")
        return []

    try:
        search_queries = {
            "ko": "신장 OR 만성신장질환 OR 투석 OR 신장이식 OR CKD",
            "en": "kidney OR chronic kidney disease OR dialysis OR kidney transplant OR CKD"
        }
        search_query = search_queries.get(language, search_queries["en"])

        params = {
            "apikey": NEWSDATA_API_KEY,
            "q": search_query,
            "language": language,
            "category": "health",
            "size": page_size,
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(NEWSDATA_BASE_URL, params=params)

        if response.status_code != 200:
            logger.error(f"NewsData API error: {response.status_code}")
            return []

        data = response.json()

        if data.get("status") != "success":
            return []

        articles = []
        for result in data.get("results", []):
            articles.append(NewsArticle(
                id=generate_article_id(result),
                title=result.get("title", ""),
                titleOriginal=result.get("title"),
                description=result.get("description"),
                descriptionOriginal=result.get("description"),
                content=result.get("content"),
                source=result.get("source_name", result.get("source_id", "Unknown")),
                sourceIcon=result.get("source_icon"),
                pubDate=result.get("pubDate", ""),
                time=format_relative_time(result.get("pubDate", ""), language),
                image=result.get("image_url"),
                link=result.get("link", "#"),
                category=result.get("category", []),
                language=language,
            ))

        return articles

    except Exception as e:
        logger.error(f"NewsData API error: {e}")
        return []


# ==================== API Endpoints ====================

@router.post("/list", response_model=NewsResponse)
async def get_news_list(request: NewsRequest):
    """
    Get kidney/health related news articles from multiple sources

    Sources tried in order (auto mode):
    1. GNews API (if API key available)
    2. RSS Feeds (always available)
    3. NewsData.io (if API key available)
    If no configured provider returns data, the endpoint reports an
    explicit upstream-unavailable error instead of fabricating articles.
    """
    try:
        # Check cache first
        cached = get_cached_news(request.source, request.language, request.page)
        if cached:
            cached["cached"] = True
            return NewsResponse(**cached)

        articles: List[NewsArticle] = []
        source_used = "unknown"

        # Determine which source to use
        if request.source == "gnews" or (request.source == "auto" and GNEWS_API_KEY):
            # Try GNews first
            query = "kidney health" if request.language == "en" else "신장 건강"
            articles = await fetch_gnews(query, request.language, request.page_size)
            if articles:
                source_used = "gnews"

        if not articles and (request.source == "rss" or request.source == "auto"):
            # Try RSS feeds
            articles = await fetch_all_rss_feeds(request.language)
            if articles:
                source_used = "rss"

        if not articles and (request.source == "newsdata" or request.source == "auto"):
            # Try NewsData.io
            articles = await fetch_newsdata(request.query, request.language, request.page_size)
            if articles:
                source_used = "newsdata"

        if not articles:
            raise HTTPException(
                status_code=503,
                detail="뉴스 제공자가 기사를 반환하지 않았습니다. 잠시 후 다시 시도해 주세요.",
            )

        response_data = {
            "articles": articles[:request.page_size],
            "totalResults": len(articles),
            "status": "success",
            "nextPage": None,
            "cached": False,
            "sourceUsed": source_used,
        }

        # Cache the response
        set_cached_news(request.source, request.language, request.page, response_data)

        return NewsResponse(**response_data)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching news: {e}", exc_info=True)
        raise HTTPException(
            status_code=502,
            detail="외부 뉴스 제공자와 통신하지 못했습니다.",
        )


@router.get("/detail/{article_id}", response_model=NewsArticle)
async def get_news_detail(article_id: str, request: Request, language: str = "en"):
    """Return an article from the live provider/cache by its stable article id."""
    for cached in _news_cache.values():
        if not is_cache_valid(cached["timestamp"]):
            continue
        for article in cached["data"].get("articles", []):
            article_id_value = article.id if isinstance(article, NewsArticle) else article.get("id")
            if article_id_value == article_id:
                return article if isinstance(article, NewsArticle) else NewsArticle(**article)

    # A saved article must remain viewable even after the provider rotates it
    # out of the live feed. Only consult the bookmark owned by the request user.
    user_id = _optional_request_user_id(request)
    if user_id:
        try:
            saved = await db["bookmarks"].find_one({
                "$and": [
                    {"$or": [{"userId": user_id}, {"user_id": user_id}]},
                    {"$or": [
                        {"itemType": "news", "itemId": article_id},
                        {"itemType": {"$exists": False}, "articleId": article_id},
                    ]},
                ]
            })
            if saved:
                data = saved.get("itemData") or saved.get("articleData") or {}
                if data:
                    pub_date = data.get("pubDate") or data.get("pub_date") or saved.get("createdAt") or ""
                    return NewsArticle(
                        id=article_id,
                        title=data.get("title", ""),
                        titleOriginal=data.get("titleOriginal"),
                        description=data.get("description"),
                        descriptionOriginal=data.get("descriptionOriginal"),
                        content=data.get("content"),
                        source=data.get("source", ""),
                        sourceIcon=data.get("sourceIcon"),
                        pubDate=str(pub_date),
                        time=data.get("time") or str(pub_date),
                        image=data.get("image"),
                        link=data.get("link", ""),
                        category=data.get("category"),
                        language=data.get("language") or language,
                    )
        except Exception as exc:
            logger.warning("Saved news fallback failed for %s: %s", article_id, exc)

    try:
        query = "kidney health" if language == "en" else "신장 건강"
        if GNEWS_API_KEY:
            for article in await fetch_gnews(query, language, 50):
                if article.id == article_id:
                    return article
        for article in await fetch_all_rss_feeds(language):
            if article.id == article_id:
                return article
        if NEWSDATA_API_KEY:
            for article in await fetch_newsdata(query, language, 50):
                if article.id == article_id:
                    return article
    except Exception as exc:
        logger.error("Error fetching news detail: %s", exc, exc_info=True)
        raise HTTPException(status_code=502, detail="외부 뉴스 제공자와 통신하지 못했습니다.") from exc
    raise HTTPException(status_code=404, detail="뉴스 기사를 찾을 수 없습니다.")


@router.get("/health")
async def health_check():
    """Health check endpoint for news API"""
    return {
        "status": "healthy",
        "service": "news_api",
        "gnews_configured": bool(GNEWS_API_KEY),
        "newsdata_configured": bool(NEWSDATA_API_KEY),
        "rss_feeds_available": len(RSS_FEEDS.get("en", [])) + len(RSS_FEEDS.get("ko", [])),
        "cache_entries": len(_news_cache)
    }


@router.post("/clear-cache")
async def clear_cache(admin_user_id: str = Depends(require_admin)):
    """Clear news cache (admin endpoint)"""
    global _news_cache
    count = len(_news_cache)
    _news_cache = {}
    return {"status": "success", "cleared_entries": count}


@router.get("/sources")
async def get_available_sources():
    """Get list of available news sources"""
    return {
        "sources": [
            {
                "id": "auto",
                "name": "Auto (Best Available)",
                "description": "Automatically selects the best available source",
                "available": True,
            },
            {
                "id": "gnews",
                "name": "GNews API",
                "description": "Global news aggregator",
                "available": bool(GNEWS_API_KEY),
            },
            {
                "id": "rss",
                "name": "RSS Feeds",
                "description": "Direct RSS feeds from medical news sites",
                "available": True,
            },
            {
                "id": "newsdata",
                "name": "NewsData.io",
                "description": "News data API",
                "available": bool(NEWSDATA_API_KEY),
            },
        ],
        "languages": [
            {"code": "en", "name": "English"},
            {"code": "ko", "name": "한국어"},
        ]
    }
