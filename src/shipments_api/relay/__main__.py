import asyncio

from loguru import logger

from shipments_api.core.config import get_settings
from shipments_api.core.database import SessionFactory
from shipments_api.relay.publisher import KafkaPublisher
from shipments_api.relay.relay import OutboxRelay
from shipments_api.repository.outbox import OutboxRepository


async def run_relay() -> None:
    settings = get_settings()
    async with KafkaPublisher(
        bootstrap_servers=settings.kafka_bootstrap_servers, topic=settings.kafka_topic
    ) as publisher:
        async with SessionFactory() as session:
            relay = OutboxRelay(session, OutboxRepository(session), publisher)
            await relay.run()


def main() -> None:
    try:
        asyncio.run(run_relay())
    except KeyboardInterrupt:
        logger.info("Relay stopped")


if __name__ == "__main__":
    main()
