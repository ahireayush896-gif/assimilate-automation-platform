import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class AttachmentResponse(BaseModel):
    attachment_id: uuid.UUID
    file_url: str
    file_type: str
    uploaded_at: datetime

    class Config:
        from_attributes = True


class RevisionResponse(BaseModel):
    revision_id: uuid.UUID
    iteration_number: int
    author_type: str
    diff_patch: str
    files_modified: list = []
    ai_summary: Optional[str] = None
    reviewer_feedback: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class TicketResponse(BaseModel):
    ticket_id: uuid.UUID
    repo_id: uuid.UUID
    creator_id: uuid.UUID
    assigned_reviewer_id: Optional[uuid.UUID] = None
    prompt: str
    category: str
    priority: str
    status: str
    created_at: datetime
    attachments: List[AttachmentResponse] = []
    revisions: List[RevisionResponse] = []

    class Config:
        from_attributes = True


class TicketCreateResponse(BaseModel):
    message: str
    ticket: TicketResponse
