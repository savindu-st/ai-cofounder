import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from shared.db.base import Base


class Evidence(Base):
    __tablename__ = "evidence"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    venture_id = Column(String, ForeignKey("ventures.id"), nullable=False, index=True)
    claim = Column(Text, nullable=False)
    source_url = Column(String, nullable=True)
    confidence_score = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    venture = relationship("Venture", back_populates="evidence")
