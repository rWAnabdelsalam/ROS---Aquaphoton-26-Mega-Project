import asyncio
import json

import websockets


async def main():

    async with websockets.connect("ws://localhost:8765") as websocket:

        command = {
            "movement": "forward",
            "speed": "high",
            "mode": "manual"
        }

        await websocket.send(json.dumps(command))

        print("Command sent:", command)

        response = await websocket.recv()

        print("Response:", response)


asyncio.run(main())
