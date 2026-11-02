import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from shipments_api.domain.statuses import ShipmentStatus


class ShipmentCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    sender: str = Field(min_length=1, max_length=200)
    recipient: str = Field(min_length=1, max_length=200)


class ShipmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    tracking_number: str
    sender: str
    recipient: str
    current_status: ShipmentStatus
    created_at: datetime
    updated_at: datetime


class StatusChange(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    status: ShipmentStatus
    comment: str | None = Field(min_length=1, max_length=500, default=None)


class StatusHistoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    status: ShipmentStatus
    comment: str | None
    created_at: datetime
