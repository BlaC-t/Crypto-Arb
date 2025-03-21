import asyncio
import best_bid_ask
import data_fetch
from datetime import datetime, timedelta

global record_bids
record_bids = {}


async def calculate_vwap(bids):
    if not bids:
        return None
    total_value = sum(float(bid["best_bid"]) * float(bid["volume"]) for bid in bids)
    total_volume = sum(float(bid["volume"]) for bid in bids)
    return total_value / total_volume if total_volume > 0 else None


async def main():
    fetch_task = asyncio.create_task(data_fetch.main())
    last_vwap_time = datetime.now()

    while True:
        process_task = asyncio.create_task(best_bid_ask.main(record_bids))
        await asyncio.gather(process_task)

        # Calculate rolling VWAP every second
        current_time = datetime.now()

        # Remove bids older than 5 seconds
        record_bids_copy = record_bids.copy()
        for timestamp in list(record_bids_copy.keys()):
            bid_time = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S.%f")
            if (current_time - bid_time) > timedelta(seconds=5):
                del record_bids[timestamp]

        # Calculate VWAP for the remaining bids
        recent_bids = list(record_bids.values())
        vwap = await calculate_vwap(recent_bids)
        if vwap is None:
            print("Invalid VWAP")
        else:
            print(f"VWAP: {vwap}")

        await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())
