# task_manager.py
import asyncio
from datetime import datetime, timedelta

class Task:
    def __init__(self, temperature, duration, start_time):
        self.temperature = temperature
        self.duration = duration
        self.start_time = start_time

current_task = None

async def task_loop():
    global current_task
    start_time = datetime.now()
    while True:
        if current_task is None:
            break
        if datetime.now() >= start_time + timedelta(seconds=current_task.duration):
            stop_task()
            break
        print("loop")
        # Add sensor checking and relay control logic here
        await asyncio.sleep(1)  # Check conditions every second

def start_task(temperature, duration):
    global current_task
    current_task = Task(temperature, duration, datetime.now())

def stop_task():
    global current_task
    current_task = None

def update_task(temperature, duration):
    stop_task()  # Stop the current task
    start_task(temperature, duration)  # Start with new parameters
