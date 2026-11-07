from typing import Any, Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from shipments_api.repository.outbox import OutboxRepository


class EventPublisher(Protocol):
    async def publish(self, key: str, value: dict[str, Any]) -> None: ...


class OutboxRelay:
    def __init__(
        self,
        session: AsyncSession,
        repository: OutboxRepository,
        publisher: EventPublisher,
        batch_size: int = 100,
    ) -> None:
        self._session = session
        self._repository = repository
        self._publisher = publisher
        self._batch_size = batch_size

    async def publish_pending(self) -> int:
        async with self._session.begin():
            unpublished_events = await self._repository.get_unpublished(self._batch_size)
        for event in unpublished_events:
            await self._publisher.publish(key=event.payload["shipment_id"], value=event.payload)
            async with self._session.begin():
                await self._repository.mark_published(event)
        return len(unpublished_events)
