import machine, neopixel, utime

NUM_LEDS = 14
np = neopixel.NeoPixel(machine.Pin(16), NUM_LEDS)
CENTER_LEDS = [6, 7]
COL_WHITE = (10, 10, 10)
COL_GREEN = (0, 255, 0)
FINE_DEVIATION = 3
COARSE_DEVIATION = 12
CENTER_DEVIATION = 0.5
target_speed = 16.0
current_speed = 16.0
reverse = False

def dot_position(current_speed, target_speed):
    '''
    Calculates and returns the LED index number where the dot should be based on the current speed and target speed
    
    :param current_speed: Vehicle current speed in mph
    :param target_speed: Target speed in mph
    '''
    # Clear the strip
    np.fill((0, 0, 0))

    # Find the speed difference
    diff = current_speed - target_speed
    # Clamp difference
    clamped_diff = max(-3.0, min(3.0, diff))
        
    # Calculate the position of the LED that the dot should be at, convert it to an integer
    dot_position = int((clamped_diff + FINE_DEVIATION) / (FINE_DEVIATION * 2) * 13)

    # Calculate center indicator position
    if abs(diff) < 3.0:
        for i in CENTER_LEDS:
            np[i] = (COL_WHITE)
    else:
        excess = abs(diff) - FINE_DEVIATION
        coarse_ratio = min(1.0, excess / (COARSE_DEVIATION - FINE_DEVIATION))
        pixel_shift = coarse_ratio * 6
        if diff > 0:
            start_index = 6 - pixel_shift
        else:
            start_index = 6 + pixel_shift
        idx = int(round(start_index))
        idx = max(0, min(12, idx))
    # Write the center indicator
        np[idx] = COL_WHITE
        np[idx + 1] = COL_WHITE
    
    # If the vehicle speed is within the center deviation, turn on both center indicators
    if abs(diff) < CENTER_DEVIATION:
        np[6] = COL_GREEN
        np[7] = COL_GREEN
    else:
        # Write the dot and show the strip
        if diff > 0:
            np[dot_position] = (0, 0, 255)
        else:
            np[dot_position] = (255, 0, 0)

    np.write()


# Testing the indicator
while True:

    ################## Manual input mode
    # current_speed = float(input("Current speed: "))

    ################### Auto scrolling
    if reverse:
        current_speed -= 0.1
        if current_speed <= 13:
            reverse = False
    else:
        current_speed += 0.1
        if current_speed >= 19:
            reverse = True
    print("Current speed: ", current_speed)
    utime.sleep(0.05)

    dot_position(current_speed, target_speed)