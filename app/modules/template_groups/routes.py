from fastapi import APIRouter, Depends
from app.database.supabase_client import get_supabase
from app.modules.template_groups.schemas import (
    TemplateGroupCreate, TemplateGroupUpdate, TemplateGroupResponse, TemplateGroupWithCount,
    TemplateInGroupSummary,
)
from app.modules.template_groups.service import TemplateGroupService
from app.core.dependencies import require_permission
from supabase import Client
from typing import List, Dict, Union

router = APIRouter(prefix="/template-groups", tags=["template-groups"])


def get_template_group_service(supabase: Client = Depends(get_supabase)) -> TemplateGroupService:
    return TemplateGroupService(supabase)


@router.get("", response_model=List[Union[TemplateGroupResponse, TemplateGroupWithCount]])
async def list_template_groups(
    limit: int = 10,
    offset: int = 0,
    include_template_count: bool = False,
    user_data: Dict = Depends(require_permission("template_groups:read")),
    service: TemplateGroupService = Depends(get_template_group_service),
):
    """List all template groups. Use include_template_count=true to get template count per group."""
    return service.list_groups(limit=limit, offset=offset, include_template_count=include_template_count)


@router.post("", response_model=TemplateGroupResponse, status_code=201)
async def create_template_group(
    data: TemplateGroupCreate,
    user_data: Dict = Depends(require_permission("template_groups:create")),
    service: TemplateGroupService = Depends(get_template_group_service),
):
    """Create a new template group."""
    return service.create(data)


@router.get("/{group_id}/templates", response_model=List[TemplateInGroupSummary])
async def list_templates_in_group(
    group_id: str,
    user_data: Dict = Depends(require_permission("template_groups:read")),
    service: TemplateGroupService = Depends(get_template_group_service),
):
    """List templates in this template group (minimal info for preview)."""
    return service.list_templates_in_group(group_id)


@router.get("/{group_id}", response_model=TemplateGroupResponse)
async def get_template_group(
    group_id: str,
    user_data: Dict = Depends(require_permission("template_groups:read")),
    service: TemplateGroupService = Depends(get_template_group_service),
):
    """Get template group by ID."""
    return service.get_by_id(group_id)


@router.put("/{group_id}", response_model=TemplateGroupResponse)
async def update_template_group(
    group_id: str,
    data: TemplateGroupUpdate,
    user_data: Dict = Depends(require_permission("template_groups:update")),
    service: TemplateGroupService = Depends(get_template_group_service),
):
    """Update template group."""
    return service.update(group_id, data)


@router.delete("/{group_id}", status_code=204)
async def delete_template_group(
    group_id: str,
    user_data: Dict = Depends(require_permission("template_groups:delete")),
    service: TemplateGroupService = Depends(get_template_group_service),
):
    """Delete template group."""
    service.delete(group_id)
    return None


@router.post("/{group_id}/templates/{template_id}", status_code=204)
async def assign_template_to_group(
    group_id: str,
    template_id: str,
    user_data: Dict = Depends(require_permission("template_groups:assign")),
    service: TemplateGroupService = Depends(get_template_group_service),
):
    """Assign a template to a template group (idempotent)."""
    service.assign_template(group_id, template_id)
    return None


@router.delete("/{group_id}/templates/{template_id}", status_code=204)
async def unassign_template_from_group(
    group_id: str,
    template_id: str,
    user_data: Dict = Depends(require_permission("template_groups:assign")),
    service: TemplateGroupService = Depends(get_template_group_service),
):
    """Remove a template from a template group."""
    service.unassign_template(group_id, template_id)
    return None
