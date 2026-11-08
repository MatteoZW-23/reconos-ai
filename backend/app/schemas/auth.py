from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional
from datetime import datetime
from app.models.user import UserRole

class Token(BaseModel):
    access_token: str
    token_type: str
    user_id: str
    organization_id: str
    organization_name: str
    role: UserRole
    full_name: str
    email: str

class TokenPayload(BaseModel):
    sub: Optional[str] = None
    org_id: Optional[str] = None
    role: Optional[str] = None
    branch_id: Optional[str] = None

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str
    role: UserRole = UserRole.ACCOUNTANT
    organization_id: Optional[str] = None
    branch_id: Optional[str] = None

    @field_validator('password')
    @classmethod
    def password_bytes_limit(cls, value: str) -> str:
        if len(value.encode('utf-8')) > 72:
            raise ValueError('Password must be at most 72 UTF-8 bytes')
        return value

class UserResponse(BaseModel):
    id: str
    organization_id: str
    branch_id: Optional[str] = None
    email: str
    full_name: str
    role: UserRole
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

class OnboardingRequest(BaseModel):
    organization_name: str
    default_currency: str = "USD"
    admin_full_name: str
    admin_email: EmailStr
    admin_password: str = Field(min_length=8)
    branch_name: Optional[str] = "Headquarters"
    branch_code: Optional[str] = "HQ-01"

    @field_validator('admin_password')
    @classmethod
    def password_bytes_limit(cls, value: str) -> str:
        if len(value.encode('utf-8')) > 72:
            raise ValueError('Password must be at most 72 UTF-8 bytes')
        return value
