import aiofiles
import asyncio
from datetime import datetime
from pathlib import Path
import json

class mm_Trader:
    def __init__(self):
        self.trade_history = []
        self.trade_history_file = Path("trade_history.jsonl")
        self.inventory_file = Path("inventory.json")
        self.inventory = {"Fund": {"USD": 10000000}}  # Default value
        # We'll load inventory in a separate async method

    async def initialize(self):
        """Initialize the trader by loading inventory"""
        self.inventory = await self._load_inventory()
        return self

    async def _load_inventory(self):
        """Load initial inventory from JSON file"""
        if self.inventory_file.exists():
            async with aiofiles.open(self.inventory_file, mode='r') as f:
                content = await f.read()
                return json.loads(content)
        return {"Fund": {"USD": 10000000}}

    async def _save_inventory(self):
        """Save current inventory to JSON file"""
        async with aiofiles.open(self.inventory_file, mode='w') as f:
            await f.write(json.dumps(self.inventory))

    async def _ensure_pair_exists(self, pair):
        """Ensure the trading pair exists in inventory"""
        if pair not in self.inventory:
            self.inventory[pair] = 0.0
            await self._save_inventory()

    async def _save_trade_history(self, trade):
        """Append trade to JSONL file"""
        async with aiofiles.open(self.trade_history_file, mode='a') as f:
            await f.write(json.dumps(trade) + "\n")

    async def _execute_buy(self, price, volume, exchange, pair, current_time):
        """Execute buy operation"""
        total_cost = price * volume
        self.inventory["Fund"]["USD"] -= total_cost
        self.inventory[pair] += volume
        await self._save_inventory()
        
        trade = {
            'time': current_time,
            'type': 'buy',
            'price': price,
            'volume': volume,
            'exchange': exchange,
            'pair': pair,
            'inventory': self.inventory.copy()
        }
        await self._save_trade_history(trade)
        print(f"[{exchange.upper()} BUY] {volume} {pair} @ {price} | Total: {total_cost} | Inventory: {self.inventory}")

    async def _execute_sell(self, price, volume, exchange, pair, current_time):
        """Execute sell operation"""
        total_revenue = price * volume
        self.inventory["Fund"]["USD"] += total_revenue
        self.inventory[pair] -= volume
        await self._save_inventory()
        
        trade = {
            'time': current_time,
            'type': 'sell',
            'price': price,
            'volume': volume,
            'exchange': exchange,
            'pair': pair,
            'inventory': self.inventory.copy()
        }
        await self._save_trade_history(trade)
        print(f"[{exchange.upper()} SELL] {volume} {pair} @ {price} | Total: {total_revenue} | Inventory: {self.inventory}")

    async def execute_trade(self, best_bid, best_ask, upper_bound, lower_bound, buy_exchange, sell_exchange, bid_volume, ask_volume, pair):
        """Execute trades based on the strategy"""
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
        
        # Ensure pair exists in inventory
        self._ensure_pair_exists(pair)
        
        # Buy condition with budget check
        if lower_bound <= best_bid <= upper_bound:
            # Calculate maximum volume we can buy within budget
            max_affordable_volume = min(bid_volume, self.inventory["Fund"]["USD"] / best_bid)
            
            if max_affordable_volume <= 0:
                # Check if we have any inventory to sell
                if self.inventory[pair] <= 0:
                    print(f"[INFO] Insufficient funds and no inventory to sell, skipping this trade.")
                    return
                
                # Calculate maximum volume we can sell
                sell_volume = min(self.inventory[pair], ask_volume)
                if sell_volume <= 0:
                    print(f"[INFO] No inventory to sell, skipping this trade.")
                    return
                
                # Execute sell only
                await self._execute_sell(best_ask, sell_volume, sell_exchange, pair, current_time)
            elif bid_volume == 0:
                # Calculate maximum volume we can sell
                sell_volume = min(self.inventory[pair], ask_volume)
                if sell_volume <= 0:
                    print(f"[INFO] No inventory to sell or buy, skipping this trade.")
                    return
                await self._execute_sell(best_ask, sell_volume, sell_exchange, pair, current_time)
                return
                
            # Check funds again after selling
            max_affordable_volume = min(bid_volume, self.inventory["Fund"]["USD"] / best_bid)
            if lower_bound <= best_bid <= upper_bound and max_affordable_volume > 0:
                # Execute buy
                await self._execute_buy(best_bid, max_affordable_volume, buy_exchange, pair, current_time)
                
                # Immediately sell at best ask with available ask volume
                sell_volume = min(max_affordable_volume, ask_volume)
                await self._execute_sell(best_ask, sell_volume, sell_exchange, pair, current_time)

async def trading_strategy(upper_bound, lower_bound, best_bid, best_ask, buy_exchange, sell_exchange):
    """Main trading strategy loop"""
    trader = Trader()
    
    while True:
        await trader.execute_trade(best_bid, best_ask, upper_bound, lower_bound, buy_exchange, sell_exchange)
        await asyncio.sleep(1)