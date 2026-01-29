import config
import utime as time
from display import DisplayManager
from performance import PerformanceMonitor
from uart_manager import UartManager
import math

# --- Hardware Setup ---
oled_driver = config.OLED_1inch3()
display = DisplayManager(oled_driver)

# --- Debug Flags ---
DEBUG_PERFORMANCE = False
DEBUG_VERBOSE = False
DEBUG_SIMULATE_SPEED = False
perf_monitor = (
    PerformanceMonitor(verbose=DEBUG_VERBOSE) if DEBUG_PERFORMANCE else None
)

# Debug value
below = True

# ---------------------- Main Program -----------------------

def simulate_speed_data(uart_manager, current_mph, target_mph, below_state):
    """
    Simulates RPM fluctuations around a target speed for testing without UART.
    Returns the new 'below' state.
    """
    if below_state:
        if current_mph < target_mph + 2:
            uart_manager.rpm += 1
        else:
            below_state = False
    else:  # not below
        if current_mph > target_mph - 2:
            uart_manager.rpm -= 1
        else:
            below_state = True
    return below_state

# --- Managers ---
uart_manager = UartManager(config.uart)

# Live values
screen = 0
last_screen = screen
NUM_SCREENS = 6
distance = 0
timer_running = False
timer_state = 'reset'
timer_elapsed_ms = 0
timer_start_ms = time.ticks_ms()
target_mph = 0.0
mph = 0.0
last_print_ticks = time.ticks_ms() #Demo for time and distance reamining 
timer_start_ticks = 0


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

    # -------- Input Handling ---------------
    uart_manager.update()

    # --------- Derived Values (runs even with stale data)
    power = uart_manager.voltage * uart_manager.current
    mph = uart_manager.rpm * wheel_circumference_in * 60 / 63360.0
    if timer_running:
        distance += mph * sample_dt / 3600  # distance in miles

    # -------- Simulate Speed if no UART data ---------------
    if DEBUG_SIMULATE_SPEED and not uart_manager.new_data:
        below = simulate_speed_data(uart_manager, mph, target_mph, below)

    # --------- Button Handling via config -------------
    screen_delta, timer_toggle, timer_reset, clear_alert_signal = oled_driver.check_button()

    if clear_alert_signal:
        display.clear_alert()

    if timer_toggle:
        if timer_running:
            timer_elapsed_ms += time.ticks_diff(current_time, timer_start_ms)
            timer_running = False
            timer_state = 'paused'
            print("Timer stopped")
        else:
            timer_start_ms = current_time
            timer_running = True
            timer_state = 'running'
            print("Timer started")

    if timer_reset:
        timer_elapsed_ms = 0
        distance = 0
        timer_running = False
        timer_state = 'reset'
        timer_start_ms = current_time
        display.show_alert("TIMER", "RESET", 3)

    if screen_delta:
        screen += screen_delta

    # Wrap screen
    new_screen = screen % NUM_SCREENS
    if new_screen != last_screen:
        print("screen: ", new_screen)
        last_screen = new_screen
        display.screen_changed()
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
    if display.update_alert():
        continue

    if perf_monitor: perf_monitor.start()

    if screen == 0:
        invert_speed = target_mph > 0 and mph < target_mph
        display.draw_large_num(mph, "MPH", uart_manager.uart_blink, timer_state, invert=invert_speed, eco=uart_manager.eco)
    elif screen == 1:
        display.draw_time(elapsed_time, "ELAPSED", uart_manager.uart_blink, timer_state)
    elif screen == 2:
        display.draw_large_num(uart_manager.current, "AMPS", uart_manager.uart_blink, timer_state)
    elif screen == 3:
        display.draw_large_num(uart_manager.voltage, "VOLTS", uart_manager.uart_blink, timer_state)
    elif screen == 4:
        display.draw_demo_distance(distance)
    elif screen == 5:
        display.draw_large_num(target_mph, "TARGET MPH", uart_manager.uart_blink, timer_state)

    if perf_monitor: perf_monitor.stop()

    # --------- DEBUG LOGGING ----------------------
    if perf_monitor:
        if timer_running:
            # Pass race data when the timer is active
            perf_monitor.update(
                remaining_time=remaining_time_sec, remaining_dist=remaining_distance
            )
        else:
            # Otherwise, just update for performance stats
            perf_monitor.update()
