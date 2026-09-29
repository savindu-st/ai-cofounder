from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from shared.db.base import Base


class VentureStateRecord(Base):
    __tablename__ = "venture_states"

    id = Column(Integer, primary_key=True, autoincrement=True)
    venture_id = Column(String, ForeignKey("ventures.id"), nullable=False, index=True)
    stage = Column(String, nullable=False)
    state_json = Column(JSON, nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    venture = relationship("Venture", back_populates="states")
