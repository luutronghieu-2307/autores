import asyncio

from document_setup.src.configs.app import settings

from document_setup_listener import start_listener as DocumentSetupListener
from utils import set_num_partitions, init_singleton
import topics


async def main():
    await set_num_partitions(settings.KAFKA, [topics.DOCUMENT_SETUP_REQUEST_LOCAL, topics.DOCUMENT_SETUP_RESPONSE_LOCAL], 3)
    await init_singleton()
    await DocumentSetupListener(
        [topics.DOCUMENT_SETUP_REQUEST_LOCAL],
        "document_setup_05_20_2025"
    )


if __name__ == "__main__":
    asyncio.run(main())