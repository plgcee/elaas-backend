from pydantic import BaseModel, model_validator
from typing import Optional, Dict, Any
from datetime import datetime, timedelta


class WorkshopCreate(BaseModel):
    name: str
    description: Optional[str] = None
    template_id: Optional[str] = None  # legacy single-template; use template_group_id for group deploy
    template_group_id: Optional[str] = None
    environment_id: Optional[str] = None
    terraform_vars: Optional[Dict[str, Any]] = None  # flat for single-template; keyed by template_id for group
    ttl_hours: Optional[int] = 48  # Default 48 hours

    @model_validator(mode="after")
    def require_template_or_group(self):
        if not self.template_id and not self.template_group_id:
            raise ValueError("Either template_id or template_group_id must be set")
        if self.template_id and self.template_group_id:
            raise ValueError("Cannot set both template_id and template_group_id")
        return self


class WorkshopUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    terraform_vars: Optional[Dict[str, Any]] = None
    ttl_hours: Optional[int] = None


class WorkshopResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    template_id: Optional[str] = None
    template_group_id: Optional[str] = None
    user_id: str
    environment_id: Optional[str] = None
    terraform_vars: Optional[Dict[str, Any]] = None
    status: str
    fargate_task_arn: Optional[str] = None
    deployment_output: Optional[Dict[str, Any]] = None
    ttl_hours: Optional[int] = 48
    expires_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class WorkshopDeployRequest(BaseModel):
    terraform_vars: Dict[str, Any]
