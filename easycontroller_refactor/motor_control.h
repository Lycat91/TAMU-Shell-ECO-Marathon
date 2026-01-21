#pragma once

#include <stdint.h>
#include <stdbool.h>
#include "pico/stdlib.h"

// ISR handlers (must retain behavior)
void on_adc_fifo(void);
void on_pwm_wrap(void);

// Core commutation/PWM
uint get_halls(void);
void writePhases(uint ah, uint bh, uint ch, uint al, uint bl, uint cl);
void writePWM(uint motorState, uint duty, bool synchronous);

// Debug / utilities
void identify_halls(void);
void commutate_open_loop(void);
void commutate_open_loop_Computer_Control(void);

// Serial helpers (used by debug modes)
void check_serial_input(void);
void check_serial_input_for_Phase_Current(void);
void wait_for_serial_command(const char *message);
