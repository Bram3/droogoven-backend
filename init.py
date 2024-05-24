import time
import time
import board
import adafruit_pcf8574

# 1 FAN
# 2 XTR1
# 3 XTR2
# 4 BEEPER
# 5 HEATER
# 6 COOLER
# 7 START?


i2c = board.I2C()  # uses board.SCL and board.SDA
# i2c = board.STEMMA_I2C()  # For using the built-in STEMMA QT connector on a microcontroller
pcf = adafruit_pcf8574.PCF8574(i2c)

for i in range(8):
   pin = pcf.get_pin(i)
   pin.switch_to_output(value=True)
   pin.value = False

# for i in range(8):
#    if i != 1 and i != 5:
#        continue
#    pin = pcf.get_pin(i)
#    pin.switch_to_output(value=True)
#    pin.value = True

#time.sleep(1)
#{#p1.write("p5", "HIGH")
#time.sleep(1)è
#p1.write("p5", "HIGH")
#p1.write("p4", "HIGH")
