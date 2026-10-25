from datetime import datetime, timezone

from sqlalchemy import (
    Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(120))
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    favorites: Mapped[list["Favorite"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    brokerage: Mapped[str] = mapped_column(String(160))
    rating: Mapped[float] = mapped_column(Float, default=5.0)
    recent_sales: Mapped[int] = mapped_column(Integer, default=0)
    avatar: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(40), nullable=True)


class Neighborhood(Base):
    __tablename__ = "neighborhoods"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    city: Mapped[str] = mapped_column(String(120), index=True)
    state: Mapped[str] = mapped_column(String(2))
    zip_code: Mapped[str] = mapped_column(String(10), unique=True, index=True)
    description: Mapped[str] = mapped_column(Text)
    median_price: Mapped[int] = mapped_column(Integer)
    school_score: Mapped[int] = mapped_column(Integer)          # 0-10
    school_grade: Mapped[str] = mapped_column(String(3))
    walk_score: Mapped[int] = mapped_column(Integer)            # 0-100
    crime_label: Mapped[str] = mapped_column(String(60))
    crime_is_low: Mapped[bool] = mapped_column(Boolean, default=True)

    properties: Mapped[list["Property"]] = relationship(back_populates="neighborhood")


class Property(Base):
    __tablename__ = "properties"

    id: Mapped[int] = mapped_column(primary_key=True)
    address: Mapped[str] = mapped_column(String(200))
    city: Mapped[str] = mapped_column(String(120), index=True)
    state: Mapped[str] = mapped_column(String(2), index=True)
    zip_code: Mapped[str] = mapped_column(String(10), index=True)
    price: Mapped[int] = mapped_column(Integer, index=True)       # sale price, or monthly rent for rentals
    original_price: Mapped[int | None] = mapped_column(Integer, nullable=True)
    beds: Mapped[int] = mapped_column(Integer)
    baths: Mapped[float] = mapped_column(Float)
    sqft: Mapped[int] = mapped_column(Integer)
    home_type: Mapped[str] = mapped_column(String(30), index=True)  # house | condo | townhouse | multi-family
    listing_type: Mapped[str] = mapped_column(String(10), index=True, default="buy")  # buy | rent | sold
    brokerage: Mapped[str] = mapped_column(String(160), default="HomeFind Realty")
    image: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    listed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    open_house_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sold_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_new_construction: Mapped[bool] = mapped_column(Boolean, default=False)
    is_foreclosure: Mapped[bool] = mapped_column(Boolean, default=False)
    is_trending: Mapped[bool] = mapped_column(Boolean, default=False)
    is_recommended: Mapped[bool] = mapped_column(Boolean, default=False)
    agent_id: Mapped[int | None] = mapped_column(ForeignKey("agents.id"), nullable=True)
    neighborhood_id: Mapped[int | None] = mapped_column(ForeignKey("neighborhoods.id"), nullable=True)

    agent: Mapped[Agent | None] = relationship()
    neighborhood: Mapped[Neighborhood | None] = relationship(back_populates="properties")


class Favorite(Base):
    __tablename__ = "favorites"
    __table_args__ = (UniqueConstraint("user_id", "property_id", name="uq_favorite"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    user: Mapped[User] = relationship(back_populates="favorites")
    property: Mapped[Property] = relationship()


class Lead(Base):
    """A 'Contact Agent' message from a visitor."""
    __tablename__ = "leads"

    id: Mapped[int] = mapped_column(primary_key=True)
    agent_id: Mapped[int] = mapped_column(ForeignKey("agents.id"), index=True)
    property_id: Mapped[int | None] = mapped_column(ForeignKey("properties.id"), nullable=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    message: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class PreApprovalRequest(Base):
    __tablename__ = "pre_approval_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    full_name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    annual_income: Mapped[float] = mapped_column(Float)
    monthly_debts: Mapped[float] = mapped_column(Float)
    down_payment: Mapped[float] = mapped_column(Float)
    credit_band: Mapped[str] = mapped_column(String(20))
    estimated_max_price: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Subscriber(Base):
    """Email capture for new-listing alerts / mobile app launch."""
    __tablename__ = "subscribers"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    topic: Mapped[str] = mapped_column(String(40), default="app-alerts")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
