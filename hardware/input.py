import dataclasses
import json
from dataclasses import dataclass, field

from hardware import ds18b20
from hardware.am2315 import am2315

@dataclass
class SensorData:
    temperature: float = 0.0
    humidity: float = 0.0
    ow1: float = 0.0
    ow2: float = 0.0
    ow3: float = 0.0
    ow4: float = 0.0
    ow5: float = 0.0
    average_temp: float = 0.0

    def to_json(self):
        return json.dumps(
            self,
            default=lambda o: o.__dict__,
            sort_keys=True,
            indent=4)
    def to_dict(self):
        return dataclasses.asdict(self)

def get_sensor_data() -> SensorData:
    thSens = am2315()
    thDat = thSens.getTempHumid()
    data = SensorData()
    data.temperature = thDat[0]
    data.humidity = thDat[1]
    ow_temps = ds18b20.read_all()
    data.ow1 = ow_temps[0]
    data.ow2 = ow_temps[1]
    data.ow3 = ow_temps[2]
    data.ow4 = ow_temps[3]
    data.ow5 = ow_temps[4]
    data.average_temp = round((sum(ow_temps) + data.temperature) / (len(ow_temps) + 1) * 1000) / 1000

    return data
