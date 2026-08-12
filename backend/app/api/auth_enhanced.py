"""
Enhanced Authentication API Router

Additional authentication endpoints:
- Email/username availability checks
- Password reset flow
- Account management
- Refresh token support (future)
"""

import logging
from collections.abc import Iterable
from datetime import datetime, timedelta, timezone
import secrets

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, HTTPException, status, Depends
from app.db.connection import get_users_collection
from app.services.auth import hash_password, verify_password, get_current_user
from app.models.auth_enhanced import (
    CheckEmailRequest,
    CheckEmailResponse,
    CheckUsernameRequest,
    CheckUsernameResponse,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    ResetPasswordRequest,
    ResetPasswordResponse,
    ChangePasswordRequest,
    ChangePasswordResponse,
    DeleteAccountRequest,
    DeleteAccountResponse,
)
from app.utils.validators import PasswordValidator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth-enhanced"])


# These collections are written by both the current MyPage APIs and older
# compatibility APIs.  Cleanup must cover both ownership field spellings so a
# retry cannot leave user data behind in a legacy collection.
_USER_OWNED_COLLECTIONS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("chat_rooms", ("user_id",)),
    ("conversation_history", ("user_id",)),
    ("bookmarks", ("userId", "user_id")),
    ("user_preferences", ("userId", "user_id")),
    ("notifications", ("userId", "user_id")),
    ("notification_settings", ("userId", "user_id")),
    ("user_context", ("user_id",)),
    ("health_profiles", ("userId", "user_id")),
    ("health_records", ("user_id",)),
    ("health_labs", ("user_id",)),
    ("health_medications", ("user_id",)),
    ("health_vitals", ("user_id",)),
    ("health_symptoms", ("user_id",)),
    ("lab_results", ("user_id",)),
    ("medications", ("user_id",)),
    ("vital_signs", ("user_id",)),
    ("health_events", ("user_id",)),
    ("diet_sessions", ("user_id",)),
    ("diet_meals", ("user_id",)),
    ("diet_goals", ("user_id",)),
    ("meal_logs", ("user_id",)),
    ("nutrition_analyses", ("user_id",)),
    ("user_streaks", ("user_id",)),
    ("points", ("userId", "user_id")),
    ("points_transactions", ("userId", "user_id")),
    ("points_history", ("userId", "user_id")),
    ("user_levels", ("userId", "user_id")),
    ("user_badges", ("userId", "user_id")),
    ("user_points", ("userId", "user_id")),
    ("tokens", ("userId", "user_id")),
    ("token_transactions", ("userId", "user_id")),
)


def _user_id_values(user_id: str) -> list[object]:
    """Return string and ObjectId forms used by legacy user-owned records."""
    values: list[object] = [user_id]
    try:
        values.append(ObjectId(user_id))
    except (InvalidId, TypeError, ValueError):
        pass
    return values


def _ownership_filter(user_id: str, fields: Iterable[str]) -> dict:
    """Build a filter that matches all supported ownership field variants."""
    values = _user_id_values(user_id)
    return {"$or": [{field: {"$in": values}} for field in fields]}


async def _delete_user_owned_data(database, user_id: str) -> None:
    """Delete user-owned records in an idempotent, retry-safe manner."""
    for collection_name, fields in _USER_OWNED_COLLECTIONS:
        await database[collection_name].delete_many(_ownership_filter(user_id, fields))

    # Preserve community moderation history while removing the user's identity.
    community_filter = _ownership_filter(user_id, ("userId",))
    await database["posts"].update_many(
        community_filter,
        {"$set": {"isDeleted": True, "userId": "deleted_user"}},
    )
    await database["comments"].update_many(
        community_filter,
        {"$set": {"isDeleted": True, "userId": "deleted_user"}},
    )

    # Likes and anonymous-number mappings are user-owned auxiliary records.
    auxiliary_filter = _ownership_filter(user_id, ("userId", "user_id"))
    likes_collection = database["likes"]
    affected_post_ids = await likes_collection.distinct("postId", auxiliary_filter)
    await likes_collection.delete_many(auxiliary_filter)

    # `posts.likes` is a denormalized counter maintained by the community API.
    # Recompute it after deleting likes so retries are idempotent and cannot
    # double-decrement the counter.
    for post_id in affected_post_ids:
        remaining_likes = await likes_collection.count_documents({"postId": post_id})
        try:
            post_object_id = post_id if isinstance(post_id, ObjectId) else ObjectId(post_id)
        except (InvalidId, TypeError, ValueError):
            continue
        await database["posts"].update_one(
            {"_id": post_object_id},
            {"$set": {"likes": remaining_likes}},
        )

    await database["post_anonymous_users"].delete_many(auxiliary_filter)


