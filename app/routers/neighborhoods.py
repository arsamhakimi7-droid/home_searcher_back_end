from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Neighborhood
from ..schemas import NeighborhoodOut
from ..services import escape_like

router = APIRouter(prefix="/neighborhoods", tags=["neighborhoods"])


def _out(n: Neighborhood) -> NeighborhoodOut:
    return NeighborhoodOut(
        id=n.id, name=n.name, city=n.city, state=n.state, zip_code=n.zip_code,
        description=n.description, median_price=n.median_price,
        school_score=n.school_score, school_grade=n.school_grade,
        walk_score=n.walk_score, crime_label=n.crime_label, crime_is_low=n.crime_is_low,
        label=f"{n.city} ({n.zip_code})",
        schools_display=f"{n.school_score}/10 ({n.school_grade})",
        walk_display=f"{n.walk_score} / 100",
    )


@router.get("", response_model=list[NeighborhoodOut])
def list_neighborhoods(
    q: str | None = Query(None, max_length=80, description="City, neighborhood name or ZIP"),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    stmt = select(Neighborhood)
    if q:
        term = q.replace(",", " ").strip().split()
        for raw in term:
            pat = f"%{escape_like(raw.lower())}%"
            stmt = stmt.where(or_(
                func.lower(Neighborhood.name).like(pat, escape="\\"),
                func.lower(Neighborhood.city).like(pat, escape="\\"),
                func.lower(Neighborhood.state).like(pat, escape="\\"),
                Neighborhood.zip_code.like(pat, escape="\\"),
            ))
    return [_out(n) for n in db.scalars(stmt.order_by(Neighborhood.id).limit(limit))]


@router.get("/{zip_code}", response_model=NeighborhoodOut)
def get_neighborhood(zip_code: str, db: Session = Depends(get_db)):
    n = db.scalar(select(Neighborhood).where(Neighborhood.zip_code == zip_code))
    if not n:
        raise HTTPException(404, "Neighborhood not found")
    return _out(n)
