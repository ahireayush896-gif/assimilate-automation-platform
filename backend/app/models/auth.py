import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.session import Base


class Tenant(Base):
    __tablename__ = "tenants"

    tenant_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    db_name = Column(String(100), unique=True, nullable=False)
    status = Column(String(50), default="ACTIVE", nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    users = relationship("User", back_populates="tenant", cascade="all, delete-orphan")
    invitations = relationship("Invitation", back_populates="tenant", cascade="all, delete-orphan")


class User(Base):
    __tablename__ = "users"

    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False)
    employee_id = Column(String(50), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    phone_number = Column(String(20), nullable=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, default="DEVELOPER")  # 'DEVELOPER', 'REVIEWER', 'ORG_ADMIN'
    github_username = Column(String(100), nullable=True)
    status = Column(String(50), default="ACTIVE", nullable=False)  # 'ACTIVE', 'PENDING_ACTIVATION', 'DEACTIVATED'
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    tenant = relationship("Tenant", back_populates="users")
    audit_logs = relationship("AuditAuthLog", back_populates="user", cascade="all, delete-orphan")


class AuditAuthLog(Base):
    __tablename__ = "audit_auth_logs"

    log_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    event_type = Column(String(50), nullable=False)  # 'LOGIN_SUCCESS', 'LOGIN_FAILED', 'ROLE_UPDATED'
    ip_address = Column(String(50), nullable=False)
    user_agent = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    user = relationship("User", back_populates="audit_logs")


class Invitation(Base):
    __tablename__ = "invitations"

    invitation_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False)
    invited_email = Column(String(255), nullable=False)
    assigned_role = Column(String(50), nullable=False)
    token_hash = Column(String(255), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    status = Column(String(50), default="PENDING", nullable=False)  # 'PENDING', 'ACCEPTED', 'EXPIRED'
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    tenant = relationship("Tenant", back_populates="invitations")
