from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from shared.db.base import Base


class RoadmapRecord(Base):
    __tablename__ = "roadmaps"

    venture_id = Column(String, ForeignKey("ventures.id"), primary_key=True, index=True)
    roadmap_json = Column(JSON, nullable=False)
    confidence_score = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    venture = relationship("Venture", back_populates="roadmap")
