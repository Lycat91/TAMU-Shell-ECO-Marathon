## Usage
#1. Connect the TX of the sender Pico to RX of the receiver Pico.
#2. Connect a common GND between both Picos.
#3. Run `uart_counter_receiver.py` on the receiver Pico.
#4. The terminal will print incoming counter values every 250 ms.


from machine import UART, Pin
import time

#UART Setup ----------------
# UART0 uses pins GP0 (TX) and GP1 (RX) on the Pico
# Baud rate must match Lucas' code: 115200
uart = UART(0, baudrate=115200, tx=Pin(0), rx=Pin(1))

buffer = ""       # Temporary storage for incomplete messages
counter = 0       # Stores the latest counter value

#Main Loop ----------------
while True:
    # Check if any UART data has arrived
    if uart.any():
        # Read all available bytes from UART and decode to string
        data = uart.read().decode(errors="ignore")
        buffer += data  # Add to buffer in case the message is split

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
