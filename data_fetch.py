import asyncio
from websockets import connect
import aiofiles
import sys
import json
import httpx
import time
import datetime
import os

from tools import symbol_formating, send_ping

RECONNECT_THRESHOLD = 86400 - 60

EXCHANGE_CONFIG = {
    "binance": {
        "rest_url": "https://api.binance.com/api/v3/depth",
        "ws_url": "wss://stream.binance.com:443/ws/{pair}@depth",
        "rate_limit": 0.2,
        "symbol_format": "xxxyyyy",
        "param_map": {"instrument_id": "symbol", "depth_size": "limit"},
        "snapshot_parser": lambda data: {
            "asks": data["asks"],
            "bids": data["bids"],
            "ts": data["lastUpdateId"],
        },
        "subscription_template": {
            "method": "SUBSCRIBE",
            "params": ["{pair}@depth"],
            "id": 1,
        },
    },
    "okx": {
        "rest_url": "https://www.okx.com//api/v5/market/books",
        "ws_url": "wss://ws.okx.com:8443/ws/v5/public",
        "rate_limit": 0.2,  # 10次/2秒 → 每次请求间隔 ≥0.2秒
        "symbol_format": "XXX-YYYY",
        "param_map": {"instrument_id": "instId", "depth_size": "sz"},  # 最大400
        "snapshot_parser": lambda data: {
            "asks": data["data"][0]["asks"],
            "bids": data["data"][0]["bids"],
            "ts": data["data"][0]["ts"],
        },
        "subscription_template": {
            "op": "subscribe",
            "args": [{"channel": "books", "instId": "{pair}"}],  # 频道名称  # BTC-USDT
        },
    },
    "bybit": {
        "rest_url": "https://api.bybit.com/v5/market/orderbook",
        "ws_url": "wss://stream.bybit.com/v5/public/spot",
        "rate_limit": 0.1,  # 10次/秒
        "symbol_format": "XXXYYYY",
        "depth": 200,
        "param_map": {
            "instrument_id": "symbol",  # Bybit使用symbol参数
            "depth_size": "limit",  # 档位数参数
        },
        "snapshot_parser": lambda data: {  # 自定义解析逻辑
            "asks": data["result"]["a"],
            "bids": data["result"]["b"],
            "ts": data["result"]["ts"],
        },
        "subscription_template": {
            "op": "subscribe",
            "args": ["orderbook.{depth}.{pair}"],  # 订阅100档深度
        },
    },
    "bitget": {
        "rest_url": "https://api.bitget.com/api/spot/v2/market/depth",
        "ws_url": "wss://ws.bitget.com/v2/ws/public",
        "rate_limit": 0.1,
        "symbol_format": "XXXYYYY",
        "param_map": {"instrument_id": "symbol", "depth_size": "limit"},
        "snapshot_parser": lambda data: {
            "asks": [[entry[0], entry[1]] for entry in data["data"]["asks"]],
            "bids": [[entry[0], entry[1]] for entry in data["data"]["bids"]],
            "ts": data["data"]["ts"],
        },
        "subscription_template": {
            "op": "subscribe",
            "args": [{"instType": "SPOT", "channel": "books", "instId": "{pair}"}],
        },
    },
}


