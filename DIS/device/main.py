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

# Button debounce state
DEBOUNCE_MS = 150      # adjust to taste
RESET_HOLD_MS = 500    # how long both buttons must be held for reset

last_keyA = 1
last_keyB = 1
last_press_time_A = 0
last_press_time_B = 0
last_reset_time = 0


# ---------------------- Main Program -----------------------

# UART Setup
uart = UART(1, baudrate=115200, tx=Pin(4), rx=Pin(5))

# Live values
voltage = 0.0
current = 0.0
rpm = 5
duty = 0
throttle = 0.0
buffer = ""
mode = 0
last_mode = mode
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
    # Time Calculation always runs
    current_time = time.ticks_ms()
    elapsed_time = time.ticks_diff(current_time, start_time) / 1000
    sample_dt = time.ticks_diff(current_time, last_sample_time) / 1000
    last_sample_time = current_time

    # -------- UART Parsing ---------------
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
                except Exception as e:
                    print("Parse error:", e, "on line:", line)

    # --------- Derived Values (runs even with stale data)
    power = voltage * current
    mph = rpm * wheel_circumference_in * 60 / 63360.0
    distance += mph * sample_dt / 3600 * 100  # distance in miles

    # --------- Button Handling -------------------------
    t_now = time.ticks_ms()
    a_now = keyA.value()   # 1 = not pressed, 0 = pressed
    b_now = keyB.value()

    pressedA = False
    pressedB = False

    # Detect NEW press on A (1 -> 0) with debounce
    if last_keyA == 1 and a_now == 0:
        if time.ticks_diff(t_now, last_press_time_A) > DEBOUNCE_MS:
            pressedA = True
            last_press_time_A = t_now

    # Detect NEW press on B (1 -> 0) with debounce
    if last_keyB == 1 and b_now == 0:
        if time.ticks_diff(t_now, last_press_time_B) > DEBOUNCE_MS:
            pressedB = True
            last_press_time_B = t_now

    # Update last states
    last_keyA = a_now
    last_keyB = b_now

    # ---- Single-button actions (mode change) ----
    if pressedA and not b_now == 0:   # A pressed, B not currently held
        mode += 1
        print("Forward switch")

    if pressedB and not a_now == 0:   # B pressed, A not currently held
        mode -= 1
        print("Backward switch")

    # ---- Both buttons: reset time/distance ----
    if a_now == 0 and b_now == 0:
        # Only trigger reset if they've been held together long enough
        if time.ticks_diff(t_now, last_reset_time) > RESET_HOLD_MS:
            start_time = time.ticks_ms()
            last_sample_time = start_time
            elapsed_time = 0
            distance = 0
            last_reset_time = t_now
            print("Reset time & distance")

    else:
        # If not both held, keep reset timer current
        last_reset_time = t_now

    # Wrap mode
    if mode < 0:
        mode = 4
    if mode > 4:
        mode = 0

    if mode != last_mode:
        print("mode =", mode)
        last_mode = mode

    # --------- Time/Distance Reset --------------------
    if keyA.value() == 0 and keyB.value() == 0:
        start_time = time.ticks_ms()
        last_sample_time = start_time
        elapsed_time = 0
        distance = 0

    if mode < 0:
        mode = 4
    if mode > 4:
        mode = 0

    # --------- DISPLAY (always runs) ------------------
    if mode == 0:
        oled.draw_large_num(mph, "MPH")
    if mode == 1:
        oled.draw_time(elapsed_time, "ELAPSED")
    if mode == 2:
        oled.draw_large_num(current, "AMPS")
    if mode == 3:

        oled.draw_large_num(voltage, "VOLTS")
    if mode == 4:
        oled.draw_speed(distance, mode)


    # print(
    #     f"Time: {elapsed_time:.2f}s | delta t: {sample_dt:.2f}s | "
    #     f"Voltage: {voltage:.2f} V | Current: {current:.2f} A | RPM: {rpm} | Speed: {mph:.2f} Mph |"
    #     f"Duty: {duty:.0f} | Throttle: {throttle:.1f} %"
    # )

