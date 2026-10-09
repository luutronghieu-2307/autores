import asyncio

from document_setup.src.configs.app import settings

from write_listener import start_listener as WriteListener
from utils import set_num_partitions, init_singleton
import topics


async def main():
    await set_num_partitions(settings.KAFKA, [topics.WRITE_SECTION_REQUEST_LOCAL, topics.WRITE_SECTION_RESPONSE_LOCAL], 3)
    await init_singleton()
    await WriteListener(
        [topics.WRITE_SECTION_REQUEST_LOCAL],
        "write_section_05_20_2025"
    )


if __name__ == "__main__":
    asyncio.run(main())