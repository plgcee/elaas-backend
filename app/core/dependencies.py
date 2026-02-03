"""
Core dependencies for route protection and permission checking
"""

from fastapi import Depends, HTTPException, Request, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.database.supabase_client import get_supabase
from app.modules.auth.service import AuthService
from supabase import Client
from typing import List, Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

security = HTTPBearer()


def _get_request_cache(request: Request) -> Dict[str, Any]:
    """Return request-scoped cache for access data (group_ids, role_ids, permission_ids, permission_names)."""
    if not hasattr(request.state, "access_cache"):
        request.state.access_cache = {}
    return request.state.access_cache


def get_auth_service(supabase: Client = Depends(get_supabase)) -> AuthService:
    return AuthService(supabase)


def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Security(security),
    auth_service: AuthService = Depends(get_auth_service)
) -> dict:
    """Extract current user info from JWT token"""
    token = credentials.credentials
    user_data = auth_service.get_current_user(token)
    return user_data


def is_super_user(user_data: dict, supabase: Client) -> bool:
    """Check if user is a super user from app_metadata"""
    try:
        # Check if user has super_user flag in app_metadata
        # app_metadata is set server-side and cannot be modified by users
        app_metadata = user_data.get("app_metadata", {})
        if app_metadata.get("type") == "super_user":
            return True
        return False
    except Exception:
        return False


def get_user_group_ids(user_id: str, supabase: Client, cache: Optional[Dict[str, Any]] = None) -> List[str]:
    """Return group_ids from group_members. Uses request-scoped cache when provided."""
    if cache is not None and "group_ids" in cache:
        return cache["group_ids"]
    try:
        result = supabase.table("group_members")\
            .select("group_id")\
            .eq("user_id", user_id)\
            .execute()
        if not result.data:
            ids = []
        else:
            ids = [g["group_id"] for g in result.data]
        if cache is not None:
            cache["group_ids"] = ids
        return ids
    except Exception as e:
        logger.error(f"Error getting user group ids: {e}")
        return []


def get_accessible_role_ids(user_id: str, supabase: Client, cache: Optional[Dict[str, Any]] = None) -> List[str]:
    """Return role_ids from group_roles where group_id in user's groups. Uses request-scoped cache when provided."""
    if cache is not None and "role_ids" in cache:
        return cache["role_ids"]
    try:
        group_ids = get_user_group_ids(user_id, supabase, cache)
        if not group_ids:
            ids = []
        else:
            result = supabase.table("group_roles")\
                .select("role_id")\
                .in_("group_id", group_ids)\
                .execute()
            ids = list({r["role_id"] for r in result.data}) if result.data else []
        if cache is not None:
            cache["role_ids"] = ids
        return ids
    except Exception as e:
        logger.error(f"Error getting accessible role ids: {e}")
        return []


def get_accessible_permission_ids(user_id: str, supabase: Client, cache: Optional[Dict[str, Any]] = None) -> List[str]:
    """Return distinct permission_ids from role_permissions for user's accessible roles. Uses request-scoped cache when provided."""
    if cache is not None and "permission_ids" in cache:
        return cache["permission_ids"]
    try:
        role_ids = get_accessible_role_ids(user_id, supabase, cache)
        if not role_ids:
            ids = []
        else:
            result = supabase.table("role_permissions")\
                .select("permission_id")\
                .in_("role_id", role_ids)\
                .execute()
            ids = list({r["permission_id"] for r in result.data}) if result.data else []
        if cache is not None:
            cache["permission_ids"] = ids
        return ids
    except Exception as e:
        logger.error(f"Error getting accessible permission ids: {e}")
        return []


def check_workshop_access(workshop_id: str, user_data: dict, supabase: Client, workshop: Optional[Dict[str, Any]] = None) -> dict:
    """Allow if super_user, or member of workshop's environment's group, or owner when no environment. Optional workshop dict avoids duplicate fetch."""
    user_id = user_data["id"]
    if is_super_user(user_data, supabase):
        return user_data
    if workshop is None:
        workshop_result = supabase.table("workshops")\
            .select("environment_id, user_id")\
            .eq("id", workshop_id)\
            .single()\
            .execute()
        if not workshop_result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workshop not found"
            )
        workshop = workshop_result.data
    if workshop.get("environment_id"):
        return check_environment_access(workshop["environment_id"], user_data, supabase)
    if workshop.get("user_id") == user_id:
        return user_data
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You must be a member of this workshop's environment's group or the workshop owner to access it"
    )


def check_deployment_access(deployment_id: str, user_data: dict, supabase: Client) -> dict:
    """Allow if super_user or user has access to deployment's workshop (via group or owner)"""
    user_id = user_data["id"]
    if is_super_user(user_data, supabase):
        return user_data
    deployment_result = supabase.table("deployments")\
        .select("workshop_id, user_id")\
        .eq("id", deployment_id)\
        .single()\
        .execute()
    if not deployment_result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deployment not found"
        )
    deployment = deployment_result.data
    workshop_result = supabase.table("workshops")\
        .select("environment_id, user_id")\
        .eq("id", deployment["workshop_id"])\
        .single()\
        .execute()
    if not workshop_result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workshop not found"
        )
    workshop = workshop_result.data
    if workshop.get("environment_id"):
        return check_environment_access(workshop["environment_id"], user_data, supabase)
    if deployment.get("user_id") == user_id:
        return user_data
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You must be a member of this deployment's workshop's group or the deployment owner to access it"
    )


