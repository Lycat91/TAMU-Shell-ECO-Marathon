from machine import Pin, SPI, UART
import framebuf, time

# ------- Pins -------
DC, RST, MOSI, SCK, CS = 8, 12, 11, 10, 9

# Pushbuttons (unchanged)
KEY0 = Pin(15, Pin.IN, Pin.PULL_UP)
KEY1 = Pin(17, Pin.IN, Pin.PULL_UP)

# UART (unchanged)
uart = UART(1, baudrate=115200, tx=Pin(4), rx=Pin(5))

# OLED Display Setup
class OLED_1inch3(framebuf.FrameBuffer):
    def __init__(self):
        self.width = 128
        self.height = 64
        self.rotate = 180
        self._glyph_cache = {}      
        self._tiny = bytearray(8)
        self._gfb = framebuf.FrameBuffer(self._tiny, 8, 8, framebuf.MONO_HMSB)

        self.cs = Pin(CS, Pin.OUT)
        self.rst = Pin(RST, Pin.OUT)
        self.dc = Pin(DC, Pin.OUT)
        self.cs(1)

        self.spi = SPI(1, baudrate=40000000, polarity=0, phase=0,
                       sck=Pin(SCK), mosi=Pin(MOSI))

        self.buffer = bytearray(self.width * self.height // 8)
        super().__init__(self.buffer, self.width, self.height, framebuf.MONO_HMSB)
        self.init_display()

    def write_cmd(self, cmd):
        self.cs(1); self.dc(0); self.cs(0)
        self.spi.write(bytearray([cmd]))
        self.cs(1)

    def write_data(self, buf):
        self.cs(1); self.dc(1); self.cs(0)
        if isinstance(buf, int):
            self.spi.write(bytes([buf]))
        else:
            self.spi.write(buf)  # send the whole buffer/slice as-is
        self.cs(1)


    def init_display(self):
        self.rst(1); time.sleep(0.001)
        self.rst(0); time.sleep(0.01)
        self.rst(1)
        for cmd in [
            0xAE, 0x00, 0x10, 0xB0, 0xDC, 0x00,
            0x81, 0x6F,
            0xAF, 0x21, 0xA1, 0xC0, 0xA4, 0xA6, 0xA8, 0x3F,
            0xD3, 0x60, 0xD5, 0x41, 0xD9, 0x22, 0xDB, 0x35,
            0xAD, 0x8A, 0xAF
        ]:
            self.write_cmd(cmd)

    def show(self):
        self.write_cmd(0xB0)
        for page in range(0, 64):
            column = page if self.rotate == 180 else (63 - page)
            self.write_cmd(0x00 + (column & 0x0F))
            self.write_cmd(0x10 + (column >> 4))
            for num in range(0, 16):
                self.write_data(self.buffer[page * 16 + num])

        # --- cache for small glyphs (digits only) ---
    def _digit_rows(self, ch):
        """Return 8x8 bitmap rows for digits 0-9 (cached)."""
        r = self._glyph_cache.get(ch)
        if r is not None:
            return r
        self._gfb.fill(0)
        self._gfb.text(ch, 0, 0, 1)
        r = bytes(self._tiny)
        self._glyph_cache[ch] = r
        return r

    def _draw_scaled_char(self, ch, x, y, scale=4, color=1):
        """Draw one scaled character (digit) at x,y."""
        rows = self._digit_rows(ch)
        for r in range(8):
            b = rows[r]
            yy = y + r * scale
            if yy >= self.height or yy + scale <= 0:
                continue
            m = 0x80
            for c in range(8):
                if b & m:
                    xx = x + (7-c) * scale
                    if xx < self.width and xx + scale > 0:
                        self.fill_rect(xx, yy, scale, scale, color)
                m >>= 1

    def draw_speed(self, value, mode):
        """
        Draw a numeric speed like 16.2 inside fixed boxes:
        [0-39], [41-80], decimal point, [87-127]
        """
        # clear display first
        self.fill(0)

        # draw decimal dot
        self.fill_rect(86, 42, 5, 5, 1)

        # label
        if mode == 0:
            self.text("mph", 100, 54, 1)
        if mode == 1:
            self.text("sec", 100, 54, 1)
        if mode == 2:
            self.text(" V ", 100, 54, 1)
        if mode == 2:
            self.text("Miles", 100, 54, 1)


        # format and clamp number
        s = "{:.1f}".format(value)
        if len(s) == 4 and s[1] == "0" and s[0] == "0":
            s = s[1:]  # strip leading zero if needed

        # split digits
        # Example "16.2" -> d1='1', d2='6', d3='2'
        parts = s.split(".")
        whole = parts[0]
        dec = parts[1] if len(parts) > 1 else "0"

        if len(whole) == 1:
            d1 = "0"
            d2 = whole[0]
        else:
            d1, d2 = whole[-2], whole[-1]
        d3 = dec[0]

        # draw scaled digits (adjust scale/offset as needed)
        scale = 6
        y_offset = 4
        self._draw_scaled_char(d1, 0,  y_offset, scale)
        self._draw_scaled_char(d2, 41, y_offset, scale)
        self._draw_scaled_char(d3, 87, y_offset, scale)

        self.show()