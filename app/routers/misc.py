from fastapi import APIRouter, Depends, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Subscriber
from ..schemas import Message, SubscribeIn

router = APIRouter(tags=["misc"])


@router.get("/health", response_model=Message)
def health():
    return Message(detail="ok")


@router.post("/subscribe", response_model=Message, status_code=status.HTTP_201_CREATED)
def subscribe(body: SubscribeIn, db: Session = Depends(get_db)):
    """Idempotent email capture for listing alerts / app launch."""
    email = body.email.lower()
    if not db.scalar(select(Subscriber.id).where(func.lower(Subscriber.email) == email)):
        db.add(Subscriber(email=email, topic=body.topic))
        db.commit()
    return Message(detail="You're on the list. We'll let you know when new homes match.")
