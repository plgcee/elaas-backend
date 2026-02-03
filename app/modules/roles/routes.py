from fastapi import APIRouter, Depends, HTTPException, status
from app.database.supabase_client import get_supabase
from app.modules.roles.schemas import (
    PermissionCreate, PermissionUpdate, PermissionResponse,
    RoleCreate, RoleUpdate, RoleResponse, RoleWithPermissionsResponse,
    RolePermissionAssign, RolePermissionResponse,
    BulkPermissionAssign, BulkPermissionAssignResponse, BulkPermissionUpdate
)
from app.modules.roles.service import RoleService, PermissionService
from app.core.dependencies import (
    require_permission,
    get_access_cache,
    get_accessible_role_ids,
    get_accessible_permission_ids,
    is_super_user,
)
from supabase import Client
from typing import List, Optional, Dict

router = APIRouter(prefix="/roles", tags=["roles"])


def get_role_service(supabase: Client = Depends(get_supabase)) -> RoleService:
    return RoleService(supabase)


def get_permission_service(supabase: Client = Depends(get_supabase)) -> PermissionService:
    return PermissionService(supabase)


# Permission endpoints
@router.post("/permissions", response_model=PermissionResponse, status_code=201)
async def create_permission(
    permission_data: PermissionCreate,
    user_data: Dict = Depends(require_permission("roles:create")),
    service: PermissionService = Depends(get_permission_service)
):
    """Create a new permission"""
    return service.create_permission(permission_data)


@router.get("/permissions", response_model=List[PermissionResponse])
async def list_permissions(
    resource: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    user_data: Dict = Depends(require_permission("roles:read")),
    service: PermissionService = Depends(get_permission_service),
    supabase: Client = Depends(get_supabase),
    cache: Dict = Depends(get_access_cache)
):
    """List permissions visible to user's groups (or all if super_user)"""
    permission_ids = None if is_super_user(user_data, supabase) else get_accessible_permission_ids(user_data["id"], supabase, cache)
    return service.list_permissions(resource=resource, permission_ids=permission_ids, limit=limit, offset=offset)


@router.get("/permissions/{permission_id}", response_model=PermissionResponse)
async def get_permission(
    permission_id: str,
    user_data: Dict = Depends(require_permission("roles:read")),
    service: PermissionService = Depends(get_permission_service),
    supabase: Client = Depends(get_supabase),
    cache: Dict = Depends(get_access_cache)
):
    """Get permission by ID (only if in user's groups' roles)"""
    if not is_super_user(user_data, supabase) and permission_id not in get_accessible_permission_ids(user_data["id"], supabase, cache):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission not accessible to your groups")
    return service.get_permission_by_id(permission_id)


@router.put("/permissions/{permission_id}", response_model=PermissionResponse)
async def update_permission(
    permission_id: str,
    permission_data: PermissionUpdate,
    user_data: Dict = Depends(require_permission("roles:update")),
    service: PermissionService = Depends(get_permission_service),
    supabase: Client = Depends(get_supabase),
    cache: Dict = Depends(get_access_cache)
):
    """Update permission (only if in user's groups' roles)"""
    if not is_super_user(user_data, supabase) and permission_id not in get_accessible_permission_ids(user_data["id"], supabase, cache):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission not accessible to your groups")
    return service.update_permission(permission_id, permission_data)


@router.delete("/permissions/{permission_id}", status_code=204)
async def delete_permission(
    permission_id: str,
    user_data: Dict = Depends(require_permission("roles:delete")),
    service: PermissionService = Depends(get_permission_service),
    supabase: Client = Depends(get_supabase),
    cache: Dict = Depends(get_access_cache)
):
    """Delete permission (only if in user's groups' roles)"""
    if not is_super_user(user_data, supabase) and permission_id not in get_accessible_permission_ids(user_data["id"], supabase, cache):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission not accessible to your groups")
    service.delete_permission(permission_id)
    return None


# Role endpoints
@router.post("", response_model=RoleResponse, status_code=201)
async def create_role(
    role_data: RoleCreate,
    user_data: Dict = Depends(require_permission("roles:create")),
    service: RoleService = Depends(get_role_service)
):
    """Create a new role"""
    return service.create_role(role_data)


@router.get("", response_model=List[RoleResponse])
async def list_roles(
    limit: int = 10,
    offset: int = 0,
    user_data: Dict = Depends(require_permission("roles:read")),
    service: RoleService = Depends(get_role_service),
    supabase: Client = Depends(get_supabase),
    cache: Dict = Depends(get_access_cache)
):
    """List roles visible to user's groups (or all if super_user)"""
    role_ids = None if is_super_user(user_data, supabase) else get_accessible_role_ids(user_data["id"], supabase, cache)
    return service.list_roles(limit=limit, offset=offset, role_ids=role_ids)


@router.get("/{role_id}", response_model=RoleResponse)
async def get_role(
    role_id: str,
    user_data: Dict = Depends(require_permission("roles:read")),
    service: RoleService = Depends(get_role_service),
    supabase: Client = Depends(get_supabase),
    cache: Dict = Depends(get_access_cache)
):
    """Get role by ID (only if assigned to user's groups)"""
    if not is_super_user(user_data, supabase) and role_id not in get_accessible_role_ids(user_data["id"], supabase, cache):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Role not accessible to your groups")
    return service.get_role_by_id(role_id)


