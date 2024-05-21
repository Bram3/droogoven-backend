import os
import glob
import time

base_dir = '/sys/bus/w1/devices/'

def read_temp_raw(device_file):
    with open(device_file, 'r') as f:
        lines = f.readlines()
    return lines


def read_temp(device_file):
    lines = read_temp_raw(device_file)
    while lines[0].strip()[-3:] != 'YES':
        time.sleep(0.2)
        lines = read_temp_raw(device_file)
    equals_pos = lines[1].find('t=')
    if equals_pos != -1:
        temp_string = lines[1][equals_pos + 2:]
        temp_c = float(temp_string) / 1000.0
        return temp_c

def read_all():
    temps = []
    for folder in glob.glob(base_dir + '28*'):
        device_file = folder + '/w1_slave'
        temp_c = read_temp(device_file)
        temps.append(temp_c)
    return temps
