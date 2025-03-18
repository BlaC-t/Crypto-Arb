import asyncio
from websockets import connect
import aiofiles
import sys
import json
import httpx
import time
import datetime
import os

async def symbol_formating(symbol_format: str, pair: str) -> str:
    pair_letters_only = ''.join([char for char in pair if char.isalpha()])

    if "USDT" in pair_letters_only.upper():
        first_part = pair_letters_only.upper().split("USDT")[0]
        second_part = "USDT"
    else:
        raise ValueError("The input string must contain 'USDT'.")
    
    if not (symbol_format.count("x") + symbol_format.count("X") == len(first_part) and
            symbol_format.count("y") + symbol_format.count("Y") == len(second_part)):
        raise ValueError("The format string does not match the expected structure.")

    mapped_string = ""
    format_index = 0

    for char in symbol_format:
        if char.lower() == "x":
            mapped_char = first_part[format_index]
            if char.isupper():
                mapped_string += mapped_char.upper()
            else:
                mapped_string += mapped_char.lower()
            format_index += 1

        elif char.lower() == "y":
            mapped_char = second_part[format_index - len(first_part)]
            if char.isupper():
                mapped_string += mapped_char.upper()
            else:
                mapped_string += mapped_char.lower()
            format_index += 1
        else:
            mapped_string += char
    return mapped_string

async def send_ping(ws, exchange_name):
    while True:
        try:
            if exchange_name == "bybit":
                # 生成包含时间戳的ping消息
                ping_msg = {"op": "ping", "ts": int(time.time() * 1000)}
                await ws.send(json.dumps(ping_msg))
                print(f"[{exchange_name.upper()}] Sent ping message: {ping_msg}")
            elif exchange_name == "bitget":
                await ws.send("ping")
                print(f"[{exchange_name.upper()}] Sent ping message: ping")
            else:
                print(f"[{exchange_name.upper()}] Ping mechanism not defined.")
                break
            await asyncio.sleep(20)  # 每15秒发送一次ping消息
        except Exception as e:
            print(f"[{exchange_name.upper()}] Error sending ping message: {e}")
            break

async def read_jsonl_async(file_path):
    data = []
    async with aiofiles.open(file_path, mode='r') as f:
        async for line in f:
            try:
                record = json.loads(line)
                data.append(record)
            except json.JSONDecodeError:
                print(f"Invalid JSON data in line: {line}")
    return data