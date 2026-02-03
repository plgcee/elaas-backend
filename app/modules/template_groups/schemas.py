from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class TemplateGroupCreate(BaseModel):
    name: str
    description: Optional[str] = None


class TemplateGroupUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class TemplateGroupResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TemplateGroupWithCount(TemplateGroupResponse):
    template_count: int = 0


class TemplateInGroupSummary(BaseModel):
    """Minimal template info for listing templates in a group."""
    id: str
    name: str
    description: Optional[str] = None
