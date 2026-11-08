from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime

from app.models.transaction import NormalizedTransaction, TransactionType
from app.models.financial_account import FinancialAccount
from app.schemas.reconciliation import BalanceCheckResponse
from app.utils.decimal_math import verify_balance_equation

class BalanceChecker:
    @staticmethod
    def check_account_balance(
        db: Session,
        account_id: str,
        organization_id: str,
        date_from: datetime,
        date_to: datetime
    ) -> BalanceCheckResponse:
        account = db.query(FinancialAccount).filter(
            FinancialAccount.id == account_id,
            FinancialAccount.organization_id == organization_id
        ).first()

        if not account:
            raise ValueError("Financial account not found")

        # Sum credits
        credits_res = db.query(func.coalesce(func.sum(NormalizedTransaction.amount), 0)).filter(
            NormalizedTransaction.organization_id == organization_id,
            NormalizedTransaction.financial_account_id == account_id,
            NormalizedTransaction.currency == account.currency,
            NormalizedTransaction.transaction_type == TransactionType.CREDIT,
            NormalizedTransaction.transaction_date >= date_from,
            NormalizedTransaction.transaction_date <= date_to,
            NormalizedTransaction.is_duplicate == False
        ).scalar()
        total_credits = Decimal(str(credits_res))

        # Sum debits
        debits_res = db.query(func.coalesce(func.sum(NormalizedTransaction.amount), 0)).filter(
            NormalizedTransaction.organization_id == organization_id,
            NormalizedTransaction.financial_account_id == account_id,
            NormalizedTransaction.currency == account.currency,
            NormalizedTransaction.transaction_type == TransactionType.DEBIT,
            NormalizedTransaction.transaction_date >= date_from,
            NormalizedTransaction.transaction_date <= date_to,
            NormalizedTransaction.is_duplicate == False
        ).scalar()
        total_debits = Decimal(str(debits_res))

        opening_balance = Decimal(str(account.opening_balance))
        actual_closing = Decimal(str(account.current_balance))

        is_balanced, variance = verify_balance_equation(
            opening=opening_balance,
            credits=total_credits,
            debits=total_debits,
            closing=actual_closing
        )

        expected_closing = opening_balance + total_credits - total_debits

        status_msg = ("Arithmetic comparison only: the account opening and current balances are not dated. "
                      "The selected period may not align with either balance; this does not verify reconciliation.")

        return BalanceCheckResponse(
            account_id=account.id,
            account_name=account.name,
            currency=account.currency,
            opening_balance=opening_balance,
            total_credits=total_credits,
            total_debits=total_debits,
            expected_closing=expected_closing,
            actual_closing=actual_closing,
            variance=variance,
            is_balanced=is_balanced,
            status_message=status_msg
        )
