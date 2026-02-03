from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from app.database.supabase_client import get_supabase
from app.modules.deployments.schemas import DeploymentResponse, DeploymentLogsResponse
from app.modules.deployments.service import DeploymentService
from app.modules.deployments.destroy_worker import destroy_workshop_async
from app.modules.deployments import process_registry
from app.modules.workshops.service import WorkshopService
from app.modules.templates.service import TemplateService
from app.core.dependencies import require_permission, check_deployment_access, check_workshop_access
from supabase import Client
from typing import List, Dict


def get_workshop_service(supabase: Client = Depends(get_supabase)) -> WorkshopService:
    return WorkshopService(supabase)


def get_template_service(supabase: Client = Depends(get_supabase)) -> TemplateService:
    return TemplateService(supabase)

router = APIRouter(prefix="/deployments", tags=["deployments"])


def get_deployment_service(supabase: Client = Depends(get_supabase)) -> DeploymentService:
    return DeploymentService(supabase)


@router.get("/{deployment_id}", response_model=DeploymentResponse)
async def get_deployment(
    deployment_id: str,
    user_data: Dict = Depends(require_permission("deployments:read")),
    service: DeploymentService = Depends(get_deployment_service),
    supabase: Client = Depends(get_supabase)
):
    """Get deployment by ID (only if user has access via workshop's group or is deployment owner)"""
    check_deployment_access(deployment_id, user_data, supabase)
    return service.get_deployment_by_id(deployment_id)


@router.get("/workshop/{workshop_id}", response_model=List[DeploymentResponse])
async def list_deployments_by_workshop(
    workshop_id: str,
    user_data: Dict = Depends(require_permission("deployments:read")),
    service: DeploymentService = Depends(get_deployment_service),
    supabase: Client = Depends(get_supabase)
):
    """List all deployments for a workshop (only if user has access to the workshop via group)"""
    check_workshop_access(workshop_id, user_data, supabase)
    return service.list_deployments_by_workshop(workshop_id)


@router.get("/{deployment_id}/logs", response_model=DeploymentLogsResponse)
async def get_deployment_logs(
    deployment_id: str,
    user_data: Dict = Depends(require_permission("deployments:read")),
    service: DeploymentService = Depends(get_deployment_service),
    supabase: Client = Depends(get_supabase)
):
    """
    Poll for deployment logs.
    Returns current logs and deployment status.
    """
    check_deployment_access(deployment_id, user_data, supabase)
    deployment = service.get_deployment_by_id(deployment_id)
    return DeploymentLogsResponse(
        deployment_id=deployment.id,
        logs=deployment.deployment_logs or [],
        status=deployment.status,
        has_more=deployment.status in ["pending", "deploying"]
    )


@router.post("/{deployment_id}/cancel", response_model=DeploymentResponse)
async def cancel_deployment(
    deployment_id: str,
    user_data: Dict = Depends(require_permission("deployments:cancel")),
    deployment_service: DeploymentService = Depends(get_deployment_service),
    workshop_service: WorkshopService = Depends(get_workshop_service),
    supabase: Client = Depends(get_supabase)
):
    """Cancel an in-progress deployment. Terminates the Terraform process and marks deployment/workshop as cancelled/pending."""
    check_deployment_access(deployment_id, user_data, supabase)
    deployment = deployment_service.get_deployment_by_id(deployment_id)
    if deployment.status not in ("pending", "deploying"):
        raise HTTPException(status_code=400, detail="Deployment cannot be cancelled")
    workshop_id = deployment.workshop_id
    process_registry.terminate(deployment_id)
    deployment_service.update_deployment_status(deployment_id, "cancelled")
    workshop_service.update_workshop_status(workshop_id, "pending")
    return deployment_service.get_deployment_by_id(deployment_id)


@router.post("/workshop/{workshop_id}/destroy", response_model=DeploymentResponse, status_code=201)
async def destroy_workshop(
    workshop_id: str,
    background_tasks: BackgroundTasks,
    user_data: Dict = Depends(require_permission("workshops:destroy")),
    workshop_service: WorkshopService = Depends(get_workshop_service),
    template_service: TemplateService = Depends(get_template_service),
    deployment_service: DeploymentService = Depends(get_deployment_service),
    supabase: Client = Depends(get_supabase)
):
    """
    Destroy infrastructure for a workshop using its state file(s).
    Single-template: one destroy. Template-group: one destroy per deployed template in the workshop.
    """
    check_workshop_access(workshop_id, user_data, supabase)
    workshop = workshop_service.get_workshop_by_id(workshop_id)

    if workshop.status not in ["deployed", "failed"]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot destroy workshop with status '{workshop.status}'. Workshop must be deployed first."
        )

    # One state per (workshop_id, template_id); create a new deployment per template for destroy so user can track in UI
    deployments = deployment_service.list_deployments_by_workshop(workshop_id)
    eligible = [d for d in deployments if d.status in ("deployed", "failed")]

    if getattr(workshop, "template_group_id", None):
        # Group workshop: latest deployment per template = templates that have deployed state
        seen_templates = set()
        template_ids_to_destroy = []
        for d in eligible:
            if d.template_id not in seen_templates:
                seen_templates.add(d.template_id)
                template_ids_to_destroy.append(d.template_id)
        if not template_ids_to_destroy:
            raise HTTPException(status_code=400, detail="No deployed resources to destroy for this workshop")
        workshop_service.update_workshop_status(workshop_id, "destroying")
        from app.modules.deployments.schemas import DeploymentCreate
        created = []
        for template_id in template_ids_to_destroy:
            deployment_data = DeploymentCreate(
                workshop_id=workshop_id,
                template_id=template_id,
                terraform_vars={},
            )
            deployment = deployment_service.create_deployment(deployment_data, user_data["id"])
            created.append(deployment)
            background_tasks.add_task(
                destroy_workshop_async,
                workshop_id=workshop_id,
                template_id=template_id,
                supabase=supabase,
                deployment_id=deployment.id,
            )
        return created[0]
    else:
        # Single-template: create one new deployment for destroy
        if not eligible:
            raise HTTPException(status_code=400, detail="No deployed resources to destroy for this workshop")
        template_id = workshop.template_id
        if not template_id:
            raise HTTPException(status_code=400, detail="Workshop has no template_id")
        template = template_service.get_template_by_id(template_id)
        if not template.zip_file_path:
            raise HTTPException(status_code=400, detail="Template ZIP file not found")
        from app.modules.deployments.schemas import DeploymentCreate
        deployment_data = DeploymentCreate(
            workshop_id=workshop_id,
            template_id=template_id,
            terraform_vars={},
        )
        deployment = deployment_service.create_deployment(deployment_data, user_data["id"])
        workshop_service.update_workshop_status(workshop_id, "destroying")
        background_tasks.add_task(
            destroy_workshop_async,
            workshop_id=workshop_id,
            template_id=template_id,
            supabase=supabase,
            deployment_id=deployment.id,
        )
        return deployment
