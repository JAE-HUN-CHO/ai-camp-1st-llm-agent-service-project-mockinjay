"""
Bookmarks API Router
논문 북마크 API 엔드포인트 - /api/bookmarks
프론트엔드 호환용 별도 라우터 (mypage/bookmarks와 별개)
"""
from fastapi import APIRouter, HTTPException, status, Query, Depends
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime
import logging

from app.api.dependencies import get_current_user, require_user_match
from app.services.mypage.bookmark_service import BookmarkService

logger = logging.getLogger(__name__)
bookmark_service = BookmarkService()

router = APIRouter(prefix="/api/bookmarks", tags=["bookmarks"])


# ==================== Request/Response Models ====================

class BookmarkCreateRequest(BaseModel):
    """북마크 생성 요청 모델"""
    user_id: str
    paper_id: str
    title: str
    authors: Optional[List[str]] = None
    journal: Optional[str] = None
    pub_date: Optional[str] = None
    abstract: Optional[str] = None
    url: Optional[str] = None
    tags: Optional[List[str]] = None
    notes: Optional[str] = None


class NewsBookmarkCreateRequest(BaseModel):
    """Create a bookmark for a real news article returned by the news API."""
    user_id: str
    article_id: str
    title: str
    description: Optional[str] = None
    content: Optional[str] = None
    source: str
    pub_date: str
    image: Optional[str] = None
    link: str
    language: str = "en"


class BookmarkUpdateRequest(BaseModel):
    """북마크 업데이트 요청 모델"""
    tags: Optional[List[str]] = None
    notes: Optional[str] = None


class BookmarkedPaper(BaseModel):
    """북마크된 논문 응답 모델"""
    id: str
    userId: str
    paperId: str
    createdAt: str
    title: str
    authors: List[str] = []
    journal: str = ""
    pubDate: str = ""
    abstract: str = ""
    url: str = ""
    tags: List[str] = []
    notes: str = ""
    bookmarkedAt: str


def _serialize_bookmark(bookmark: dict) -> dict:
    """Expose one stable response shape for canonical and legacy documents."""
    item_type = bookmark.get("itemType", "paper")
    item_id = bookmark.get("itemId") or bookmark.get("paperId") or ""
    item_data = bookmark.get("itemData") or bookmark.get("paperData") or {}
    created_at = bookmark.get("createdAt") or datetime.utcnow().isoformat()
    if isinstance(created_at, datetime):
        created_at = created_at.isoformat()
    if item_type == "news":
        return {
            "id": bookmark.get("id") or str(bookmark.get("_id", "")),
            "userId": bookmark.get("userId", ""),
            "itemType": item_type,
            "itemId": item_id,
            "itemData": item_data,
            "createdAt": created_at,
            "bookmarkedAt": created_at,
        }
    return {
        "id": bookmark.get("id") or str(bookmark.get("_id", "")),
        "userId": bookmark.get("userId", ""),
        "itemType": "paper",
        "itemId": item_id,
        "paperId": item_id,
        "paperData": item_data,
        "createdAt": created_at,
        "title": item_data.get("title", ""),
        "authors": item_data.get("authors", []) or [],
        "journal": item_data.get("journal", "") or "",
        "pubDate": item_data.get("pub_date", item_data.get("pubDate", "")) or "",
        "abstract": item_data.get("abstract", "") or "",
        "url": item_data.get("url", "") or "",
        "tags": item_data.get("tags", []) or [],
        "notes": item_data.get("notes", "") or "",
        "bookmarkedAt": created_at,
    }


# ==================== API Endpoints ====================

