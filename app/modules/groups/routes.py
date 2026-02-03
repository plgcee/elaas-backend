from fastapi import APIRouter, Depends
from app.database.supabase_client import get_supabase
from app.modules.groups.schemas import (
    GroupCreate, GroupUpdate, GroupResponse, GroupWithRolesResponse,
    GroupMemberAdd, GroupMemberResponse,
    GroupRoleAssign, GroupRoleResponse
)
from app.modules.groups.service import GroupService
from app.core.dependencies import require_permission, get_current_user_id, check_group_admin, check_group_member, is_super_user, get_access_cache, get_user_group_ids
from supabase import Client
from typing import List, Optional, Dict

router = APIRouter(prefix="/groups", tags=["groups"])


def get_group_service(supabase: Client = Depends(get_supabase)) -> GroupService:
    return GroupService(supabase)


@router.post("", response_model=GroupResponse, status_code=201)
async def create_group(
    group_data: GroupCreate,
    user_data: Dict = Depends(require_permission("groups:create")),
    service: GroupService = Depends(get_group_service)
):
    """Create a new group (requires groups:create permission)"""
    return service.create_group(group_data, user_data["id"])


@router.get("", response_model=List[GroupResponse])
async def list_groups(
    created_by_me: bool = False,
    limit: int = 10,
    offset: int = 0,
    user_data: Dict = Depends(require_permission("groups:read")),
    service: GroupService = Depends(get_group_service),
    supabase: Client = Depends(get_supabase),
    cache: Dict = Depends(get_access_cache)
):
    """List groups the user is a member of (or all if super_user). Use created_by_me=true to restrict to groups they created."""
    member_of_user_id = None if is_super_user(user_data, supabase) else user_data["id"]
    group_ids = get_user_group_ids(user_data["id"], supabase, cache) if member_of_user_id else None
    return service.list_groups(member_of_user_id=member_of_user_id, created_by_me=created_by_me, group_ids=group_ids, limit=limit, offset=offset)


@router.get("/{group_id}", response_model=GroupResponse)
async def get_group(
    group_id: str,
    user_data: Dict = Depends(require_permission("groups:read")),
    service: GroupService = Depends(get_group_service),
    supabase: Client = Depends(get_supabase)
):
    """Get group by ID (only if user is a member)"""
    if not is_super_user(user_data, supabase):
        check_group_member(group_id, user_data, supabase)
    return service.get_group_by_id(group_id)


@router.put("/{group_id}", response_model=GroupResponse)
async def update_group(
    group_id: str,
    group_data: GroupUpdate,
    current_user: Dict = Depends(get_current_user_id),
    service: GroupService = Depends(get_group_service),
    supabase: Client = Depends(get_supabase)
):
    """Update group (requires groups:update permission or group admin)"""
    if not is_super_user(current_user, supabase):
        check_group_admin(group_id, current_user, supabase)
    return service.update_group(group_id, group_data)


@router.delete("/{group_id}", status_code=204)
async def delete_group(
    group_id: str,
    current_user: Dict = Depends(get_current_user_id),
    service: GroupService = Depends(get_group_service),
    supabase: Client = Depends(get_supabase)
):
    """Delete group (requires groups:delete permission or group admin)"""
    if not is_super_user(current_user, supabase):
        check_group_admin(group_id, current_user, supabase)
    service.delete_group(group_id)
    return None


@router.post("/{group_id}/members", response_model=GroupMemberResponse, status_code=201)
async def add_member(
    group_id: str,
    member_data: GroupMemberAdd,
    current_user: Dict = Depends(get_current_user_id),
    service: GroupService = Depends(get_group_service),
    supabase: Client = Depends(get_supabase)
):
    """Add a member to the group (requires groups:manage_members or group admin)"""
    if not is_super_user(current_user, supabase):
        check_group_admin(group_id, current_user, supabase)
    return service.add_member(group_id, member_data)


@router.get("/{group_id}/members", response_model=List[GroupMemberResponse])
async def list_members(
    group_id: str,
    user_data: Dict = Depends(require_permission("groups:read")),
    service: GroupService = Depends(get_group_service),
    supabase: Client = Depends(get_supabase)
):
    """List all members of a group (only if user is a member)"""
    if not is_super_user(user_data, supabase):
        check_group_member(group_id, user_data, supabase)
    return service.list_members(group_id)


@router.delete("/{group_id}/members/{user_id}", status_code=204)
async def remove_member(
    group_id: str,
    user_id: str,
    current_user: Dict = Depends(get_current_user_id),
    service: GroupService = Depends(get_group_service),
    supabase: Client = Depends(get_supabase)
):
    """Remove a member from the group (requires groups:manage_members or group admin)"""
    if not is_super_user(current_user, supabase):
        check_group_admin(group_id, current_user, supabase)
    service.remove_member(group_id, user_id)
    return None


@router.get("/{group_id}/with-roles", response_model=GroupWithRolesResponse)
async def get_group_with_roles(
    group_id: str,
    user_data: Dict = Depends(require_permission("groups:read")),
    service: GroupService = Depends(get_group_service),
    supabase: Client = Depends(get_supabase)
):
    """Get group with all associated roles (only if user is a member)"""
    if not is_super_user(user_data, supabase):
        check_group_member(group_id, user_data, supabase)
    return service.get_group_with_roles(group_id)


@router.post("/{group_id}/roles", response_model=GroupRoleResponse, status_code=201)
async def assign_role_to_group(
    group_id: str,
    role_assign: GroupRoleAssign,
    current_user: Dict = Depends(get_current_user_id),
    service: GroupService = Depends(get_group_service),
    supabase: Client = Depends(get_supabase)
):
    """Assign a role to a group (requires groups:update or group admin)"""
    if not is_super_user(current_user, supabase):
        check_group_admin(group_id, current_user, supabase)
    return service.assign_role_to_group(group_id, role_assign.role_id)


@router.get("/{group_id}/roles", response_model=List[dict])
async def get_group_roles(
    group_id: str,
    user_data: Dict = Depends(require_permission("groups:read")),
    service: GroupService = Depends(get_group_service),
    supabase: Client = Depends(get_supabase)
):
    """Get all roles for a group (only if user is a member)"""
    if not is_super_user(user_data, supabase):
        check_group_member(group_id, user_data, supabase)
    return service.get_group_roles(group_id)


@router.delete("/{group_id}/roles/{role_id}", status_code=204)
async def remove_role_from_group(
    group_id: str,
    role_id: str,
    current_user: Dict = Depends(get_current_user_id),
    service: GroupService = Depends(get_group_service),
    supabase: Client = Depends(get_supabase)
):
    """Remove a role from a group (requires groups:update or group admin)"""
    if not is_super_user(current_user, supabase):
        check_group_admin(group_id, current_user, supabase)
    service.remove_role_from_group(group_id, role_id)
    return None
