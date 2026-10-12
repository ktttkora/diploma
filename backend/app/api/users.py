"""
User profile API endpoints.

Provides user profile management functionality.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.schemas.user import UserResponse, UserUpdate
from app.api.deps import get_current_user
from app.core.security import get_password_hash


router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("/me", response_model=UserResponse)
def get_me(
    current_user: User = Depends(get_current_user)
):
    """
    Get current user profile.

    Args:
        current_user: Authenticated user from JWT token

    Returns:
        Current user object
    """
    return current_user


@router.put("/me", response_model=UserResponse)
def update_me(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update current user profile.

    Args:
        user_update: Updated user data (email and/or password)
        current_user: Authenticated user from JWT token
        db: Database session

    Returns:
        Updated user object

    Raises:
        HTTPException 400: If new email already exists
    """
    # Update email if provided
    if user_update.email is not None:
        # Check if new email already exists
        existing_user = db.query(User).filter(
            User.email == user_update.email,
            User.id != current_user.id
        ).first()

        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )

        current_user.email = user_update.email

    # Update password if provided
    if user_update.password is not None:
        current_user.hashed_password = get_password_hash(user_update.password)

    db.commit()
    db.refresh(current_user)

    return current_user


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_me(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete current user account.

    This will also delete all related videos, analyses, and errors (CASCADE).

    Args:
        current_user: Authenticated user from JWT token
        db: Database session

    Returns:
        No content (204)
    """
    db.delete(current_user)
    db.commit()

    return None
