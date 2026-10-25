from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

# ---------- auth ----------

class RegisterIn(BaseModel):
    full_name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)

    @field_validator("full_name")
    @classmethod
    def _strip(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Name must not be blank")
        return v


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: EmailStr
    full_name: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ---------- properties ----------

class Badge(BaseModel):
    key: str
    label: str


class AgentBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    brokerage: str
    avatar: str


class PropertyOut(BaseModel):
    id: int
    address: str
    city: str
    state: str
    zip_code: str
    full_address: str
    price: int
    original_price: int | None
    beds: int
    baths: float
    sqft: int
    home_type: str
    listing_type: str
    brokerage: str
    image: str
    description: str | None
    listed_at: datetime
    open_house_at: datetime | None
    badge: Badge | None
    est_monthly: int | None          # only for sale listings
    is_favorite: bool = False
    agent: AgentBrief | None = None


class PropertyPage(BaseModel):
    items: list[PropertyOut]
    total: int
    page: int
    page_size: int
    pages: int


class CategoryOut(BaseModel):
    key: str
    title: str
    subtitle: str
    image: str
    count: int


class SuggestionOut(BaseModel):
    label: str
    kind: Literal["city", "zip", "address"]
    value: str


# ---------- agents / leads ----------

class AgentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    brokerage: str
    rating: float
    recent_sales: int
    avatar: str


class ContactAgentIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    phone: str | None = Field(default=None, max_length=40)
    message: str = Field(min_length=5, max_length=2000)
    property_id: int | None = None


class LeadOut(BaseModel):
    id: int
    status: str = "received"
    detail: str


# ---------- neighborhoods ----------

class NeighborhoodOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    city: str
    state: str
    zip_code: str
    description: str
    median_price: int
    school_score: int
    school_grade: str
    walk_score: int
    crime_label: str
    crime_is_low: bool
    label: str                 # e.g. "Lake Forest (92630)"
    schools_display: str       # e.g. "9/10 (A+)"
    walk_display: str          # e.g. "82 / 100"


# ---------- mortgage ----------

class MortgageCalcIn(BaseModel):
    home_price: float = Field(gt=0, le=100_000_000)
    down_payment: float | None = Field(default=None, ge=0)
    down_payment_pct: float | None = Field(default=None, ge=0, le=100)
    annual_rate: float | None = Field(default=None, ge=0, le=25, description="Percent; defaults to current 30y rate")
    years: int = Field(default=30, ge=1, le=40)
    property_tax_rate: float = Field(default=1.1, ge=0, le=10, description="Percent of price per year")
    insurance_rate: float = Field(default=0.35, ge=0, le=5, description="Percent of price per year")
    hoa_monthly: float = Field(default=0, ge=0, le=100_000)
    include_schedule: bool = False


class MortgageCalcOut(BaseModel):
    home_price: float
    down_payment: float
    annual_rate: float
    years: int
    loan_amount: float
    principal_and_interest: float
    property_tax: float
    insurance: float
    hoa: float
    total_monthly: float
    total_interest: float
    total_paid: float
    schedule: list[dict] | None = None


class RateOut(BaseModel):
    product: str
    rate: float


class RatesOut(BaseModel):
    rates: list[RateOut]
    note: str


CreditBand = Literal["excellent", "good", "fair", "poor"]


class AffordabilityIn(BaseModel):
    annual_income: float = Field(gt=0, le=100_000_000)
    monthly_debts: float = Field(default=0, ge=0, le=1_000_000)
    down_payment: float = Field(default=0, ge=0, le=100_000_000)
    credit_band: CreditBand = "good"
    years: int = Field(default=30, ge=1, le=40)


class AffordabilityOut(BaseModel):
    max_price: float
    loan_amount: float
    monthly_housing_budget: float
    debt_to_income: float
    rate_used: float
    estimated_monthly_payment: float


class PreApprovalIn(AffordabilityIn):
    full_name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    phone: str | None = Field(default=None, max_length=40)


class PreApprovalOut(BaseModel):
    id: int
    estimate: AffordabilityOut
    detail: str


# ---------- misc ----------

class SubscribeIn(BaseModel):
    email: EmailStr
    topic: str = Field(default="app-alerts", max_length=40)


class Message(BaseModel):
    detail: str
