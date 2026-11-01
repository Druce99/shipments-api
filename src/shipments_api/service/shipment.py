import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from shipments_api.domain.exceptions import ShipmentNotFound
from shipments_api.domain.statuses import ShipmentStatus, validate_transition
from shipments_api.models.shipment import Shipment, StatusHistory
from shipments_api.repository.shipment import ShipmentRepository


class ShipmentService:
    def __init__(self, session: AsyncSession, repository: ShipmentRepository) -> None:
        self._session = session
        self._repository = repository

    async def change_status(
        self, shipment_id: uuid.UUID, new_status: ShipmentStatus, comment: str | None = None
    ) -> Shipment:
        async with self._session.begin():
            shipment = await self._repository.get_for_update(shipment_id)
            if shipment is None:
                raise ShipmentNotFound(shipment_id)
            validate_transition(shipment.current_status, new_status)
            shipment.current_status = new_status
            new_history = StatusHistory(shipment_id=shipment.id, status=new_status, comment=comment)
            await self._repository.add_history(new_history)
            return shipment