@router.get("/{role_id}/with-permissions", response_model=RoleWithPermissionsResponse)
async def get_role_with_permissions(
    role_id: str,
    user_data: Dict = Depends(require_permission("roles:read")),
    service: RoleService = Depends(get_role_service),
    supabase: Client = Depends(get_supabase),
    cache: Dict = Depends(get_access_cache)
):
    """Get role with all associated permissions (only if assigned to user's groups)"""
    if not is_super_user(user_data, supabase) and role_id not in get_accessible_role_ids(user_data["id"], supabase, cache):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Role not accessible to your groups")
    return service.get_role_with_permissions(role_id)


@router.put("/{role_id}", response_model=RoleResponse)
async def update_role(
    role_id: str,
    role_data: RoleUpdate,
    user_data: Dict = Depends(require_permission("roles:update")),
    service: RoleService = Depends(get_role_service),
    supabase: Client = Depends(get_supabase),
    cache: Dict = Depends(get_access_cache)
):
    """Update role (only if assigned to user's groups)"""
    if not is_super_user(user_data, supabase) and role_id not in get_accessible_role_ids(user_data["id"], supabase, cache):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Role not accessible to your groups")
    return service.update_role(role_id, role_data)


@router.delete("/{role_id}", status_code=204)
async def delete_role(
    role_id: str,
    user_data: Dict = Depends(require_permission("roles:delete")),
    service: RoleService = Depends(get_role_service),
    supabase: Client = Depends(get_supabase),
    cache: Dict = Depends(get_access_cache)
):
    """Delete role (only if assigned to user's groups)"""
    if not is_super_user(user_data, supabase) and role_id not in get_accessible_role_ids(user_data["id"], supabase, cache):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Role not accessible to your groups")
    service.delete_role(role_id)
    return None


# Role-Permission association endpoints
@router.post("/{role_id}/permissions", response_model=RolePermissionResponse, status_code=201)
async def assign_permission_to_role(
    role_id: str,
    permission_assign: RolePermissionAssign,
    user_data: Dict = Depends(require_permission("roles:assign")),
    service: RoleService = Depends(get_role_service),
    supabase: Client = Depends(get_supabase),
    cache: Dict = Depends(get_access_cache)
):
    """Assign a permission to a role (only if role assigned to user's groups)"""
    if not is_super_user(user_data, supabase) and role_id not in get_accessible_role_ids(user_data["id"], supabase, cache):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Role not accessible to your groups")
    return service.assign_permission_to_role(role_id, permission_assign.permission_id)


@router.get("/{role_id}/permissions", response_model=List[PermissionResponse])
async def get_role_permissions(
    role_id: str,
    user_data: Dict = Depends(require_permission("roles:read")),
    service: RoleService = Depends(get_role_service),
    supabase: Client = Depends(get_supabase),
    cache: Dict = Depends(get_access_cache)
):
    """Get all permissions for a role (only if role assigned to user's groups)"""
    if not is_super_user(user_data, supabase) and role_id not in get_accessible_role_ids(user_data["id"], supabase, cache):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Role not accessible to your groups")
    return service.get_role_permissions(role_id)


@router.delete("/{role_id}/permissions/{permission_id}", status_code=204)
async def remove_permission_from_role(
    role_id: str,
    permission_id: str,
    user_data: Dict = Depends(require_permission("roles:assign")),
    service: RoleService = Depends(get_role_service),
    supabase: Client = Depends(get_supabase),
    cache: Dict = Depends(get_access_cache)
):
    """Remove a permission from a role (only if role assigned to user's groups)"""
    if not is_super_user(user_data, supabase) and role_id not in get_accessible_role_ids(user_data["id"], supabase, cache):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Role not accessible to your groups")
    service.remove_permission_from_role(role_id, permission_id)
    return None


@router.post("/{role_id}/permissions/bulk-assign", response_model=BulkPermissionAssignResponse, status_code=200)
async def bulk_assign_permissions_to_role(
    role_id: str,
    bulk_data: BulkPermissionAssign,
    user_data: Dict = Depends(require_permission("roles:assign")),
    service: RoleService = Depends(get_role_service),
    supabase: Client = Depends(get_supabase),
    cache: Dict = Depends(get_access_cache)
):
    """Bulk assign multiple permissions to a role (only if role assigned to user's groups)"""
    if not is_super_user(user_data, supabase) and role_id not in get_accessible_role_ids(user_data["id"], supabase, cache):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Role not accessible to your groups")
    return service.bulk_assign_permissions_to_role(role_id, bulk_data.permission_ids)


@router.put("/{role_id}/permissions/bulk-update", response_model=BulkPermissionAssignResponse, status_code=200)
async def bulk_update_role_permissions(
    role_id: str,
    bulk_data: BulkPermissionUpdate,
    user_data: Dict = Depends(require_permission("roles:assign")),
    service: RoleService = Depends(get_role_service),
    supabase: Client = Depends(get_supabase),
    cache: Dict = Depends(get_access_cache)
):
    """Bulk update/replace all permissions for a role (only if role assigned to user's groups)"""
    if not is_super_user(user_data, supabase) and role_id not in get_accessible_role_ids(user_data["id"], supabase, cache):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Role not accessible to your groups")
    return service.bulk_update_role_permissions(role_id, bulk_data.permission_ids)
