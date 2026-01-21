#pragma once

#include <stdint.h>
#include <stdbool.h>
#include "pico/stdlib.h"

// -----------------------------------------------------------------------------
// Runtime state / measurements (globals kept to preserve ISR behavior)
// -----------------------------------------------------------------------------

extern int adc_isense;
extern int adc_vsense;
extern int adc_throttle;

extern int adc_bias;
extern int duty_cycle;
extern int voltage_mv;
extern int current_ma;
extern int current_target_ma;
extern int hall;
extern uint motorState;
extern int fifo_level;
extern uint64_t ticks_since_init;

extern volatile int throttle;      // 0-255, updated from ADC or serial

extern int motorstate_counter;
extern int prev_motorstate;
extern volatile float rpm;
extern absolute_time_t rpm_time_start;
extern absolute_time_t rpm_time_end;

extern int current_ma_smoothed;

extern bool smart_cruise;
extern int battery_current_ma;
extern int prev_current_target_ma;
extern absolute_time_t time_since_last_movement;
