from jetson_read_serial import *
from plan_laptop.jetson_receive_string import msg
import json

wingspan = float(msg)

# kirim sensor_value ke software 
# urutan sensor: "tinggi;berat;suhu;oksigen;heartrate;wingspan"
