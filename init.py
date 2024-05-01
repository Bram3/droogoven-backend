import pcf8574_io
import time
p1 = pcf8574_io.PCF(0x20)

for i in range(8):
    p1.pin_mode("p"+str(i), "OUTPUT")
    p1.write("p"+str(i), "LOW")