async def _mark_deletion_failed(users_collection, user_id, error: Exception) -> None:
    """Leave a retry marker without persisting sensitive exception details."""
    try:
        await users_collection.update_one(
            {"_id": user_id},
            {
                "$set": {
                    "deletion_status": "failed",
                    "deletion_failed_at": datetime.now(timezone.utc),
                },
                "$unset": {"deletion_error": ""},
            },
        )
    except Exception:
        logger.exception("Failed to persist account deletion failure state")
    logger.error("Account deletion failed and remains retryable: %s", error)


# ============================================
# Email/Username Validation Endpoints
# ============================================

@router.post("/check-email", response_model=CheckEmailResponse)
async def check_email_availability(request: CheckEmailRequest) -> CheckEmailResponse:
    """
    Check if email is available for registration.

    This endpoint allows the frontend to check email availability
    before the user submits the registration form.

    Args:
        request: Email to check

    Returns:
        CheckEmailResponse: Availability status and message
    """
    users_collection = get_users_collection()

    # Check if email exists
    existing_user = await users_collection.find_one({"email": request.email})

    if existing_user:
        return CheckEmailResponse(
            available=False,
            message="이 이메일은 이미 사용 중입니다",
            suggestions=None
        )

    return CheckEmailResponse(
        available=True,
        message="사용 가능한 이메일입니다",
        suggestions=None
    )


@router.post("/check-username", response_model=CheckUsernameResponse)
async def check_username_availability(request: CheckUsernameRequest) -> CheckUsernameResponse:
    """
    Check if username is available for registration.

    This endpoint allows the frontend to check username availability
    before the user submits the registration form.

    Args:
        request: Username to check

    Returns:
        CheckUsernameResponse: Availability status and message
    """
    users_collection = get_users_collection()

    # Check if username exists
    existing_user = await users_collection.find_one({"username": request.username})

    if existing_user:
        # Generate suggestions by appending numbers
        base_username = request.username
        suggestions = [
            f"{base_username}{i}" for i in range(1, 4)
        ]

        return CheckUsernameResponse(
            available=False,
            message="이 사용자명은 이미 사용 중입니다",
            suggestions=suggestions
        )

    return CheckUsernameResponse(
        available=True,
        message="사용 가능한 사용자명입니다",
        suggestions=None
    )


# ============================================
# Password Reset Flow
# ============================================

@router.post("/forgot-password", response_model=ForgotPasswordResponse)
async def forgot_password(request: ForgotPasswordRequest) -> ForgotPasswordResponse:
    """
    Initiate password reset flow.

    Generates a password reset token and sends it to the user's email.

    NOTE: Email sending is not implemented in this version. In production,
    you would send an email with the reset link.

    Args:
        request: User's email address

    Returns:
        ForgotPasswordResponse: Success status
    """
    users_collection = get_users_collection()

    # Find user by email
    user = await users_collection.find_one({"email": request.email})

    # For security, always return success even if email doesn't exist
    # This prevents email enumeration attacks
    if not user:
        logger.info(f"Password reset requested for non-existent email: {request.email}")
        return ForgotPasswordResponse(
            success=True,
            message="비밀번호 재설정 링크가 이메일로 전송되었습니다 (이메일이 등록되어 있는 경우)",
            reset_token_sent=False
        )

    # Generate reset token
    reset_token = secrets.token_urlsafe(32)
    reset_token_expires = datetime.utcnow() + timedelta(hours=1)

    # Save token to database
    await users_collection.update_one(
        {"_id": user["_id"]},
        {
            "$set": {
                "reset_token": reset_token,
                "reset_token_expires": reset_token_expires
            }
        }
    )

    logger.info(f"Password reset token generated for user {user['_id']}")

    # TODO: Send email with reset link
    # reset_link = f"https://careguide.com/reset-password?token={reset_token}"
    # send_email(user["email"], "Password Reset", reset_link)

    return ForgotPasswordResponse(
        success=True,
        message="비밀번호 재설정 링크가 이메일로 전송되었습니다",
        reset_token_sent=True
    )


