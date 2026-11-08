from pydantic import BaseModel
from typing import Optional
from decimal import Decimal
from datetime import datetime
from app.models.financial_account import AccountType

class AccountCreate(BaseModel):
    name: str
    account_type: AccountType
    provider_name: str
    account_number: str
    currency: str = "USD"
    opening_balance: Decimal = Decimal("0.0000")
    branch_id: Optional[str] = None

class AccountResponse(BaseModel):
    id: str
    organization_id: str
    branch_id: Optional[str] = None
    name: str
    account_type: AccountType
    provider_name: str
    account_number: str
    currency: str
    opening_balance: Decimal
    current_balance: Decimal
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True
