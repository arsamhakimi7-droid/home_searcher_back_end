from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import mortgage as calc
from ..config import settings
from ..database import get_db
from ..deps import get_optional_user
from ..models import PreApprovalRequest, User
from ..schemas import (
    AffordabilityIn, AffordabilityOut, MortgageCalcIn, MortgageCalcOut,
    PreApprovalIn, PreApprovalOut, RateOut, RatesOut,
)

router = APIRouter(prefix="/mortgage", tags=["mortgage"])

RATE_NOTE = "Illustrative rates for estimation only. Actual rates depend on lender, credit and market."


@router.get("/rates", response_model=RatesOut)
def rates():
    return RatesOut(rates=[RateOut(product=k, rate=v) for k, v in settings.rates.items()], note=RATE_NOTE)


@router.post("/calculate", response_model=MortgageCalcOut)
def calculate(body: MortgageCalcIn):
    if body.down_payment is not None:
        down = body.down_payment
    elif body.down_payment_pct is not None:
        down = body.home_price * body.down_payment_pct / 100
    else:
        down = body.home_price * calc.DEFAULT_DOWN_PAYMENT_PCT
    if down > body.home_price:
        raise HTTPException(422, "Down payment cannot exceed the home price")

    rate = body.annual_rate if body.annual_rate is not None else settings.rates["30-year fixed"]
    b = calc.breakdown(
        body.home_price, down, rate, body.years,
        body.property_tax_rate / 100, body.insurance_rate / 100, body.hoa_monthly,
    )
    schedule = calc.amortization_by_year(b.loan_amount, rate, body.years) if body.include_schedule else None
    return MortgageCalcOut(
        home_price=body.home_price, down_payment=round(down, 2), annual_rate=rate, years=body.years,
        loan_amount=b.loan_amount, principal_and_interest=b.principal_and_interest,
        property_tax=b.property_tax, insurance=b.insurance, hoa=b.hoa,
        total_monthly=b.total_monthly, total_interest=b.total_interest, total_paid=b.total_paid,
        schedule=schedule,
    )


def _affordability(body: AffordabilityIn) -> AffordabilityOut:
    base = settings.rates["30-year fixed" if body.years >= 25 else "15-year fixed"]
    rate = round(base + calc.CREDIT_ADJUSTMENTS[body.credit_band], 3)
    r = calc.max_affordable_price(body.annual_income, body.monthly_debts, body.down_payment, rate, body.years)
    pi = calc.monthly_payment(r["loan_amount"], rate, body.years)
    return AffordabilityOut(**r, rate_used=rate, estimated_monthly_payment=round(pi, 2))


@router.post("/affordability", response_model=AffordabilityOut)
def affordability(body: AffordabilityIn):
    return _affordability(body)


@router.post("/pre-approval", response_model=PreApprovalOut, status_code=201)
def pre_approval(body: PreApprovalIn, db: Session = Depends(get_db), user: User | None = Depends(get_optional_user)):
    """Records the request and returns an instant *estimate*. This is not a lender's pre-approval."""
    est = _affordability(body)
    row = PreApprovalRequest(
        user_id=user.id if user else None, full_name=body.full_name.strip(), email=body.email.lower(),
        phone=body.phone, annual_income=body.annual_income, monthly_debts=body.monthly_debts,
        down_payment=body.down_payment, credit_band=body.credit_band, estimated_max_price=est.max_price,
    )
    db.add(row)
    db.commit()
    return PreApprovalOut(
        id=row.id, estimate=est,
        detail="Request received. A loan partner will contact you to complete your official pre-approval.",
    )
