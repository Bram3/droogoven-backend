import dataclasses
import json
from dataclasses import dataclass, field

from hardware import ds18b20
from hardware.am2315 import am2315

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
    def to_dict(self):
        return dataclasses.asdict(self)

def get_sensor_data() -> SensorData:
    thSens = am2315()
    thDat = thSens.getTempHumid()
    data = SensorData()
    data.am2320_temp = thDat[0]
    data.am2320_humidity = thDat[1]
    data.ow_temps = ds18b20.read_all()
    data.average_temp = round((sum(data.ow_temps) + data.am2320_temp) / (len(data.ow_temps) + 1) * 1000) / 1000

    return data
