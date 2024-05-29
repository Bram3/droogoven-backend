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

i2c = board.I2C()
pcf = adafruit_pcf8574.PCF8574(i2c)


class Task(BaseModel):
    """
    A data class representing a task with duration and temperature settings.
    """
    days: int = Field(default=0, ge=0)
    hours: int = Field(default=0, ge=0)
    minutes: int = Field(default=0, ge=0)
    never_ending: bool = Field(default=False)
    temp_low: int = Field(default=0, ge=0)
    temp_high: int = Field(default=0, ge=0)
    cooler_on: int = Field(default=0, ge=0)
    cooler_off: int = Field(default=0, ge=0)
    start_date: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)

    def end_time(self):
        """
        Calculates the end time of the task based on the start time and duration.
        """
        duration = datetime.timedelta(days=self.days, hours=self.hours, minutes=self.minutes)
        return self.start_date + duration

    def to_dict(self):
        """
        Converts the task to a dictionary.
        """
        return json.loads(self.json())


class Logic:
    """
    Manages the logic for reading sensor data, managing tasks, and controlling hardware.
    """

    def __init__(self, sio: SocketIO, db_path="data2.db"):
        self.sio = sio
        self.current_task: Task = None
        self.cooler_cycle_status = False
        self.cooler_off_start_time = None
        self.cooler_on_start_time = None
        self.connection = sqlite3.connect(db_path, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
        self.connection.row_factory = sqlite3.Row
        self.initialize_db()

    def initialize_db(self):
        """
        Initializes the database by creating necessary tables if they do not already exist.
        """
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
        """
        Retrieves sensor data for a specified period and averages down if needed.

        Args:
            days (int): The number of days for which to retrieve data.

        Returns:
            List[dict]: A list of dictionaries representing the sensor data.
        """
        with self.connection as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) FROM SensorData
                WHERE timestamp >= datetime('now', ?)
            """, ('-' + str(days) + ' day',))
            count = cursor.fetchone()[0]
            step = max(1, count // 1000)
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
        """
        Starts a new task with the given settings.

        Args:
            task_data (dict): A dictionary with task settings.

        Raises:
            ValueError: If the task data is invalid.
        """
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
        """
        Stops the current task and turns off all hardware.
        """
        logging.info("Task stopped.")
        self.current_task = None
        self.cooler_cycle_status = False
        self.cooler_off_start_time = None
        self.cooler_on_start_time = None
        self.control_hardware(False, False, False)

    def get_current_task(self):
        """
        Retrieves the current task.

        Returns:
            dict: The current task as a dictionary, or None if no task is active.
        """
        if self.current_task:
            return self.current_task.to_dict()
        return None

    def control_hardware(self, heater, cooler, fan):
        """
        Controls the hardware state for the heater, cooler, and fan.

        Args:
            heater (bool): State of the heater.
            cooler (bool): State of the cooler.
            fan (bool): State of the fan.
        """
        self.set_hardware_state(1, heater)
        self.set_hardware_state(6, cooler)
        self.set_hardware_state(5, fan)

    def set_hardware_state(self, pin_number, state):
        """
        Sets the state of a hardware pin.

        Args:
            pin_number (int): The pin number of the hardware.
            state (bool): The desired state of the pin.
        """
        pin = pcf.get_pin(pin_number)
        pin.switch_to_output(value=True)
        pin.value = state

    async def emit_sensor_data(self, sensor_data):
        """
        Emits the sensor data via Socket.IO.

        Args:
            sensor_data (SensorData): The sensor data to emit.
        """
        await self.sio.emit('sensor_state', sensor_data.to_dict())

    def store_sensor_data(self, sensor_data):
        """
        Stores the sensor data in the database.

        Args:
            sensor_data (SensorData): The sensor data to store.
        """
        try:
            with self.connection as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO SensorData (timestamp, temperature, humidity, ow1, ow2, ow3, ow4, ow5) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        datetime.datetime.now(),
                        sensor_data.temperature,
                        sensor_data.humidity,
                        sensor_data.ow1,
                        sensor_data.ow2,
                        sensor_data.ow3,
                        sensor_data.ow4,
                        sensor_data.ow5,
                    )
                )
                conn.commit()
                logging.info("Sensor data stored successfully")
        except Exception as e:
            logging.error(f"Error storing sensor data: {e}")

    def is_task_expired(self):
        """
        Checks if the current task has expired.

        Returns:
            bool: True if the task has expired, otherwise False.
        """
        return not self.current_task.never_ending and datetime.datetime.utcnow() >= self.current_task.end_time()

    async def handle_expired_task(self):
        """
        Handles an expired task by stopping it and sending a notification.
        """
        logging.info("Task has expired")
        await self.sio.emit("task_done", {"message": "Task has finished."})
        self.stop()

    def manage_cooler_cycle(self, sensor_data):
        """
        Manages the cooler cycle based on the current sensor data and task settings.

        Args:
            sensor_data (SensorData): The current sensor data.
        """
        if not self.cooler_cycle_status:
            self.handle_cooling_off_state(sensor_data)
        else:
            self.handle_cooling_on_state()

    def handle_cooling_off_state(self, sensor_data):
        """
        Handles the logic when the cooler is off.

        Args:
            sensor_data (SensorData): The current sensor data.
        """
        heater = sensor_data.temperature < self.current_task.temp_low
        if sensor_data.temperature > self.current_task.temp_high:
            heater = False
        fan = True
        cooler = False

        if self.cooler_off_start_time and (self.cooler_off_start_time + datetime.timedelta(
                minutes=self.current_task.cooler_off)) < datetime.datetime.utcnow():
            self.cooler_cycle_status = True
            self.cooler_on_start_time = datetime.datetime.utcnow()

        self.control_hardware(heater, cooler, fan)

    def handle_cooling_on_state(self):
        """
        Handles the logic when the cooler is on.
        """
        heater = False
        fan = False
        cooler = True

        if self.cooler_on_start_time and (self.cooler_on_start_time + datetime.timedelta(
                minutes=self.current_task.cooler_on)) < datetime.datetime.utcnow():
            self.cooler_cycle_status = False
            self.cooler_off_start_time = datetime.datetime.utcnow()

        self.control_hardware(heater, cooler, fan)

    async def logic_loop(self):
        """
        The main logic loop that continuously fetches sensor data, processes it, and controls hardware.
        If the loop takes longer than the set timeout, the iteration is skipped.
        """
        while True:
            try:
                await asyncio.wait_for(self.logic_iteration(), timeout=15.0)
            except asyncio.TimeoutError:
                logging.error("Iteration timed out, skipping to the next iteration")
            await asyncio.sleep(1)

    async def logic_iteration(self):
        """
        Performs a single iteration of the main logic.
        Fetches sensor data, emits it, stores it, performs safety checks, and manages the current task.
        """
        logging.info("Starting logic iteration")
        sensor_data = hardware.get_sensor_data()
        logging.info(f"Fetched sensor data: {sensor_data}")

        # Safety checks for extreme values
        if sensor_data.temperature > 200 or sensor_data.humidity > 101:
            logging.error("Extreme sensor values detected, not emitting or storing data")
            return

        await self.emit_sensor_data(sensor_data)
        logging.info("Emitted sensor data")

        self.store_sensor_data(sensor_data)
        logging.info("Stored sensor data")

        # Safety checks
        if sensor_data.humidity > 90:
            logging.error("Humidity above 90, stopping task")
            self.stop()
            return

        if sensor_data.ow3 > 50:
            logging.error("OW3 temperature above 50, stopping task")
            self.stop()
            return

        if sensor_data.temperature > 100:
            logging.error("Temperature above 100, stopping task")
            self.stop()
            return

        if self.current_task:
            if self.is_task_expired():
                await self.handle_expired_task()
            else:
                self.manage_cooler_cycle(sensor_data)
