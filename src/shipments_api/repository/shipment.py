import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shipments_api.domain.statuses import ShipmentStatus
from shipments_api.models.shipment import Shipment, StatusHistory


class ShipmentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, shipment: Shipment) -> None:
        self._session.add(shipment)
        await self._session.flush()

    async def get(self, shipment_id: uuid.UUID) -> Shipment | None:
        stmt = select(Shipment).where(Shipment.id == shipment_id)
        result = await self._session.scalars(stmt)
        return result.first()

    async def add_history(self, status_history: StatusHistory) -> None:
        self._session.add(status_history)
        await self._session.flush()

    async def get_for_update(self, shipment_id: uuid.UUID) -> Shipment | None:
        stmt = select(Shipment).where(Shipment.id == shipment_id).with_for_update()
        result = await self._session.scalars(stmt)
        return result.first()

    async def list_history(self, shipment_id: uuid.UUID) -> Sequence[StatusHistory]:
        stmt = (
            select(StatusHistory)
            .where(StatusHistory.shipment_id == shipment_id)
            .order_by(StatusHistory.id)
        )
        result = await self._session.scalars(stmt)
        return result.all()

    async def list_shipments(
        self, *, status: ShipmentStatus | None, limit: int, offset: int
    ) -> Sequence[Shipment]:
        stmt = select(Shipment).order_by(Shipment.created_at.desc(), Shipment.id)
        if status is not None:
            stmt = stmt.where(Shipment.current_status == status)
        stmt = stmt.limit(limit).offset(offset)
        result = await self._session.scalars(stmt)
        return result.all()
