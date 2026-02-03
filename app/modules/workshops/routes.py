from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from app.database.supabase_client import get_supabase
from app.modules.workshops.schemas import WorkshopCreate, WorkshopUpdate, WorkshopResponse, WorkshopDeployRequest
from app.modules.workshops.service import WorkshopService
from app.modules.deployments.service import DeploymentService
from app.modules.deployments.schemas import DeploymentCreate, DeploymentResponse
from app.modules.deployments.deployment_worker import deploy_workshop_async
from app.modules.templates.service import TemplateService
from app.core.dependencies import require_permission, get_current_user_id, get_access_cache, get_user_group_ids, check_workshop_access, is_super_user
from supabase import Client
from typing import List, Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/workshops", tags=["workshops"])


def get_workshop_service(supabase: Client = Depends(get_supabase)) -> WorkshopService:
    return WorkshopService(supabase)


def get_deployment_service(supabase: Client = Depends(get_supabase)) -> DeploymentService:
    return DeploymentService(supabase)


def get_template_service(supabase: Client = Depends(get_supabase)) -> TemplateService:
    return TemplateService(supabase)


@router.post("", response_model=WorkshopResponse, status_code=201)
async def create_workshop(
    workshop_data: WorkshopCreate,
    user_data: Dict = Depends(require_permission("workshops:create")),
    service: WorkshopService = Depends(get_workshop_service)
):
    """Create a new workshop"""
    return service.create_workshop(workshop_data, user_data["id"])


