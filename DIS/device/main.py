import config, utime
import comm
oled = config.OLED_1inch3()

# # Zones
# oled.fill(0) 
# oled.show() 
# oled.rect(0,0,40,50,1) 
# oled.rect(41,0,40,50,1) 
# oled.fill_rect(82,46,4,4,1) 
# oled.rect(87,0,40,50,1) 
# oled.text("mph",100,54) 
# oled.show()
oled.fill(0)
oled.draw_speed(99.9)
utime.sleep(1)

for i in range(999):
    draw_start_time = utime.ticks_ms()
    oled.draw_speed(i/10)
    draw_stop_time = utime.ticks_ms()
    utime.sleep(.05)
    final_time = utime.ticks_ms()
    draw_time = utime.ticks_diff(draw_start_time, draw_stop_time)/1000
    i_time = utime.ticks_diff(draw_start_time, final_time)/1000

    print(i/1000, "draw:", draw_time, " total: ", i_time)

    print("Voltage",comm.voltage,"Current",comm.current,"RPM",comm.rpm)