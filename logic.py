import asyncio
import datetime
import json
import logging

from flask_socketio import SocketIO
from pydantic import BaseModel, Field

import hardware


class Task(BaseModel):
    days: int = Field(default=0, ge=0)
    hours: int = Field(default=0, ge=0)
    minutes: int = Field(default=0, ge=0)
    never_ending: bool = Field(default=False)
    max_temperature: int = Field(default=0, ge=0)
    start_date: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)

    def end_time(self):
        duration = datetime.timedelta(days=self.days, hours=self.hours, minutes=self.minutes)
        return self.start_date + duration
    def to_dict(self):
        return json.loads(self.json())

class Logic:
    def __init__(self, sio: SocketIO):
        self.sio = sio
        self.current_task: Task = None

    def start(self, task_data):
        try:
            task = Task(**task_data)
            self.current_task = task
            logging.info(f"Task started with settings: {task}")
        except Exception as e:
            logging.error(f"Error starting task: {e}")
            raise ValueError(f"Invalid task data: {e}")

    def stop(self):
        logging.info("Task stopped.")
        self.current_task = None
    def get_current_task(self):
        if self.current_task:
            return self.current_task.to_dict()  # Convert dataclass to dict
        return None
    async def logic_loop(self):
        while True:
            sensor_data  = hardware.get_sensor_data()
            await self.sio.emit('sensor_state', sensor_data.to_dict()   )

            if self.current_task:
                if not self.current_task.never_ending and datetime.datetime.utcnow() >= self.current_task.end_time():
                    logging.info("Task has expired")
                    await self.sio.emit("task_done", {"message": "Task has finished."})
                    self.stop()
                else:
                    logging.info("loop")
            await asyncio.sleep(1)
