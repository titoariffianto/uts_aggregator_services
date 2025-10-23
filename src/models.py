from pydantic import BaseModel, Field
from datetime import datetime
from typing import Any, List, Union

class Event(BaseModel):
    """
    Model dasar untuk sebuah event.
    """
    topic: str
    event_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    source: str
    payload: dict[str, Any]

PublishPayload = Union[Event, List[Event]]