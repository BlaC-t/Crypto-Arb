import asyncio
from data_processing import process_latest_data
from data_fetch import main as data_fetch_main


async def main():
    fetch_task = asyncio.create_task(data_fetch.main())
    process_task = asyncio.create_task(process_latest_data())
    await asyncio.gather(fetch_task, process_task)

if __name__ == "__main__":
    asyncio.run(main())