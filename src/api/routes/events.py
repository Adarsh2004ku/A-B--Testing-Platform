from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from src.utils.database import get_db
from src.models.event import Event
from src.models.user import User
from src.models.experiment import Experiment
from src.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()

class EventRequest(BaseModel):
    user_id: str
    experiment_name: str
    event_type: str
    metadata: dict = {}

@router.post("/events")
def log_event(request: EventRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.external_id == request.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="user_not_found")

    experiment = db.query(Experiment).filter(
        Experiment.name == request.experiment_name
    ).first()
    if not experiment:
        raise HTTPException(status_code=404, detail="experiment_not_found")

    event = Event(
        user_id=user.id,
        experiment_id=experiment.id,
        event_type=request.event_type,
        metadata=request.metadata
    )
    db.add(event)
    db.commit()

    logger.info("Event logged", extra={
        "user_id": request.user_id,
        "experiment": request.experiment_name,
        "event_type": request.event_type
    })

    return {"status": "ok", "event_type": request.event_type}
