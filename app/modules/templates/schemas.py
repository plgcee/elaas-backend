from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime


class TemplateCreate(BaseModel):
    name: str
    description: Optional[str] = None
    version: str = "1.0.0"
    environment: Optional[str] = None


class TemplateUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    version: Optional[str] = None
    environment: Optional[str] = None


class TemplateResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    version: str
    user_id: str
    zip_file_path: Optional[str] = None
    variables_json: Optional[Dict[str, Any]] = None
    ui_variables_json: Optional[Dict[str, Any]] = None
    validation_issues: Optional[List[str]] = None
    environment: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    group_ids: Optional[List[str]] = None

    class Config:
        from_attributes = True


class TemplateUploadResponse(BaseModel):
    template_id: str
    message: str
    file_path: str


class TemplateUploadWithDataRequest(BaseModel):
    name: str
    description: Optional[str] = None
    version: str = "1.0.0"
    environment: Optional[str] = None


class TemplateUploadWithDataResponse(BaseModel):
    template_id: str
    name: str
    description: Optional[str] = None
    version: str
    zip_file_path: str
    variables_json: Dict[str, Any]
    ui_variables_json: Optional[Dict[str, Any]] = None
    validation_passed: bool
    validation_issues: List[str]
    environment: Optional[str] = None
    message: str
