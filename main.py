import asyncio
import data_processing
import data_fetch


async def main():
    fetch_task = asyncio.create_task(data_fetch.main())
    process_task = asyncio.create_task(data_processing.main())
    await asyncio.gather(fetch_task, process_task)


if __name__ == "__main__":
    asyncio.run(main())
