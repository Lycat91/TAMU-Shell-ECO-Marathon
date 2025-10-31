## Usage
# 1. Connect the TX (GP4) of the sender Pico to RX (GP5) of the receiver Pico.
# 2. Connect the RX (GP5) of the sender Pico to TX (GP4) of the receiver Pico.
# 3. Connect a common GND between both Picos.
# 4. Run `uart_counter_receiver.py` on the receiver Pico.
# 5. The terminal will print incoming counter values every 250 ms.

from machine import UART, Pin
import time
import math  # for pi

# UART Setup
uart = UART(1, baudrate=115200, tx=Pin(4), rx=Pin(5))

voltage = 0.0
current = 0.0
rpm = 0
buffer = ""

# Wheel parameters
wheel_diameter_in = 16
wheel_circumference_in = math.pi * wheel_diameter_in  # Circumference in inches

print("Waiting for UART data...\n")

# ----------------- TIME VARIABLES -----------------
start_time = time.ticks_ms()        # Program start timestamp
last_sample_time = start_time       # Last sample timestamp
# ---------------------------------------------------

while True:
    if uart.any():
        data = uart.read()
        if not data:
            continue

        # Convert bytes to printable characters manually
        for b in data:
            if 32 <= b <= 126 or b == 10:  # printable ASCII + newline
                buffer += chr(b)

        # Process complete lines
        while '\n' in buffer:
            line, buffer = buffer.split('\n', 1)
            line = line.strip()
            if not line:
                continue

            # ----------------- TIME CALCULATION -----------------
            current_time = time.ticks_ms()
            elapsed_time = time.ticks_diff(current_time, start_time) / 1000  # total seconds since start
            sample_dt = time.ticks_diff(current_time, last_sample_time) / 1000  # seconds since last sample
            last_sample_time = current_time  # update for next line
            # ------------------------------------------------------

            # Split line into parts: "V=..., I=..., RPM=..."
            try:
                parts = line.split(',')
                for p in parts:
                    p = p.strip()
                    if '=' in p:
                        key, value = p.split('=', 1)
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
                            throttle = int(float(value))/255 * 100

                # Calculate power
                power = voltage * current

                # Calculate speed in MPH
                mph = rpm * wheel_circumference_in * 60 / 63360  # inches/min to miles/hour

                # Print all values including MPH and time
                print(f"Time: {elapsed_time:.2f}s | delta t: {sample_dt:.2f}s | Voltage: {voltage:.2f} V | Current: {current:.2f} A | RPM: {rpm} | Power: {power:.2f} W | Speed: {mph:.2f} MPH | Duty: {duty:.2f} | Throttle: {throttle:.2f} %")

                # Stall detection
                if throttle != 0 and rpm < 30:
                    print("----------------------------------Stall occurred!------------------------------------")

            except Exception as e:
                print("Parse error:", e, "on line:", line)


#wheel diameter = 16 inches, A
