from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class PermissionCreate(BaseModel):
    name: str
    resource: str
    action: str
    description: Optional[str] = None


class PermissionUpdate(BaseModel):
    name: Optional[str] = None
    resource: Optional[str] = None
    action: Optional[str] = None
    description: Optional[str] = None


class PermissionResponse(BaseModel):
    id: str
    name: str
    resource: str
    action: str
    description: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class RoleCreate(BaseModel):
    name: str
    description: Optional[str] = None


class RoleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class RoleResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class RoleWithPermissionsResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    permissions: List[PermissionResponse]
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class RolePermissionAssign(BaseModel):
    permission_id: str


class RolePermissionResponse(BaseModel):
    id: str
    role_id: str
    permission_id: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class BulkPermissionAssign(BaseModel):
    permission_ids: List[str]


class BulkPermissionAssignResponse(BaseModel):
    role_id: str
    assigned_count: int
    skipped_count: int
    assigned_permissions: List[RolePermissionResponse]
    message: str


class BulkPermissionUpdate(BaseModel):
    permission_ids: List[str]
