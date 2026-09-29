import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


# 1. Organization & Admin Signup
class TenantSignupRequest(BaseModel):
    organization_name: str = Field(..., min_length=2, max_length=255, example="Acme Innovations")
    slug: str = Field(..., min_length=2, max_length=100, example="acme-innovations")
    admin_name: str = Field(..., min_length=2, max_length=255, example="Rahul Sharma")
    admin_email: EmailStr = Field(..., example="rahul@acme.com")
    employee_id: str = Field(..., min_length=2, max_length=50, example="EMP-0001")
    phone_number: Optional[str] = Field(None, example="+919876543210")
    password: str = Field(..., min_length=8, example="SecureAdminPass@2026")


# 2. Login Request & Response
class LoginRequest(BaseModel):
    email: EmailStr = Field(..., example="rahul@acme.com")
    password: str = Field(..., example="SecureAdminPass@2026")


class UserProfile(BaseModel):
    user_id: uuid.UUID
    tenant_id: uuid.UUID
    organization_name: str
    employee_id: str
    name: str
    email: str
    role: str
    github_username: Optional[str] = None
    is_active: bool

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserProfile


# 3. Employee Invitation Workflow
class InviteEmployeeRequest(BaseModel):
    employee_id: str = Field(..., min_length=2, max_length=50, example="EMP-1042")
    name: str = Field(..., min_length=2, max_length=255, example="Priya Patel")
    email: EmailStr = Field(..., example="priya@acme.com")
    phone_number: Optional[str] = Field(None, example="+919876543211")
    role: str = Field("DEVELOPER", pattern="^(DEVELOPER|REVIEWER|ORG_ADMIN)$", example="DEVELOPER")


class InviteResponse(BaseModel):
    message: str
    invitation_id: uuid.UUID
    invited_email: str
    activation_link: str
    expires_at: datetime


class ActivateAccountRequest(BaseModel):
    token: str = Field(..., description="Activation token from email invite")
    password: str = Field(..., min_length=8, example="NewSecurePassword@2026")
