import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Date, DateTime, Boolean,
    ForeignKey, Text, Integer
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from db import Base

class Series(Base):
    __tablename__ = "series"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    series_uid = Column(Text, unique=True, nullable=False)
    study_id = Column(UUID(as_uuid=True), ForeignKey("studies.id"))
    body_part = Column(String(50))
