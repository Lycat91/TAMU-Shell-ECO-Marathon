## Usage
# 1. Connect the TX (GP8) of the sender Pico to RX (GP5) of the receiver Pico.
# 2. Connect the RX (GP9) of the sender Pico to TX (GP4) of the receiver Pico.
# 3. Connect a common GND between both Picos.
# 4. Run `uart_counter_receiver.py` on the receiver Pico.
# 5. The terminal will print incoming counter values every 250 ms.



from machine import UART, Pin
import time

# UART Setup ----------------
# Using UART1: GP4 (TX) and GP5 (RX)
# Baud rate must match Lucas' code: 115200
uart = UART(1, baudrate=115200, tx=Pin(4), rx=Pin(5))

buffer = ""       # Temporary storage for incomplete messages
counter = 0       # Stores the latest counter value
print("Counter received:", counter)

#Main Loop ----------------
while True:
    # Check if any UART data has arrived iterate through the string, to figure out how to isulate the counter part and the actual number. =/
    if uart.any():
        # Read all available bytes from UART and decode to string
        data = uart.read()
        print(data)
        #buffer += data  # Add to buffer in case the message is split

        # Process complete lines ending with '\n'
        while "\n" in buffer:
            line, buffer = buffer.split("\n", 1)  # Split first full line
            line = line.strip()                    # Remove extra spaces or newline characters

            # Check if the line starts with "counter="
            if line.startswith("counter="):
                try:
                    # Extract the number after "=" and convert to integer
                    counter = int(line.split("=")[1])
                    print("Counter received:", counter)
                except ValueError:
                    # If conversion fails, print an error
                    print("Error: could not convert value to integer:", line)

    # Small delay to keep CPU responsive
    time.sleep(0.05)
