from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import select
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

    async def get_unpublished(self, limit: int) -> Sequence[OutboxEvent]:
        stmt = (
            select(OutboxEvent)
            .where(OutboxEvent.published_at.is_(None))
            .order_by(OutboxEvent.id)
            .limit(limit)
        )
        result = await self._session.scalars(stmt)
        return result.all()

    async def mark_published(self, event: OutboxEvent) -> None:
        event.published_at = datetime.now(UTC)
        await self._session.flush()
