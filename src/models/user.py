from sqlalchemy import Column, String, Boolean,DateTime,JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime, timezone
from src.models.base import Base


class User(Base):
    __tablename__ = 'users'

    id = Column(UUID(as_uuid = True),primary_key=True,default=uuid.uuid4)
    external_id = Column(String,unique=True,nullable=False) # your app's user ID
    country = Column(String, nullable=True)
    device_type = Column(String, nullable=True) # mobile,desktop,tablet
    user_type = Column(String, nullable=True) # free,premium,enterprise
    attributes = Column(JSON,default={}) # ANY EXTRA ATTRIBUTES YOU WANT TO STORE
    created_at = Column(DateTime(timezone=True), default=lambda:datetime.now(timezone.utc.utc))


    # relationship
    assignments = relationship("Assignment", back_populates="user")
    events = relationship("Event", back_populates="user")