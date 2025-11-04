from machine import Pin, SPI
import framebuf
import time

# ---------------------- OLED Pin Configuration ----------------------
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
            0x81, 0x6F,          # ← added contrast data byte
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

running = False
start_time = 0
elapsed_time = 0
update_interval = 0.1

while True:
    # Check if either button is pressed (active LOW)
    if not KEY0.value() or not KEY1.value():
        # Toggle timer state
        if not running:
            # Start or resume timer
            start_time = time.ticks_ms() - int(elapsed_time * 1000)
            running = True
        else:
            # Pause timer
            elapsed_time = time.ticks_diff(time.ticks_ms(), start_time) / 1000
            running = False

        # Debounce delay
        time.sleep(0.25)

    # Update timer if running
    if running:
        elapsed_time = time.ticks_diff(time.ticks_ms(), start_time) / 1000

    # Display
    oled.fill(0)
    oled.text("Timer", 45, 10)
    oled.text("{:.2f}s".format(elapsed_time), 40, 30)
    oled.text("K0/K1: Start/Pause", 5, 50)
    oled.show()

    time.sleep(update_interval)
''
from machine import Pin
import time

k0 = Pin(15, Pin.IN, Pin.PULL_UP)
k1 = Pin(17, Pin.IN, Pin.PULL_UP)

while True:
    print("KEY0:", k0.value(), "KEY1:", k1.value())
    time.sleep(0.2)
''