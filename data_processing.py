#!/usr/bin/env python3
import os
import glob
import json
from datetime import datetime

def get_latest_line(file_path):
    """
    read the last line of the file
    """
    if not os.path.exists(file_path):
        return None
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
        lines = [line.strip() for line in lines if line.strip()]
        if not lines:
            return None
        return lines[-1]

def get_latest_update_file(exchange_dir):
    
    pattern = os.path.join(exchange_dir, "orderbook_*update-*.txt")
    files = glob.glob(pattern)
    if not files:
        return None

    def extract_date(filename):
        #  orderbook_{pair}-update-{date}.txt
        base = os.path.basename(filename)
        parts = base.split('-')
        if len(parts) < 2:
            return None
        date_part = parts[-1].replace(".txt", "")
        try:
            return datetime.fromisoformat(date_part)
        except Exception:
            return None

    files_with_dates = [(f, extract_date(f)) for f in files]
    files_with_dates = [(f, d) for f, d in files_with_dates if d is not None]
    if not files_with_dates:
        return None

    files_with_dates.sort(key=lambda x: x[1], reverse=True)
    return files_with_dates[0][0]

def get_latest_update_for_exchange(exchange, pair):
 
    exchange_dir = exchange  
    today = datetime.now().date().isoformat()
    # get the data of today
    file_name = f"orderbook_{pair}-update-{today}.txt"
    file_path = os.path.join(exchange_dir, file_name)
    if not os.path.exists(file_path):
        file_path = get_latest_update_file(exchange_dir)
    if not file_path:
        return None

    latest_line = get_latest_line(file_path)
    if latest_line:
        try:
            return json.loads(latest_line)
        except json.JSONDecodeError:
            print(f" failed to fetch data from {file_path} ")
            return None
    return None
"""
main part --dealing with the data format

"""
def get_best_bid_and_ask(exchange,pair):
    update = get_latest_update_for_exchange(exchange, pair)
    if not update:
        return None, None

    if exchange == "binance":
        bids = update.get("b", [])
        asks = update.get("a", [])
        if bids and asks:
            best_bid = bids[0][0]
            best_ask = asks[0][0]
            return best_bid, best_ask
        return None, None

    elif exchange == "okx":
        data_list = update.get("data", [])
        if data_list and isinstance(data_list, list):
            data_entry = data_list[0]  # 
            bids = data_entry.get("bids", [])
            asks = data_entry.get("asks", [])
            if bids and asks:
                best_bid = bids[0][0]  # 
                best_ask = asks[0][0]
                return best_bid, best_ask
        return None, None

    elif exchange == "bybit":
        data_entry = update.get("data", {})
        bids = data_entry.get("b", [])
        asks = data_entry.get("a", [])
        if bids and asks:
            best_bid = bids[0][0]  # 
            best_ask = asks[0][0]
            return best_bid, best_ask
        return None, None

    elif exchange == "bitget":
        data_list = update.get("data", [])
        if data_list and isinstance(data_list, list):
            data_entry = data_list[0]
            bids = data_entry.get("bids", [])
            asks = data_entry.get("asks", [])
            if bids and asks:
                best_bid = bids[0][0]  # 
                best_ask = asks[0][0]
                return best_bid, best_ask
        return None, None

    else:
        print(f"{exchange} data process is wrong")
        return None, None

def get_global_best_bid_and_ask(pair):
    exchanges = ["binance", "okx", "bybit", "bitget"]
    best_bid_dict = {}
    best_ask_dict = {}

    for exch in exchanges:
        bid, ask = get_best_bid_and_ask(exch, pair)
        if bid is not None and ask is not None:
            best_bid_dict[exch] = bid
            best_ask_dict[exch] = ask

    if best_bid_dict and best_ask_dict:
        global_best_bid = max(best_bid_dict.values())
        global_best_ask = min(best_ask_dict.values())
    else:
        global_best_bid, global_best_ask = None, None

    # retuern the global best bid and ask and the best bid and ask for each exchange
    return {
        "global_best_bid": global_best_bid,
        "global_best_ask": global_best_ask,
        "exchanges_bid": best_bid_dict,
        "exchanges_ask": best_ask_dict
    }

def perform_arbitrage(pair):
    # fetch all the data
    data = get_global_best_bid_and_ask(pair)
    best_bid = data["global_best_bid"]
    best_ask = data["global_best_ask"]

    if best_bid is None or best_ask is None:
        print("not enough data to perform arbitrage")
        return
    
    best_bid = float(best_bid)
    best_ask = float(best_ask)
    # calculate the spread
    spread = best_bid - best_ask

    # minima profit theshold 
    min_profit_threshold = 0.01  # 

    if spread > min_profit_threshold:
        print(f"aribitragy oppotunity exists, bst ask: {best_ask} , best bid: {best_bid},profit could be {spread}")
        
        #  data["exchanges_ask"]  data["exchanges_bid"]
        sell_exchange = max(data["exchanges_bid"], key=data["exchanges_bid"].get)
        buy_exchange = min(data["exchanges_ask"], key=data["exchanges_ask"].get)

        print(f"suggesting long {buy_exchange} , short {sell_exchange}  fot {pair}")
        
        

    else:
        print("no arbitrage opportunity")



    
def main():
    # 
    exchanges = {
        "binance": "btcusdt",  # Binance using lowercase for pair
        "okx": "BTC-USDT",
        "bybit": "BTCUSDT",
        "bitget": "BTCUSDT"
    }
    
    print("=== latest orderbook data ===")
    for exchange, pair in exchanges.items():
        update = get_latest_update_for_exchange(exchange, pair)
        if update is None :
            print(f"{exchange.upper()} cant fetch  {pair} update data")
    
    print("\n monitor the best bid and ask")
    arbitrage_pair = "BTCUSDT"  ## pairs to check for arbitrage
    perform_arbitrage(arbitrage_pair)

if __name__ == "__main__":
    main()