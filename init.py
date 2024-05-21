import pcf8574_io
import time
import time
import board
import adafruit_pcf8574

p1 = pcf8574_io.PCF(0x20)

# 1 FAN
# 2 XTR1
# 3 XTR2
# 4 BEEPER
# 5 HEATER
# 6 COOLER
# 7 START?

for i in range(8):
    p1.pin_mode("p"+str(i), "OUTPUT")
    p1.write("p"+str(i), "LOW")


i2c = board.I2C()  # uses board.SCL and board.SDA
# i2c = board.STEMMA_I2C()  # For using the built-in STEMMA QT connector on a microcontroller
pcf = adafruit_pcf8574.PCF8574(i2c)


#for i in range(8):
#    if i != 1 and i != 5:
#        continue
#    fan = pcf.get_pin(i)
#    fan.switch_to_output(value=True)
#    fan.value = True

#time.sleep(1)
#{#p1.write("p5", "HIGH")
#time.sleep(1)
#p1.write("p5", "HIGH")
#p1.write("p4", "HIGH")
