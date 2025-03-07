import asyncio
import websockets
import json

async def test_okx_subscription():
    try:
        async with websockets.connect("wss://ws.okx.com:8443/ws/v5/public") as ws:
            # 发送订阅请求
            subscribe_msg = {
                "op": "subscribe",
                "args": [{
                    "channel": "books",
                    "instId": "BTC-USDT"
                }]
            }
            await ws.send(json.dumps(subscribe_msg))

            # 接收订阅确认
            response = await ws.recv()
            print("订阅响应:", json.loads(response))

            # 持续接收数据
            while True:
                data = await ws.recv()
                print("收到数据:", json.loads(data))

    except Exception as e:
        print(f"发生错误: {e}")

asyncio.run(test_okx_subscription())