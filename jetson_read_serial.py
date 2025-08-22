import serial
import time

ser = serial.Serial(port='/dev/ttyUSB0', baudrate=9600, timeout=1)

time.sleep(2)  # wait for serial connection to initialize

print("Reading from serial... Press Ctrl+C to stop.")

try:
    while True:
        if ser.in_waiting > 0:   # check if data is available
            line = ser.readline().decode('utf-8').strip()  # read line
            print(f"Received: {line}")
            sensor_value = float(line.split(";")) # parsed values sensor[]

except KeyboardInterrupt:
    print("\nStopped by user.")

finally:
    ser.close()
    print("Serial connection closed.")
