from sqlalchemy.ext.asyncio import AsyncSession

from shipments_api.models.outbox import OutboxEvent
from shipments_api.schemas.events import ShipmentStatusChanged


class OutboxRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, event: ShipmentStatusChanged) -> OutboxEvent:
        outbox_event = OutboxEvent(
            event_id=event.event_id,
            event_type=event.event_type,
            payload=event.model_dump(mode="json"),
        )
        self._session.add(outbox_event)
        await self._session.flush()
        return outbox_event
