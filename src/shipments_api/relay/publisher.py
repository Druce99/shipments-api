import json
from typing import Any

from aiokafka import AIOKafkaProducer


class KafkaPublisher:
    def __init__(self, bootstrap_servers: str, topic: str) -> None:
        self._topic = topic
        self._producer = AIOKafkaProducer(bootstrap_servers=bootstrap_servers)

    async def publish(self, key: str, value: dict[str, Any]) -> None:
        b_key = key.encode()
        b_value = json.dumps(value).encode()
        await self._producer.send_and_wait(topic=self._topic, value=b_value, key=b_key)

    async def __aenter__(self) -> "KafkaPublisher":
        await self._producer.start()
        return self

    async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None:
        await self._producer.stop()
