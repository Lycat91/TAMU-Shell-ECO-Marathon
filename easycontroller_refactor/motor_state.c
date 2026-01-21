#include "motor_state.h"

int adc_isense = 0;
int adc_vsense = 0;
int adc_throttle = 0;

int adc_bias = 0;
int duty_cycle = 0;
int voltage_mv = 0;
int current_ma = 0;
int current_target_ma = 0;
int hall = 0;
uint motorState = 0;
int fifo_level = 0;
uint64_t ticks_since_init = 0;

volatile int throttle = 0;  // 0-255

int motorstate_counter = 0;
int prev_motorstate = 0;
volatile float rpm = 0.0f;
absolute_time_t rpm_time_start = 0;
absolute_time_t rpm_time_end = 0;

int current_ma_smoothed = 0;

bool smart_cruise = false;
int battery_current_ma = 0;
int prev_current_target_ma = 0;
absolute_time_t time_since_last_movement = 0;
