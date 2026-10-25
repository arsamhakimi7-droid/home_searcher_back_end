"""Pure mortgage math, no database or web dependencies."""
from dataclasses import dataclass

DEFAULT_DOWN_PAYMENT_PCT = 0.20
DEFAULT_PROPERTY_TAX_RATE = 0.011   # of price, per year
DEFAULT_INSURANCE_RATE = 0.0035     # of price, per year
FRONT_END_DTI = 0.28                # housing cost / gross monthly income
BACK_END_DTI = 0.36                 # (housing + other debts) / gross monthly income

# Illustrative rate adjustments by credit band (percentage points).
CREDIT_ADJUSTMENTS = {"excellent": 0.0, "good": 0.25, "fair": 0.75, "poor": 1.5}


def monthly_rate(annual_rate_pct: float) -> float:
    return annual_rate_pct / 100 / 12


def payment_factor(annual_rate_pct: float, years: int) -> float:
    """Monthly principal+interest payment per $1 borrowed."""
    r, n = monthly_rate(annual_rate_pct), years * 12
    if r == 0:
        return 1 / n
    return r / (1 - (1 + r) ** -n)


def monthly_payment(principal: float, annual_rate_pct: float, years: int) -> float:
    if principal <= 0:
        return 0.0
    return principal * payment_factor(annual_rate_pct, years)


@dataclass
class PaymentBreakdown:
    loan_amount: float
    principal_and_interest: float
    property_tax: float
    insurance: float
    hoa: float
    total_monthly: float
    total_interest: float
    total_paid: float


def breakdown(
    price: float,
    down_payment: float,
    annual_rate_pct: float,
    years: int,
    property_tax_rate: float = DEFAULT_PROPERTY_TAX_RATE,
    insurance_rate: float = DEFAULT_INSURANCE_RATE,
    hoa_monthly: float = 0.0,
) -> PaymentBreakdown:
    loan = max(price - down_payment, 0.0)
    pi = monthly_payment(loan, annual_rate_pct, years)
    tax = price * property_tax_rate / 12
    ins = price * insurance_rate / 12
    total_interest = max(pi * years * 12 - loan, 0.0)
    return PaymentBreakdown(
        loan_amount=round(loan, 2),
        principal_and_interest=round(pi, 2),
        property_tax=round(tax, 2),
        insurance=round(ins, 2),
        hoa=round(hoa_monthly, 2),
        total_monthly=round(pi + tax + ins + hoa_monthly, 2),
        total_interest=round(total_interest, 2),
        total_paid=round(loan + total_interest, 2),
    )


def estimate_monthly_for_price(price: int, annual_rate_pct: float) -> int:
    """Headline 'Est. $X/mo' shown on listing cards: 20% down, 30-year fixed, P&I only."""
    return round(monthly_payment(price * (1 - DEFAULT_DOWN_PAYMENT_PCT), annual_rate_pct, 30))


def amortization_by_year(loan: float, annual_rate_pct: float, years: int) -> list[dict]:
    r = monthly_rate(annual_rate_pct)
    pi = monthly_payment(loan, annual_rate_pct, years)
    balance, rows = loan, []
    for year in range(1, years + 1):
        interest_y = principal_y = 0.0
        for _ in range(12):
            interest = balance * r
            principal = min(pi - interest, balance)
            balance -= principal
            interest_y += interest
            principal_y += principal
        rows.append({
            "year": year,
            "principal_paid": round(principal_y, 2),
            "interest_paid": round(interest_y, 2),
            "remaining_balance": round(max(balance, 0.0), 2),
        })
    return rows


def max_affordable_price(
    annual_income: float,
    monthly_debts: float,
    down_payment: float,
    annual_rate_pct: float,
    years: int = 30,
    property_tax_rate: float = DEFAULT_PROPERTY_TAX_RATE,
    insurance_rate: float = DEFAULT_INSURANCE_RATE,
) -> dict:
    """Largest price that satisfies both the 28% front-end and 36% back-end DTI rules."""
    gross_monthly = annual_income / 12
    housing_budget = max(min(FRONT_END_DTI * gross_monthly, BACK_END_DTI * gross_monthly - monthly_debts), 0.0)
    k = payment_factor(annual_rate_pct, years)
    t = (property_tax_rate + insurance_rate) / 12
    # housing = (price - down) * k + price * t   ->   solve for price
    price = (housing_budget + down_payment * k) / (k + t)
    price = max(price, 0.0)
    loan = max(price - down_payment, 0.0)
    return {
        "max_price": round(price, -2),
        "loan_amount": round(loan, -2),
        "monthly_housing_budget": round(housing_budget, 2),
        "debt_to_income": round((housing_budget + monthly_debts) / gross_monthly, 4) if gross_monthly else 0.0,
    }
