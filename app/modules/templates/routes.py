from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from app.database.supabase_client import get_supabase
from app.modules.templates.schemas import (
    TemplateCreate, TemplateUpdate, TemplateResponse, TemplateUploadResponse,
    TemplateUploadWithDataRequest, TemplateUploadWithDataResponse
)
from app.modules.templates.service import TemplateService
from app.core.dependencies import require_permission, get_current_user_id
from supabase import Client
from typing import List, Optional, Dict

router = APIRouter(prefix="/templates", tags=["templates"])


def get_template_service(supabase: Client = Depends(get_supabase)) -> TemplateService:
    return TemplateService(supabase)


@router.get("", response_model=List[TemplateResponse])
async def list_templates(
    user_id: Optional[str] = None,
    template_group_id: Optional[str] = None,
    limit: int = 10,
    offset: int = 0,
    include_groups: bool = False,
    user_data: Dict = Depends(require_permission("templates:read")),
    service: TemplateService = Depends(get_template_service),
):
    """List all templates, optionally filtered by user or template group."""
    return service.list_templates(user_id=user_id, template_group_id=template_group_id, limit=limit, offset=offset, include_groups=include_groups)


@router.post("", response_model=TemplateResponse, status_code=201)
async def create_template(
    template_data: TemplateCreate,
    user_data: Dict = Depends(require_permission("templates:create")),
    service: TemplateService = Depends(get_template_service)
):
    """Create a new Terraform template"""
    return service.create_template(template_data, user_data["id"])


@router.post("/upload-with-data", response_model=TemplateUploadWithDataResponse, status_code=201)
async def upload_template_with_data(
    file: UploadFile = File(...),
    name: str = Form(...),
    description: Optional[str] = Form(None),
    version: str = Form("1.0.0"),
    environment: Optional[str] = Form(None),
    user_data: Dict = Depends(require_permission("templates:create")),
    service: TemplateService = Depends(get_template_service)
):
    """
    Upload Terraform ZIP file with template metadata.
    Validates the Terraform files, parses variables, stores ZIP in S3,
    and stores parsed JSON in Postgres. Returns the variables JSON
    for frontend form generation. Only ZIP files are accepted.
    """
    if not file.filename or not file.filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="Only ZIP files are accepted")
    template_data = TemplateUploadWithDataRequest(
        name=name,
        description=description,
        version=version,
        environment=environment
    )
    
    return await service.upload_and_process_template(template_data, file, user_data["id"])


@router.put("/{template_id}/upload-with-data", response_model=TemplateUploadWithDataResponse)
async def update_template_with_data(
    template_id: str,
    file: UploadFile = File(...),
    version: Optional[str] = Form(None),
    user_data: Dict = Depends(require_permission("templates:update")),
    service: TemplateService = Depends(get_template_service)
):
    """
    Update an existing template by uploading a new ZIP file version.
    Validates the Terraform files, parses variables, stores ZIP in S3,
    and updates the template record with new version and variables. Only ZIP files are accepted.
    """
    if not file.filename or not file.filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="Only ZIP files are accepted")
    return await service.update_template_with_file(template_id, file, version, user_data["id"])


@router.post("/{template_id}/upload", response_model=TemplateUploadResponse)
async def upload_template(
    template_id: str,
    file: UploadFile = File(...),
    user_data: Dict = Depends(require_permission("templates:upload")),
    service: TemplateService = Depends(get_template_service)
):
    """Upload Terraform template ZIP file"""
    if not file.filename.endswith('.zip'):
        raise HTTPException(status_code=400, detail="File must be a ZIP file")
    
    file_path = await service.upload_template_file(template_id, file)
    return TemplateUploadResponse(
        template_id=template_id,
        message="Template uploaded successfully",
        file_path=file_path
    )


@router.get("/{template_id}", response_model=TemplateResponse)
async def get_template(
    template_id: str,
    include_groups: bool = False,
    user_data: Dict = Depends(require_permission("templates:read")),
    service: TemplateService = Depends(get_template_service),
):
    """Get template by ID."""
    return service.get_template_by_id(template_id, include_groups=include_groups)


@router.put("/{template_id}", response_model=TemplateResponse)
async def update_template(
    template_id: str,
    template_data: TemplateUpdate,
    user_data: Dict = Depends(require_permission("templates:update")),
    service: TemplateService = Depends(get_template_service)
):
    """Update template"""
    return service.update_template(template_id, template_data)


@router.delete("/{template_id}", status_code=204)
async def delete_template(
    template_id: str,
    user_data: Dict = Depends(require_permission("templates:delete")),
    service: TemplateService = Depends(get_template_service)
):
    """Delete template"""
    service.delete_template(template_id)
    return None
