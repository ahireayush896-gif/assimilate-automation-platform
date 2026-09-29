import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Union
import jwt
from passlib.context import CryptContext
from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain password against the salted bcrypt hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Generates a salted bcrypt hash for the password."""
    return pwd_context.hash(password)


def create_access_token(
    subject: Union[str, Any],
    tenant_id: str,
    tenant_slug: str,
    db_name: str,
    role: str,
    employee_id: str,
    email: str,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Creates a signed JWT with full tenant and RBAC role claims.
    """
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode = {
        "sub": str(subject),
        "tenant_id": str(tenant_id),
        "tenant_slug": tenant_slug,
        "db_name": db_name,
        "role": role,
        "employee_id": employee_id,
        "email": email,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }

    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Dict[str, Any]:
    """
    Decodes and validates a JWT token signature and expiration.
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except jwt.PyJWTError as e:
        raise ValueError(f"Invalid or expired token: {str(e)}")


def generate_activation_token(user_id: str) -> str:
    """
    Generates a secure, cryptographically random activation token for user invitations.
    """
    random_bytes = secrets.token_hex(16)
    signature = hmac.new(
        settings.JWT_SECRET_KEY.encode(),
        f"{user_id}:{random_bytes}".encode(),
        hashlib.sha256
    ).hexdigest()
    return f"{random_bytes}_{signature}"
