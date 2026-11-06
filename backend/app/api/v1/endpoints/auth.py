"""
Authentication API Endpoints (Registration, Login, Profile, Password)
"""

import re
from datetime import timedelta
from typing import List
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    check_login_rate_limit,
    record_login_failure,
    reset_login_failures,
)
from app.core.exceptions import (
    ConflictException,
    UnauthorizedException,
    ValidationException,
)
from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.models.organization import Organization, Workspace
from app.models.membership import Membership, RoleEnum
from app.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    TokenResponse,
    UserProfileResponse,
    UserMembershipInfo,
)
from app.schemas.user import UserRead, UserUpdate, ChangePasswordRequest

router = APIRouter(prefix="/auth", tags=["Authentication"])


def _slugify(text: str) -> str:
    slug = re.sub(r"[^\w\s-]", "", text).strip().lower()
    return re.sub(r"[-\s]+", "-", slug)


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register New User Account",
    description="Registers a user and optionally provisions an organization with an initial default workspace.",
)
def register(
    req: RegisterRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    # Check for duplicate user email
    existing = db.query(User).filter(User.email == req.email.lower()).first()
    if existing:
        raise ConflictException(
            f"An account with email '{req.email}' already exists.",
            details={"email": req.email},
        )

    # Create new user
    hashed_pwd = get_password_hash(req.password)
    user = User(
        email=req.email.lower(),
        password_hash=hashed_pwd,
        full_name=req.full_name,
        is_active=True,
        is_platform_admin=False,
    )
    db.add(user)
    db.flush()  # Generate user.id

    # If organization_name supplied, provision organization & default workspace
    if req.organization_name:
        org_slug = _slugify(req.organization_name)
        # Ensure unique slug
        base_slug = org_slug or "org"
        counter = 1
        while db.query(Organization).filter(Organization.slug == org_slug).first():
            org_slug = f"{base_slug}-{counter}"
            counter += 1

        org = Organization(
            name=req.organization_name,
            slug=org_slug,
            is_active=True,
        )
        db.add(org)
        db.flush()

        # Add user as ORG_OWNER
        membership = Membership(
            organization_id=org.id,
            user_id=user.id,
            role=RoleEnum.ORG_OWNER.value,
        )
        db.add(membership)

        # Create default 'production' workspace
        default_workspace = Workspace(
            organization_id=org.id,
            name="Production",
            slug="production",
            description="Default production environment workspace",
        )
        db.add(default_workspace)

    # Issue access token
    access_token = create_access_token(
        subject=user.id,
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        extra_claims={"email": user.email},
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserRead.model_validate(user),
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="User Login",
    description="Authenticates user credentials and returns a signed JWT access token.",
)
def login(
    req: LoginRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> TokenResponse:
    rate_key = f"{request.client.host if request.client else 'local'}:{req.email.lower()}"
    check_login_rate_limit(rate_key)

    user = db.query(User).filter(User.email == req.email.lower()).first()
    if not user or not verify_password(req.password, user.password_hash):
        record_login_failure(rate_key)
        raise UnauthorizedException("Invalid email address or password.")

    if not user.is_active:
        raise UnauthorizedException("This user account has been deactivated.")

    # Successful login: reset rate limit tracking
    reset_login_failures(rate_key)

    access_token = create_access_token(
        subject=user.id,
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        extra_claims={"email": user.email},
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserRead.model_validate(user),
    )


@router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
    summary="User Logout",
    description="Terminates client session and clears local credential state.",
)
def logout(
    current_user: User = Depends(get_current_user),
) -> dict:
    return {"message": "Logged out successfully", "user_id": str(current_user.id)}


@router.get(
    "/me",
    response_model=UserProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Current User Profile & Memberships",
    description="Returns authenticated user profile along with all accessible organization memberships.",
)
def get_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserProfileResponse:
    memberships = (
        db.query(Membership)
        .join(Organization, Membership.organization_id == Organization.id)
        .filter(Membership.user_id == current_user.id, Organization.is_active.is_(True))
        .all()
    )

    membership_info: List[UserMembershipInfo] = [
        UserMembershipInfo(
            organization_id=m.organization.id,
            organization_name=m.organization.name,
            organization_slug=m.organization.slug,
            role=m.role,
        )
        for m in memberships
    ]

    return UserProfileResponse(
        user=UserRead.model_validate(current_user),
        memberships=membership_info,
    )


@router.put(
    "/me",
    response_model=UserRead,
    status_code=status.HTTP_200_OK,
    summary="Update Profile",
    description="Update user profile information.",
)
def update_profile(
    req: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserRead:
    if req.full_name is not None:
        current_user.full_name = req.full_name
        db.add(current_user)

    return UserRead.model_validate(current_user)


@router.post(
    "/change-password",
    status_code=status.HTTP_200_OK,
    summary="Change Password",
    description="Allows authenticated user to update their account password.",
)
def change_password(
    req: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    if not verify_password(req.current_password, current_user.password_hash):
        raise UnauthorizedException("Current password provided is incorrect.")

    current_user.password_hash = get_password_hash(req.new_password)
    db.add(current_user)

    return {"message": "Password changed successfully."}
