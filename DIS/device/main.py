import config
import utime as time

oled = config.OLED_1inch3()
from machine import SPI
from machine import UART
import math


DC = 8
RST = 12
MOSI = 11
SCK = 10
CS = 9

# Debug value
below = True

# ---------------------- Main Program -----------------------

# UART Setup
uart = config.uart

# Live values
voltage = 0.0
current = 0.0
rpm = 0
duty = 0
throttle = 0.0
buffer = ""
screen = 0
last_screen = screen
NUM_SCREENS = 6
distance = 0
timer_running = False
timer_elapsed_ms = 0
timer_start_ms = time.ticks_ms()
target_mph = 0.0
uart_blink = False

# Race targets
RACE_DISTANCE_MI = 1
RACE_TIME_MIN = 4
goal_distance_mi = RACE_DISTANCE_MI
goal_time_sec = RACE_TIME_MIN * 60

# Wheel parameters
wheel_diameter_in = 16
wheel_circumference_in = math.pi * wheel_diameter_in  # inches

print("Waiting for UART data...\n")

# ----------------- TIME VARIABLES -----------------
last_sample_time = time.ticks_ms()
elapsed_time = 0.0
sample_dt = 0.0
# ---------------------------------------------------

while True:
    # Time Calculation always runs
    current_time = time.ticks_ms()
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
                # print(line)       #DEBUG
                if not line:
                    continue

                try:
                    # Determine type of message based on identifying char

                    # If Status message, parse the message
                    if line[0] == "s":
                        # print([line[0]])
                        voltage = float(line[1:4])/10
                        current = float(line[4:10])/1000
                        rpm = int(line[10:13])
                        duty = int(line[13:16])
                        throttle = int(line[16:])
                        print(line, voltage, current, rpm, duty, throttle)
                        
                except Exception as e:
                    print("Parse error:", e, "on line:", line)

                uart_blink = not uart_blink
            

    # --------- Derived Values (runs even with stale data)
    power = voltage * current
    mph = rpm * wheel_circumference_in * 60 / 63360.0
    if timer_running:
        distance += mph * sample_dt / 3600  # distance in miles

    # --------- Button Handling via config -------------
    screen_delta, timer_toggle, timer_reset = oled.check_button()

    if timer_toggle:
        if timer_running:
            timer_elapsed_ms += time.ticks_diff(current_time, timer_start_ms)
            timer_running = False
            print("Timer stopped")
        else:
            timer_start_ms = current_time
            timer_running = True
            print("Timer started")

    if timer_reset:
        timer_elapsed_ms = 0
        distance = 0
        timer_running = False
        timer_start_ms = current_time
        oled.show_alert("TIMER", "RESET", 3)

    if screen_delta:
        screen += screen_delta

    # Wrap screen
    new_screen = screen % NUM_SCREENS
    if new_screen != last_screen:
        print("screen: ", new_screen)
        last_screen = new_screen
    screen = new_screen

    # --------- Timer Calculation ----------------------
    if timer_running:
        elapsed_time = (timer_elapsed_ms + time.ticks_diff(current_time, timer_start_ms)) / 1000
    else:
        elapsed_time = timer_elapsed_ms / 1000
    
    # --------- Target Speed Calculation ----------------------
    remaining_distance = max(goal_distance_mi - distance, 0)
    if timer_running:
        remaining_time_sec = max(goal_time_sec - elapsed_time, 0.001)
    else:
        remaining_time_sec = max(goal_time_sec - elapsed_time, 0.001)
    target_mph = (remaining_distance / (remaining_time_sec / 3600)) if remaining_time_sec > 0 else 0

    # --------- DISPLAY (always runs) ------------------
    if oled.update_alert():
        continue

    if screen == 0:
        invert_speed = target_mph > 0 and mph < target_mph
        oled.draw_large_num(mph, "MPH", invert=invert_speed)
    if screen == 1:
        oled.draw_time(elapsed_time, "ELAPSED")
    if screen == 2:
        oled.draw_large_num(current, "AMPS")
    if screen == 3:
        oled.draw_large_num(voltage, "VOLTS")
    if screen == 4:
        oled.draw_demo_distance(distance)
    if screen == 5:
        oled.draw_large_num(target_mph, "TARGET MPH")


    # # Fluctuations around the target speed for debug purposes
    # if below:
    #     if mph < target_mph + 5:
    #         rpm += 1
    #     else:
    #         below = False
    # if not below:
    #     if mph > target_mph - 5:
    #         rpm -= 1
    #     else:
    #         below = True




