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