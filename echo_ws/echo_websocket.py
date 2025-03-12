import asyncio
import websockets
import logging
import os

logger = logging.getLogger(__name__)

async def echo(websocket):
    while True:
        try:
            message = await websocket.recv()
            length = len(message)
            logger.info(f"Received message: {length}")
            is_str = isinstance(message, str)
            echo_message = message if length < 100 else message[:100]
            await websocket.send(f"Server received texted={is_str} length={length} part of message: >")
            await websocket.send(echo_message)
        except websockets.ConnectionClosedOK:
            print("Connection closed normally")
            break
        

async def main():
    port = int(os.getenv("SOCKPORT", 8085))
    # 测试server,不限制max_size
    async with websockets.serve(echo, port=port, max_size=None):
        print("WebSocket server started")
        await asyncio.Future()  # Run forever

if __name__ == "__main__":
    logging.basicConfig(
    format="[%(asctime)s] %(levelname)s in %(lineno)d : %(module)s: %(message)s",
    level=logging.INFO,
)
    asyncio.run(main())