import asyncio
import best_bid_ask
import data_fetch
from datetime import datetime, timedelta
import tools
import mm_trading  # Add this import

global record_bids
record_bids = {}


async def calculate_vwap(bids):
    if not bids:
        return None
    total_value = sum(float(bid["best_bid"]) * float(bid["best_bid_volume"]) for bid in bids)
    total_volume = sum(float(bid["best_bid_volume"]) for bid in bids)
    return total_value / total_volume if total_volume > 0 else None


async def remove_old_bids(record_bids, current_time, max_age_seconds=5):
    """Remove bids older than max_age_seconds from record_bids"""
    record_bids_copy = record_bids.copy()
    for timestamp in list(record_bids_copy.keys()):
        bid_time = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S.%f")
        if (current_time - bid_time) > timedelta(seconds=max_age_seconds):
            del record_bids[timestamp]


async def main():
    fetch_task = asyncio.create_task(data_fetch.main())
    last_vwap_time = datetime.now()
    trader = mm_trading.mm_Trader()  # Initialize trader

    while True:
        process_task = asyncio.create_task(best_bid_ask.main(record_bids))
        await asyncio.gather(process_task)

        # Remove bids older than 5 seconds
        current_time = datetime.now()
        await remove_old_bids(record_bids, current_time)

        # Calculate rolling VWAP
        recent_bids = list(record_bids.values())
        vwap = await calculate_vwap(recent_bids)
        
        # Calculate Bollinger Bands every 5 seconds
        if (current_time - last_vwap_time) > timedelta(seconds=5):
            recent_bids = list(record_bids.values())
            if len(recent_bids) >= 5:
                bid_prices = [float(bid["best_bid"]) for bid in recent_bids[-5:]]
                avg, upper_bound, lower_bound = await tools.bollinger_bands(bid_prices)
                
                # Get current best bid/ask and exchanges
                best_bid = float(recent_bids[-1]["best_bid"])
                best_ask = float(recent_bids[-1]["best_ask"])
                buy_exchange = recent_bids[-1]["best_bid_exchange"]  # Get buy exchange
                sell_exchange = recent_bids[-1]["best_ask_exchange"]  # Get sell exchange
                bid_volume = float(recent_bids[-1]["best_bid_volume"])
                ask_volume = float(recent_bids[-1]["best_ask_volume"])
                pair = recent_bids[-1]["pair"]
                
                # Execute trading strategy with exchange information
                # await trader.execute_trade(best_bid, best_ask, upper_bound, lower_bound, buy_exchange, sell_exchange, bid_volume, ask_volume, pair)
                
                last_vwap_time = current_time

        await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())
