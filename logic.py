import asyncio
import datetime
import json
import logging
import board
import adafruit_pcf8574

from flask_socketio import SocketIO
from pydantic import BaseModel, Field

import hardware
import sqlite3

i2c = board.I2C()  # uses board.SCL and board.SDA
# i2c = board.STEMMA_I2C()  # For using the built-in STEMMA QT connector on a microcontroller
pcf = adafruit_pcf8574.PCF8574(i2c)


class Task(BaseModel):
    days: int = Field(default=0, ge=0)
    hours: int = Field(default=0, ge=0)
    minutes: int = Field(default=0, ge=0)
    never_ending: bool = Field(default=False)
    temp_low: int = Field(default=0, ge=0)
    temp_high: int = Field(default=0, ge=0)
    # fan_low: int = Field(default=0)
    # fan_high: int = Field(default=0)
    cooler_on: int = Field(default=0, ge=0)
    cooler_off: int = Field(default=0, ge=0)
    start_date: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)

    def end_time(self):
        duration = datetime.timedelta(days=self.days, hours=self.hours, minutes=self.minutes)
        return self.start_date + duration

    def to_dict(self):
        return json.loads(self.json())


class Logic:
    def __init__(self, sio: SocketIO, db_path="data2.db"):
        self.sio = sio
        self.current_task: Task = None
        self.cooler_cycle_status = False
        self.cooler_off_start_time = None
        self.cooler_on_start_time = None
        self.connection = sqlite3.connect(db_path, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
        self.connection.row_factory = sqlite3.Row  # This allows dictionary access to rows
        self.initialize_db()

    def initialize_db(self):
        """Initializes the database by creating necessary tables if they do not already exist."""
        with self.connection as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS SensorData (
                    timestamp DATETIME PRIMARY KEY,
                    temperature REAL,
                    humidity REAL,
                    ow1 REAL,
                    ow2 REAL,
                    ow3 REAL,
                    ow4 REAL,
                    ow5 REAL
                );
            """)
            conn.commit()

    def get_sensor_data_for_period(self, days):
        with self.connection as conn:
            cursor = conn.cursor()
            # First, count the total number of entries for the specified period.
            cursor.execute("""
                SELECT COUNT(*) FROM SensorData
                WHERE timestamp >= datetime('now', ?)
            """, ('-' + str(days) + ' day',))
            count = cursor.fetchone()[0]

            # Calculate the number of rows to skip to average down to about 1000 entries
            step = max(1, count // 1000)

            # Retrieve and average data if needed
            cursor.execute("""
                SELECT
                    MIN(timestamp) as timestamp,
                    AVG(temperature) as temperature,
                    AVG(humidity)  as humidity,
                    AVG(ow1) as ow1,
                    AVG(ow2) as ow2,
                    AVG(ow3) as ow3,
                    AVG(ow4) as ow4,
                    AVG(ow5) as ow5,
                    COUNT(*) as count
                FROM (
                    SELECT *,
                        ROW_NUMBER() OVER (ORDER BY timestamp) as rownum
                    FROM SensorData
                    WHERE timestamp >= datetime('now', ?)
                )
                WHERE rownum % ? = 0
                GROUP BY (rownum - 1) / ?
            """, ('-' + str(days) + ' day', step, step))
            return [dict(row) for row in cursor.fetchall()]

    def start(self, task_data):
        try:
            task = Task(**task_data)
            self.current_task = task
            self.cooler_cycle_status = False
            self.cooler_off_start_time = datetime.datetime.utcnow()
            logging.info(f"Task started with settings: {task}")
        except Exception as e:
            logging.error(f"Error starting task: {e}")
            raise ValueError(f"Invalid task data: {e}")

    def stop(self):
        logging.info("Task stopped.")
        self.current_task = None
        self.cooler_cycle_status = False
        self.cooler_off_start_time = None
        self.cooler_on_start_time = None
        self.control_hardware(False, False, False)

    def get_current_task(self):
        if self.current_task:
            return self.current_task.to_dict()  # Convert dataclass to dict
        return None

    def control_hardware(self, heater, cooler, fan):
        if heater is not None:
            heater_pin = pcf.get_pin(1)
            heater_pin.switch_to_output(value=True)
            heater_pin.value = heater
        if cooler is not None:
            cooler_pin = pcf.get_pin(6)
            cooler_pin.switch_to_output(value=True)
            cooler_pin.value = cooler
        if fan is not None:
            fan_pin = pcf.get_pin(5)
            fan_pin.switch_to_output(value=True)
            fan_pin.value = fan

    async def logic_loop(self):
        while True:
            sensor_data = hardware.get_sensor_data()
            await self.sio.emit('sensor_state', sensor_data.to_dict())
            with self.connection as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO SensorData (timestamp, temperature, humidity, ow1, ow2, ow3, ow4, ow5) VALUES (?, ?, ?, ?,?,?,?,?)",
                    (datetime.datetime.now(), sensor_data.temperature, sensor_data.humidity, sensor_data.ow1,
                     sensor_data.ow2, sensor_data.ow3, sensor_data.ow4, sensor_data.ow5))
                conn.commit()
            if self.current_task:
                if not self.current_task.never_ending and datetime.datetime.utcnow() >= self.current_task.end_time():
                    logging.info("Task has expired")
                    await self.sio.emit("task_done", {"message": "Task has finished."})
                    self.stop()
                else:

                    # Manage Cooler Cycle
                    if not self.cooler_cycle_status:
                        # Cooling Off State
                        heater = sensor_data.temperature < self.current_task.temp_low
                        if sensor_data.temperature > self.current_task.temp_high:
                            heater = False
                        fan = True
                        cooler = False

                        if self.cooler_off_start_time and (self.cooler_off_start_time + datetime.timedelta(
                                minutes=self.current_task.cooler_off)) < datetime.datetime.utcnow():
                            self.cooler_cycle_status = True
                            self.cooler_on_start_time = datetime.datetime.utcnow()

                    else:
                        # Cooling On State
                        heater = False
                        fan = False
                        cooler = True

                        if self.cooler_on_start_time and (self.cooler_on_start_time + datetime.timedelta(
                                minutes=self.current_task.cooler_on)) < datetime.datetime.utcnow():
                            self.cooler_cycle_status = False
                            self.cooler_off_start_time = datetime.datetime.utcnow()

                    # Control Hardware
                    self.control_hardware(heater, cooler, fan)

            await asyncio.sleep(1)
