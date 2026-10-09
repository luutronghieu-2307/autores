import asyncio

from document_setup.src.configs.app import settings

from chatbot_listener import start_listener as ChatbotListener
from utils import set_num_partitions, init_singleton
import topics


async def main():
    await set_num_partitions(settings.KAFKA, [topics.CHATBOT_REQUEST_LOCAL, topics.CHATBOT_RESPONSE_LOCAL], 3)
    await init_singleton()
    await ChatbotListener(
        [topics.CHATBOT_REQUEST_LOCAL],
        "chatbot_09_06_2025"
    )


if __name__ == "__main__":
    asyncio.run(main())