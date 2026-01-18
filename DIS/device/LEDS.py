import machine, neopixel, utime

NUM_LEDS = 14
np = neopixel.NeoPixel(machine.Pin(16), NUM_LEDS)
CENTER = [6, 7]
DEVIATION = 3
target_speed = 16.0
current_speed = 16.0
reverse = False

def get_index(current_speed, target_speed):
    diff = current_speed - target_speed
    # Clamp difference
    offset_magnitude = max(-DEVIATION, min(DEVIATION, diff)) / DEVIATION
    index = round(7 + int(offset_magnitude * 6))
    return index
    print(index)


def set_dot(start_index):
    # Draw in the center indicator
    np.fill((0, 0, 0))
    for i in CENTER:
        np[i] = (1, 1, 1)

    # Draw the current speed dot
    np[start_index] = (0, 255, 0)
    np.write()


# Testing the indicator
while True:

    ################## Manual input mode
    current_speed = float(input("Current speed: "))

    #################### Auto scrolling
    # if reverse:
    #     current_speed -= 0.1
    #     if current_speed <= 8:
    #         reverse = False
    # else:
    #     current_speed += 0.1
    #     if current_speed >= 24:
    #         reverse = True
    # print("Current speed: ", current_speed)
    # utime.sleep(0.1)

    set_dot(get_index(current_speed, target_speed))