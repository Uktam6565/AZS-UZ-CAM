import asyncio
import websockets


async def main():
    url = "ws://localhost:8000/api/v1/realtime/queue/station/1"

    async with websockets.connect(url) as ws:
        print("CONNECTED")

        while True:
            msg = await ws.recv()
            print(msg)


asyncio.run(main())