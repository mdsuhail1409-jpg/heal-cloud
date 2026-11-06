"""
Cryptographic Security, Password Hashing, JWT Tokens and Rate Limiting Guardrails
"""

import time
import uuid
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timedelta, timezone
import bcrypt
import jwt

from app.core.config import settings
from app.core.exceptions import UnauthorizedException, RateLimitException


# In-memory sliding window rate limiter for authentication attempts
_login_attempt_history: Dict[str, List[float]] = {}


def get_password_hash(password: str) -> str:
    """Generate a secure salted bcrypt hash for a plaintext password."""
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a salted bcrypt hash."""
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except Exception:
        return False


def create_access_token(
    subject: Union[str, uuid.UUID],
    expires_delta: Optional[timedelta] = None,
    extra_claims: Optional[Dict[str, Any]] = None,
) -> str:
    """Create a cryptographically signed JWT access token."""
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    payload: Dict[str, Any] = {
        "sub": str(subject),
        "exp": int(expire.timestamp()),
        "iat": int(now.timestamp()),
        "jti": str(uuid.uuid4()),
        "type": "access",
    }
    if extra_claims:
        payload.update(extra_claims)

    encoded_jwt = jwt.encode(
        payload,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
    return encoded_jwt


def decode_access_token(token: str) -> Dict[str, Any]:
    """
    Decode and cryptographically verify a JWT access token.
    Raises UnauthorizedException if signature invalid, token expired, or malformed.
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            options={"require": ["exp", "sub"]},
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise UnauthorizedException("Access token has expired. Please authenticate again.")
    except (jwt.InvalidTokenError, Exception) as exc:
        raise UnauthorizedException(f"Invalid access token credentials: {str(exc)}")


def check_login_rate_limit(key: str) -> None:
    """
    Check if a key (e.g. email or client IP) has breached failed login rate limits.
    Raises RateLimitException if attempts exceed threshold.
    """
    now = time.time()
    window = settings.RATE_LIMIT_LOGIN_WINDOW_SECONDS
    max_attempts = settings.RATE_LIMIT_LOGIN_ATTEMPTS

    if key in _login_attempt_history:
        # Prune timestamps outside current sliding window
        valid_attempts = [ts for ts in _login_attempt_history[key] if now - ts < window]
        _login_attempt_history[key] = valid_attempts

        if len(valid_attempts) >= max_attempts:
            retry_after = int(window - (now - valid_attempts[0]))
            raise RateLimitException(
                f"Too many failed login attempts. Account temporarily locked for {max_attempts} attempts. Try again in {max(1, retry_after)} seconds."
            )


def record_login_failure(key: str) -> None:
    """Record a failed login attempt timestamp."""
    now = time.time()
    if key not in _login_attempt_history:
        _login_attempt_history[key] = []
    _login_attempt_history[key].append(now)


def reset_login_failures(key: str) -> None:
    """Reset failed login attempts upon successful authentication."""
    if key in _login_attempt_history:
        del _login_attempt_history[key]
