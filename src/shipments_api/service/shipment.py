import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from shipments_api.domain.exceptions import ShipmentNotFound
from shipments_api.domain.statuses import ShipmentStatus, validate_transition
from shipments_api.domain.tracking import generate_tracking_number
from shipments_api.models.shipment import Shipment, StatusHistory
from shipments_api.repository.outbox import OutboxRepository
from shipments_api.repository.shipment import ShipmentRepository
from shipments_api.schemas.events import ShipmentStatusChanged


class ShipmentService:
    def __init__(
        self,
        session: AsyncSession,
        repository: ShipmentRepository,
        outbox_repository: OutboxRepository,
    ) -> None:
        self._session = session
        self._repository = repository
        self._outbox_repository = outbox_repository

    async def change_status(
        self, shipment_id: uuid.UUID, new_status: ShipmentStatus, comment: str | None = None
    ) -> Shipment:
        async with self._session.begin():
            shipment = await self._repository.get_for_update(shipment_id)
            if shipment is None:
                raise ShipmentNotFound(shipment_id)
            validate_transition(shipment.current_status, new_status)
            old_status = shipment.current_status
            shipment.current_status = new_status
            new_history = StatusHistory(shipment_id=shipment.id, status=new_status, comment=comment)
            await self._repository.add_history(new_history)
            event = ShipmentStatusChanged(
                occurred_at=datetime.now(UTC),
                shipment_id=shipment.id,
                tracking_number=shipment.tracking_number,
                old_status=old_status,
                new_status=new_status,
                comment=comment,
            )
            await self._outbox_repository.add(event)
            return shipment

    async def create_shipment(self, sender: str, recipient: str) -> Shipment:
        async with self._session.begin():
            shipment = Shipment(
                tracking_number=generate_tracking_number(),
                sender=sender,
                recipient=recipient,
                current_status=ShipmentStatus.CREATED,
            )
            await self._repository.add(shipment)
            history = StatusHistory(
                shipment_id=shipment.id, status=ShipmentStatus.CREATED, comment=None
            )
            await self._repository.add_history(history)
            return shipment

    async def get_shipment(self, shipment_id: uuid.UUID) -> Shipment:
        async with self._session.begin():
            shipment = await self._repository.get(shipment_id)
            if shipment is None:
                raise ShipmentNotFound(shipment_id)
            return shipment

    async def get_history(self, shipment_id: uuid.UUID) -> Sequence[StatusHistory]:
        async with self._session.begin():
            shipment = await self._repository.get(shipment_id)
            if shipment is None:
                raise ShipmentNotFound(shipment_id)
            history = await self._repository.list_history(shipment_id)
            return history

    async def list_shipments(
        self, *, status: ShipmentStatus | None, limit: int, offset: int
    ) -> Sequence[Shipment]:
        async with self._session.begin():
            list_shipment = await self._repository.list_shipments(
                status=status, limit=limit, offset=offset
            )
            return list_shipment
