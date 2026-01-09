import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Date, DateTime, Boolean,
    ForeignKey, Text, Integer
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from db import Base

class Image(Base):
    __tablename__ = "images"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sop_uid = Column(Text, unique=True, nullable=False)
    series_id = Column(UUID(as_uuid=True), ForeignKey("series.id"))
    file_path = Column(Text, nullable=False)
    thumbnail_path = Column(Text)
    instance_number = Column(Integer)
