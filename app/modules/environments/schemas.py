from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class EnvironmentCreate(BaseModel):
    name: str
    description: Optional[str] = None
    group_id: str
    ttl_hours: Optional[int] = None


class EnvironmentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    ttl_hours: Optional[int] = None


class EnvironmentResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    group_id: str
    user_id: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    workshop_count: Optional[int] = None
    ttl_hours: Optional[int] = None
    expires_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class EnvironmentWithWorkshopsResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    group_id: str
    user_id: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    ttl_hours: Optional[int] = None
    expires_at: Optional[datetime] = None
    workshops: Optional[List[dict]] = None

    class Config:
        from_attributes = True
