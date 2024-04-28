import json
from dataclasses import dataclass, field

import board
import adafruit_am2320

from hardware import ds18b20

i2c = board.I2C()  # uses board.SCL and board.SDA
am = adafruit_am2320.AM2320(i2c)

@dataclass
class SensorData:
    am2320_temp: float = 0.0
    am2320_humidity: float = 0.0
    ow_temps: list = field(default_factory=list)
    average_temp: float = 0.0

    def to_json(self):
        return json.dumps(
            self,
            default=lambda o: o.__dict__,
            sort_keys=True,
            indent=4)

def get_sensor_data() -> SensorData:
    data = SensorData()

    for i in range(10):
        try:
            data.am2320_temp = am.temperature
            data.am2320_humidity = am.relative_humidity
            break
        except:
            print("sensor failed to read")

    data.ow_temps = ds18b20.read_all()
    data.average_temp = round((sum(data.ow_temps) + data.am2320_temp) / (len(data.ow_temps) + 1) * 1000) / 1000

    return data
