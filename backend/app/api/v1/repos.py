import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_role, get_current_tenant_db
from app.models.auth import User
from app.models.tenant import Repository
from app.schemas.repo import RepositoryConnectRequest, RepositoryResponse

router = APIRouter(prefix="/repos", tags=["Repository Operations"])


@router.post("/connect", response_model=RepositoryResponse, status_code=status.HTTP_201_CREATED)
def connect_repository(
    payload: RepositoryConnectRequest,
    current_user: User = Depends(require_role(["ORG_ADMIN", "REVIEWER"])),
    db: Session = Depends(get_current_tenant_db)
):
    """
    Links a GitHub repository to the active organization's private tenant database.
    Requires ORG_ADMIN or REVIEWER privileges.
    """
    # Check if repo already connected
    existing = db.query(Repository).filter(
        Repository.repo_name == payload.repo_name,
        Repository.is_active == True
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Repository '{payload.repo_name}' is already connected."
        )

    new_repo = Repository(
        repo_name=payload.repo_name,
        github_repo_url=payload.github_repo_url,
        default_branch=payload.default_branch,
        github_installation_id=payload.github_installation_id,
        is_active=True
    )
    db.add(new_repo)
    db.commit()
    db.refresh(new_repo)
    return new_repo


@router.get("", response_model=List[RepositoryResponse])
def list_repositories(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_current_tenant_db)
):
    """
    Lists all active GitHub repositories linked to the authenticated employee's organization.
    """
    return db.query(Repository).filter(Repository.is_active == True).all()
