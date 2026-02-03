from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime


class DeploymentCreate(BaseModel):
    workshop_id: str
    template_id: str
    terraform_vars: Dict[str, Any]


class DeploymentResponse(BaseModel):
    id: str
    workshop_id: str
    template_id: str
    user_id: str
    status: str
    terraform_vars: Dict[str, Any]
    deployment_logs: List[str]
    terraform_state_key: Optional[str] = None
    deployment_output: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class DeploymentLogsResponse(BaseModel):
    deployment_id: str
    logs: List[str]
    status: str
    has_more: bool = False
