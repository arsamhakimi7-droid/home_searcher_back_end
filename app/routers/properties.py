import math
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_optional_user
from ..models import Favorite, Property, User
from ..schemas import CategoryOut, PropertyOut, PropertyPage, SuggestionOut
from ..services import (
    CATEGORIES, CATEGORY_KEYS, category_clause, escape_like, favorite_ids_for,
    text_search_clause, to_property_out, with_relations,
)

router = APIRouter(tags=["properties"])

HOME_TYPES = {"house", "condo", "townhouse", "multi-family"}
SORTS = {
    "newest": [Property.listed_at.desc(), Property.id.desc()],
    "price_asc": [Property.price.asc(), Property.id.asc()],
    "price_desc": [Property.price.desc(), Property.id.asc()],
    "sqft_desc": [Property.sqft.desc(), Property.id.asc()],
}


@router.get("/properties", response_model=PropertyPage)
def search_properties(
    q: str | None = Query(None, max_length=120, description="Address, city, state or ZIP"),
    listing_type: Literal["buy", "rent", "sold"] | None = None,
    category: str | None = Query(None, description="new-listings | open-houses | price-reduced | recently-sold | new-construction | foreclosures"),
    min_price: int | None = Query(None, ge=0),
    max_price: int | None = Query(None, ge=0),
    beds: int | None = Query(None, ge=0, le=20, description="Minimum bedrooms"),
    baths: float | None = Query(None, ge=0, le=20, description="Minimum bathrooms"),
    home_type: str | None = Query(None, description="Comma separated: house,condo,townhouse,multi-family"),
    sort: Literal["newest", "price_asc", "price_desc", "sqft_desc"] = "newest",
    page: int = Query(1, ge=1),
    page_size: int = Query(12, ge=1, le=50),
    db: Session = Depends(get_db),
    user: User | None = Depends(get_optional_user),
):
    if category and category not in CATEGORY_KEYS:
        raise HTTPException(422, f"Unknown category '{category}'")
    if min_price is not None and max_price is not None and min_price > max_price:
        raise HTTPException(422, "min_price cannot be greater than max_price")

    conds = []
    if q and (clause := text_search_clause(q)) is not None:
        conds.append(clause)
    if listing_type:
        conds.append(Property.listing_type == listing_type)
    if category:
        conds.append(category_clause(category))
    if min_price is not None:
        conds.append(Property.price >= min_price)
    if max_price is not None:
        conds.append(Property.price <= max_price)
    if beds is not None:
        conds.append(Property.beds >= beds)
    if baths is not None:
        conds.append(Property.baths >= baths)
    if home_type:
        types = {t.strip().lower() for t in home_type.split(",") if t.strip()}
        if not types <= HOME_TYPES:
            raise HTTPException(422, f"home_type must be any of {sorted(HOME_TYPES)}")
        conds.append(Property.home_type.in_(types))

    total = db.scalar(select(func.count()).select_from(Property).where(*conds)) or 0
    rows = db.scalars(
        select(Property).options(with_relations()).where(*conds)
        .order_by(*SORTS[sort]).offset((page - 1) * page_size).limit(page_size)
    ).all()
    fav = favorite_ids_for(db, user)
    return PropertyPage(
        items=[to_property_out(p, fav) for p in rows],
        total=total, page=page, page_size=page_size,
        pages=max(math.ceil(total / page_size), 1),
    )


@router.get("/properties/trending", response_model=list[PropertyOut])
def trending(limit: int = Query(4, ge=1, le=20), db: Session = Depends(get_db), user: User | None = Depends(get_optional_user)):
    rows = db.scalars(
        select(Property).options(with_relations())
        .where(Property.is_trending.is_(True), Property.listing_type == "buy")
        .order_by(Property.id).limit(limit)
    ).all()
    fav = favorite_ids_for(db, user)
    return [to_property_out(p, fav) for p in rows]


@router.get("/properties/recommended", response_model=list[PropertyOut])
def recommended(limit: int = Query(4, ge=1, le=20), db: Session = Depends(get_db), user: User | None = Depends(get_optional_user)):
    """Personalised when the user has favourites (similar price band / same cities); curated otherwise."""
    fav_ids = favorite_ids_for(db, user)
    pool = db.scalars(
        select(Property).options(with_relations())
        .where(Property.listing_type == "buy").order_by(Property.id)
    ).all()

    if fav_ids:
        favs = [p for p in pool if p.id in fav_ids]
        if favs:
            avg = sum(p.price for p in favs) / len(favs)
            cities = {(p.city, p.state) for p in favs}
            candidates = [p for p in pool if p.id not in fav_ids]
            candidates.sort(key=lambda p: abs(p.price - avg) / avg + (0 if (p.city, p.state) in cities else 0.25))
            return [to_property_out(p, fav_ids) for p in candidates[:limit]]

    curated = [p for p in pool if p.is_recommended]
    return [to_property_out(p, fav_ids) for p in curated[:limit]]


@router.get("/properties/categories", response_model=list[CategoryOut])
def categories(db: Session = Depends(get_db)):
    out = []
    for c in CATEGORIES:
        count = db.scalar(select(func.count()).select_from(Property).where(category_clause(c["key"]))) or 0
        out.append(CategoryOut(**c, count=count))
    return out


@router.get("/properties/suggestions", response_model=list[SuggestionOut])
def suggestions(q: str = Query(..., min_length=1, max_length=60), db: Session = Depends(get_db)):
    """Autocomplete for the hero search box."""
    pat = f"%{escape_like(q.strip().lower())}%"
    out: list[SuggestionOut] = []
    seen: set[str] = set()

    for city, state in db.execute(
        select(Property.city, Property.state).where(func.lower(Property.city).like(pat, escape="\\")).distinct().limit(5)
    ):
        label = f"{city}, {state}"
        if label not in seen:
            seen.add(label)
            out.append(SuggestionOut(label=label, kind="city", value=label))
    for (zip_code,) in db.execute(select(Property.zip_code).where(Property.zip_code.like(pat, escape="\\")).distinct().limit(3)):
        out.append(SuggestionOut(label=zip_code, kind="zip", value=zip_code))
    for address, city, state in db.execute(
        select(Property.address, Property.city, Property.state).where(func.lower(Property.address).like(pat, escape="\\")).limit(4)
    ):
        out.append(SuggestionOut(label=f"{address}, {city}, {state}", kind="address", value=f"{address}, {city}, {state}"))
    return out[:8]


@router.get("/properties/{property_id}", response_model=PropertyOut)
def get_property(property_id: int, db: Session = Depends(get_db), user: User | None = Depends(get_optional_user)):
    p = db.scalar(select(Property).options(with_relations()).where(Property.id == property_id))
    if not p:
        raise HTTPException(404, "Property not found")
    return to_property_out(p, favorite_ids_for(db, user))
