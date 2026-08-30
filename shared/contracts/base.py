from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional

class BaseContract(BaseModel):
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True

class TimestampedContract(BaseContract):
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
