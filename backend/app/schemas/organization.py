from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class BranchCreate(BaseModel):
    name: str
    code: str
    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = "Zimbabwe"

class BranchResponse(BaseModel):
    id: str
    organization_id: str
    name: str
    code: str
    address: Optional[str] = None
    city: Optional[str] = None
    country: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

class OrganizationCreate(BaseModel):
    name: str
    default_currency: str = "USD"

class OrganizationResponse(BaseModel):
    id: str
    name: str
    slug: str
    default_currency: str
    is_active: bool
    created_at: datetime
    branches: list[BranchResponse] = []

    class Config:
        from_attributes = True
