#!/usr/bin/env python3
import os
import glob
import json
from datetime import datetime

def get_latest_line(file_path):
    """
    读取文件，返回最后一行非空数据
    """
    if not os.path.exists(file_path):
        return None
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
        # 过滤掉空行
        lines = [line.strip() for line in lines if line.strip()]
        if not lines:
            return None
        return lines[-1]

def get_latest_update_file(exchange_dir):
    """
    在指定目录中查找最新的 update 文件，文件名格式为：
    orderbook_{pair}-update-{date}.txt
    返回最新日期的文件路径
    """
    pattern = os.path.join(exchange_dir, "orderbook_*update-*.txt")
    files = glob.glob(pattern)
    if not files:
        return None

    def extract_date(filename):
        # 从文件名中提取日期部分，假设文件名格式为 orderbook_{pair}-update-{date}.txt
        base = os.path.basename(filename)
        parts = base.split('-')
        if len(parts) < 2:
            return None
        # 最后一个部分类似 "{date}.txt"
        date_part = parts[-1].replace(".txt", "")
        try:
            return datetime.fromisoformat(date_part)
        except Exception:
            return None

    files_with_dates = [(f, extract_date(f)) for f in files]
    files_with_dates = [(f, d) for f, d in files_with_dates if d is not None]
    if not files_with_dates:
        return None
    # 按日期降序排序，最新的在最前面
    files_with_dates.sort(key=lambda x: x[1], reverse=True)
    return files_with_dates[0][0]

def get_latest_update_for_exchange(exchange, pair):
    """
    根据交易所名称和交易对，查找对应的 update 文件并返回最新一行数据（解析成 dict）
    优先尝试使用当天的 update 文件，若不存在则查找最新日期的文件
    """
    exchange_dir = exchange  # 假设每个交易所的文件都在以交易所名称命名的目录下
    today = datetime.now().date().isoformat()
    # 拼接当天的文件名
    file_name = f"orderbook_{pair}-update-{today}.txt"
    file_path = os.path.join(exchange_dir, file_name)
    if not os.path.exists(file_path):
        # 当天文件不存在，则查找目录中最新的 update 文件
        file_path = get_latest_update_file(exchange_dir)
    if not file_path:
        return None

    latest_line = get_latest_line(file_path)
    if latest_line:
        try:
            return json.loads(latest_line)
        except json.JSONDecodeError:
            print(f"解析 {file_path} 中的 JSON 数据失败")
            return None
    return None

def get_best_bid_and_ask(exchange,pair):
    update = get_latest_update_for_exchange(exchange, pair)
    ## distinguish among different exchanges
    if exchange == "binance":
        if update:
            bids = update.get("b", [])
            asks = update.get("a", [])
            if bids and asks:
                best_bid = bids[0]
                best_ask = asks[0]
                return best_bid, best_ask
        return None, None
    if update:
        bids = update.get("bids", [])
        asks = update.get("asks", [])
        if bids and asks:
            best_bid = bids[0]
            best_ask = asks[0]
            return best_bid, best_ask
    return None, None

def combine_best_bid_and_ask(exchanges, pair):


    
def main():
    # 定义各交易所及其对应的交易对（与写入 update 文件时保持一致）
    exchanges = {
        "binance": "btcusdt",
        "okx": "BTC-USDT",
        "bybit": "BTCUSDT",
        "bitget": "BTCUSDT"
    }
    
    for exchange, pair in exchanges.items():
        update = get_latest_update_for_exchange(exchange, pair)
        if update:
            print(f"【{exchange.upper()}】最新 update 数据（交易对 {pair}）：")
            print(json.dumps(update, indent=4, ensure_ascii=False))
        else:
            print(f"【{exchange.upper()}】未找到 update 数据（交易对 {pair}）。")

if __name__ == "__main__":
    main()
