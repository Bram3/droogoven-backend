import asyncio
import websockets
import json
import logging

import hardware

logging.basicConfig(level=logging.INFO)

connected = set()

async def handle_connection(websocket, path):
    connected.add(websocket)
    logging.info(f"New connection added. Total connections: {len(connected)}")
    try:
        while True:
            data = hardware.get_sensor_data()
            if data:
                await websocket.send(data.to_json())
            else:
                logging.warning("Warning: Sensor data is empty")
            await asyncio.sleep(0.1)  # Control the frequency of updates
    except websockets.exceptions.ConnectionClosed as e:
        logging.error(f"Connection closed with error: {e}")
    except Exception as e:
        logging.error(f"Unhandled error: {e}")
    finally:
        if websocket in connected:
            connected.remove(websocket)
            logging.info(f"Connection removed. Total connections: {len(connected)}")

async def send_pings():
    while True:
        disconnected = set()
        # First, detect disconnected sockets
        for ws in connected.copy():
            try:
                await ws.ping()
            except Exception:
                disconnected.add(ws)

        # Then, remove the disconnected sockets
        connected.difference_update(disconnected)
        for ws in disconnected:
            logging.info(f"Disconnected detected and removed. Total connections: {len(connected)}")
        await asyncio.sleep(10)  # Ping interval


async def start_server():
    server = await websockets.serve(handle_connection, "0.0.0.0", 8765)

    try:
        await asyncio.gather(
            server.wait_closed(),
            send_pings()
        )
    finally:
        server.close()
        await server.wait_closed()
        logging.info("Server has been closed.")

if __name__ == "__main__":
    asyncio.run(start_server())
