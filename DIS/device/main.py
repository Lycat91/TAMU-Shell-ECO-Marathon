import config
import utime as time
import comm

oled = config.OLED_1inch3()
from machine import Pin, SPI
from machine import UART, Pin
import time
import math


DC = 8
RST = 12
MOSI = 11
SCK = 10
CS = 9

# ---------------------- Main Program -----------------------

# UART Setup
uart = UART(1, baudrate=115200, tx=Pin(4), rx=Pin(5))

# Live values
voltage = 0.0
current = 0.0
rpm = 0
duty = 0  # NEW: init so it's always defined
throttle = 0.0  # NEW: init so it's always defined
buffer = ""

# Wheel parameters
wheel_diameter_in = 16
wheel_circumference_in = math.pi * wheel_diameter_in  # inches

print("Waiting for UART data...\n")

# ----------------- TIME VARIABLES -----------------
start_time = time.ticks_ms()
last_sample_time = start_time
elapsed_time = 0.0  # NEW: init so OLED can show time before UART data
sample_dt = 0.0  # NEW
# ---------------------------------------------------

while True:
    if uart.any():
        data = uart.read()
        if data:
            # Convert bytes to printable characters
            for b in data:
                if 32 <= b <= 126 or b == 10:
                    buffer += chr(b)

            # Process complete lines
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                line = line.strip()
                if not line:
                    continue

                # -------- TIME CALCULATION --------
                current_time = time.ticks_ms()
                elapsed_time = time.ticks_diff(current_time, start_time) / 1000
                sample_dt = time.ticks_diff(current_time, last_sample_time) / 1000
                last_sample_time = current_time
                # ----------------------------------

                try:
                    parts = line.split(",")
                    for p in parts:
                        p = p.strip()
                        if "=" in p:
                            key, value = p.split("=", 1)
                            key = key.strip()
                            value = value.strip()
                            if key == "V":
                                voltage = float(value)
                            elif key == "I":
                                current = float(value)
                            elif key == "RPM":
                                rpm = int(float(value))
                            elif key == "DUTY":
                                duty = int(float(value))
                            elif key == "THROTTLE":
                                throttle = float(value) / 255 * 100

                    power = voltage * current
                    mph = rpm * wheel_circumference_in * 60 / 63360.0

                    # print(
                    #     f"Time: {elapsed_time:.2f}s | delta t: {sample_dt:.2f}s | "
                    #     f"Voltage: {voltage:.2f} V | Current: {current:.2f} A | RPM: {rpm} | Speed: {mph:.2f} Mph |"
                    #     f"Duty: {duty:.0f} | Throttle: {throttle:.1f} %"
                    # )
                    oled.draw_speed(throttle)

                    if throttle != 0 and rpm < 30:
                        print(
                            "----------------------------------Stall occurred!------------------------------------"
                        )

                except Exception as e:
                    print("Parse error:", e, "on line:", line)
