from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class GroupCreate(BaseModel):
    name: str
    description: Optional[str] = None


class GroupUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class GroupResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    user_id: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class GroupWithRolesResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    user_id: str
    roles: List[dict]  # RoleResponse from roles module
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class GroupMemberAdd(BaseModel):
    user_id: str


class GroupMemberResponse(BaseModel):
    id: str
    group_id: str
    user_id: str
    role: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class GroupRoleAssign(BaseModel):
    role_id: str


class GroupRoleResponse(BaseModel):
    id: str
    group_id: str
    role_id: str
    created_at: datetime
    
    class Config:
        from_attributes = True