@router.post("/reset-password", response_model=ResetPasswordResponse)
async def reset_password(request: ResetPasswordRequest) -> ResetPasswordResponse:
    """
    Reset password using reset token.

    Validates the reset token and sets a new password.

    Args:
        request: Reset token and new password

    Returns:
        ResetPasswordResponse: Success status
    """
    users_collection = get_users_collection()

    # Validate password
    password_valid, password_errors = PasswordValidator.validate(request.new_password)
    if not password_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "비밀번호가 요구사항을 충족하지 않습니다",
                "errors": password_errors,
                "requirements": PasswordValidator.get_requirements_text()
            }
        )

    # Find user with valid reset token
    user = await users_collection.find_one({
        "reset_token": request.token,
        "reset_token_expires": {"$gt": datetime.utcnow()}
    })

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="유효하지 않거나 만료된 재설정 토큰입니다"
        )

    # Update password and clear reset token
    hashed_password = hash_password(request.new_password)

    await users_collection.update_one(
        {"_id": user["_id"]},
        {
            "$set": {
                "password": hashed_password,
                "updated_at": datetime.utcnow()
            },
            "$unset": {
                "reset_token": "",
                "reset_token_expires": ""
            }
        }
    )

    logger.info(f"Password reset successful for user {user['_id']}")

    return ResetPasswordResponse(
        success=True,
        message="비밀번호가 성공적으로 재설정되었습니다"
    )


# ============================================
# Password Change (Authenticated)
# ============================================

@router.post("/change-password", response_model=ChangePasswordResponse)
async def change_password(
    request: ChangePasswordRequest,
    current_user: dict = Depends(get_current_user)
) -> ChangePasswordResponse:
    """
    Change password for authenticated user.

    Requires current password for verification.

    Args:
        request: Current password and new password
        current_user: Current authenticated user from JWT

    Returns:
        ChangePasswordResponse: Success status
    """
    users_collection = get_users_collection()

    # Verify current password
    if not verify_password(request.current_password, current_user["password"]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="현재 비밀번호가 올바르지 않습니다"
        )

    # Validate new password
    password_valid, password_errors = PasswordValidator.validate(request.new_password)
    if not password_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "비밀번호가 요구사항을 충족하지 않습니다",
                "errors": password_errors,
                "requirements": PasswordValidator.get_requirements_text()
            }
        )

    # Check that new password is different from current
    if verify_password(request.new_password, current_user["password"]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="새 비밀번호는 현재 비밀번호와 달라야 합니다"
        )

    # Update password
    hashed_password = hash_password(request.new_password)

    await users_collection.update_one(
        {"_id": current_user["_id"]},
        {
            "$set": {
                "password": hashed_password,
                "updated_at": datetime.utcnow()
            }
        }
    )

    logger.info(f"Password changed successfully for user {current_user['_id']}")

    return ChangePasswordResponse(
        success=True,
        message="비밀번호가 성공적으로 변경되었습니다"
    )


# ============================================
# Account Deletion
# ============================================

@router.delete("/account", response_model=DeleteAccountResponse)
async def delete_account(
    request: DeleteAccountRequest,
    current_user: dict = Depends(get_current_user)
) -> DeleteAccountResponse:
    """
    Delete user account.

    This is a destructive operation that permanently deletes the user
    and all associated data. Requires password confirmation.

    Args:
        request: Password and confirmation
        current_user: Current authenticated user from JWT

    Returns:
        DeleteAccountResponse: Success status and data export URL
    """
    users_collection = get_users_collection()

    # Verify password
    if not verify_password(request.password, current_user["password"]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="비밀번호가 올바르지 않습니다"
        )

    user_id = str(current_user["_id"])

    # TODO: Export user data before deletion (GDPR compliance)
    # data_export_url = await export_user_data(user_id)

    # Mark the operation before cleanup.  If the process or a database call
    # fails, the user record remains available so the same request can retry
    # the idempotent cleanup instead of leaving an orphaned partial deletion.
    try:
        await users_collection.update_one(
            {"_id": current_user["_id"]},
            {
                "$set": {
                    "deletion_status": "in_progress",
                    "deletion_started_at": datetime.now(timezone.utc),
                },
                "$unset": {"deletion_failed_at": "", "deletion_error": ""},
            },
        )

        from app.db.connection import db
        await _delete_user_owned_data(db, user_id)

        # Delete the identity last.  All dependent cleanup above is safe to
        # repeat if this request is retried after a transient failure.
        await users_collection.delete_one({"_id": current_user["_id"]})

        logger.info(f"Account deleted successfully for user {user_id}")

        return DeleteAccountResponse(
            success=True,
            message="계정이 성공적으로 삭제되었습니다",
            data_export_url=None  # TODO: Implement data export
        )

    except Exception as e:
        await _mark_deletion_failed(users_collection, current_user["_id"], e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="계정 삭제 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요"
        )


# ============================================
# Health Check
# ============================================

@router.get("/health")
async def health_check():
    """Health check endpoint for Enhanced Auth API"""
    return {
        "status": "healthy",
        "service": "auth_enhanced_api",
        "endpoints": {
            "check_email": "ready",
            "check_username": "ready",
            "forgot_password": "ready",
            "reset_password": "ready",
            "change_password": "ready",
            "delete_account": "ready"
        }
    }
