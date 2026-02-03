from fastapi import APIRouter, Depends, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.database.supabase_client import get_supabase
from app.modules.auth.schemas import (
    LoginRequest, RegisterRequest, TokenResponse, RegisterResponse,
    SetSuperUserRequest
)
from app.modules.auth.service import AuthService
from app.core.dependencies import get_current_user_id, is_super_user, get_user_permissions
from app.config.permissions_config import get_permission_matrix
from supabase import Client
from typing import Dict, List

router = APIRouter(prefix="/auth", tags=["auth"])

# Security scheme for JWT Bearer token
security = HTTPBearer()


def get_auth_service(supabase: Client = Depends(get_supabase)) -> AuthService:
    return AuthService(supabase)


def get_current_token(
    credentials: HTTPAuthorizationCredentials = Security(security)
) -> str:
    """Extract JWT token from Authorization header"""
    return credentials.credentials


@router.post("/register", response_model=RegisterResponse, status_code=201)
async def register(
    register_data: RegisterRequest,
    service: AuthService = Depends(get_auth_service)
):
    """Register a new user"""
    return service.register(register_data)


@router.post("/login", response_model=TokenResponse)
async def login(
    login_data: LoginRequest,
    service: AuthService = Depends(get_auth_service)
):
    """Login and get access token"""
    return service.login(login_data)


@router.post("/logout", status_code=200)
async def logout(
    token: str = Depends(get_current_token),
    service: AuthService = Depends(get_auth_service)
):
    """Logout and invalidate token"""
    service.logout(token)
    return {"message": "Logged out successfully"}


@router.get("/me")
async def get_current_user(
    current_user: Dict = Depends(get_current_user_id),
    supabase: Client = Depends(get_supabase),
):
    """Get current authenticated user and their permissions (for frontend UI)."""
    if is_super_user(current_user, supabase):
        permissions: List[str] = [p["name"] for p in get_permission_matrix()["permissions"]]
    else:
        permissions = get_user_permissions(current_user["id"], supabase)
    return {**current_user, "permissions": permissions}


@router.post("/set-super-user", status_code=200)
async def set_super_user(
    request: SetSuperUserRequest,
    current_user: Dict = Depends(get_current_user_id),
    service: AuthService = Depends(get_auth_service),
    supabase: Client = Depends(get_supabase)
):
    """Set super_user status for a user (requires current user to be super_user)"""
    # Only super users can set other users as super users
    if not is_super_user(current_user, supabase):
        raise HTTPException(status_code=403, detail="Only super users can set super_user status")
    
    service.set_super_user(request.user_id, request.is_super_user)
    return {
        "message": f"User {request.user_id} super_user status set to {request.is_super_user}",
        "user_id": request.user_id,
        "is_super_user": request.is_super_user
    }
