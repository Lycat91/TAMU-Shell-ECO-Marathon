from machine import Pin, SPI
import framebuf, time

# ---------- pins ----------
DC, RST, MOSI, SCK, CS = 8, 12, 11, 10, 9

# ---------- orientation flags ----------
MIRROR_X = True   # << if text looks BACKWARDS, set True
FLIP_Y   = False  # << if text is UPSIDE-DOWN, set True

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

    def _cmd(self, b):
        self.cs(1); self.dc(0); self.cs(0); self.spi.write(bytes([b])); self.cs(1)

    def _data(self, mv):
        self.cs(1); self.dc(1); self.cs(0); self.spi.write(mv); self.cs(1)

    def _init(self):
        self.rst(1); time.sleep(0.005)
        self.rst(0); time.sleep(0.02)
        self.rst(1); time.sleep(0.02)

        for c in [0xAE, 0x00, 0x10, 0xB0, 0xDC, 0x00,
                  0x81, 0x6F, 0x21,
                  (0xA0 if MIRROR_X else 0xA1),    # segment remap
                  (0xC8 if FLIP_Y else 0xC0),      # COM scan dir
                  0xA4, 0xA6, 0xA8, 0x3F, 0xD3, 0x60, 0xD5, 0x41,
                  0xD9, 0x22, 0xDB, 0x35, 0xAD, 0x8A, 0xAF]:
            self._cmd(c)

    def show(self):
        # write 64 pages of 16 bytes each
        for page in range(64):
            column = (63 - page) if MIRROR_X else page
            self._cmd(0x00 + (column & 0x0F))
            self._cmd(0x10 + (column >> 4))
            start = page * 16
            self._data(memoryview(self.buffer)[start:start+16])

# ---- text scaling helpers (mono, no colors) ----
def _draw_char_scaled(fb, ch, x, y, s=3):
    tmp = bytearray(8); g = framebuf.FrameBuffer(tmp, 8, 8, framebuf.MONO_HMSB)
    g.fill(0); g.text(ch, 0, 0, 1)
    for r in range(8):
        b = tmp[r]
        for c in range(8):
            if (b >> (7-c)) & 1:
                fb.fill_rect(x + c*s, y + r*s, s, s, 1)

def text_scaled(fb, s, x, y, scale=3, spacing=1):
    cx = x
    for ch in s:
        _draw_char_scaled(fb, ch, cx, y, scale)
        cx += 8*scale + spacing

# --------------- demo: current speed only ---------------
oled = OLED_1inch3()

# Example current speed; replace with your sensor value
current_speed = 12.3  # mph

oled.fill(0)
text_scaled(oled, "{:.1f}".format(current_speed), 6, 8, scale=3)  # big
text_scaled(oled, "mph", 100, 42, scale=1)                        # small label
oled.show()
