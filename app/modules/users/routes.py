from fastapi import APIRouter, Depends, HTTPException, status
from app.database.supabase_client import get_supabase
from app.modules.users.schemas import (
    UserUpdate, UserResponse, UserWithGroupsResponse,
    UserGroupAdd, UserGroupResponse
)
from app.modules.users.service import UserService
from app.core.dependencies import require_permission, get_current_user_id, check_group_admin, is_super_user, user_can_access_user
from supabase import Client
from typing import List, Dict

router = APIRouter(prefix="/users", tags=["users"])


def get_user_service(supabase: Client = Depends(get_supabase)) -> UserService:
    return UserService(supabase)


@router.get("", response_model=List[UserResponse])
async def list_users(
    limit: int = 10,
    offset: int = 0,
    user_data: Dict = Depends(require_permission("users:read")),
    service: UserService = Depends(get_user_service),
    supabase: Client = Depends(get_supabase)
):
    """List users: token user_id -> their groups -> all group members. Super_user gets all users."""
    current_user_id = user_data["id"]  # from token
    allow_all = is_super_user(user_data, supabase)
    return service.list_users(current_user_id=current_user_id, limit=limit, offset=offset, allow_all=allow_all)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    user_data: Dict = Depends(require_permission("users:read")),
    service: UserService = Depends(get_user_service),
    supabase: Client = Depends(get_supabase)
):
    """Get user by ID (only if same user or shares a group)"""
    if not is_super_user(user_data, supabase) and not user_can_access_user(user_data["id"], user_id, supabase):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User not accessible")
    return service.get_user_by_id(user_id)


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    user_data_body: UserUpdate,
    user_data: Dict = Depends(require_permission("users:update")),
    service: UserService = Depends(get_user_service),
    supabase: Client = Depends(get_supabase)
):
    """Update user (only if same user or shares a group)"""
    if not is_super_user(user_data, supabase) and not user_can_access_user(user_data["id"], user_id, supabase):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User not accessible")
    return service.update_user(user_id, user_data_body)


@router.delete("/{user_id}", status_code=204)
async def delete_user(
    user_id: str,
    user_data: Dict = Depends(require_permission("users:delete")),
    service: UserService = Depends(get_user_service),
    supabase: Client = Depends(get_supabase)
):
    """Delete user (only if same user or shares a group)"""
    if not is_super_user(user_data, supabase) and not user_can_access_user(user_data["id"], user_id, supabase):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User not accessible")
    service.delete_user(user_id)
    return None


@router.get("/{user_id}/with-groups", response_model=UserWithGroupsResponse)
async def get_user_with_groups(
    user_id: str,
    user_data: Dict = Depends(require_permission("users:read")),
    service: UserService = Depends(get_user_service),
    supabase: Client = Depends(get_supabase)
):
    """Get user with all associated groups (only if same user or shares a group)"""
    if not is_super_user(user_data, supabase) and not user_can_access_user(user_data["id"], user_id, supabase):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User not accessible")
    return service.get_user_with_groups(user_id)


@router.get("/{user_id}/groups", response_model=List[dict])
async def get_user_groups(
    user_id: str,
    user_data: Dict = Depends(require_permission("users:read")),
    service: UserService = Depends(get_user_service),
    supabase: Client = Depends(get_supabase)
):
    """Get all groups for a user (only if same user or shares a group)"""
    if not is_super_user(user_data, supabase) and not user_can_access_user(user_data["id"], user_id, supabase):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User not accessible")
    return service.get_user_groups(user_id)


@router.post("/{user_id}/groups", response_model=UserGroupResponse, status_code=201)
async def add_user_to_group(
    user_id: str,
    group_data: UserGroupAdd,
    current_user: Dict = Depends(get_current_user_id),
    service: UserService = Depends(get_user_service),
    supabase: Client = Depends(get_supabase)
):
    """Add user to a group (requires group admin or super user)"""
    # Super users can add to any group, others need to be group admin
    if not is_super_user(current_user, supabase):
        check_group_admin(group_data.group_id, current_user, supabase)
    
    return service.add_user_to_group(user_id, group_data)


@router.delete("/{user_id}/groups/{group_id}", status_code=204)
async def remove_user_from_group(
    user_id: str,
    group_id: str,
    current_user: Dict = Depends(get_current_user_id),
    service: UserService = Depends(get_user_service),
    supabase: Client = Depends(get_supabase)
):
    """Remove user from a group (requires group admin or super user)"""
    # Super users can remove from any group, others need to be group admin
    if not is_super_user(current_user, supabase):
        check_group_admin(group_id, current_user, supabase)
    
    service.remove_user_from_group(user_id, group_id)
    return None
