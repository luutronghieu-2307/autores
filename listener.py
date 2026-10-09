from abc import ABC, abstractmethod
from aiokafka import AIOKafkaProducer
from aiokafka.consumer import AIOKafkaConsumer
from aiokafka.structs import ConsumerRecord
import asyncio
import logging
import json
import traceback
import time
import uuid
from aiokafka.errors import KafkaError
import random

from producers import get_producer
from status_type import AIStatus
from exception_type import AIERROR
from utils import get_mongodb_client, get_redis_client, get_redis_stack_client, send_health_check
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

logger = logging.getLogger(__name__)


class BaseAsyncListener(ABC):
    def __init__(self, topics, consumer_config: dict, concurency: int = 100) -> None:
        self._topics = topics
        self._consumer_config = consumer_config
        self._semaphore = asyncio.Semaphore(concurency)
        self._work_queue = asyncio.Queue(maxsize=2 * concurency)
        self.mongo_client = get_mongodb_client()
        self.redis_client = get_redis_stack_client()
        self.redis = get_redis_client()
        self._running = False
        self._worker_tasks: list[asyncio.Task] = []

    async def _ingestor_loop(self):
        await self._consumer.start()
        logger.info("Ingestor loop started. Fetching messages...")
        try:
            async for record in self._consumer:
                await self._work_queue.put(record)
                try:
                    value = json.loads(record.value)
                    if "document_id" in value:
                        _id = value["document_id"]
                        await send_health_check(id=_id, status=AIStatus.PENDING, topic=record.topic, event_type=value["event_type"])
                    elif "conv_id" in value:
                        _id = value["conv_id"]
                    else:
                        _id = "admin"
                except Exception:
                    logger.info("Invalid JSON body")
                    pass
                
                await self._consumer.commit()
        finally:
            logger.warning("Ingestor loop is shutting down.")
            await self._consumer.stop()

    async def _worker_loop(self, worker_id: int):
        while self._running:
            try:
                record = await self._work_queue.get()
                async with self._semaphore:
                    await self._handle_record(record=record)
                self._work_queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception:
                logger.error(f"Unhandled exception in Worker-{worker_id}. Continuing...", exc_info=True)
                self._work_queue.task_done()

    async def start(self):
        self._running = True
        await self.mongo_client.aconnect()
        try:
            self._consumer = AIOKafkaConsumer(
                *self._topics, **self._consumer_config
            )
            for i in range(self._semaphore._value):
                task = asyncio.create_task(self._worker_loop(worker_id=i))
                self._worker_tasks.append(task)
            ingestor_task = asyncio.create_task(self._ingestor_loop())
            await asyncio.gather(ingestor_task, *self._worker_tasks)
        except KafkaError as e:
            logger.error(f"Recoverable Kafka error: {e}. Attempting to restart consumer in 5 seconds.")
            await self._stop_consumer()
            await asyncio.sleep(5)
        except Exception:
            logger.error(f"Unhandled exception in listener. Restarting in 5 seconds.\n{traceback.format_exc()}")
            await self._stop_consumer()
            await asyncio.sleep(5)
        finally:
            logger.info("Running cleanup before potential restart...")
            await self._stop_consumer()

    async def _stop_consumer(self):
        """Stops the consumer if it is running."""
        if self._running:
            logger.info("Stopping Kafka consumer...")
            await self._work_queue.join()
        
            # Cancel all worker tasks
            for task in self._worker_tasks:
                task.cancel()
            
            # Wait for all tasks to finish cancelling
            await asyncio.gather(*self._worker_tasks, return_exceptions=True)
            self._worker_tasks.clear()
            await self._consumer.stop()
            self._running = False
            logger.info("Consumer stopped.")

    async def _task_timer(self, _id: str, event_type: str, topic: str, ttl: int = 300):
        while True:
            await send_health_check(id=_id, status=AIStatus.PROCESSING, topic=topic, event_type=event_type, ttl=ttl)
            await asyncio.sleep(int(ttl / 2))

    async def task_timer(self, _id: str, event_type: str, topic: str, total_time: float, ttl: int = 300):
        try:
            await asyncio.wait_for(self._task_timer(_id, event_type, topic, ttl), timeout=total_time)
        except asyncio.CancelledError:
            raise
        except asyncio.TimeoutError:
            pass

    async def _finalize_task(
        self,
        timer_task: asyncio.Task | None,
        success: bool,
        _id: str,
        producer: AIOKafkaProducer,
        topic: str,
        message: dict,
        event_type: str,
        is_suspended: bool = False
    ):
        if timer_task and not timer_task.done():
            timer_task.cancel()
            try:
                await timer_task
            except asyncio.CancelledError:
                pass
        await self.send_message(producer, topic, message, _id if _id != "admin" else "")
        if is_suspended:
            error_code = message.get("error_code", 608)
            error_msg = message.get("error", "An unspecified error occurred.")
            await send_health_check(id=_id, status=AIStatus.SUSPENDED, topic=topic, event_type=event_type, error=error_code, error_message=error_msg)
        else:
            if success:
                await send_health_check(id=_id, status=AIStatus.FINISHED, topic=topic, event_type=event_type)
            else:
                error_code = message.get("error_code", 608)
                error_msg = message.get("error", "An unspecified error occurred.")
                await send_health_check(id=_id, status=AIStatus.ERROR, topic=topic, event_type=event_type, error=error_code, error_message=error_msg)

    async def test_error(self, user_id: str, error_code: int):
        # return {}
        if user_id in ["683802b787b2175089765cc8"]:
            error_index = random.random()
            if error_index > 0.6:
                return {}
            else:
                raise AIERROR(status_code=error_code, message="Test error")
        else:
            return {}

    async def get_key(self, model_id: str = "") -> tuple[str, str]:
        key = f"AI_KEY:{model_id}"
        llm_key_bytes = await self.redis.get(key)
        if llm_key_bytes is None:
            llm_key = ""
        else:
            llm_key = json.loads(llm_key_bytes)
        db_key_bytes = await self.redis.get("AI_KEY:db_key")
        if db_key_bytes is None:
            db_key = ""
        else:
            db_key = json.loads(db_key_bytes)
        search_web_key_bytes = await self.redis.get("AI_KEY:search_web_key")
        if search_web_key_bytes is None:
            search_web_key = ""
        else:
            search_web_key = json.loads(search_web_key_bytes)
        return llm_key, db_key, search_web_key
    
    async def send_message(self, producer, topic, message, document_id: str = ""):
        key = str(uuid.uuid4())
        try:
            _ = await producer.send_and_wait(
                topic=topic, 
                key=key, 
                value=message,
            )
        except Exception:
            producer = await get_producer()
            _ = await producer.send_and_wait(
                topic=topic, 
                key=key, 
                value=message,
            )
        finally:
            if document_id:
                current_timestamp = time.time()
                redis_key = f"DOCUMENT_REPORT:{document_id}"
                await self.redis.sadd(redis_key, f"{current_timestamp} - {key}")

    def field_validate_str(self, field_dict: dict):
        """Validate that all fields are strings"""
        for field_name, field_value in field_dict.items():
            if not isinstance(field_value, str):
                raise ValueError(f"{field_name} must be a string")

    def field_validate_list_str(self, field_dict: dict):
        """Validate that all fields are lists of strings"""
        for field_name, field_value in field_dict.items():
            if not isinstance(field_value, list):
                raise ValueError(f"{field_name} must be a list")
            else:
                for value in field_value:
                    if not isinstance(value, str):
                        raise ValueError(f"{field_name} must be a list of string")
                        
    def field_validate_bool(self, field_dict: dict):
        """Validate that all fields are booleans"""
        for field_name, field_value in field_dict.items():
            if not isinstance(field_value, bool):
                raise ValueError(f"{field_name} must be a boolean")

    def field_validate_number(self, field_dict: dict):
        """Validate that all fields are numbers (int or float)"""
        for field_name, field_value in field_dict.items():
            if not isinstance(field_value, (int, float)):
                raise ValueError(f"{field_name} must be a number")
 
    def field_validate_list_number(self, field_dict: dict):
        """Validate that all fields in the list are lists of strings"""
        for field_name, field_value in field_dict.items():
            if not isinstance(field_value, list):
                raise ValueError(f"{field_name} must be a list")
            else:
                for value in field_value:
                    if not isinstance(value, (int, float)):
                        raise ValueError(f"{field_name} must be a list of number")

    def field_validate_dict(self, field_dict: dict):
        """Validate that all fields are dictionaries"""
        for field_name, field_value in field_dict.items():
            if not isinstance(field_value, dict):
                raise ValueError(f"{field_name} must be a dictionary")
                
    def field_validate_list_dict(self, field_dict: dict):
        """Validate that all fields are lists of strings"""
        for field_name, field_value in field_dict.items():
            if not isinstance(field_value, list):
                raise ValueError(f"{field_name} must be a list")
            else:
                for value in field_value:
                    if not isinstance(value, dict):
                        raise ValueError(f"{field_name} must be a dictionary")

    def empty_value_check(self, field_dict: dict):
        """Check that all string fields are not empty and all list fields are not empty"""
        for field_name, field_value in field_dict.items():
            if isinstance(field_value, str):
                if not field_value.strip():
                    raise ValueError(f"{field_name} cannot be empty")
            elif isinstance(field_value, list):
                if not field_value:
                    raise ValueError(f"{field_name} cannot be empty")
            elif isinstance(field_value, dict):
                if not field_value:
                    raise ValueError(f"{field_name} cannot be empty")

    async def clean_up(self, thread_id: str, document_id: str = ""):
        keys_to_delete: list[bytes] = []
        async for key in self.redis_client.scan_iter(match=f"*:{thread_id}:*"):
            keys_to_delete.append(key)
        if keys_to_delete:
            logger.info(f"Clean up redis for {thread_id}")
            _ = await self.redis_client.delete(*keys_to_delete)
        db = self.mongo_client["BotGraph"]
        checkpoint_collection = db["BotCheckpoint"]
        writes_collection = db["BotWrite"]
        delete_checkpoint_task = checkpoint_collection.delete_many({"thread_id": thread_id})
        delete_writes_task = writes_collection.delete_many({"thread_id": thread_id})
        await asyncio.gather(delete_checkpoint_task, delete_writes_task)
        if document_id:
            admin_db = self.mongo_client["admin"]
            outline_colletion = admin_db["outlines"]
            await outline_colletion.update_many(
                {
                    "documentId": document_id
                },
                {
                    "$set": {
                        "content": "",
                        "contentArr": [],
                        "updatedAt": int(time.time()),
                    }
                }
            )

    @abstractmethod
    async def _handle_record(self, record: ConsumerRecord):
        pass