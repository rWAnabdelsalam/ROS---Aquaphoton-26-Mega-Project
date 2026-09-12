import asyncio
import json
import websockets


async def main():
    async with websockets.connect("ws://localhost:8765") as ws:
        for i in range(20):
            msg = json.loads(await ws.recv())
            if msg.get("type") == "telemetry":
                print("distance:", msg.get("distance"),
                      " voltage:", msg.get("voltage"))


asyncio.run(main())
