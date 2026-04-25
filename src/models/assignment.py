from sqlalchemy import Column, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import uuid
from src.models.base import Base

class Assignment(Base):
    __tablename__ = "assignments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    experiment_id = Column(UUID(as_uuid=True), ForeignKey("experiments.id"), nullable=False)
    variant_id = Column(UUID(as_uuid=True), ForeignKey("variants.id"), nullable=False)
    assigned_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # one user gets one variant per experiment
    __table_args__ = (
        UniqueConstraint("user_id", "experiment_id", name="uq_user_experiment"),
    )

    # relationships
    user = relationship("User", back_populates="assignments")
    experiment = relationship("Experiment", back_populates="assignments")
    variant = relationship("Variant", back_populates="assignments")