def user_can_access_user(current_user_id: str, target_user_id: str, supabase: Client) -> bool:
    """True if target is self or shares at least one group with current user"""
    if current_user_id == target_user_id:
        return True
    my_group_ids = get_user_group_ids(current_user_id, supabase)
    if not my_group_ids:
        return False
    member_result = supabase.table("group_members")\
        .select("id")\
        .eq("user_id", target_user_id)\
        .in_("group_id", my_group_ids)\
        .limit(1)\
        .execute()
    return bool(member_result.data)


def get_user_permissions(user_id: str, supabase: Client, cache: Optional[Dict[str, Any]] = None) -> List[str]:
    """Get all permissions for a user through their roles. Populates request-scoped cache when provided."""
    if cache is not None and "permission_names" in cache:
        return cache["permission_names"]
    try:
        role_ids = get_accessible_role_ids(user_id, supabase, cache)
        if not role_ids:
            names = []
            if cache is not None:
                cache["permission_names"] = names
                cache["permission_ids"] = []
            return names
        permissions_result = supabase.table("role_permissions")\
            .select("permission_id, permissions(name)")\
            .in_("role_id", role_ids)\
            .execute()
        permissions = set()
        permission_ids = set()
        if permissions_result.data:
            for rp in permissions_result.data:
                if rp.get("permission_id"):
                    permission_ids.add(rp["permission_id"])
                if rp.get("permissions") and rp["permissions"].get("name"):
                    permissions.add(rp["permissions"]["name"])
        names = list(permissions)
        if cache is not None:
            cache["permission_names"] = names
            cache["permission_ids"] = list(permission_ids)
        return names
    except Exception as e:
        logger.error(f"Error getting user permissions: {e}")
        return []


def require_permission(required_permission: str):
    """Factory function to create permission check dependency"""
    def check_permission(
        request: Request,
        user_data: dict = Depends(get_current_user_id),
        supabase: Client = Depends(get_supabase)
    ) -> dict:
        """Dependency to check if user has required permission"""
        user_id = user_data["id"]
        if is_super_user(user_data, supabase):
            return user_data
        cache = _get_request_cache(request)
        user_permissions = get_user_permissions(user_id, supabase, cache)
        if required_permission not in user_permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required: {required_permission}"
            )
        return user_data
    return check_permission


def get_access_cache(request: Request) -> Dict[str, Any]:
    """Dependency that returns request-scoped access cache (populated by require_permission when used)."""
    return _get_request_cache(request)


def check_group_admin(
    group_id: str,
    user_data: dict = Depends(get_current_user_id),
    supabase: Client = Depends(get_supabase)
) -> dict:
    """Check if user is admin/owner of a group or super user"""
    user_id = user_data["id"]
    
    # Super users bypass checks
    if is_super_user(user_data, supabase):
        return user_data
    
    # Check if user is owner/creator of the group
    group_result = supabase.table("groups")\
        .select("user_id")\
        .eq("id", group_id)\
        .single()\
        .execute()
    
    if group_result.data and group_result.data.get("user_id") == user_id:
        return user_data
    
    # Check if user is admin/owner in group_members
    member_result = supabase.table("group_members")\
        .select("role")\
        .eq("group_id", group_id)\
        .eq("user_id", user_id)\
        .in_("role", ["owner", "admin"])\
        .execute()
    
    if member_result.data:
        return user_data
    
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You must be a group owner or admin to perform this action"
    )


def check_group_member(
    group_id: str,
    user_data: dict = Depends(get_current_user_id),
    supabase: Client = Depends(get_supabase)
) -> dict:
    """Check if user is a member of a group or super user"""
    user_id = user_data["id"]
    
    # Super users bypass checks
    if is_super_user(user_data, supabase):
        return user_data
    
    # Check if user is a member
    member_result = supabase.table("group_members")\
        .select("id")\
        .eq("group_id", group_id)\
        .eq("user_id", user_id)\
        .execute()
    
    if member_result.data:
        return user_data
    
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You must be a member of this group"
    )


def check_environment_access(
    environment_id: str,
    user_data: dict,
    supabase: Client
) -> dict:
    """Check if user has access to an environment (must be member of environment's group)"""
    user_id = user_data["id"]
    
    # Super users bypass checks
    if is_super_user(user_data, supabase):
        return user_data
    
    # Get environment's group_id
    env_result = supabase.table("environments")\
        .select("group_id")\
        .eq("id", environment_id)\
        .single()\
        .execute()
    
    if not env_result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Environment not found"
        )
    
    group_id = env_result.data["group_id"]
    
    # Check if user is a member of that group
    member_result = supabase.table("group_members")\
        .select("id")\
        .eq("group_id", group_id)\
        .eq("user_id", user_id)\
        .execute()
    
    if not member_result.data:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You must be a member of this environment's group to access it"
        )
    
    return user_data
