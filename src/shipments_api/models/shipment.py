import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from shipments_api.domain.statuses import ShipmentStatus
from shipments_api.models.base import Base


def status_column() -> Enum:
    return Enum(
        ShipmentStatus,
        native_enum=False,
        length=32,
        create_constraint=True,
        name="status_valid",
        values_callable=lambda e: [m.value for m in e],
    )


class Shipment(Base):
    __tablename__ = "shipments"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tracking_number: Mapped[str] = mapped_column(String(32), unique=True)
    sender: Mapped[str] = mapped_column(Text)
    recipient: Mapped[str] = mapped_column(Text)
    current_status: Mapped[ShipmentStatus] = mapped_column(status_column())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class StatusHistory(Base):
    __tablename__ = "status_history"
    __table_args__ = (Index("ix_status_history_shipment_id_id", "shipment_id", "id"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    shipment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("shipments.id", ondelete="RESTRICT"))
    status: Mapped[ShipmentStatus] = mapped_column(status_column())
    comment: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
