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
        self._big_slot_x0   = 9                      # tens
        self._big_slot_x1   = 43           # ones
        self._big_slot_xdot = 79       # '.'
        self._big_slot_x2   = 93  # tenths

        # ---- Precompute fixed slot positions for MM:SS ----
        dmed = self.w_digits_med.stringlen("0")
        colon_w = self.w_digits_med.stringlen(":")
        # layout: M M : S S with gaps
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

        #--------- Alert State ----------------
        self._msg_top = None
        self._msg_bottom = None
        self._msg_until  = 0 # ms timestamp; 0 means no active message

        # -------- Button state ----------
        now = time.ticks_ms()
        self.key0 = KEY0
        self.key1 = KEY1
        self._debounce_ms = 150
        self._longpress_ms = 3000
        self._reset_alert_ms = 3000
        self._last_key0 = self.key0.value()
        self._last_key1 = self.key1.value()
        self._last_time_k0 = now
        self._last_time_k1 = now
        self._k1_press_start = None
        self._k1_reset_fired = False
        
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

    def invert_buffer(self):
        """Invert the current framebuffer pixels in memory (no show)."""
        for i in range(len(self.buffer)):
            self.buffer[i] ^= 0xFF

    def invert_screen(self):
        """Invert the current framebuffer pixels and push to display."""
        self.invert_buffer()
        self.show()

    def draw_demo_distance(self, distance):
        """Draw distance that caps at out .999 for demo purposes only"""
        # Turn into integer in thousands, clamp, then peel off digits n1, n2, n3
        distance = int(distance * 1000)

        if distance < 0:
            distance = 0
        if distance > 999:
            distance = 999

        # Get each digit from distance in n1, n2, n3 order
        # Also get the length in pixels for each digit
        n1 = distance // 100
        n2 = (distance // 10) % 10
        n3 = distance % 10

        self.fill(0)
        y = self._big_slot_y
        self.w_digits_large.set_wrap(False)

        # Decimal point
        self.w_digits_large.set_textpos(0, y)
        self.w_digits_large.printstring(".")

        # Tenths digit (n1)
        self.w_digits_large.set_textpos(14, y)
        self.w_digits_large.printstring(str(n1))

        # Hundredths digit (n2)
        self.w_digits_large.set_textpos(53, y)
        self.w_digits_large.printstring(str(n2))

        # Thousandths digit (n3)
        self.w_digits_large.set_textpos(91, y)
        self.w_digits_large.printstring(str(n3))

        # Draw the label
        label = "MILES"
        label_x = self.width - len(label) * 8
        label_y = self.height - 8
        self.text(label, label_x, label_y, 1)

        self.show()
        
    def draw_large_num(self, num, label, uart_blink, timer_state, invert=False, eco=False):
        """
        Draw speed as fixed DD.D using precomputed slots.
        Set invert=True to flip colors before showing.
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

        # Draw the status bar
        self.draw_status(uart_blink, timer_state)

        # Draw the eco mode line
        if eco:
            self.line(0, self.height - 12, self.width, self.height - 12, 1)

        


        if invert:
            self.invert_buffer()

        self.show()

    def draw_time(self, seconds, label, uart_blink, timer_state):
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

        # Draw the status bar
        self.draw_status(uart_blink, timer_state)

        self.show()

    def draw_status(self, uart_blink, timer_state):
        """
        Draw UART and timer indicators on the bottom row without clearing full screen.
        uart_blink: bool toggled when UART message is seen; shows 'U' when True.
        timer_state: 'running' -> inverted 'REC' (black on white box)
                     'paused'  -> white 'REC' text
                     other     -> hidden
        """
        y = self.height - 8
        # Clear status region
        self.fill_rect(0, y, 40, 8, 0)

        # UART indicator
        if uart_blink:
            self.text("U", 0, y, 1)

        # Timer indicator
        x_rec = 11  # 8px char + 3px gap
        if timer_state == "running":
            # White box with black text
            self.fill_rect(x_rec - 1, y - 1, 26, 10, 1)
            self.text("REC", x_rec, y, 0)
        elif timer_state == "paused":
            # White text, no box
            self.text("REC", x_rec, y, 1)

    def check_button(self):
        """
        Debounced button handler.
        - KEY0: short press -> advance screen by 1
        - KEY1: short press -> toggle timer start/stop
        - KEY1: long press (3s) -> reset timer
        Returns (screen_delta, timer_toggle, timer_reset)
        """
        now = time.ticks_ms()
        k0 = self.key0.value()
        k1 = self.key1.value()

        screen_delta = 0
        timer_toggle = False
        timer_reset = False

        # KEY0 short press: detect falling edge with debounce
        if self._last_key0 == 1 and k0 == 0:
            if time.ticks_diff(now, self._last_time_k0) > self._debounce_ms:
                screen_delta = 1
                self._last_time_k0 = now

        # KEY1 press start
        if self._last_key1 == 1 and k1 == 0:
            if time.ticks_diff(now, self._last_time_k1) > self._debounce_ms:
                self._k1_press_start = now
                self._k1_reset_fired = False

        # KEY1 long press detection while held
        if self._k1_press_start is not None and k1 == 0 and not self._k1_reset_fired:
            press_ms = time.ticks_diff(now, self._k1_press_start)
            if press_ms >= self._longpress_ms:
                timer_reset = True
                self._k1_reset_fired = True

        # KEY1 release: decide short vs long press
        if self._last_key1 == 0 and k1 == 1 and self._k1_press_start is not None:
            press_ms = time.ticks_diff(now, self._k1_press_start)
            if not self._k1_reset_fired and press_ms < self._longpress_ms:
                timer_toggle = True
            if self._k1_reset_fired:
                self.clear_alert()
                self._k1_reset_fired = False
            self._k1_press_start = None
            self._last_time_k1 = now

        self._last_key0 = k0
        self._last_key1 = k1

        return screen_delta, timer_toggle, timer_reset

    def draw_alert(self, top, bottom):
        """
        Draw two words in the letter font
        'top' goes on the upper half
        'bottom' goes on the bottom half
        """
        self.fill(0)

        if top:
            top = top.upper()
            w_top = self.w_letters_big.stringlen(top)
            x_top = max(0, (self.width - w_top) // 2)
            self.w_letters_big.set_textpos(x_top, 0)
            self.w_letters_big.printstring(top)
        if bottom:
            bottom = bottom.upper()
            w_bottom = self.w_letters_big.stringlen(bottom)
            x_bottom = max(0, (self.width - w_bottom)// 2)
            self.w_letters_big.set_textpos(x_bottom, 24)
            self.w_letters_big.printstring(bottom)
        
        self.show()

    def show_alert(self, top, bottom, seconds):
        """
        Schedule an alert for a certain amount of seconds
        """

        # Convert seconds to ms
        ms = int(seconds * 1000)
        now = time.ticks_ms()
        self._msg_top = top
        self._msg_bottom = bottom
        self._msg_until = time.ticks_add(now, ms)
        print("Alert: {} {}".format(top or "", bottom or ""))

    def clear_alert(self):
        """Clear any active alert immediately."""
        self._msg_top = None
        self._msg_bottom = None
        self._msg_until = 0
    
    def update_alert(self):
        """
        If an alert is active and not expired, draw it and return True
        If there's no alert active, return False
        """

        if self._msg_top is None:
            return False
        
        now = time.ticks_ms()
        if time.ticks_diff(self._msg_until, now) <= 0:
            self._msg_top = None
            self._msg_bottom = None
            self._msg_until = 0
            return False
        
        # Otherwise, draw the alert
        self.draw_alert(self._msg_top, self._msg_bottom)
        return True
