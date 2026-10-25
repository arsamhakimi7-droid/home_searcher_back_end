"""Query/serialisation helpers shared by several routers."""
from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session, joinedload

from . import mortgage
from .config import settings
from .models import Favorite, Property, User
from .schemas import AgentBrief, Badge, PropertyOut

NEW_LISTING_WINDOW = timedelta(hours=24)

CATEGORIES = [
    {"key": "new-listings", "title": "New Listings", "subtitle": "Fresh properties added in the last 24h", "image": "/assets/89749.png"},
    {"key": "open-houses", "title": "Open Houses", "subtitle": "Tour local homes in person this weekend", "image": "/assets/06cb1.png"},
    {"key": "price-reduced", "title": "Price Reduced", "subtitle": "Great value deals right now", "image": "/assets/85fd3.png"},
    {"key": "recently-sold", "title": "Recently Sold", "subtitle": "See what buyers paid in your area", "image": "/assets/78bf5.png"},
    {"key": "new-construction", "title": "New Construction", "subtitle": "Modern builds and upcoming projects", "image": "/assets/d87bb.png"},
    {"key": "foreclosures", "title": "Foreclosures", "subtitle": "Find bank-owned bargains", "image": "/assets/520b6.png"},
]
CATEGORY_KEYS = {c["key"] for c in CATEGORIES}


def _aware(dt: datetime | None) -> datetime | None:
    """SQLite drops tzinfo; treat naive values as UTC."""
    if dt is not None and dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def category_clause(key: str):
    now = datetime.now(timezone.utc)
    if key == "new-listings":
        return and_(Property.listing_type != "sold", Property.listed_at >= now - NEW_LISTING_WINDOW)
    if key == "open-houses":
        return and_(Property.listing_type != "sold", Property.open_house_at.is_not(None), Property.open_house_at >= now)
    if key == "price-reduced":
        return and_(Property.listing_type == "buy", Property.original_price.is_not(None), Property.original_price > Property.price)
    if key == "recently-sold":
        return Property.listing_type == "sold"
    if key == "new-construction":
        return and_(Property.listing_type != "sold", Property.is_new_construction.is_(True))
    if key == "foreclosures":
        return and_(Property.listing_type != "sold", Property.is_foreclosure.is_(True))
    raise KeyError(key)


def badge_for(p: Property) -> Badge | None:
    now = datetime.now(timezone.utc)
    open_house = _aware(p.open_house_at)
    listed = _aware(p.listed_at)
    if p.listing_type == "sold":
        return Badge(key="sold", label="Sold")
    if p.is_foreclosure:
        return Badge(key="foreclosure", label="Foreclosure")
    if p.listing_type == "buy" and p.original_price and p.original_price > p.price:
        return Badge(key="price-reduced", label="Price Reduced")
    if open_house and open_house >= now:
        return Badge(key="open-house", label="Open House")
    if listed and listed >= now - NEW_LISTING_WINDOW:
        return Badge(key="new-listing", label="New Listing")
    if p.is_new_construction:
        return Badge(key="new-construction", label="New Construction")
    return None


def to_property_out(p: Property, favorite_ids: set[int] | None = None) -> PropertyOut:
    est = None
    if p.listing_type == "buy":
        est = mortgage.estimate_monthly_for_price(p.price, settings.rates["30-year fixed"])
    return PropertyOut(
        id=p.id,
        address=p.address,
        city=p.city,
        state=p.state,
        zip_code=p.zip_code,
        full_address=f"{p.address}, {p.city}, {p.state}",
        price=p.price,
        original_price=p.original_price,
        beds=p.beds,
        baths=p.baths,
        sqft=p.sqft,
        home_type=p.home_type,
        listing_type=p.listing_type,
        brokerage=p.brokerage,
        image=p.image,
        description=p.description,
        listed_at=p.listed_at,
        open_house_at=p.open_house_at,
        badge=badge_for(p),
        est_monthly=est,
        is_favorite=bool(favorite_ids and p.id in favorite_ids),
        agent=AgentBrief.model_validate(p.agent) if p.agent else None,
    )


def favorite_ids_for(db: Session, user: User | None) -> set[int]:
    if user is None:
        return set()
    return set(db.scalars(select(Favorite.property_id).where(Favorite.user_id == user.id)))


def escape_like(term: str) -> str:
    return term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def text_search_clause(q: str):
    """Every whitespace-separated term must match address, city, state, zip, or neighborhood."""
    clauses = []
    for raw in q.replace(",", " ").split():
        pat = f"%{escape_like(raw.lower())}%"
        clauses.append(or_(
            func.lower(Property.address).like(pat, escape="\\"),
            func.lower(Property.city).like(pat, escape="\\"),
            func.lower(Property.state).like(pat, escape="\\"),
            Property.zip_code.like(pat, escape="\\"),
        ))
    return and_(*clauses) if clauses else None


def with_relations():
    return joinedload(Property.agent)
