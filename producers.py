import asyncio
from aiokafka import AIOKafkaProducer

from document_setup.src.configs.app import settings

from utils import serializer

_PRODUCER: AIOKafkaProducer | None = None
_PRODUCER_LOCK = asyncio.Lock()


async def get_producer():
    global _PRODUCER
    if _PRODUCER is None:
        async with _PRODUCER_LOCK:
            producer = AIOKafkaProducer(
                bootstrap_servers=settings.KAFKA,
                key_serializer=serializer,
                value_serializer=serializer,
            )
            await producer.start()
            _PRODUCER = producer
    return _PRODUCER
