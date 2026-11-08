from decimal import Decimal, ROUND_HALF_UP
from typing import Union

FOUR_PLACES = Decimal("0.0001")
TWO_PLACES = Decimal("0.01")

def to_decimal(val: Union[str, int, float, Decimal, None], default: str = "0.0000") -> Decimal:
    if val is None or val == "":
        return Decimal(default)
    if isinstance(val, float):
        # Convert via string representation to avoid float binary representation artifacts
        return Decimal(str(round(val, 6))).quantize(FOUR_PLACES, rounding=ROUND_HALF_UP)
    try:
        return Decimal(str(val)).quantize(FOUR_PLACES, rounding=ROUND_HALF_UP)
    except Exception:
        return Decimal(default)

def is_amount_within_tolerance(
    amount1: Decimal,
    amount2: Decimal,
    abs_tolerance: Decimal = Decimal("0.0000"),
    percent_tolerance: Decimal = Decimal("0.0000")
) -> bool:
    diff = abs(amount1 - amount2)
    if diff <= abs_tolerance:
        return True
    if percent_tolerance > Decimal("0.0000") and amount1 != Decimal("0.0000"):
        relative_diff = diff / abs(amount1)
        if relative_diff <= percent_tolerance:
            return True
    return False

def verify_balance_equation(opening: Decimal, credits: Decimal, debits: Decimal, closing: Decimal) -> tuple[bool, Decimal]:
    """
    Equation: Opening Balance + Total Credits - Total Debits = Expected Closing Balance.
    Returns: (is_balanced: bool, variance: Decimal)
    """
    expected_closing = opening + credits - debits
    variance = closing - expected_closing
    is_balanced = (variance == Decimal("0.0000"))
    return is_balanced, variance
