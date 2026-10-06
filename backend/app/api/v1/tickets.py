import os
import shutil
import uuid
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_user, get_current_tenant_db
from app.models.auth import User
from app.models.tenant import Repository, Ticket, Attachment, Revision
from app.schemas.ticket import TicketResponse, TicketCreateResponse

router = APIRouter(prefix="/tickets", tags=["Ticket Operations"])

# Local uploads directory for visual evidence
UPLOAD_DIR = Path("uploads")


@router.post("", response_model=TicketCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_ticket(
    repo_id: uuid.UUID = Form(...),
    prompt: str = Form(..., min_length=5),
    category: str = Form("BUG_FIX"),
    priority: str = Form("P2"),
    attachment: Optional[UploadFile] = File(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_current_tenant_db)
):
    """
    Ingests a new automation ticket (bug prompt, category, priority, and visual screenshot).
    Stores ticket in the organization's private database and marks status as AI_GENERATING.
    """
    # 1. Validate that the target repository exists and is active
    repo = db.query(Repository).filter(
        Repository.repository_id == repo_id,
        Repository.is_active == True
    ).first()

    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository with ID '{repo_id}' not found in active organization catalog."
        )

    # 2. Validate category and priority
    valid_categories = ["BUG_FIX", "UI_IMPROVEMENT", "FEATURE", "REFACTOR"]
    valid_priorities = ["P0", "P1", "P2", "P3"]

    if category not in valid_categories:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid category. Must be one of: {valid_categories}"
        )

    if priority not in valid_priorities:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid priority. Must be one of: {valid_priorities}"
        )

    # 3. Create Ticket Record
    new_ticket = Ticket(
        repo_id=repo_id,
        creator_id=current_user.user_id,
        prompt=prompt.strip(),
        category=category,
        priority=priority,
        status="AI_GENERATING"
    )
    db.add(new_ticket)
    db.flush()

    # 4. Handle Visual Attachment (Screenshot / Log)
    if attachment and attachment.filename:
        tenant_slug = current_user.tenant.slug
        target_dir = UPLOAD_DIR / tenant_slug / str(new_ticket.ticket_id)
        target_dir.mkdir(parents=True, exist_ok=True)

        safe_filename = f"{uuid.uuid4().hex[:8]}_{attachment.filename}"
        file_path = target_dir / safe_filename

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(attachment.file, buffer)

        file_type = "SCREENSHOT" if attachment.content_type and "image" in attachment.content_type else "LOG"

        new_attachment = Attachment(
            ticket_id=new_ticket.ticket_id,
            file_url=str(file_path),
            file_type=file_type
        )
        db.add(new_attachment)

    db.commit()
    db.refresh(new_ticket)

    # Load relationships for clean serialization
    ticket_with_relations = db.query(Ticket).options(
        joinedload(Ticket.attachments),
        joinedload(Ticket.revisions)
    ).filter(Ticket.ticket_id == new_ticket.ticket_id).first()

    return TicketCreateResponse(
        message="Ticket ingested successfully. Status moved to AI_GENERATING.",
        ticket=TicketResponse.model_validate(ticket_with_relations)
    )


@router.get("", response_model=List[TicketResponse])
def list_tickets(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_current_tenant_db)
):
    """
    Lists all automation tickets in the organization's private database.
    """
    return db.query(Ticket).options(
        joinedload(Ticket.attachments),
        joinedload(Ticket.revisions)
    ).order_by(Ticket.created_at.desc()).all()


@router.get("/{ticket_id}", response_model=TicketResponse)
def get_ticket(
    ticket_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_current_tenant_db)
):
    """
    Retrieves full details of a specific ticket including attachments and AI revisions.
    """
    ticket = db.query(Ticket).options(
        joinedload(Ticket.attachments),
        joinedload(Ticket.revisions)
    ).filter(Ticket.ticket_id == ticket_id).first()

    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket '{ticket_id}' not found."
        )

    return ticket
