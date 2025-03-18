import asyncio
import aiofiles
import json
from tools import read_jsonl_async
from pathlib import Path
import re
import datetime  # Add this import at top of file


async def process_data(data):
    # 获取当前时间戳
    current_time = time.time()
    # 计算数据时间戳与当前时间的差值
    time_diff = abs(data['E']/1000 - current_time)
    # 如果是最新的数据则处理
    if time_diff < 60:  # 60秒内的数据
        # 在这里编写处理数据的逻辑
        # 可以对数据进行筛选、转换、计算等操作
        # 最后返回处理后的数据
        pass
    return

def gather_update_files(base_path="."):
    """Scan directory structure and group files by date/pair (today only)"""
    from pathlib import Path
    import re
    
    file_groups = []
    today_date = datetime.date.today().isoformat()  # Get current date in YYYY-MM-DD format
    print(today_date)
    
    for exchange_dir in Path(base_path).iterdir():
        if not exchange_dir.is_dir():
            continue
            
        for file_path in exchange_dir.glob("orderbook_*-update-*.jsonl"):
            # Use more precise regex pattern for date matching
            match = re.match(r"orderbook_(.+)-update-(\d{4}-\d{2}-\d{2})\.jsonl", file_path.name)
            if match:
                pair, date = match.groups()
                if date != today_date:  # Add date filter check
                    continue
                file_groups.append(str(file_path))

    return file_groups

async def main():
    paths = gather_update_files()
    print(paths)
    
    task = []
    for i in range(len(paths)):
        each_path = paths[i]
        async with aiofiles.open(each_path, 'r') as f:
            async for line in f:
                data = json.loads(line)
                task.append(asyncio.create_task(process_data(data)))
    
    results = await asyncio.gather(*task)
    print(f"Processed {len(results)} entries")

if __name__ == "__main__":
    asyncio.run(main())
