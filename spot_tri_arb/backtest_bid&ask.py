import asyncio
import websockets
import json
import redis
import time

# Config
SYMBOLS = ['btcusdt', 'ethbtc', 'ethusdt']
WS_URL = f"wss://stream.binance.com:9443/stream?streams=" + "/".join([f"{s}@bookTicker" for s in SYMBOLS])

# Redis client
r = redis.Redis(host='localhost', port=6379, db=0)

# 
quote_cache = {}

async def stream_quotes_to_redis():
    async with websockets.connect(WS_URL) as ws:
        print(" Connected to Binance WebSocket")
        while True:
            try:
                message = await ws.recv()
                msg = json.loads(message)
                payload = msg['data']
                symbol = payload['s'].lower()

                bid = float(payload['b'])
                ask = float(payload['a'])

                # 
                quote_cache[f"{symbol}_bid"] = bid
                quote_cache[f"{symbol}_ask"] = ask

                #  Redis
                r.hset("backtest", mapping=quote_cache)
                print(f"[{symbol}] bid={bid}, ask={ask} → stored in Redis key: 'backtest'")

            except Exception as e:
                print(f" Error in stream_quotes_to_redis: {e}")
                await asyncio.sleep(1)  # 

if __name__ == '__main__':
    asyncio.run(stream_quotes_to_redis())
