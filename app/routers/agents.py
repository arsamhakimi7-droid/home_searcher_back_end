from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_optional_user
from ..models import Agent, Lead, Property, User
from ..schemas import AgentOut, ContactAgentIn, LeadOut

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("", response_model=list[AgentOut])
def list_agents(limit: int = Query(8, ge=1, le=50), db: Session = Depends(get_db)):
    return db.scalars(
        select(Agent).order_by(Agent.rating.desc(), Agent.recent_sales.desc(), Agent.id).limit(limit)
    ).all()


@router.get("/{agent_id}", response_model=AgentOut)
def get_agent(agent_id: int, db: Session = Depends(get_db)):
    agent = db.get(Agent, agent_id)
    if not agent:
        raise HTTPException(404, "Agent not found")
    return agent


@router.post("/{agent_id}/contact", response_model=LeadOut, status_code=status.HTTP_201_CREATED)
def contact_agent(
    agent_id: int,
    body: ContactAgentIn,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_optional_user),
):
    """Stores the inquiry. Hook an email/CRM integration in here (see README)."""
    agent = db.get(Agent, agent_id)
    if not agent:
        raise HTTPException(404, "Agent not found")
    if body.property_id is not None and not db.get(Property, body.property_id):
        raise HTTPException(404, "Property not found")
    lead = Lead(
        agent_id=agent.id, property_id=body.property_id, user_id=user.id if user else None,
        name=body.name.strip(), email=body.email.lower(), phone=body.phone, message=body.message.strip(),
    )
    db.add(lead)
    db.commit()
    return LeadOut(id=lead.id, detail=f"Your message was sent to {agent.name}. They'll reply to {lead.email}.")
