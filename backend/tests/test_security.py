"""
Unit tests for security utilities.

Tests password hashing and JWT token creation/verification.
"""

import pytest
from datetime import timedelta

from app.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    verify_token
)


def test_password_hashing():
    """Test that password hashing produces different hash."""
    password = "testpassword123"
    hashed = get_password_hash(password)

    assert hashed != password
    assert len(hashed) > 20


def test_password_verification():
    """Test that correct password verifies, incorrect does not."""
    password = "testpassword123"
    hashed = get_password_hash(password)

    assert verify_password(password, hashed) is True
    assert verify_password("wrongpassword", hashed) is False


def test_password_hash_is_unique():
    """Test that same password produces different hashes (salt)."""
    password = "testpassword123"
    hash1 = get_password_hash(password)
    hash2 = get_password_hash(password)

    assert hash1 != hash2
    # Both should still verify
    assert verify_password(password, hash1)
    assert verify_password(password, hash2)


def test_create_and_verify_token():
    """Test JWT token creation and verification."""
    email = "test@example.com"
    token = create_access_token(data={"sub": email})

    assert token is not None
    assert len(token) > 50

    decoded_email = verify_token(token)
    assert decoded_email == email


def test_verify_invalid_token():
    """Test that invalid token returns None."""
    assert verify_token("invalid.token.here") is None
    assert verify_token("") is None


def test_token_with_custom_expiry():
    """Test token creation with custom expiration."""
    email = "test@example.com"
    token = create_access_token(
        data={"sub": email},
        expires_delta=timedelta(minutes=5)
    )

    assert verify_token(token) == email


def test_expired_token():
    """Test that expired token returns None."""
    email = "test@example.com"
    token = create_access_token(
        data={"sub": email},
        expires_delta=timedelta(seconds=-1)  # Already expired
    )

    assert verify_token(token) is None
