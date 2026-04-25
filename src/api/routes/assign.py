from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from src.utils.database import get_db
from src.core.assignment import assign_user
from src.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()

class AssignRequest(BaseModel):
    user_id: str
    experiment_name: str

@router.post("/assign")
def assign(request: AssignRequest, db: Session = Depends(get_db)):
    result = assign_user(request.user_id, request.experiment_name, db)
    if not result.get("assigned"):
        raise HTTPException(status_code=404, detail=result.get("reason"))
    return result
