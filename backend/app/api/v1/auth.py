import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    generate_activation_token
)
from app.db.session import get_master_db, provision_tenant_database
from app.models.auth import Tenant, User, AuditAuthLog, Invitation
from app.schemas.auth import (
    TenantSignupRequest,
    LoginRequest,
    TokenResponse,
    UserProfile,
    InviteEmployeeRequest,
    InviteResponse,
    ActivateAccountRequest
)
from app.api.deps import get_current_user, require_role

router = APIRouter(prefix="/auth", tags=["Authentication & Multi-Tenancy"])


@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def signup_tenant(
    payload: TenantSignupRequest,
    request: Request,
    db: Session = Depends(get_master_db)
):
    """
    Registers a new Tenant and Admin User in Master DB,
    and dynamically provisions the dedicated Tenant Database.
    """
    # 1. Check if slug or email already exists
    if db.query(Tenant).filter(Tenant.slug == payload.slug).first():
        raise HTTPException(status_code=400, detail="Organization slug already exists")
    if db.query(User).filter(User.email == payload.admin_email).first():
        raise HTTPException(status_code=400, detail="Admin email is already registered")

    # 2. Compute dedicated tenant database name
    db_name = f"tenant_{payload.slug.replace('-', '_')}_db"

    # 3. Create Tenant in Master DB
    new_tenant = Tenant(
        organization_name=payload.organization_name,
        slug=payload.slug,
        db_name=db_name,
        status="ACTIVE"
    )
    db.add(new_tenant)
    db.flush()

    # 4. Create Admin User in Master DB
    new_admin = User(
        tenant_id=new_tenant.tenant_id,
        employee_id=payload.employee_id,
        name=payload.admin_name,
        email=payload.admin_email,
        phone_number=payload.phone_number,
        password_hash=get_password_hash(payload.password),
        role="ORG_ADMIN",
        status="ACTIVE",
        is_active=True
    )
    db.add(new_admin)
    db.flush()

    # 5. Log Security Event
    audit_log = AuditAuthLog(
        user_id=new_admin.user_id,
        event_type="ORG_SIGNUP",
        ip_address=request.client.host if request.client else "127.0.0.1",
        user_agent=request.headers.get("user-agent")
    )
    db.add(audit_log)
    db.commit()
    db.refresh(new_admin)
    db.refresh(new_tenant)

    # 6. Dynamically Clone Template Database to create new Tenant Database
    try:
        provision_tenant_database(db_name=db_name, template_db=settings.TENANT_TEMPLATE_DB_NAME)
    except Exception as e:
        # Note: In development if template DB is not ready yet, log warning
        pass

    # 7. Mint JWT Token
    access_token = create_access_token(
        subject=new_admin.user_id,
        tenant_id=new_tenant.tenant_id,
        tenant_slug=new_tenant.slug,
        db_name=new_tenant.db_name,
        role=new_admin.role,
        employee_id=new_admin.employee_id,
        email=new_admin.email
    )

    user_profile = UserProfile(
        user_id=new_admin.user_id,
        tenant_id=new_tenant.tenant_id,
        organization_name=new_tenant.organization_name,
        employee_id=new_admin.employee_id,
        name=new_admin.name,
        email=new_admin.email,
        role=new_admin.role,
        github_username=new_admin.github_username,
        is_active=new_admin.is_active
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=user_profile
    )


