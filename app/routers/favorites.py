from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import Favorite, Property, User
from ..services import to_property_out, with_relations
from ..schemas import PropertyOut

router = APIRouter(prefix="/favorites", tags=["favorites"])


@router.get("", response_model=list[PropertyOut])
def list_favorites(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = db.scalars(
        select(Property).options(with_relations())
        .join(Favorite, Favorite.property_id == Property.id)
        .where(Favorite.user_id == user.id).order_by(Favorite.created_at.desc())
    ).all()
    ids = {p.id for p in rows}
    return [to_property_out(p, ids) for p in rows]


@router.get("/ids", response_model=list[int])
def favorite_ids(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return list(db.scalars(select(Favorite.property_id).where(Favorite.user_id == user.id)))


@router.put("/{property_id}", status_code=status.HTTP_204_NO_CONTENT)
def add_favorite(property_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Idempotent: saving an already-saved home is a no-op."""
    if not db.get(Property, property_id):
        raise HTTPException(404, "Property not found")
    exists = db.scalar(select(Favorite.id).where(Favorite.user_id == user.id, Favorite.property_id == property_id))
    if not exists:
        db.add(Favorite(user_id=user.id, property_id=property_id))
        db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/{property_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_favorite(property_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    db.execute(delete(Favorite).where(Favorite.user_id == user.id, Favorite.property_id == property_id))
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
