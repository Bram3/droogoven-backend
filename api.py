import json
import logging

import socketio
from aiohttp import web
import asyncio

from logic import Logic

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Create a Socket.IO server
sio = socketio.AsyncServer(async_mode='aiohttp', cors_allowed_origins='*')
app = web.Application()
sio.attach(app)
logic = Logic(sio)


@sio.event
async def connect(sid, environ):
    logging.info(f"Client connected {sid}")


@sio.event
async def disconnect(sid):
    logging.info(f"Client disconnected {sid}")

@sio.event
async def get_sensors_24h(sid, data):
    sensor_data = logic.get_sensor_data_for_period(1)  # last 24 hours
    await sio.emit('sensor_data_24h', sensor_data, to=sid)

@sio.event
async def get_sensors_7d(sid, data):
    sensor_data = logic.get_sensor_data_for_period(7)  # last 7 days
    await sio.emit('sensor_data_7d', sensor_data, to=sid)

@sio.event
async def start_task(sid, data):
    try:
        logic.start(data)
        await sio.emit('response', {'message': 'Task started successfully'}, to=sid)
        await get_task_status(sid, "")
    except ValueError as e:
        await sio.emit('response-error', {'message': str(e)}, to=sid)


@sio.event
async def stop_task(sid, data):
    logic.stop()
    await sio.emit('response', {'message': 'Task stopped successfully'}, to=sid)


@sio.event
async def get_task_status(sid, data):
    task = logic.get_current_task()
    await sio.emit('task_status', task, to=sid)


async def start_background_tasks(app):
    app['logic_task'] = asyncio.create_task(logic.logic_loop())


async def cleanup_background_tasks(app):
    app['logic_task'].cancel()
    await app['logic_task']


async def current_task_handler(request):
    task = logic.get_current_task()
    if task:
        return web.Response(text=json.dumps(task), content_type='application/json')
    else:
        return web.Response(text=json.dumps({'message': 'No active task'}), content_type='application/json', status=404)


app.on_startup.append(start_background_tasks)
app.on_cleanup.append(cleanup_background_tasks)

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    web.run_app(app, port=8080)
