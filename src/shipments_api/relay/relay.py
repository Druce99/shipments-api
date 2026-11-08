import asyncio
from typing import Any, Protocol

from loguru import logger
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
        poll_interval: float = 1.0,
    ) -> None:
        self._session = session
        self._repository = repository
        self._publisher = publisher
        self._batch_size = batch_size
        self._poll_interval = poll_interval

    async def publish_pending(self) -> int:
        async with self._session.begin():
            unpublished_events = await self._repository.get_unpublished(self._batch_size)
        for event in unpublished_events:
            await self._publisher.publish(key=event.payload["shipment_id"], value=event.payload)
            async with self._session.begin():
                await self._repository.mark_published(event)
        return len(unpublished_events)

    async def run(self) -> None:
        logger.info("Relay started")
        while True:
            try:
                count = await self.publish_pending()
            except Exception:
                logger.exception("Failed to publish pending events")
                await asyncio.sleep(self._poll_interval)
                continue
            if count > 0:
                logger.info("Published {} events", count)
            else:
                await asyncio.sleep(self._poll_interval)
