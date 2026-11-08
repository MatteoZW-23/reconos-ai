from pydantic import BaseModel, Field, field_validator
from typing import Optional
from decimal import Decimal
from datetime import date, datetime
from app.models.shift import ShiftStatus

class ShiftCreate(BaseModel):
    branch_id: str
    cashier_name: str = Field(min_length=1, max_length=255)
    shift_date: date
    shift_number: str = Field(min_length=1, max_length=50)
    opening_cash: Decimal = Field(ge=0, max_digits=18, decimal_places=4, allow_inf_nan=False)
    cash_sales: Decimal = Field(ge=0, max_digits=18, decimal_places=4, allow_inf_nan=False)
    mobile_money_sales: Decimal = Field(ge=0, max_digits=18, decimal_places=4, allow_inf_nan=False)
    card_sales: Decimal = Field(ge=0, max_digits=18, decimal_places=4, allow_inf_nan=False)
    cash_payouts: Decimal = Field(default=Decimal("0.0000"), ge=0, max_digits=18, decimal_places=4, allow_inf_nan=False)
    closing_cash_counted: Decimal = Field(ge=0, max_digits=18, decimal_places=4, allow_inf_nan=False)

    @field_validator('shift_number', 'cashier_name')
    @classmethod
    def clean_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError('Value cannot be blank')
        return value

class ShiftVerify(BaseModel):
    status: ShiftStatus
    supervisor_notes: Optional[str] = Field(default=None, max_length=500)

class ShiftResponse(BaseModel):
    id: str
    organization_id: str
    branch_id: str
    cashier_id: Optional[str] = None
    cashier_name: str
    shift_date: date
    shift_number: str
    opening_cash: Decimal
    cash_sales: Decimal
    mobile_money_sales: Decimal
    card_sales: Decimal
    cash_payouts: Decimal
    closing_cash_counted: Decimal
    system_expected_cash: Decimal
    cash_discrepancy: Decimal
    status: ShiftStatus
    supervisor_notes: Optional[str] = None
    verified_by_id: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
