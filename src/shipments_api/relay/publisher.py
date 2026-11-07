import json
from typing import Any

from aiokafka import AIOKafkaProducer


class KafkaPublisher:
    def __init__(self, bootstrap_servers: str, topic: str) -> None:
        self._topic = topic
        self._producer = AIOKafkaProducer(bootstrap_servers=bootstrap_servers)

    async def start(self) -> None:
        await self._producer.start()

    async def stop(self) -> None:
        await self._producer.stop()

    async def publish(self, key: str, value: dict[str, Any]) -> None:
        b_key = key.encode()
        b_value = json.dumps(value).encode()
        await self._producer.send_and_wait(topic=self._topic, value=b_value, key=b_key)
