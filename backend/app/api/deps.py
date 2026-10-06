from typing import List, Callable
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.core.security import decode_access_token
from app.db.session import get_master_db, get_tenant_session
from app.models.auth import User

security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_master_db)
) -> User:
    """
    Validates JWT token, extracts identity claims, and fetches user from Master DB.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials or token expired",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(credentials.credentials)
        user_id = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except Exception:
        raise credentials_exception

    user = db.query(User).filter(User.user_id == user_id, User.is_active == True).first()
    if user is None:
        raise credentials_exception
    return user


def require_role(allowed_roles: List[str]) -> Callable:
    """
    RBAC Dependency Guard: Enforces that the authenticated user possesses an authorized role.
    Rejects unauthorized access with HTTP 403 Forbidden.
    """
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: Requires one of roles {allowed_roles}, but user has '{current_user.role}'"
            )
        return current_user

    return role_checker


def get_current_tenant_db(
    current_user: User = Depends(get_current_user)
):
    """
    Dependency that provides an active SQLAlchemy Session connected to the
    authenticated employee's private tenant database (e.g. tenant_<slug>_db).
    """
    db_name = current_user.tenant.db_name
    session = get_tenant_session(db_name)
    try:
        yield session
    finally:
        session.close()

