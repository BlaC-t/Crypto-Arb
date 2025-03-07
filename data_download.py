import asyncio
from websockets import connect
import aiofiles
import sys
import json
import httpx
import time
import datetime
import os

RECONNECT_THRESHOLD = 86400 - 60

EXCHANGE_CONFIG = {
    "binance": {
        "rest_url": "https://api.binance.com/api/v3/depth",
        "ws_url": "wss://stream.binance.com:443/ws/{pair}@depth",
        "rate_limit": 0.2,  # 5次/秒
        "param_map": {
            "instrument_id": "symbol",
            "depth_size": "limit"
        },
        "snapshot_parser": lambda data: {
            "asks": data["asks"],
            "bids": data["bids"],
            "ts": data["lastUpdateId"]
        },
        "subscription_template": {
            "method": "SUBSCRIBE",
            "params": ["{pair}@depth"],
            "id": 1
        }
    },
    "okx": {
        "rest_url": "https://www.okx.com/api/v5/market/books",
        "ws_url": "wss://ws.okx.com:8443/ws/v5/public",
        "rate_limit": 0.2,  # 10次/2秒
        "param_map": {
            "instrument_id": "instId",
            "depth_size": "sz"
        },
        "snapshot_parser": lambda data: {
            "asks": data["data"][0]["asks"],
            "bids": data["data"][0]["bids"],
            "ts": data["data"][0]["ts"]
        },
        "subscription_template": {
            "op": "subscribe",
            "args": [{
                "channel": "books",
                "instId": "{pair}"
            }]
        }
    }
}

async def get_snapshot(url, params, exchange_name, pair, date):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)

        response.raise_for_status()  # Raise error for non-200 responses
        snapshot = response.json()

        snapshot["timestamp"] = time.time()
        file_path = f"{exchange_name}/orderbook_{pair.lower()}-snapshot-{date}.txt"
        
        async with aiofiles.open(file_path, mode="a") as f:
            await f.write(json.dumps(snapshot) + "\n")
        print(f"Snapshot written to {file_path}")

    except httpx.HTTPStatusError as exc:
        error_json = exc.response.json()
        if error_json.get("code") == -1003:
            print("Rate limit exceeded while fetching snapshot. Waiting before retrying...")
            print(f"Error message: {error_json.get('msg')}")
            # Wait for a while before trying again (adjust as needed)
            await asyncio.sleep(60)
            pass
        else:
            print(f"HTTP error occurred: {exc}")

    except Exception as e:
        print(f"An error occurred while getting snapshot: {e}")



async def listener(ws, exchange_name, pair, date, stop_event):
    while not stop_event.is_set():
        try:
            data = await ws.recv()
            async with aiofiles.open(f"{exchange_name}/orderbook_{pair}-update-{date}.txt", mode="a") as f:
                await f.write(data + "\n")
                print(datetime.datetime.now())
        except asyncio.TimeoutError:
            continue
        except Exception as e:
            print(f'Error receiving data: {e}')
            break
            

async def orderbook_download_binance(pair): # UNIUSDT
    # set up the websocket and rest API URLs
    os.makedirs("binance", exist_ok=True)
    date = datetime.datetime.now().date()
    pair_lower = pair.lower()

    ws_url = f"wss://stream.binance.com:443/ws/{pair_lower}@depth"
    rest_url = f"https://api.binance.com/api/v3/depth"
    
    # get the snapshot
    params = {
        "symbol": pair.upper(),
        "limit": 100
    }

    await get_snapshot(rest_url, params, "binance", pair_lower, date)

    connect_start_time = time.time()
    stop_event = asyncio.Event()
    ws = await connect(ws_url)
    listener_task = asyncio.create_task(listener(ws, "binance", pair_lower, date, stop_event))

    while True:
        elasped = time.time() - connect_start_time
        if elasped > RECONNECT_THRESHOLD:
            new_date = datetime.datetime.now().date()
            if new_date != date:
                date = new_date
                await get_snapshot(rest_url, params, "binance", pair_lower, date)
            
            new_stop_event = asyncio.Event()
            new_ws = await connect(ws_url)
            new_listener_task = asyncio.create_task(listener(new_ws, "binance", pair_lower, date, new_stop_event))
            await asyncio.sleep(0.1)

            stop_event.set()
            await ws.close()
            try:
                await listener_task
            except Exception as e:
                print(f'Error in listener_task: {e}')

            ws = new_ws
            listener_task = new_listener_task
            stop_event = new_stop_event
            connect_start_time = time.time()
            await get_snapshot(rest_url, params, "binance", pair_lower, date)
            print('Reconnection successful, new connection established')

        await asyncio.sleep(1)

# asyncio.run(orderbook_download_binance("UNIUSDT"))




async def orderbook_download_OKX(pair): # BTC-USDT
    os.makedirs("OKX", exist_ok=True)
    date = datetime.datetime.now().date()
    pair_usable = pair[:-4] + "-" + pair[-4:]
    pass

asyncio.run(orderbook_download_OKX("UNIUSDT"))

async def orderbook_download_BitGet(pair):
    date = datetime.datetime.now().date()

    pair_lower = pair.lower()
    pass

async def orderbook_download_CryptoCom(pair):
    date = datetime.datetime.now().date()

    pair_lower = pair.lower()
    pass

async def orderbook_download_HyperLiquid(pair):
    date = datetime.datetime.now().date()

    pair_lower = pair.lower()
    pass