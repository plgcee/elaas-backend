from pydantic import BaseModel, EmailStr
from typing import Optional


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    email: str


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None


class RegisterResponse(BaseModel):
    user_id: str
    email: str
    message: str


class SetSuperUserRequest(BaseModel):
    user_id: str
    is_super_user: bool = True
