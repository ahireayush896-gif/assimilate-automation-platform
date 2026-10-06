import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text, Integer, BigInteger
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.db.session import Base


class Repository(Base):
    """Git repositories connected to the organization."""
    __tablename__ = "repositories"

    repository_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    repo_name = Column(String(255), nullable=False)
    github_repo_url = Column(Text, nullable=False)
    default_branch = Column(String(100), default="main", nullable=False)
    github_installation_id = Column(BigInteger, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    tickets = relationship("Ticket", back_populates="repository", cascade="all, delete-orphan")


class Ticket(Base):
    """The central engineering work item / automation request."""
    __tablename__ = "tickets"

    ticket_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    repo_id = Column(UUID(as_uuid=True), ForeignKey("repositories.repository_id", ondelete="CASCADE"), nullable=False)
    creator_id = Column(UUID(as_uuid=True), nullable=False)  # References users.user_id in Master DB
    assigned_reviewer_id = Column(UUID(as_uuid=True), nullable=True)  # References users.user_id in Master DB
    prompt = Column(Text, nullable=False)
    category = Column(String(50), nullable=False)  # 'BUG_FIX', 'UI_IMPROVEMENT', 'FEATURE', 'REFACTOR'
    priority = Column(String(20), default="P2", nullable=False)  # 'P0', 'P1', 'P2', 'P3'
    status = Column(String(50), default="DRAFT", nullable=False)  # 'DRAFT', 'AI_GENERATING', 'PENDING_REVIEW', 'APPROVED', 'PR_OPENED', 'FAILED'
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    repository = relationship("Repository", back_populates="tickets")
    attachments = relationship("Attachment", back_populates="ticket", cascade="all, delete-orphan")
    revisions = relationship("Revision", back_populates="ticket", cascade="all, delete-orphan")
    executions = relationship("Execution", back_populates="ticket", cascade="all, delete-orphan")
    pull_requests = relationship("PullRequest", back_populates="ticket", cascade="all, delete-orphan")


class Attachment(Base):
    """Visual attachments (UI screenshots, console logs, Figma designs) for the AI."""
    __tablename__ = "attachments"

    attachment_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticket_id = Column(UUID(as_uuid=True), ForeignKey("tickets.ticket_id", ondelete="CASCADE"), nullable=False)
    file_url = Column(Text, nullable=False)
    file_type = Column(String(50), nullable=False)  # 'SCREENSHOT', 'LOG', 'FIGMA_MOCK'
    uploaded_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    ticket = relationship("Ticket", back_populates="attachments")


class Revision(Base):
    """Iteration history of AI-generated and human-edited code diff patches."""
    __tablename__ = "revisions"

    revision_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticket_id = Column(UUID(as_uuid=True), ForeignKey("tickets.ticket_id", ondelete="CASCADE"), nullable=False)
    iteration_number = Column(Integer, nullable=False, default=1)
    author_type = Column(String(20), nullable=False)  # 'AI', 'REVIEWER', 'DEVELOPER'
    diff_patch = Column(Text, nullable=False)  # Unified Git diff format
    files_modified = Column(JSONB, default=list, nullable=False)  # e.g., ["src/app.py", "styles.css"]
    ai_summary = Column(Text, nullable=True)
    reviewer_feedback = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    ticket = relationship("Ticket", back_populates="revisions")


class Execution(Base):
    """Checkpointed state machine audit log for asynchronous workers."""
    __tablename__ = "executions"

    execution_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticket_id = Column(UUID(as_uuid=True), ForeignKey("tickets.ticket_id", ondelete="CASCADE"), nullable=False)
    current_step = Column(String(50), nullable=False)  # 'INIT', 'CONTEXT_COLLECTED', 'AI_DIFF_GENERATED', 'SANDBOX_CLONED', 'PATCH_APPLIED', 'LINT_PASSED', 'BRANCH_PUSHED', 'PR_OPENED'
    status = Column(String(50), nullable=False)  # 'RUNNING', 'COMPLETED', 'FAILED', 'RETRYING'
    execution_logs = Column(JSONB, default=list, nullable=False)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    ticket = relationship("Ticket", back_populates="executions")


class PullRequest(Base):
    """Maps the approved ticket revision to the resulting GitHub Pull Request."""
    __tablename__ = "pull_requests"

    pr_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticket_id = Column(UUID(as_uuid=True), ForeignKey("tickets.ticket_id", ondelete="CASCADE"), nullable=False)
    github_pr_number = Column(Integer, nullable=False)
    github_pr_url = Column(Text, nullable=False)
    branch_name = Column(String(255), nullable=False)  # e.g., 'ai/ticket-104-bug-fix'
    target_branch = Column(String(100), default="main", nullable=False)
    status = Column(String(50), default="OPEN", nullable=False)  # 'OPEN', 'MERGED', 'CLOSED'
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    ticket = relationship("Ticket", back_populates="pull_requests")