@router.get("")
async def get_bookmarks(
    user_id: str = Query(..., description="User ID"),
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0),
    current_user: str = Depends(get_current_user),
):
    """
    사용자의 북마크 목록 조회
    GET /api/bookmarks?user_id={user_id}
    """
    try:
        require_user_match(user_id, current_user)
        result = await bookmark_service.get_bookmarks(current_user, limit, offset, item_type="paper")
        bookmarks = [_serialize_bookmark(bookmark) for bookmark in result["bookmarks"]]

        return {
            "bookmarks": bookmarks,
            "total": result["total"],
            "status": "success"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching bookmarks: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="북마크 조회 중 오류가 발생했습니다"
        )


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_bookmark_endpoint(
    request: BookmarkCreateRequest,
    current_user: str = Depends(get_current_user),
):
    """
    새 북마크 생성
    POST /api/bookmarks
    """
    try:
        require_user_match(request.user_id, current_user)
        logger.info(f"Creating bookmark for user: {current_user}, paper: {request.paper_id}")
        bookmark_data = {
            "title": request.title,
            "authors": request.authors or [],
            "journal": request.journal or "",
            "pub_date": request.pub_date or "",
            "abstract": request.abstract or "",
            "url": request.url or "",
            "tags": request.tags or [],
            "notes": request.notes or "",
        }
        bookmark = await bookmark_service.add_bookmark(current_user, request.paper_id, bookmark_data)
        return {
            "bookmark": _serialize_bookmark(bookmark),
            "status": "success"
        }

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating bookmark: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="북마크 생성 중 오류가 발생했습니다"
        )


@router.get("/news")
async def get_news_bookmarks(
    user_id: str = Query(...),
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0),
    current_user: str = Depends(get_current_user),
):
    require_user_match(user_id, current_user)
    result = await bookmark_service.get_bookmarks(current_user, limit, offset, item_type="news")
    return {
        "bookmarks": [_serialize_bookmark(bookmark) for bookmark in result["bookmarks"]],
        "total": result["total"],
        "status": "success",
    }


@router.post("/news", status_code=status.HTTP_201_CREATED)
async def create_news_bookmark(
    request: NewsBookmarkCreateRequest,
    current_user: str = Depends(get_current_user),
):
    require_user_match(request.user_id, current_user)
    data = {
        "title": request.title,
        "description": request.description,
        "content": request.content,
        "source": request.source,
        "pubDate": request.pub_date,
        "image": request.image,
        "link": request.link,
        "language": request.language,
    }
    bookmark = await bookmark_service.add_bookmark(current_user, request.article_id, data, item_type="news")
    return {"bookmark": _serialize_bookmark(bookmark), "status": "success"}


@router.delete("/news/{bookmark_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_news_bookmark(
    bookmark_id: str,
    current_user: str = Depends(get_current_user),
):
    await bookmark_service.remove_bookmark_by_id(current_user, bookmark_id)
    return None


@router.patch("/{bookmark_id}")
async def update_bookmark_endpoint(
    bookmark_id: str,
    request: BookmarkUpdateRequest,
    current_user: str = Depends(get_current_user),
):
    """
    북마크 업데이트 (메모/태그)
    PATCH /api/bookmarks/{bookmark_id}
    """
    try:
        logger.info(f"Updating bookmark {bookmark_id} for user {current_user}")
        bookmark = await bookmark_service.update_bookmark_by_id(
            current_user,
            bookmark_id,
            {"tags": request.tags, "notes": request.notes},
        )
        return {
            "bookmark": _serialize_bookmark(bookmark),
            "status": "success"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating bookmark: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="북마크 업데이트 중 오류가 발생했습니다"
        )


@router.delete("/{bookmark_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_bookmark_endpoint(
    bookmark_id: str,
    current_user: str = Depends(get_current_user),
):
    """
    북마크 삭제
    DELETE /api/bookmarks/{bookmark_id}

    The database operation is scoped by both bookmark id and JWT subject.
    """
    try:
        logger.info(f"Deleting bookmark {bookmark_id} for user {current_user}")
        await bookmark_service.remove_bookmark_by_id(current_user, bookmark_id)
        return None

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting bookmark: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="북마크 삭제 중 오류가 발생했습니다"
        )
