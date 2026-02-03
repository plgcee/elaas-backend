from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class EnvironmentCreate(BaseModel):
    name: str
    description: Optional[str] = None
    group_id: str


class EnvironmentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class EnvironmentResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    group_id: str
    user_id: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    
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
    workshops: Optional[List[dict]] = None
    
    class Config:
        from_attributes = True