async def get_snapshot(exchange_name, pair, date):
    """
    Get snapshot from exchange.
    """

    config = EXCHANGE_CONFIG[exchange_name]

    try:
        if exchange_name == "bybit":
            params = {
                config["param_map"]["instrument_id"]: pair.upper(),
                config["param_map"]["depth_size"]: "100",
                "category": "spot",
            }
        elif exchange_name == "bitget":
            config["rest_url"] = (
                "https://api.bitget.com/api/v2/spot/market/orderbook?symbol=BTCUSDT&type=step0&limit=100"
            )
            params = {
                config["param_map"]["instrument_id"]: pair.upper(),
                config["param_map"]["depth_size"]: "100",
                "category": "spot",
            }
        else:
            params = {
                config["param_map"]["instrument_id"]: pair.upper(),
                config["param_map"]["depth_size"]: "100",
            }

        async with httpx.AsyncClient() as client:
            response = await client.get(config["rest_url"], params=params)

        response.raise_for_status()  # Raise error for non-200 responses
        data = response.json()

        snapshot = config["snapshot_parser"](data)
        snapshot["timestamp"] = time.time()

        os.makedirs(exchange_name, exist_ok=True)
        file_path = f"{exchange_name}/orderbook_{pair}-snapshot-{date}.jsonl"

        async with aiofiles.open(file_path, mode="a") as f:
            await f.write(json.dumps(snapshot) + "\n")

        print(f"[{exchange_name.upper()}] Snapshot saved to {file_path}")
        return True

    except httpx.HTTPStatusError as exc:
        error_json = exc.response.json()
        if error_json.get("code") == -1003:
            print(
                "Rate limit exceeded while fetching snapshot. Waiting before retrying..."
            )
            print(f"Error message: {error_json.get('msg')}")
            pass
        else:
            print(f"HTTP error occurred: {exc}")

    except Exception as e:
        print(f"An error occurred while getting snapshot: {e}")


async def listener(ws, exchange_name, pair, date, stop_event):
    """
    Global listener function that is used to listen to the exchange.
    Ping and Pong messages are handled here.
    """
    config = EXCHANGE_CONFIG[exchange_name]

    if exchange_name == "bybit":
        sub_msg = json.loads(
            json.dumps(config["subscription_template"])
            .replace("{pair}", pair)
            .replace("{depth}", str(config["depth"]))
        )
    else:
        sub_msg = json.loads(
            json.dumps(config["subscription_template"]).replace("{pair}", pair)
        )

    await ws.send(json.dumps(sub_msg))
    print(f"[{exchange_name.upper()}] Sent subscription: {sub_msg}")

    # wait for subscription ack
    ack = await ws.recv()
    print(f"[{exchange_name.upper()}] Subscription ack: {ack}")

    # general listener algorithm
    while not stop_event.is_set():
        try:
            data = await asyncio.wait_for(ws.recv(), timeout=10)
            message = json.loads(data)
            if exchange_name == "binance":
                if isinstance(message, dict) and message.get("e") == "ping":
                    # Respond with pong using the same payload
                    pong_msg = {"e": "pong", "id": message.get("id")}
                    await ws.send(json.dumps(pong_msg))
                    # Write ping response info to ping log file
                    ping_log = {
                        "exchange": exchange_name.upper(),
                        "timestamp": datetime.datetime.now().timestamp(),
                        "ping": message,
                        "pong": pong_msg,
                    }
                    async with aiofiles.open("ping_log.jsonl", mode="a") as f:
                        await f.write(json.dumps(ping_log) + "\n")
                    continue
                elif exchange_name == "binance":
                    if isinstance(message, dict) and message.get("e") == "ping":
                        # Respond with pong using the same payload
                        pong_msg = {"e": "pong", "id": message.get("id")}
                        await ws.send(json.dumps(pong_msg))
                        # Write ping response info to ping log file
                        ping_log = {
                            "exchange": exchange_name.upper(),
                            "timestamp": datetime.datetime.now().timestamp(),
                            "ping": message,
                            "pong": pong_msg,
                        }
                        async with aiofiles.open("ping_log.jsonl", mode="a") as f:
                            await f.write(json.dumps(ping_log) + "\n")
                        continue

            elif exchange_name == "bybit":
                if message.get("op") == "pong":
                    # Write pong message to ping log file
                    ping_log = {
                        "exchange": exchange_name.upper(),
                        "timestamp": datetime.datetime.now().timestamp(),
                        "pong": message,
                    }
                    async with aiofiles.open("ping_log.jsonl", mode="a") as f:
                        await f.write(json.dumps(ping_log) + "\n")
                else:
                    # Write other messages to the log file
                    async with aiofiles.open("ping_log.jsonl", mode="a") as f:
                        await f.write(
                            json.dumps(
                                {
                                    "exchange": exchange_name.upper(),
                                    "timestamp": datetime.datetime.now().timestamp(),
                                    "message": message,
                                }
                            )
                            + "\n"
                        )

            elif exchange_name == "bitget":
                if message == "pong":
                    # Write pong message to ping log file
                    ping_log = {
                        "exchange": exchange_name.upper(),
                        "timestamp": datetime.datetime.now().timestamp(),
                        "pong": message,
                    }
                    async with aiofiles.open("ping_log.jsonl", mode="a") as f:
                        await f.write(json.dumps(ping_log) + "\n")
                else:
                    # Write other messages to the log file
                    async with aiofiles.open("ping_log.jsonl", mode="a") as f:
                        await f.write(
                            json.dumps(
                                {
                                    "exchange": exchange_name.upper(),
                                    "timestamp": datetime.datetime.now().timestamp(),
                                    "message": message,
                                }
                            )
                            + "\n"
                        )

            record_time = datetime.datetime.now().timestamp()
            message["record_time"] = record_time
            message["EXCHANGE"] = exchange_name.upper()

            async with aiofiles.open(
                f"{exchange_name}/orderbook_{pair}-update-{date}.jsonl", mode="a"
            ) as f:
                await f.write(json.dumps(message) + "\n")

            log_message = f"[{exchange_name.upper()}] Update received @ {datetime.datetime.now()}\n"
            with open("logs.jsonl", "a") as log_file:
                log_file.write(log_message)

            # print(f"[{exchange_name.upper()}] Update received @ {datetime.datetime.now()}")

        except asyncio.TimeoutError:
            continue
        except json.JSONDecodeError:
            pass
        except Exception as e:
            print(f"Error receiving data: {e}")
            break


