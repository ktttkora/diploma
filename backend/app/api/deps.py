"""
API dependencies module.

Provides reusable dependencies for FastAPI endpoints.
"""

from typing import Optional
from fastapi import Depends, HTTPException, Query, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.core.security import verify_token


# OAuth2 scheme for token extraction
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def _load_user_by_token(token: Optional[str], db: Session) -> User:
    """
    Resolve a user from a JWT token.

    Args:
        token: JWT token, or None
        db: Database session

    Returns:
        User instance

    Raises:
        HTTPException 401: If the token is missing, invalid, or unknown
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not token:
        raise credentials_exception

    email = verify_token(token)
    if email is None:
        raise credentials_exception

    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise credentials_exception

    return user


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """
    Get the authenticated user from the Authorization header.

    Args:
        token: JWT token from the Authorization header
        db: Database session

    Returns:
        User object

    Example:
        @app.get("/me")
        def get_me(user: User = Depends(get_current_user)):
            return {"email": user.email}
    """
    return _load_user_by_token(token, db)


def get_current_user_media(
    request: Request,
    token: Optional[str] = Query(
        None,
        description="JWT token, for media elements that cannot set headers"
    ),
    db: Session = Depends(get_db)
) -> User:
    """
    Get the authenticated user for a media request.

    <video> and <img> cannot send an Authorization header, so these
    endpoints also accept the token as a query parameter.

    Args:
        request: Incoming request
        token: JWT token from the query string
        db: Database session

    Returns:
        User object
    """
    if not token:
        header = request.headers.get("Authorization", "")
        if header.lower().startswith("bearer "):
            token = header[7:].strip()

    return _load_user_by_token(token, db)


def get_current_user_optional(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Get the current user if authenticated, otherwise None.

    Args:
        token: JWT token from the Authorization header (optional)
        db: Database session

    Returns:
        User object if authenticated, None otherwise
    """
    if token is None:
        return None

    try:
        return _load_user_by_token(token, db)
    except HTTPException:
        return None
