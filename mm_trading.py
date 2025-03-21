import asyncio
from datetime import datetime
from pathlib import Path
import json

class mm_Trader:
    def __init__(self):
        self.trade_history = []
        # Load inventory from file
        self.inventory_file = Path("inventory.json")
        self.inventory = self._load_inventory()
    
    def _load_inventory(self):
        """Load initial inventory from JSON file"""
        if self.inventory_file.exists():
            with open(self.inventory_file) as f:
                return json.load(f)
        return {"Fund": {"USD": 10000000}}  # Default if file doesn't exist
    
    def _save_inventory(self):
        """Save current inventory to JSON file"""
        with open(self.inventory_file, "w") as f:
            json.dump(self.inventory, f)
    
    def _ensure_pair_exists(self, pair):
        """Ensure the trading pair exists in inventory"""
        if pair not in self.inventory:
            self.inventory[pair] = 0.0
            self._save_inventory()

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
                total_revenue = best_ask * sell_volume
                self.inventory["Fund"]["USD"] += total_revenue
                self.inventory[pair] -= sell_volume
                self._save_inventory()
                
                self.trade_history.append({
                    'time': current_time,
                    'type': 'sell',
                    'price': best_ask,
                    'volume': sell_volume,
                    'exchange': sell_exchange,
                    'pair': pair,
                    'inventory': self.inventory.copy()
                })
                print(f"[{sell_exchange.upper()} SELL] {sell_volume} {pair} @ {best_ask} | Total: {total_revenue} | Inventory: {self.inventory}")
                return
                
            # Calculate total cost
            total_cost = best_bid * max_affordable_volume
            
            # Execute buy
            self.inventory["Fund"]["USD"] -= total_cost
            self.inventory[pair] += max_affordable_volume
            self._save_inventory()
            
            self.trade_history.append({
                'time': current_time,
                'type': 'buy',
                'price': best_bid,
                'volume': max_affordable_volume,
                'exchange': buy_exchange,
                'pair': pair,
                'inventory': self.inventory.copy()
            })
            print(f"[{buy_exchange.upper()} BUY] {max_affordable_volume} {pair} @ {best_bid} | Total: {total_cost} | Inventory: {self.inventory}")
            
            # Immediately sell at best ask with available ask volume
            sell_volume = min(max_affordable_volume, ask_volume)
            total_revenue = best_ask * sell_volume
            self.inventory["Fund"]["USD"] += total_revenue
            self.inventory[pair] -= sell_volume
            self._save_inventory()
            
            self.trade_history.append({
                'time': current_time,
                'type': 'sell',
                'price': best_ask,
                'volume': sell_volume,
                'exchange': sell_exchange,
                'pair': pair,
                'inventory': self.inventory.copy()
            })
            print(f"[{sell_exchange.upper()} SELL] {sell_volume} {pair} @ {best_ask} | Total: {total_revenue} | Inventory: {self.inventory}")

async def trading_strategy(upper_bound, lower_bound, best_bid, best_ask, buy_exchange, sell_exchange):
    """Main trading strategy loop"""
    trader = Trader()
    
    while True:
        await trader.execute_trade(best_bid, best_ask, upper_bound, lower_bound, buy_exchange, sell_exchange)
        await asyncio.sleep(1)