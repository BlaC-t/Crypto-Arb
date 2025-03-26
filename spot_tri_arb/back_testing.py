import asyncio
import json
import redis
from datetime import datetime
import logging
import os
import matplotlib.pyplot as plt

# ========== CONFIG ==========
SYMBOLS = ['btcusdt', 'ethbtc', 'ethusdt']
TRADE_SIZE = 1000  # 
THRESHOLD = 0  # 

# ========== REDIS ==========
r = redis.Redis(host='localhost', port=6379, db=0)

# ========== LOGGER ==========
os.makedirs("logs", exist_ok=True)
logger = logging.getLogger("ArbitrageLogger")
logger.setLevel(logging.INFO)
log_filename = f"logs/arbitrage_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
fh = logging.FileHandler(log_filename)
formatter = logging.Formatter('%(asctime)s,%(message)s', datefmt='%Y-%m-%d %H:%M:%S')
fh.setFormatter(formatter)
logger.addHandler(fh)

# ========== DATA ==========
cumulative_profit = 0.0
profit_history = []
time_history = []


# ========== ARBITRAGE FUNCTIONS ==========
def arbitrage_path_forward(btc_ask, ethbtc_ask, ethusdt_bid):
    eth = TRADE_SIZE / ethusdt_bid
    btc = eth * ethbtc_ask
    final_usdt = btc * btc_ask
    profit = final_usdt - TRADE_SIZE-1000*0.0003
    return profit, final_usdt

def arbitrage_path_reverse(btc_bid, ethbtc_bid, ethusdt_ask):
    eth = TRADE_SIZE / ethusdt_ask
    btc = eth * ethbtc_bid
    final_usdt = btc * btc_bid
    profit = final_usdt - TRADE_SIZE-1000*0.0003
    return profit, final_usdt

# ========== PLOT FUNCTION ==========
def plot_cumulative_profit():
    plt.figure(figsize=(10, 5))
    plt.plot(time_history, profit_history, marker='o')
    plt.title("Cumulative Arbitrage Profit Over Time")
    plt.xlabel("Time")
    plt.ylabel("Cumulative Profit (USDT)")
    plt.xticks(rotation=45)
    plt.grid(True)
    plt.tight_layout()
    plt.savefig("logs/cumulative_profit.png")
    plt.close()

# ========== MAIN LOOP ==========
async def monitor_from_redis():
    global cumulative_profit
    print(" Monitoring quotes from Redis...")
    while True:
        try:
            quotes = r.hgetall("backtest")
            if not quotes:
                await asyncio.sleep(0.5)
                continue

            btc_ask = float(quotes[b"btcusdt_ask"])
            btc_bid = float(quotes[b"btcusdt_bid"])
            ethbtc_ask = float(quotes[b"ethbtc_ask"])
            ethbtc_bid = float(quotes[b"ethbtc_bid"])
            ethusdt_ask = float(quotes[b"ethusdt_ask"])
            ethusdt_bid = float(quotes[b"ethusdt_bid"])

            timestamp = datetime.now()
            print('monitoring')
            # Path 1
            profit1, final1 = arbitrage_path_forward(btc_ask, ethbtc_ask, ethusdt_bid)
            if profit1 > THRESHOLD:
                cumulative_profit += profit1
                profit_history.append(cumulative_profit)
                time_history.append(timestamp.strftime("%H:%M:%S"))
                plot_cumulative_profit()
                print(f"[{timestamp}]  Path1 SELL ETHUSDT → BUY ETHBTC, BTCUSDT | Profit=${profit1:.2f} | Cumulative=${cumulative_profit:.2f}")
                logger.info(
                    f"FORWARD_ARBITRAGE,{profit1:.2f},{final1:.2f},{cumulative_profit:.2f},"
                    f"{btc_ask:.2f},{btc_bid:.2f},{ethbtc_ask:.6f},{ethbtc_bid:.6f},{ethusdt_ask:.2f},{ethusdt_bid:.2f}"
                )

            # Path 2
            profit2, final2 = arbitrage_path_reverse(btc_bid, ethbtc_bid, ethusdt_ask)
            if profit2 > THRESHOLD:
                cumulative_profit += profit2
                profit_history.append(cumulative_profit)
                time_history.append(timestamp.strftime("%H:%M:%S"))
                plot_cumulative_profit()
                print(f"[{timestamp}]  Path2 BUY ETHUSDT → SELL ETHBTC, BTCUSDT | Profit=${profit2:.2f} | Cumulative=${cumulative_profit:.2f}")
                logger.info(
                    f"REVERSE_ARBITRAGE,{profit2:.2f},{final2:.2f},{cumulative_profit:.2f},"
                    f"{btc_ask:.2f},{btc_bid:.2f},{ethbtc_ask:.6f},{ethbtc_bid:.6f},{ethusdt_ask:.2f},{ethusdt_bid:.2f}"
                )

            await asyncio.sleep(0.2)

        except Exception as e:
            print(f" Error: {e}")
            await asyncio.sleep(1)

# ========== RUN ==========
asyncio.run(monitor_from_redis())