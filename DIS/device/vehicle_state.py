# This class contains all of the states of the vehicle for all of the "signals" that we care about.
# It includes measured signals (from the motor controller) as well as derived signals

import utime

class Vehicle:
    def __init__(self):

        # State of the vehicle
        self.state = "DRIVE"

        # Measured signals from the motor controller
        self.motor_ticks = 0
        self.smart_cruise = False
        self.motor_mph = 0.0
        self.voltage = 0.0
        self.current = 0.0
        self.throttle_position = 0.0
        self.throttle_request = 0.0
        self.duty_cycle = 0.0

        # Derived signals calculated onboard instantly (no time)
        self.distance_miles = 0.0
        self.power_instant = 0.0

        # Derived signals calculated with time
        self.energy_consumed = 0.0

        # Constants
        self.TICKS_PER_MILE = 181515

        def update_states(self):
            
            # Update distance
            self.distance_miles = self.motor_ticks / self.TICKS_PER_MILE

            # Update power instant
            self.power_instant = self.voltage * self.current

