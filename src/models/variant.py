from sqlalchemy import Column, String, Float, Boolean, DateTime, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import uuid
from src.models.base import Base

class Variant(Base):
    __tablename__ = "variants"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    experiment_id = Column(UUID(as_uuid=True), ForeignKey("experiments.id"), nullable=False)
    name = Column(String, nullable=False)          # e.g. "control", "treatment_a"
    is_control = Column(Boolean, default=False)
    traffic_weight = Column(Float, nullable=False) # e.g. 0.5 = 50%
    config = Column(JSON, default={})              # variant-specific config
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # relationships
    experiment = relationship("Experiment", back_populates="variations")
    assignments = relationship("Assignment", back_populates="variant")
