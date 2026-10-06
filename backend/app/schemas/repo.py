import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class RepositoryConnectRequest(BaseModel):
    repo_name: str = Field(..., min_length=2, max_length=255, example="ahireayush896-gif/assimilate-sandbox")
    github_repo_url: str = Field(..., example="https://github.com/ahireayush896-gif/assimilate-sandbox")
    default_branch: str = Field("main", min_length=1, max_length=100, example="main")
    github_installation_id: Optional[int] = Field(None, example=168048972)


class RepositoryResponse(BaseModel):
    repository_id: uuid.UUID
    repo_name: str
    github_repo_url: str
    default_branch: str
    github_installation_id: Optional[int] = None
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True
