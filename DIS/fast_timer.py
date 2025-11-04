from machine import Pin, SPI
import framebuf
import time

# ---------------------- OLED Pin Configuration ----------------------
DC   = 8
RST  = 12
MOSI = 11
SCK  = 10
CS   = 9

# ---------------------- Button Pins (active LOW) --------------------
KEY0 = Pin(15, Pin.IN, Pin.PULL_UP)
KEY1 = Pin(17, Pin.IN, Pin.PULL_UP)

# ---------------------- OLED Driver Class ---------------------------
class OLED_1inch3(framebuf.FrameBuffer):
    def __init__(self, rotate=180):
        self.width  = 128
        self.height = 64
        self.rotate = rotate  # 0 or 180

        self.cs  = Pin(CS,  Pin.OUT, value=1)
        self.rst = Pin(RST, Pin.OUT, value=1)
        self.dc  = Pin(DC,  Pin.OUT, value=1)

        # SPI1: SCK=GP10, MOSI=GP11
        self.spi = SPI(1, baudrate=20_000_000, polarity=0, phase=0, sck=Pin(SCK), mosi=Pin(MOSI), miso=None)

        # 1bpp buffer: 128*64/8 = 1024 bytes
        self.buffer = bytearray(self.width * self.height // 8)
        super().__init__(self.buffer, self.width, self.height, framebuf.MONO_HMSB)

        self.init_display()

    # --- low-level writes ---
    def write_cmd(self, b):
        self.cs(1); self.dc(0); self.cs(0)
        self.spi.write(bytes([b]))
        self.cs(1)

    def write_data(self, data_bytes):
        # data_bytes: bytes/bytearray/memoryview
        self.cs(1); self.dc(1); self.cs(0)
        self.spi.write(data_bytes)
        self.cs(1)

    # --- controller init (SH1107) ---
    def init_display(self):
        # Hard reset
        self.rst(1); time.sleep(0.005)
        self.rst(0); time.sleep(0.02)
        self.rst(1); time.sleep(0.02)

        # Display OFF
        self.write_cmd(0xAE)

        # Column address (start)
        self.write_cmd(0x00)   # lower column
        self.write_cmd(0x10)   # higher column

        # Page address base
        self.write_cmd(0xB0)

        # Display start line
        self.write_cmd(0xDC)
        self.write_cmd(0x00)

        # Contrast (requires data byte)
        self.write_cmd(0x81)
        self.write_cmd(0x6F)

        # Memory addressing mode (horizontal)
        self.write_cmd(0x21)

        # Segment remap (depends on rotate)
        self.write_cmd(0xA1 if self.rotate == 180 else 0xA0)

        # COM scan direction (leave at 0xC0; use 0xC8 to flip vertically)
        self.write_cmd(0xC0)

        # Entire display follow RAM
        self.write_cmd(0xA4)

        # Normal (A6) vs invert (A7)
        self.write_cmd(0xA6)

        # Multiplex ratio (1/64 duty)
        self.write_cmd(0xA8)
        self.write_cmd(0x3F)

        # Display offset
        self.write_cmd(0xD3)
        self.write_cmd(0x60)

        # Display clock divide/osc
        self.write_cmd(0xD5)
        self.write_cmd(0x41)

        # Pre-charge
        self.write_cmd(0xD9)
        self.write_cmd(0x22)

        # VCOMH
        self.write_cmd(0xDB)
        self.write_cmd(0x35)

        # Charge pump enable
        self.write_cmd(0xAD)
        self.write_cmd(0x8A)

        # Display ON
        self.write_cmd(0xAF)
        time.sleep(0.01)

    # --- push framebuffer to panel ---
    def show(self):
        # The SH1107 on many 1.3" modules maps columns in a 64-page-by-16-byte layout.
        # This matches a 1024-byte buffer written as 64 * 16 blocks.
        self.write_cmd(0xB0)  # base page (still set each loop below)
        for page in range(64):
            column = page if self.rotate == 180 else (63 - page)
            self.write_cmd(0x00 + (column & 0x0F))
            self.write_cmd(0x10 + (column >> 4))
            start = page * 16
            self.write_data(memoryview(self.buffer)[start:start+16])

# ---------------------- Timer App ----------------------
def main():
    oled = OLED_1inch3(rotate=180)

    running = False
    start_ms = 0
    elapsed_s = 0.0
    update_interval = 0.1  # seconds

    # helper: edge-detect any button press (active low) w/ debounce
    def button_pressed():
        if (KEY0.value() == 0) or (KEY1.value() == 0):
            time.sleep(0.02)  # debounce
            if (KEY0.value() == 0) or (KEY1.value() == 0):
                while (KEY0.value() == 0) or (KEY1.value() == 0):
                    time.sleep(0.01)  # wait release
                return True
        return False

    # splash
    oled.fill(0)
    oled.text("Timer Ready", 28, 24)
    oled.show()
    time.sleep(0.6)

    while True:
        # toggle run/pause on any button press
        if button_pressed():
            if not running:
                # start/resume
                start_ms = time.ticks_ms() - int(elapsed_s * 1000)
                running = True
            else:
                # pause
                elapsed_s = time.ticks_diff(time.ticks_ms(), start_ms) / 1000.0
                running = False

        if running:
            elapsed_s = time.ticks_diff(time.ticks_ms(), start_ms) / 1000.0

        # draw UI
        oled.fill(0)
        oled.text("Timer", 48, 6)
        oled.text("{:.2f}s".format(elapsed_s), 34, 26)
        oled.text("K0/K1: Start/Pause", 4, 50)
        oled.show() 

        time.sleep(update_interval)

# ---------------------- Run ----------------------
if __name__ == "__main__":
    main()