def _obfuscate_terraform_vars(vars_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Remove AWS credential keys from user-provided vars."""
    if not vars_dict:
        return {}
    return {k: v for k, v in vars_dict.items()
            if k not in ("aws_access_key_id", "aws_secret_access_key", "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY")}


@router.post("/{workshop_id}/deploy", response_model=DeploymentResponse, status_code=201)
async def deploy_workshop(
    workshop_id: str,
    background_tasks: BackgroundTasks,
    deploy_request: Optional[WorkshopDeployRequest] = None,
    user_data: Dict = Depends(require_permission("workshops:deploy")),
    workshop_service: WorkshopService = Depends(get_workshop_service),
    deployment_service: DeploymentService = Depends(get_deployment_service),
    template_service: TemplateService = Depends(get_template_service),
    supabase: Client = Depends(get_supabase)
):
    """
    Deploy a workshop with Terraform.
    Single-template: one deployment. Template-group: one deployment per template in the group.
    Uses terraform_vars from the workshop (per-template keyed by template_id for groups). Optionally override via request body for single-template.
    """
    check_workshop_access(workshop_id, user_data, supabase)
    workshop = workshop_service.get_workshop_by_id(workshop_id)
    template_ids = workshop_service.get_template_ids_for_workshop(workshop)

    if workshop.template_group_id:
        # Group workshop: one deployment per template; terraform_vars keyed by template_id
        all_vars = workshop.terraform_vars or {}
        request_vars = (deploy_request.terraform_vars if deploy_request and deploy_request.terraform_vars else None) or {}
        # Request body can be keyed by template_id: { "template_id_1": {...}, "template_id_2": {...} }
        is_per_template = (
            len(request_vars) > 0
            and all(k in template_ids for k in request_vars.keys())
            and all(isinstance(v, dict) for v in request_vars.values())
        )
        if is_per_template:
            per_template_vars = {
                tid: _obfuscate_terraform_vars((request_vars.get(tid) or all_vars.get(tid) or {}))
                for tid in template_ids
            }
        else:
            # Shared override (flat dict) or no request vars: use request as shared, else workshop per-template
            if request_vars:
                shared = _obfuscate_terraform_vars(request_vars)
                per_template_vars = {tid: shared for tid in template_ids}
            else:
                per_template_vars = {tid: _obfuscate_terraform_vars(all_vars.get(tid) or {}) for tid in template_ids}

        first_deployment = None
        for template_id in template_ids:
            template = template_service.get_template_by_id(template_id)
            if not template.zip_file_path:
                raise HTTPException(status_code=400, detail=f"Template {template_id} ZIP file not found")
            vars_for_template = per_template_vars.get(template_id) or {}
            deployment_data = DeploymentCreate(
                workshop_id=workshop_id,
                template_id=template_id,
                terraform_vars=vars_for_template,
            )
            deployment = deployment_service.create_deployment(deployment_data, user_data["id"])
            if first_deployment is None:
                first_deployment = deployment
            background_tasks.add_task(
                deploy_workshop_async,
                deployment_id=deployment.id,
                workshop_id=workshop_id,
                template_id=template_id,
                terraform_vars=vars_for_template,
                supabase=supabase,
            )
        workshop_service.update_workshop_status(workshop_id, "deploying")
        return first_deployment

    # Single-template workshop (legacy)
    template_id = workshop.template_id
    template = template_service.get_template_by_id(template_id)
    if not template.zip_file_path:
        raise HTTPException(status_code=400, detail="Template ZIP file not found")
    terraform_vars = (deploy_request.terraform_vars if deploy_request and deploy_request.terraform_vars
                     else (workshop.terraform_vars or {}))
    safe_terraform_vars = _obfuscate_terraform_vars(terraform_vars)
    deployment_data = DeploymentCreate(
        workshop_id=workshop_id,
        template_id=template_id,
        terraform_vars=safe_terraform_vars,
    )
    deployment = deployment_service.create_deployment(deployment_data, user_data["id"])
    workshop_service.update_workshop_status(workshop_id, "deploying")
    background_tasks.add_task(
        deploy_workshop_async,
        deployment_id=deployment.id,
        workshop_id=workshop_id,
        template_id=template_id,
        terraform_vars=safe_terraform_vars,
        supabase=supabase,
    )
    return deployment


@router.get("", response_model=List[WorkshopResponse])
async def list_workshops(
    user_id: Optional[str] = None,
    environment_id: Optional[str] = None,
    limit: int = 10,
    offset: int = 0,
    user_data: Dict = Depends(require_permission("workshops:read")),
    service: WorkshopService = Depends(get_workshop_service),
    supabase: Client = Depends(get_supabase),
    cache: Dict = Depends(get_access_cache)
):
    """List workshops visible to user (in their groups' environments or owned when no env). Super_user sees all."""
    accessible_environment_ids = None
    current_user_id = None
    if not is_super_user(user_data, supabase):
        group_ids = get_user_group_ids(user_data["id"], supabase, cache)
        if group_ids:
            env_result = supabase.table("environments").select("id").in_("group_id", group_ids).execute()
            accessible_environment_ids = [e["id"] for e in env_result.data] if env_result.data else []
        current_user_id = user_data["id"]
    return service.list_workshops(
        user_id=user_id,
        environment_id=environment_id,
        accessible_environment_ids=accessible_environment_ids,
        current_user_id=current_user_id,
        limit=limit,
        offset=offset
    )


@router.get("/{workshop_id}", response_model=WorkshopResponse)
async def get_workshop(
    workshop_id: str,
    user_data: Dict = Depends(require_permission("workshops:read")),
    service: WorkshopService = Depends(get_workshop_service),
    supabase: Client = Depends(get_supabase)
):
    """Get workshop by ID (only if member of workshop's environment's group or owner when no env). Single DB fetch."""
    workshop = service.get_workshop_by_id(workshop_id)
    workshop_dict = getattr(workshop, "model_dump", getattr(workshop, "dict", lambda: workshop.__dict__))()
    check_workshop_access(workshop_id, user_data, supabase, workshop=workshop_dict)
    return workshop


@router.put("/{workshop_id}", response_model=WorkshopResponse)
async def update_workshop(
    workshop_id: str,
    workshop_data: WorkshopUpdate,
    user_data: Dict = Depends(require_permission("workshops:update")),
    service: WorkshopService = Depends(get_workshop_service),
    supabase: Client = Depends(get_supabase)
):
    """Update workshop (only if member of workshop's environment's group or owner when no env)"""
    check_workshop_access(workshop_id, user_data, supabase)
    return service.update_workshop(workshop_id, workshop_data)


@router.delete("/{workshop_id}", status_code=204)
async def delete_workshop(
    workshop_id: str,
    user_data: Dict = Depends(require_permission("workshops:delete")),
    service: WorkshopService = Depends(get_workshop_service),
    supabase: Client = Depends(get_supabase)
):
    """Delete workshop (only if member of workshop's environment's group or owner when no env)"""
    check_workshop_access(workshop_id, user_data, supabase)
    service.delete_workshop(workshop_id)
    return None
