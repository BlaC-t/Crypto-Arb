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
    total_usd = sum(float(bid["best_bid"]) * float(bid["best_bid_volume"]) for bid in bids)
    total_volume = sum(float(bid["best_bid_volume"]) for bid in bids)
    return total_usd / total_volume if total_volume > 0 else None


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
    trader = await mm_trading.mm_Trader().initialize()
    
    # Initialize Bollinger Bands variables
    upper_bound = None
    lower_bound = None
    
    # Create a task for reading stdin
    stop_event = asyncio.Event()
    stdin_task = asyncio.create_task(read_stdin(stop_event))

    while not stop_event.is_set():
        process_task = asyncio.create_task(best_bid_ask.main(record_bids))
        await asyncio.gather(process_task)

        # Remove bids older than 5 seconds
        current_time = datetime.now()
        await remove_old_bids(record_bids, current_time)

        # Calculate rolling VWAP
        recent_bids = list(record_bids.values())
        vwap = await calculate_vwap(recent_bids)
        
        # Update Bollinger Bands every 5 seconds
        if (current_time - last_vwap_time) > timedelta(seconds=5):
            if len(recent_bids) >= 5:
                bid_prices = [float(bid["best_bid"]) for bid in recent_bids[-5:]]
                _, upper_bound, lower_bound = await tools.bollinger_bands(bid_prices)
                last_vwap_time = current_time

        # Execute trading strategy every second with current bounds
        if upper_bound is not None and lower_bound is not None:
            # Get current best bid/ask and exchanges
            best_bid = float(recent_bids[-1]["best_bid"])
            best_ask = float(recent_bids[-1]["best_ask"])
            buy_exchange = recent_bids[-1]["best_bid_exchange"]
            sell_exchange = recent_bids[-1]["best_ask_exchange"]
            bid_volume = float(recent_bids[-1]["best_bid_volume"])
            ask_volume = float(recent_bids[-1]["best_ask_volume"])
            pair = recent_bids[-1]["pair"]
            
            # Execute trade with current bounds
            await trader.execute_trade(best_bid, best_ask, upper_bound, lower_bound, 
                                     buy_exchange, sell_exchange, bid_volume, ask_volume, pair)

        await asyncio.sleep(1)

    # Clean up tasks
    fetch_task.cancel()
    stdin_task.cancel()
    try:
        await asyncio.gather(fetch_task, stdin_task)
    except asyncio.CancelledError:
        pass

    # Calculate final inventory value
    await calculate_final_inventory_value(trader, record_bids)

async def calculate_final_inventory_value(trader, record_bids):
    """Calculate total value of inventory using last best_ask prices"""
    if not record_bids:
        print("No recent bids available to calculate inventory value")
        return
    
    # Get the last bid data
    last_bid = list(record_bids.values())[-1]
    best_ask = float(last_bid["best_ask"])
    pair = last_bid["pair"]
    
    # Get current inventory
    inventory = trader.inventory
    total_usd = inventory["Fund"]["USD"]
    
    # Calculate value of coins
    if pair in inventory and inventory[pair] > 0:
        coin_value = inventory[pair] * best_ask
        total_usd += coin_value
        print(f"\nFinal Inventory Value:")
        print(f"USD: {inventory['Fund']['USD']}")
        print(f"{pair}: {inventory[pair]} (Value: {coin_value} @ {best_ask})")
        print(f"Total Value: {total_usd}")
    else:
        print(f"\nFinal Inventory Value: {total_usd} USD (No {pair} holdings)")

async def read_stdin(stop_event):
    """Read stdin and set stop event when 'stop' is entered"""
    loop = asyncio.get_running_loop()
    while True:
        line = await loop.run_in_executor(None, input)
        if line.strip().lower() == "stop":
            stop_event.set()
            break

if __name__ == "__main__":
    asyncio.run(main())
