import board
import adafruit_pcf8574

# 1 HEATER
# 2 XTR1
# 3 XTR2
# 4 BEEPER
# 5 FAN
# 6 COOLER
# 7 START?


i2c = board.I2C()  # uses board.SCL and board.SDA
pcf = adafruit_pcf8574.PCF8574(i2c)

for i in range(8):
    pin = pcf.get_pin(i)
    pin.switch_to_output(value=True)
    pin.value = False