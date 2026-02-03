from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    phone: Optional[str] = None
    bio: Optional[str] = None


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    phone: Optional[str] = None
    bio: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class UserWithGroupsResponse(BaseModel):
    id: str
    email: str
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    phone: Optional[str] = None
    bio: Optional[str] = None
    groups: List[dict]  # Group info with membership role
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class UserGroupAdd(BaseModel):
    group_id: str
    role: Optional[str] = "member"  # owner, admin, member


class UserGroupResponse(BaseModel):
    id: str
    group_id: str
    user_id: str
    role: str
    created_at: datetime
    
    class Config:
        from_attributes = True
