import hardware
import utime as time
from display import DisplayManager, OLEDDriver, ButtonManager
from performance import PerformanceMonitor
from uart_manager import UartManager
from vehicle_state import Vehicle

# --- Hardware Setup ---
oled_driver = OLEDDriver()
display = DisplayManager(oled_driver)
button_manager = ButtonManager()

# --- Debug Flags ---
DEBUG_PERFORMANCE = False
DEBUG_VERBOSE = False
perf_monitor = (
    PerformanceMonitor(verbose=DEBUG_VERBOSE) if DEBUG_PERFORMANCE else None
)

# ---------------------- Main Program -----------------------

# --- Managers ---
uart_manager = UartManager(hardware.uart)
vehicle = Vehicle()


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
    uart_manager.update(vehicle)

    # --------- Derived Values (runs even with stale data)
    vehicle.update_states(sample_dt, current_time)

    k0_click, k1_click, k1_hold, k1_hold_release = button_manager.check_events()

    if k1_hold_release:
        display.clear_alert()

    if k1_click:
        if vehicle.timer_running:
            vehicle._stored_elapsed_ticks += time.ticks_diff(current_time, vehicle._timer_start_ticks)
            vehicle.timer_running = False
            vehicle.timer_state = 'paused'
            print("Timer stopped")
        else:
            vehicle._timer_start_ticks = current_time
            vehicle.timer_running = True
            vehicle.timer_state = 'running'
            print("Timer started")

    if k1_hold:
        vehicle._stored_elapsed_ticks = 0
        vehicle.distance_miles = 0
        vehicle.timer_running = False
        vehicle.timer_state = 'reset'
        vehicle._timer_start_ticks = current_time
        display.show_alert("TIMER", "RESET", 3)

    if k0_click:
        display.change_screen(1)

    # --------- DISPLAY (always runs) ------------------
    if display.update_alert():
        continue

    if perf_monitor: perf_monitor.start()

    display.draw_screen(vehicle, uart_manager)

    if perf_monitor: perf_monitor.stop()

    # --------- DEBUG LOGGING ----------------------
    if perf_monitor:
        if vehicle.timer_running:
            # Pass race data when the timer is active
            perf_monitor.update(
                remaining_time=vehicle.remaining_time_seconds, remaining_dist=vehicle.remaining_distance_miles
            )
        else:
            # Otherwise, just update for performance stats
            perf_monitor.update()
