from machine import Pin, SPI, UART
import framebuf, time
from writer import Writer
from fonts import font_digits_large, font_digits_med, font_letters_large

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

        self.spi = SPI(1,20000_000,polarity=0, phase=0,sck=Pin(SCK),mosi=Pin(MOSI),miso=None)
        self.dc = Pin(DC,Pin.OUT)
        self.dc(1)
        self.buffer = bytearray(self.height * self.width // 8)
        super().__init__(self.buffer, self.width, self.height, framebuf.MONO_HMSB)
        self.init_display()

        # --- Custom Font Writers ----
        self.w_digits_large = Writer(self, font_digits_large, verbose = False)
        self.w_digits_med = Writer(self, font_digits_med, verbose = False)
        self.w_letters_big = Writer(self, font_letters_large, verbose = False)

        # Large digits: no wrapping
        self.w_digits_large.set_wrap(False)
        # Medium digits: no wrapping
        self.w_digits_med.set_wrap(False)

        # ---- Precompute fixed slot positions for DD.D ----
        digit_w = self.w_digits_large.stringlen("0")
        x0 = 0
        self._big_slot_x0   = x0                      # tens
        self._big_slot_x1   = x0 + digit_w            # ones
        self._big_slot_xdot = x0 + 2 * digit_w - 2        # '.'
        self._big_slot_x2   = self._big_slot_xdot + 17  # tenths

        # ---- Precompute fixed slot positions for MM:SS ----
        dmed = self.w_digits_med.stringlen("0")
        colon_w = self.w_digits_med.stringlen(":")
        GAP_MED = 0   # tweak this if spacing looks weird

        # layout: M M : S S with gaps
        total_w_med = dmed * 4 + colon_w + GAP_MED * 4
        x0m = -4

        self._time_x_m10   = x0m
        self._time_x_m1    = self._time_x_m10   + dmed - 4
        self._time_x_colon = self._time_x_m1    + dmed - 4
        self._time_x_s10   = self._time_x_colon + colon_w - 22
        self._time_x_s1    = self._time_x_s10   + dmed - 4

        # vertical center for the MM:SS display (you can tweak later)
        self._time_y = 5

        # Vertical positioning
        self._big_slot_y = 0

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
        self.rst(1)
        time.sleep(0.001)
        self.rst(0)
        time.sleep(0.01)
        self.rst(1)
        
        self.write_cmd(0xAE)#turn off OLED display

        self.write_cmd(0x00)   #set lower column address
        self.write_cmd(0x10)   #set higher column address 

        self.write_cmd(0xB0)   #set page address 
      
        self.write_cmd(0xdc)    #et display start line 
        self.write_cmd(0x00) 
        self.write_cmd(0x81)    #contract control 
        self.write_cmd(0x6f)    #128
        self.write_cmd(0x21)    # Set Memory addressing mode (0x20/0x21) #
        if self.rotate == 0:
            self.write_cmd(0xa0)    #set segment remap
        elif self.rotate == 180:
            self.write_cmd(0xa1)
        self.write_cmd(0xc0)    #Com scan direction
        self.write_cmd(0xa4)   #Disable Entire Display On (0xA4/0xA5) 

        self.write_cmd(0xa6)    #normal / reverse
        self.write_cmd(0xa8)    #multiplex ratio 
        self.write_cmd(0x3f)    #duty = 1/64
  
        self.write_cmd(0xd3)    #set display offset 
        self.write_cmd(0x60)

        self.write_cmd(0xd5)    #set osc division 
        self.write_cmd(0x41)
    
        self.write_cmd(0xd9)    #set pre-charge period
        self.write_cmd(0x22)   

        self.write_cmd(0xdb)    #set vcomh 
        self.write_cmd(0x35)  
    
        self.write_cmd(0xad)    #set charge pump enable 
        self.write_cmd(0x8a)    #Set DC-DC enable (a=0:disable; a=1:enable)
        self.write_cmd(0XAF)

    def show(self):
        self.write_cmd(0xB0)
        for page in range(0, 64):
            column = page if self.rotate == 180 else (63 - page)
            self.write_cmd(0x00 + (column & 0x0F))
            self.write_cmd(0x10 + (column >> 4))
            # OPTIMIZATION: Slice the buffer and send 16 bytes at once
            # instead of looping 16 times for 1 byte.
            start_index = page * 16
            end_index = start_index + 16
            self.write_data(self.buffer[start_index:end_index])

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


        # label
        if mode == 0:
            self.text("mph", 100, 54, 1)
            # draw decimal dot
            self.fill_rect(86, 42, 5, 5, 1)
        if mode == 1:
            self.text("sec", 100, 54, 1)
            # draw decimal dot
            self.fill_rect(86, 42, 5, 5, 1)
        if mode == 2:
            self.text(" A ", 100, 54, 1)
            # draw decimal dot
            self.fill_rect(86, 42, 5, 5, 1)
        if mode == 3:
            self.text(" V ", 100, 54, 1)
            # draw decimal dot
            self.fill_rect(86, 42, 5, 5, 1)
        if mode == 4:
            self.text(" Miles ", 75, 54, 1)
            # draw decimal dot
            self.fill_rect(0, 42, 5, 5, 1)


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

    def draw_large_num(self, num, label):
        """
        Draw speed as fixed DD.D using precomputed slots.
        """

        # Clamp range
        if num < 0:
            num = 0.0
        if num > 99.9:
            num = 99.9

        # Avoid rounding 9.95 -> 10.0 and jumping weirdly
        v = num

        # Integer part and tenths
        int_part = int(v)              # 0..99
        tenths   = int((v * 10) % 10)  # 0..9

        ones = int_part % 10
        if int_part >= 10:
            tens = int_part // 10
            show_tens = True
        else:
            tens = 0      # value won't be used when show_tens is False
            show_tens = False

        self.fill(0)
        y = self._big_slot_y

        self.w_digits_large.set_wrap(False)

        # Tens digit (only if >= 10.0)
        if show_tens:
            self.w_digits_large.set_textpos(self._big_slot_x0, y)
            self.w_digits_large.printstring(str(tens))
        # else: leave that slot blank (screen already cleared)

        # Ones digit
        self.w_digits_large.set_textpos(self._big_slot_x1, y)
        self.w_digits_large.printstring(str(ones))

        # Decimal point
        self.w_digits_large.set_textpos(self._big_slot_xdot, y)
        self.w_digits_large.printstring(".")

        # Tenths digit
        self.w_digits_large.set_textpos(self._big_slot_x2, y)
        self.w_digits_large.printstring(str(tenths))

        #Draw the label in
        label_x = self.width - len(label) * 8
        label_y = self.height - 8
        self.text(label, label_x, label_y, 1)

        self.show()

    def draw_time(self, seconds, label):
        """
        Draw elapsed time as MM:SS using the medium digit font.
        - Always shows leading zeros (00:05, 01:23, 10:00, etc).
        - Digits and colon use fixed screen positions.
        """

        if seconds < 0:
            seconds = 0

        total = int(seconds)

        # Clamp to 99:59 max
        max_total = 99 * 60 + 59
        if total > max_total:
            total = max_total

        mins = total // 60          # 0..99
        secs = total % 60           # 0..59

        m10  = mins // 10
        m1   = mins % 10
        s10  = secs // 10
        s1   = secs % 10

        self.fill(0)

        y = self._time_y
        self.w_digits_med.set_wrap(False)

        # Minutes tens
        self.w_digits_med.set_textpos(self._time_x_m10, y)
        self.w_digits_med.printstring(str(m10))

        # Minutes ones
        self.w_digits_med.set_textpos(self._time_x_m1, y)
        self.w_digits_med.printstring(str(m1))

        # Colon
        self.w_digits_med.set_textpos(self._time_x_colon, y-7)
        self.w_digits_med.printstring(":")

        # Seconds tens
        self.w_digits_med.set_textpos(self._time_x_s10, y)
        self.w_digits_med.printstring(str(s10))

        # Seconds ones
        self.w_digits_med.set_textpos(self._time_x_s1, y)
        self.w_digits_med.printstring(str(s1))

        #Draw the label in
        label_x = self.width - len(label) * 8
        label_y = self.height - 8
        self.text(label, label_x, label_y, 1)

        self.show()