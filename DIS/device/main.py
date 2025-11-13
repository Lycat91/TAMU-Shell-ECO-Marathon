import config
import utime as time
import comm

oled = config.OLED_1inch3()
from machine import Pin, SPI
from machine import UART, Pin
import math


DC = 8
RST = 12
MOSI = 11
SCK = 10
CS = 9
keyA = Pin(15, Pin.IN, Pin.PULL_UP)
keyB = Pin(17, Pin.IN, Pin.PULL_UP)

# ---------------------- Main Program -----------------------

# UART Setup
uart = UART(1, baudrate=115200, tx=Pin(4), rx=Pin(5))

# Live values
voltage = 0.0
current = 0.0
rpm = 0
duty = 0
throttle = 0.0
buffer = ""
mode = 0
distance = 0

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
                    distance += mph * sample_dt / 3600  # distance in miles

                    # print(
                    #     f"Time: {elapsed_time:.2f}s | delta t: {sample_dt:.2f}s | "
                    #     f"Voltage: {voltage:.2f} V | Current: {current:.2f} A | RPM: {rpm} | Speed: {mph:.2f} Mph |"
                    #     f"Duty: {duty:.0f} | Throttle: {throttle:.1f} %"
                    # )
                    # Display switching logic
                    if keyA.value() == 0:
                        mode += 1
                        print("Forward switch")
                    if keyB.value() == 0:
                        mode -= 1
                        print("Backward switch")

                    ##Time/Distance reset##
                    if keyA.value() == 0 and keyB.value() == 0:
                        start_time = time.ticks_ms()
                        last_sample_time = time.ticks_ms()
                        elapsed_time = 0
                        distance = 0

                    if mode < 0:
                        mode = 3

                    if mode > 3:
                        mode = 0

                    if mode == 0:
                        oled.draw_speed(mph, mode)

                    if mode == 1:
                        oled.draw_speed(elapsed_time, mode)

                    if mode == 2:
                        oled.draw_speed(voltage, mode)
                    
                    if mode == 3:
                        oled.draw_speed(voltage, distance)

                    print("mode =", mode)

                except Exception as e:
                    print("Parse error:", e, "on line:", line)
