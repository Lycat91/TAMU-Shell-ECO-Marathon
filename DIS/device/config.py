from machine import Pin, UART, SPI
import time
import math
import framebuf

### SPI Setup between DIS and OLED ###
DC = 8          # Data/Command
RST = 12        # Reset
MOSI = 11       # Master Out Slave In
SCK = 10        # Serial Clock
CS = 9          # Chip Select (low for communication)

### Pushbutton Setup ###
KEY0 = Pin(15, Pin.IN, Pin.PULL_UP)     # Active Low
KEY1 = Pin(17, Pin.IN, Pin.PULL_UP)     # Active Low

# UART Setup Transmitter
uart = UART(1, baudrate=115200, tx=Pin(4), rx=Pin(5))

### Orientation Flags ###
MIRROR_X = True
FLIP_Y = False

# OLED Class
class OLED_1inch3(framebuf.FrameBuffer):
    def __init__(self):
        self.width, self.height = 128, 64
        self.cs  = Pin(CS,  Pin.OUT, value=1)
        self.rst = Pin(RST, Pin.OUT, value=1)
        self.dc  = Pin(DC,  Pin.OUT, value=1)
        self.spi = SPI(1, baudrate=20_000_000, polarity=0, phase=0,
                       sck=Pin(SCK), mosi=Pin(MOSI), miso=None)

        self.buffer = bytearray(self.width * self.height // 8)
        super().__init__(self.buffer, self.width, self.height, framebuf.MONO_HMSB)
        self._init()

        # --- ADD: tiny font scratch + cache for fast big text ---
        self._tiny = bytearray(8)  # 8 rows, 1 byte each
        self._gfb  = framebuf.FrameBuffer(self._tiny, 8, 8, framebuf.MONO_HMSB)
        self._glyph_cache = {}     # maps char -> bytes(8)

    # (your _cmd/_data/_init/show stay the same)

    # --- ADD: helpers for scaled text ---------------------------------------
    def _glyph_rows(self, ch):
        """Return 8 bytes for the 8x8 bitmap of ch (MSB left)."""
        r = self._glyph_cache.get(ch)
        if r is not None:
            return r
        self._gfb.fill(0)
        self._gfb.text(ch, 0, 0, 1)
        r = bytes(self._tiny)              # copy out the 8 scanlines
        self._glyph_cache[ch] = r
        return r

    def measure_big_text(self, s, scale=3, spacing=1):
        """(width, height) in pixels for scaled string s."""
        if not s:
            return (0, 0)
        scale = max(1, int(scale))
        spacing = int(spacing)
        w = len(s) * (8 * scale) + (len(s) - 1) * spacing
        h = 8 * scale
        return (w, h)

    def draw_big_text(self, s, x, y, scale=3, spacing=1, color=1):
        """
        Draw scaled text using the built-in 8x8 font.
        - scale: integer >= 1
        - spacing: pixels between characters (unscaled)
        """
        scale = max(1, int(scale))
        spacing = int(spacing)
        cx = int(x)

        for ch in s:
            rows = self._glyph_rows(ch)
            # draw 8x8 glyph scaled by 'scale'
            for r in range(8):
                b = rows[r]
                yy = y + r * scale
                # quick vertical reject
                if yy >= self.height or yy + scale <= 0:
                    continue
                mask = 0x80
                for c in range(8):
                    if b & mask:
                        xx = cx + c * scale
                        # quick horizontal reject
                        if xx < self.width and xx + scale > 0:
                            self.fill_rect(xx, yy, scale, scale, color)
                    mask >>= 1
            cx += 8 * scale + spacing

    def show(self):
        # write 64 pages of 16 bytes each
        for page in range(64):
            column = (63 - page) if MIRROR_X else page
            self._cmd(0x00 + (column & 0x0F))
            self._cmd(0x10 + (column >> 4))
            start = page * 16
            self._data(memoryview(self.buffer)[start:start+16])
