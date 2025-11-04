## Usage
# 1. Connect the TX (GP4) of the sender Pico to RX (GP5) of the receiver Pico.
# 2. Connect the RX (GP5) of the sender Pico to TX (GP4) of the receiver Pico.
# 3. Connect a common GND between both Picos.
# 4. Run `uart_counter_receiver.py` on the receiver Pico.
# 5. The terminal will print incoming counter values every 250 ms.
from machine import Pin, SPI
from machine import UART, Pin
import time
import math  # for pi
import framebuf
DC = 8
RST = 12
MOSI = 11
SCK = 10
CS = 9

# ---------------------- Button Pins ----------------------
KEY0 = Pin(15, Pin.IN, Pin.PULL_UP)  # Active LOW
KEY1 = Pin(17, Pin.IN, Pin.PULL_UP)  # Active LOW

# ---------------------- OLED Driver Class ----------------------
class OLED_1inch3(framebuf.FrameBuffer):
    def __init__(self):
        self.width = 128
        self.height = 64
        self.rotate = 180

        self.cs = Pin(CS, Pin.OUT)
        self.rst = Pin(RST, Pin.OUT)
        self.dc = Pin(DC, Pin.OUT)
        self.cs(1)

        self.spi = SPI(1, baudrate=20000000, polarity=0, phase=0,
                       sck=Pin(SCK), mosi=Pin(MOSI))

        self.buffer = bytearray(self.width * self.height // 8)
        super().__init__(self.buffer, self.width, self.height, framebuf.MONO_HMSB)
        self.init_display()

    def write_cmd(self, cmd):
        self.cs(1)
        self.dc(0)
        self.cs(0)
        self.spi.write(bytearray([cmd]))
        self.cs(1)

    def write_data(self, buf):
        self.cs(1)
        self.dc(1)
        self.cs(0)
        self.spi.write(bytearray([buf]))
        self.cs(1)

    def init_display(self):
        self.rst(1)
        time.sleep(0.001)
        self.rst(0)
        time.sleep(0.01)
        self.rst(1)

        for cmd in [0xAE, 0x00, 0x10, 0xB0, 0xDC, 0x00,
            0x81, 0x6F,          # contrast data byte
            0xAF, 0x21, 0xA1, 0xC0, 0xA4, 0xA6, 0xA8, 0x3F,
            0xD3, 0x60, 0xD5, 0x41, 0xD9, 0x22, 0xDB, 0x35,
            0xAD, 0x8A, 0xAF]:
  
            self.write_cmd(cmd)

    def show(self):
        self.write_cmd(0xB0)
        for page in range(0, 64):
            column = page if self.rotate == 180 else (63 - page)
            self.write_cmd(0x00 + (column & 0x0F))
            self.write_cmd(0x10 + (column >> 4))
            for num in range(0, 16):
                self.write_data(self.buffer[page * 16 + num])

# ---------------------- Main Program ----------------------
oled = OLED_1inch3()
oled.fill(0)
oled.show()
# UART Setup
uart = UART(1, baudrate=115200, tx=Pin(4), rx=Pin(5))

voltage = 0.0
current = 0.0
rpm = 0
duty = 0               # ensure defined even if not received yet
throttle = 0.0         # ensure defined even if not received yet
buffer = ""

# Wheel parameters
wheel_diameter_in = 16
wheel_circumference_in = math.pi * wheel_diameter_in  # Circumference in inches

print("Waiting for UART data...\n")

# ----------------- TIME VARIABLES -----------------
start_time = time.ticks_ms()        # Program start timestamp
last_sample_time = start_time       # Last sample timestamp
elapsed_time = 0.0                  # accumulate only when running
sample_dt = 0.0
# ----------------- PAUSE STATE --------------------
is_paused = False                   # KEY1 toggles this
prev_k1 = KEY1.value()              # for edge detection
# ---------------------------------------------------

while True:
    # --------- Pause/Resume button (KEY1 active LOW) ----------
    k1 = KEY1.value()
    if prev_k1 == 1 and k1 == 0:  # falling edge
        is_paused = not is_paused
        print("[TIMER]", "Paused" if is_paused else "Resumed")
        time.sleep(0.15)  # simple debounce
    prev_k1 = k1
    # ----------------------------------------------------------

    if uart.any():
        data = uart.read()
        if not data:
            continue

        # Convert bytes to printable characters manually
        for b in data:
            if 32 <= b <= 126 or b == 10:  # printable ASCII + newline
                buffer += chr(b)

        # Process complete lines
        while '\n' in buffer:
            line, buffer = buffer.split('\n', 1)
            line = line.strip()
            if not line:
                continue

            # ----------------- TIME CALCULATION -----------------
            current_time = time.ticks_ms()
            sample_dt = time.ticks_diff(current_time, last_sample_time) / 1000  # seconds since last sample
            last_sample_time = current_time  # update for next line

            if not is_paused:
                elapsed_time += sample_dt     # accumulate only when not paused
                if elapsed_time < 0:
                    elapsed_time = 0.0
            # ------------------------------------------------------

            # Split line into parts: "V=..., I=..., RPM=..."
            try:
                parts = line.split(',')
                for p in parts:
                    p = p.strip()
                    if '=' in p:
                        key, value = p.split('=', 1)
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
                            throttle = int(float(value))/255 * 100

                # Calculate power
                power = voltage * current

                # Calculate speed in MPH
                mph = rpm * wheel_circumference_in * 60 / 63360  # inches/min to miles/hour

                # Print all values including MPH and time
                print(f"Time: {elapsed_time:.2f}s | delta t: {sample_dt:.2f}s | Voltage: {voltage:.2f} V | Current: {current:.2f} A | RPM: {rpm} | Power: {power:.2f} W | Speed: {mph:.2f} MPH | Duty: {duty:.2f} | Throttle: {throttle:.2f} %")

                # Stall detection
                if throttle != 0 and rpm < 30:
                    print("----------------------------------Stall occurred!------------------------------------")

            except Exception as e:
                print("Parse error:", e, "on line:", line)
# Display
    oled.fill(0)
    oled.text("V: {:.2f}V".format(voltage), 2, 2)
    oled.text("RPM: {:>4}".format(rpm), 2, 14)
    oled.text("MPH: {:.2f}".format(rpm * wheel_circumference_in * 60 / 63360.0), 2, 26)
    oled.text("t: {:>6.1f}s {}".format(elapsed_time, "PAU" if is_paused else "RUN"), 2, 38)
    oled.text("K1: Pause/Resume", 2, 50)
    oled.show()


#wheel diameter = 16 inches, A 
