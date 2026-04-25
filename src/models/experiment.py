from sqlalchemy import Column, String, Boolean,DateTime,JSON,Enum,Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime, timezone
from src.models.base import Base
import enum

class ExperimentStatus(enum.Enum):
    draft = "draft"
    running = "running"
    paused = "paused"
    completed = "completed"


class Experiment(Base):
    __tablename__ = 'experiments'

    id = Column(UUID(as_uuid = True),primary_key=True,default=uuid.uuid4)
    name = Column(String,unique=True,nullable=False)
    description = Column(String, nullable=True)
    status = Column(Enum(ExperimentStatus), default=ExperimentStatus.draft)
    layer = Column(String,nullable = False,default = ExperimentStatus.draft)
    target_segments = Column(JSON, default=[]) # e.g. {"country": ["US", "CA"], "device_type": ["mobile"]}
    created_at = Column(DateTime(timezone=True), default=lambda:datetime.now(timezone.utc))
    started_at = Column(DateTime(timezone=True), nullable=True)
    ended_at = Column(DateTime(timezone=True), nullable=True)

    #relationship
    variations = relationship("Variant", back_populates="experiment")
    assignments = relationship("Assignment", back_populates="experiment")
    events = relationship("Event", back_populates="experiment")
