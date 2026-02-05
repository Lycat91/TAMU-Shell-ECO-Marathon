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
DEBUG_PERFORMANCE = True
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

    button_manager.update(vehicle, display, uart_manager)

    # --------- DISPLAY (always runs) ------------------
    if perf_monitor: perf_monitor.start()

    display.update(vehicle, uart_manager)

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