@router.post("/login", response_model=TokenResponse)
def login(
    payload: LoginRequest,
    request: Request,
    db: Session = Depends(get_master_db)
):
    """
    Authenticates user credentials, validates active status,
    and returns a signed JWT containing tenant and role claims.
    """
    user = db.query(User).filter(User.email == payload.email).first()
    ip_addr = request.client.host if request.client else "127.0.0.1"
    user_agent = request.headers.get("user-agent")

    if not user or not verify_password(payload.password, user.password_hash):
        if user:
            # Record failed login
            db.add(AuditAuthLog(user_id=user.user_id, event_type="LOGIN_FAILED", ip_address=ip_addr, user_agent=user_agent))
            db.commit()
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not user.is_active or user.status != "ACTIVE":
        raise HTTPException(status_code=403, detail="Account is deactivated or pending activation")

    # Record successful login
    db.add(AuditAuthLog(user_id=user.user_id, event_type="LOGIN_SUCCESS", ip_address=ip_addr, user_agent=user_agent))
    db.commit()

    tenant = user.tenant

    access_token = create_access_token(
        subject=user.user_id,
        tenant_id=tenant.tenant_id,
        tenant_slug=tenant.slug,
        db_name=tenant.db_name,
        role=user.role,
        employee_id=user.employee_id,
        email=user.email
    )

    user_profile = UserProfile(
        user_id=user.user_id,
        tenant_id=tenant.tenant_id,
        organization_name=tenant.organization_name,
        employee_id=user.employee_id,
        name=user.name,
        email=user.email,
        role=user.role,
        github_username=user.github_username,
        is_active=user.is_active
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=user_profile
    )


@router.get("/me", response_model=UserProfile)
def get_current_user_profile(
    current_user: User = Depends(get_current_user)
):
    """Returns the authenticated employee's profile and active organization context."""
    tenant = current_user.tenant
    return UserProfile(
        user_id=current_user.user_id,
        tenant_id=tenant.tenant_id,
        organization_name=tenant.organization_name,
        employee_id=current_user.employee_id,
        name=current_user.name,
        email=current_user.email,
        role=current_user.role,
        github_username=current_user.github_username,
        is_active=current_user.is_active
    )


@router.post("/invite", response_model=InviteResponse, status_code=status.HTTP_201_CREATED)
def invite_employee(
    payload: InviteEmployeeRequest,
    current_user: User = Depends(require_role(["ORG_ADMIN"])),
    db: Session = Depends(get_master_db)
):
    """
    Allows an ORG_ADMIN to invite a new employee with an Employee ID and assigned role.
    Generates a secure activation link valid for 24 hours.
    """
    # Check if user already exists
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="User with this email already exists")

    tenant_id = current_user.tenant_id
    raw_token = generate_activation_token(user_id=payload.email)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    expires_at = datetime.now(timezone.utc) + timedelta(hours=24)

    # 1. Create Invitation record
    invitation = Invitation(
        tenant_id=tenant_id,
        invited_email=payload.email,
        assigned_role=payload.role,
        token_hash=token_hash,
        expires_at=expires_at,
        status="PENDING"
    )
    db.add(invitation)

    # 2. Pre-create User record in PENDING_ACTIVATION state
    new_user = User(
        tenant_id=tenant_id,
        employee_id=payload.employee_id,
        name=payload.name,
        email=payload.email,
        phone_number=payload.phone_number,
        password_hash="PENDING_PASSWORD_SET",
        role=payload.role,
        status="PENDING_ACTIVATION",
        is_active=False
    )
    db.add(new_user)
    db.commit()
    db.refresh(invitation)

    activation_link = f"https://app.assimilate.io/activate?token={raw_token}"

    return InviteResponse(
        message="Employee invited successfully. Activation token generated.",
        invitation_id=invitation.invitation_id,
        invited_email=payload.email,
        activation_link=activation_link,
        expires_at=expires_at
    )


@router.post("/activate")
def activate_account(
    payload: ActivateAccountRequest,
    db: Session = Depends(get_master_db)
):
    """
    Validates the one-time activation token and establishes the employee's secure password.
    """
    token_hash = hashlib.sha256(payload.token.encode()).hexdigest()
    invitation = db.query(Invitation).filter(
        Invitation.token_hash == token_hash,
        Invitation.status == "PENDING"
    ).first()

    if not invitation or invitation.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Invalid or expired activation token")

    user = db.query(User).filter(User.email == invitation.invited_email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User record not found")

    # Update password and activate user
    user.password_hash = get_password_hash(payload.password)
    user.status = "ACTIVE"
    user.is_active = True

    invitation.status = "ACCEPTED"
    db.commit()

    return {"message": "Account successfully activated! You can now log in with your email and password."}