async def start_monitoring(exchange_name, pair):
    """Load in main monitor function"""
    config = EXCHANGE_CONFIG[exchange_name]
    if not config:
        raise ValueError(f"Exchange {exchange_name} not supported")

    os.makedirs(exchange_name, exist_ok=True)
    date = datetime.datetime.now().date().isoformat()

    symbol_format = config["symbol_format"]
    pair_formated = await symbol_formating(symbol_format, pair)

    # get inital snapshot
    await get_snapshot(exchange_name, pair_formated, date)

    # set up websocket connection
    ws_url = config["ws_url"].format(pair=pair_formated)
    stop_event = asyncio.Event()
    reconnect_counter = 0

    while True:
        try:
            async with connect(ws_url) as ws:
                if exchange_name in ["bitget", "bybit"]:
                    ping_task = asyncio.create_task(send_ping(ws, exchange_name))
                listener_task = asyncio.create_task(
                    listener(ws, exchange_name, pair_formated, date, stop_event)
                )

                connect_start_time = time.time()
                while True:
                    if time.time() - connect_start_time > RECONNECT_THRESHOLD:
                        new_date = datetime.datetime.now().date().isoformat()
                        if new_date != date:
                            date = new_date
                            await get_snapshot(exchange_name, pair_formated, date)

                        stop_event.set()
                        if exchange_name in ["bitget", "bybit"]:
                            ping_task.cancel()
                        await ws.close()
                        await listener_task
                        connect_start_time = time.time()
                        stop_event = asyncio.Event()
                        break
                    await asyncio.sleep(0.1)

        except Exception as e:
            reconnect_counter += 1
            wait_time = min(2**reconnect_counter, 60)
            print(
                f"[{exchange_name.upper()}] Connection error: {str(e)}, reconnecting in {wait_time}s..."
            )
            await asyncio.sleep(wait_time)


async def main():
    # monitor multiple exchanges
    tasks = [
        asyncio.create_task(start_monitoring("binance", "BTCUSDT")),
        asyncio.create_task(start_monitoring("okx", "BTCUSDT")),
        asyncio.create_task(start_monitoring("bybit", "BTCUSDT")),
        asyncio.create_task(start_monitoring("bitget", "BTCUSDT")),
    ]
    try:
        # Wait for all tasks for 1 hours (60*60 seconds)
        await asyncio.gather(*tasks)
    except asyncio.TimeoutError:
        print("Cancelling tasks due to timeout error...")
        # Cancel each task
        for task in tasks:
            task.cancel()
        # Optionally, wait for the tasks to finish cancellation
        await asyncio.gather(*tasks, return_exceptions=True)


if __name__ == "__main__":
    asyncio.run(main())
