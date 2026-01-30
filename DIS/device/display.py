from writer import Writer
from fonts import font_digits_large, font_digits_med, font_letters_large
import time
import framebuf
import hardware

class OLEDDriver(framebuf.FrameBuffer):
    def __init__(self):
        self.width = 128
        self.height = 64
        self.rotate = 180

        self.cs = hardware.oled_cs
        self.rst = hardware.oled_rst
        self.dc = hardware.oled_dc
        self.spi = hardware.spi
        
        # Initialize Pins
        self.cs(1)
        self.dc(1)

        self.buffer = bytearray(self.height * self.width // 8)
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
            self.spi.write(buf)
        self.cs(1)

    def init_display(self):
        self.rst(1)
        time.sleep(0.001)
        self.rst(0)
        time.sleep(0.01)
        self.rst(1)
        
        self.write_cmd(0xAE) # turn off OLED display
        self.write_cmd(0x00) # set lower column address
        self.write_cmd(0x10) # set higher column address 
        self.write_cmd(0xB0) # set page address 
        self.write_cmd(0xdc) # set display start line 
        self.write_cmd(0x00) 
        self.write_cmd(0x81) # contract control 
        self.write_cmd(0x6f) # 128
        self.write_cmd(0x21) # Set Memory addressing mode
        if self.rotate == 0:
            self.write_cmd(0xa0)
        elif self.rotate == 180:
            self.write_cmd(0xa1)
        self.write_cmd(0xc0) # Com scan direction
        self.write_cmd(0xa4) # Disable Entire Display On
        self.write_cmd(0xa6) # normal / reverse
        self.write_cmd(0xa8) # multiplex ratio 
        self.write_cmd(0x3f) # duty = 1/64
        self.write_cmd(0xd3) # set display offset 
        self.write_cmd(0x60)
        self.write_cmd(0xd5) # set osc division 
        self.write_cmd(0x41)
        self.write_cmd(0xd9) # set pre-charge period
        self.write_cmd(0x22)   
        self.write_cmd(0xdb) # set vcomh 
        self.write_cmd(0x35)  
        self.write_cmd(0xad) # set charge pump enable 
        self.write_cmd(0x8a) # Set DC-DC enable
        self.write_cmd(0XAF)

    def show(self):
        self.write_cmd(0xB0)
        for page in range(0, 64):
            column = page if self.rotate == 180 else (63 - page)
            self.write_cmd(0x00 + (column & 0x0F))
            self.write_cmd(0x10 + (column >> 4))
            start_index = page * 16
            end_index = start_index + 16
            self.write_data(self.buffer[start_index:end_index])

    def set_invert(self, invert):
        if invert:
            self.write_cmd(0xa7)
        else:
            self.write_cmd(0xa6)

class ButtonManager:
    def __init__(self):
        self.key0 = hardware.key0
        self.key1 = hardware.key1
        
        now = time.ticks_ms()
        self._debounce_ms = 150
        self._longpress_ms = 3000
        
        self._last_key0 = self.key0.value()
        self._last_key1 = self.key1.value()
        self._last_time_k0 = now
        self._last_time_k1 = now
        self._k1_press_start = None
        self._k1_reset_fired = False

    def check_events(self):
        now = time.ticks_ms()
        k0 = self.key0.value()
        k1 = self.key1.value()

        k0_press = False
        k1_press = False
        k1_long_press = False
        k1_long_release = False

        # KEY0 short press
        if self._last_key0 == 1 and k0 == 0:
            if time.ticks_diff(now, self._last_time_k0) > self._debounce_ms:
                k0_press = True
                self._last_time_k0 = now

        # KEY1 press start
        if self._last_key1 == 1 and k1 == 0:
            if time.ticks_diff(now, self._last_time_k1) > self._debounce_ms:
                self._k1_press_start = now
                self._k1_reset_fired = False

        # KEY1 long press detection
        if self._k1_press_start is not None and k1 == 0 and not self._k1_reset_fired:
            press_ms = time.ticks_diff(now, self._k1_press_start)
            if press_ms >= self._longpress_ms:
                k1_long_press = True
                self._k1_reset_fired = True

        # KEY1 release
        if self._last_key1 == 0 and k1 == 1 and self._k1_press_start is not None:
            press_ms = time.ticks_diff(now, self._k1_press_start)
            if not self._k1_reset_fired and press_ms < self._longpress_ms:
                k1_press = True
            if self._k1_reset_fired:
                k1_long_release = True
                self._k1_reset_fired = False
            self._k1_press_start = None
            self._last_time_k1 = now

        self._last_key0 = k0
        self._last_key1 = k1

        return k0_press, k1_press, k1_long_press, k1_long_release

class DisplayManager:
    def __init__(self, oled_driver):
        self.oled = oled_driver
        self.width = oled_driver.width
        self.height = oled_driver.height
        self.current_screen = 0
        self.num_screens = 6

        # --- Custom Font Writers ----
        self.w_digits_large = Writer(self.oled, font_digits_large, verbose=False)
        self.w_digits_med = Writer(self.oled, font_digits_med, verbose=False)
        self.w_letters_big = Writer(self.oled, font_letters_large, verbose=False)

        self.w_digits_large.set_wrap(False)
        self.w_digits_med.set_wrap(False)

        # ---- Precompute fixed slot positions for DD.D ----
        self._big_slot_x0 = 9  # tens
        self._big_slot_x1 = 43  # ones
        self._big_slot_xdot = 79  # '.'
        self._big_slot_x2 = 93  # tenths
        self._big_slot_y = 0

        # ---- Precompute fixed slot positions for MM:SS ----
        dmed = self.w_digits_med.stringlen("0")
        colon_w = self.w_digits_med.stringlen(":")
        x0m = -4
        self._time_x_m10 = x0m
        self._time_x_m1 = self._time_x_m10 + dmed - 4
        self._time_x_colon = self._time_x_m1 + dmed - 4
        self._time_x_s10 = self._time_x_colon + colon_w - 22
        self._time_x_s1 = self._time_x_s10 + dmed - 4
        self._time_y = 5

        #--------- Alert State ----------------
        self._msg_top = None
        self._msg_bottom = None
        self._msg_until = 0  # ms timestamp; 0 means no active message
        self._is_inverted = False
        self._screen_changed = True

    def change_screen(self, delta):
        self.current_screen = (self.current_screen + delta) % self.num_screens
        self.screen_changed()
        print(f"screen: {self.current_screen}")

    def _set_inversion(self, invert):
        """Internal helper to manage hardware inversion state."""
        if invert != self._is_inverted:
            self.oled.set_invert(invert)
            self._is_inverted = invert

    def screen_changed(self):
        """Signals that the screen has changed and a full redraw is needed."""
        self._screen_changed = True

    def draw_large_num(self, num, label, uart_blink, timer_state, invert=False, eco=False):
        """
        Draw speed as fixed DD.D using precomputed slots.
        Set invert=True to flip colors before showing.
        """
        self._set_inversion(invert)

        if self._screen_changed:
            self.oled.fill(0)
            label_x = self.width - len(label) * 8
            label_y = self.height - 8
            self.oled.text(label, label_x, label_y, 1)

        # Clamp range
        if num < 0: num = 0.0
        if num > 99.9: num = 99.9

        int_part = int(num)
        tenths = int((num * 10) % 10)
        ones = int_part % 10
        tens = int_part // 10

        # --- DYNAMIC: Number Area ---
        number_height = self.w_digits_large.height
        self.oled.fill_rect(0, 0, self.width, number_height, 0)

        y = self._big_slot_y

        # Tens digit (only if >= 10.0)
        if tens > 0:
            self.w_digits_large.set_textpos(self._big_slot_x0, y)
            self.w_digits_large.printstring(str(tens))

        # Ones digit
        self.w_digits_large.set_textpos(self._big_slot_x1, y)
        self.w_digits_large.printstring(str(ones))

        # Decimal point
        self.w_digits_large.set_textpos(self._big_slot_xdot, y)
        self.w_digits_large.printstring(".")

        # Tenths digit
        self.w_digits_large.set_textpos(self._big_slot_x2, y)
        self.w_digits_large.printstring(str(tenths))

        # --- DYNAMIC: Status Area ---
        self.draw_status(uart_blink, timer_state)

        # --- DYNAMIC: Eco Line ---
        eco_line_y = self.height - 12
        self.oled.hline(0, eco_line_y, self.width, 0)
        if eco:
            self.oled.line(0, eco_line_y, self.width, eco_line_y, 1)

        self.oled.show()
        self._screen_changed = False

    def draw_time(self, seconds, label, uart_blink, timer_state):
        """
        Draw elapsed time as MM:SS using the medium digit font.
        """
        self._set_inversion(False)
        if self._screen_changed:
            self.oled.fill(0)
            label_x = self.width - len(label) * 8
            label_y = self.height - 8
            self.oled.text(label, label_x, label_y, 1)

        if seconds < 0: seconds = 0
        total = int(seconds)

        max_total = 99 * 60 + 59
        if total > max_total: total = max_total

        mins = total // 60
        secs = total % 60

        m10 = mins // 10
        m1 = mins % 10
        s10 = secs // 10
        s1 = secs % 10

        # --- DYNAMIC: Time Area ---
        time_height = self.w_digits_med.height
        self.oled.fill_rect(0, 0, self.width, time_height, 0)

        y = self._time_y

        # Minutes (tens and ones)
        self.w_digits_med.set_textpos(self._time_x_m10, y)
        self.w_digits_med.printstring(str(m10))
        self.w_digits_med.set_textpos(self._time_x_m1, y)
        self.w_digits_med.printstring(str(m1))

        # Colon
        self.w_digits_med.set_textpos(self._time_x_colon, y - 7)
        self.w_digits_med.printstring(":")

        # Seconds (tens and ones)
        self.w_digits_med.set_textpos(self._time_x_s10, y)
        self.w_digits_med.printstring(str(s10))
        self.w_digits_med.set_textpos(self._time_x_s1, y)
        self.w_digits_med.printstring(str(s1))

        # --- DYNAMIC: Status Area ---
        self.draw_status(uart_blink, timer_state)
        self.oled.show()
        self._screen_changed = False

    def draw_demo_distance(self, distance):
        """Draw distance that caps at out .999 for demo purposes only"""
        # This screen has no other dynamic elements, so a full redraw is simpler.
        self._set_inversion(False)
        self.oled.fill(0)
        distance = max(0, min(int(distance * 1000), 999))

        n1 = distance // 100
        n2 = (distance // 10) % 10
        n3 = distance % 10

        y = self._big_slot_y

        self.w_digits_large.set_textpos(0, y)
        self.w_digits_large.printstring(".")
        self.w_digits_large.set_textpos(14, y)
        self.w_digits_large.printstring(str(n1))
        self.w_digits_large.set_textpos(53, y)
        self.w_digits_large.printstring(str(n2))
        self.w_digits_large.set_textpos(91, y)
        self.w_digits_large.printstring(str(n3))

        label = "MILES"
        label_x = self.width - len(label) * 8
        label_y = self.height - 8
        self.oled.text(label, label_x, label_y, 1)

        self.oled.show()
        self._screen_changed = False

    def draw_status(self, uart_blink, timer_state):
        """
        Draw UART and timer indicators on the bottom row.
        """
        y = self.height - 8
        self.oled.fill_rect(0, y, 40, 8, 0)

        if uart_blink:
            self.oled.text("U", 0, y, 1)

        x_rec = 11
        if timer_state == "running":
            self.oled.fill_rect(x_rec - 1, y - 1, 26, 10, 1)
            self.oled.text("REC", x_rec, y, 0)
        elif timer_state == "paused":
            self.oled.text("REC", x_rec, y, 1)

    def draw_alert(self, top, bottom):
        """
        Draw two words in the letter font, centered.
        """
        self._set_inversion(False)
        self.oled.fill(0)
        if top:
            top = top.upper()
            x_top = max(0, (self.width - self.w_letters_big.stringlen(top)) // 2)
            self.w_letters_big.set_textpos(x_top, 0)
            self.w_letters_big.printstring(top)
        if bottom:
            bottom = bottom.upper()
            x_bottom = max(0, (self.width - self.w_letters_big.stringlen(bottom)) // 2)
            self.w_letters_big.set_textpos(x_bottom, 24)
            self.w_letters_big.printstring(bottom)
        self.oled.show()

    def show_alert(self, top, bottom, seconds):
        """
        Schedule an alert for a certain amount of seconds.
        """
        ms = int(seconds * 1000)
        now = time.ticks_ms()
        self._msg_top = top
        self._msg_bottom = bottom
        self._msg_until = time.ticks_add(now, ms)
        print(f"Alert: {top or ''} {bottom or ''}")

    def clear_alert(self):
        """Clear any active alert immediately."""
        self._msg_top = None
        self._msg_bottom = None
        self._msg_until = 0

    def update_alert(self):
        """
        If an alert is active, draw it and return True. Otherwise, return False.
        """
        if self._msg_top is None:
            return False

        now = time.ticks_ms()
        if time.ticks_diff(self._msg_until, now) <= 0:
            self.clear_alert()
            return False

        self.draw_alert(self._msg_top, self._msg_bottom)
        return True

    def draw_screen(self, vehicle, uart_manager):
        """Dispatch drawing based on the current screen index."""
        if self.current_screen == 0:
            invert_speed = vehicle.target_mph > 0 and vehicle.motor_mph < vehicle.target_mph
            self.draw_large_num(vehicle.motor_mph, "MPH", uart_manager.uart_blink, vehicle.timer_state, invert=invert_speed, eco=vehicle.eco)
        elif self.current_screen == 1:
            self.draw_time(vehicle.timer_elapsed_seconds, "ELAPSED", uart_manager.uart_blink, vehicle.timer_state)
        elif self.current_screen == 2:
            self.draw_large_num(vehicle.current, "AMPS", uart_manager.uart_blink, vehicle.timer_state)
        elif self.current_screen == 3:
            self.draw_large_num(vehicle.voltage, "VOLTS", uart_manager.uart_blink, vehicle.timer_state)
        elif self.current_screen == 4:
            self.draw_demo_distance(vehicle.distance_miles)
        elif self.current_screen == 5:
            self.draw_large_num(vehicle.target_mph, "TARGET MPH", uart_manager.uart_blink, vehicle.timer_state)