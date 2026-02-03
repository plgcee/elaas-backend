from fastapi import APIRouter, Depends
from app.database.supabase_client import get_supabase
from app.modules.environments.schemas import (
    EnvironmentCreate, EnvironmentUpdate, EnvironmentResponse, EnvironmentWithWorkshopsResponse
)
from app.modules.environments.service import EnvironmentService
from app.core.dependencies import require_permission, get_current_user_id, check_group_admin, is_super_user, check_environment_access
from supabase import Client
from typing import List, Optional, Dict

router = APIRouter(prefix="/environments", tags=["environments"])


def get_environment_service(supabase: Client = Depends(get_supabase)) -> EnvironmentService:
    return EnvironmentService(supabase)


@router.post("", response_model=EnvironmentResponse, status_code=201)
async def create_environment(
    environment_data: EnvironmentCreate,
    user_data: Dict = Depends(require_permission("environments:create")),
    service: EnvironmentService = Depends(get_environment_service)
):
    """Create a new environment (requires environments:create permission and group membership)"""
    return service.create_environment(environment_data, user_data["id"])


@router.get("", response_model=List[EnvironmentResponse])
async def list_environments(
    group_id: Optional[str] = None,
    limit: int = 10,
    offset: int = 0,
    user_data: Dict = Depends(require_permission("environments:read")),
    service: EnvironmentService = Depends(get_environment_service)
):
    """List environments for user's groups (requires environments:read permission)"""
    return service.list_environments(
        user_id=user_data["id"],
        group_id=group_id,
        limit=limit,
        offset=offset
    )


@router.get("/{environment_id}", response_model=EnvironmentResponse)
async def get_environment(
    environment_id: str,
    user_data: Dict = Depends(require_permission("environments:read")),
    service: EnvironmentService = Depends(get_environment_service),
    supabase: Client = Depends(get_supabase)
):
    """Get environment by ID (requires environments:read permission and group membership)"""
    # Check environment access
    check_environment_access(environment_id, user_data, supabase)
    return service.get_environment_by_id(environment_id)


@router.put("/{environment_id}", response_model=EnvironmentResponse)
async def update_environment(
    environment_id: str,
    environment_data: EnvironmentUpdate,
    current_user: Dict = Depends(get_current_user_id),
    service: EnvironmentService = Depends(get_environment_service),
    supabase: Client = Depends(get_supabase)
):
    """Update environment (requires environments:update permission and group admin)"""
    # Get environment to check group
    environment = service.get_environment_by_id(environment_id)
    
    # Check if user is group admin
    if not is_super_user(current_user, supabase):
        check_group_admin(environment.group_id, current_user, supabase)
    
    return service.update_environment(environment_id, environment_data)


@router.delete("/{environment_id}", status_code=204)
async def delete_environment(
    environment_id: str,
    current_user: Dict = Depends(get_current_user_id),
    service: EnvironmentService = Depends(get_environment_service),
    supabase: Client = Depends(get_supabase)
):
    """Delete environment (requires environments:delete permission and group admin)"""
    # Get environment to check group
    environment = service.get_environment_by_id(environment_id)
    
    # Check if user is group admin
    if not is_super_user(current_user, supabase):
        check_group_admin(environment.group_id, current_user, supabase)
    
    service.delete_environment(environment_id)
    return None


@router.get("/{environment_id}/workshops", response_model=EnvironmentWithWorkshopsResponse)
async def get_environment_with_workshops(
    environment_id: str,
    user_data: Dict = Depends(require_permission("environments:read")),
    service: EnvironmentService = Depends(get_environment_service),
    supabase: Client = Depends(get_supabase)
):
    """Get environment with nested workshops (requires environments:read permission and group membership)"""
    # Check environment access
    check_environment_access(environment_id, user_data, supabase)
    return service.get_environment_with_workshops(environment_id)
