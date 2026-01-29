#include "motor_state.h"
#include "motor_user_config.h"
#include <stdio.h>
#include <stdlib.h>

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
bool record_motor_ticks = false;
int battery_current_ma = 0;
int prev_current_target_ma = 0;
absolute_time_t time_since_last_movement = 0;
uint32_t motor_ticks = 0;
bool UCO = false;
bool at_target_speed = false;
bool launch = false;
bool race_mode = true;
bool test_mode = false;
bool drive_mode = false;



void wait_for_serial_command(const char *message) {
    printf("%s\n", message);
    printf("Type any key + Enter to continue...\n");

    int c = getchar();
    (void)c;
}

void check_serial_input_for_Phase_Current(void) {
    static char buf[8];
    static int idx = 0;

    int c;
    while ((c = getchar_timeout_us(0)) != PICO_ERROR_TIMEOUT) {
        if (c == '\n' || c == '\r') {
            if (idx > 0) {
                buf[idx] = '\0';
                int val = atoi(buf);
                if (val > 0 && val < 21001) {
                    PHASE_MAX_CURRENT_MA = val;
                }
                idx = 0;
            }
        } else if (idx < (int)(sizeof(buf) - 1)) {
            buf[idx++] = (char)c;
        }
    }
}


void check_serial_input(void) {
    static char buf[8];
    static int idx = 0;

    int c;
    while ((c = getchar_timeout_us(0)) != PICO_ERROR_TIMEOUT) {
        if (c == '\n' || c == '\r') {
            if (idx > 0) {
                buf[idx] = '\0';
                int val = atoi(buf);
                if (val >= 0 && val <= 255) {
                    throttle = val;
                    printf("Throttle updated: %d\n", throttle);
                }
                idx = 0;
            }
        } else if (idx < (int)(sizeof(buf) - 1)) {
            buf[idx++] = (char)c;
        }
    }
}

void increment_motor_ticks() {
    motor_ticks++;
}
uint32_t get_motor_ticks() {
    return motor_ticks;
}
void reset_motor_ticks() {
    motor_ticks = 0;
}
void start_motor_ticks() {
    record_motor_ticks = true;
}
void stop_motor_ticks() {
    record_motor_ticks = false;
}

void get_RPM(){
    if (motorstate_counter == 0) {
        rpm_time_start = get_absolute_time();
    }

    if (motorState != prev_motorstate) {
        time_since_last_movement = get_absolute_time();
        motorstate_counter += 1;
        increment_motor_ticks();
    }

    if (motorstate_counter >= 10) {
        rpm_time_end = get_absolute_time();
        float dt_us = (float)absolute_time_diff_us(rpm_time_start, rpm_time_end);
        rpm = (motorstate_counter * 60.0f * 1e6f) / (dt_us * 138.0f); // 138 motor ticks in one rotation
        motorstate_counter = 0;
    }

    if (absolute_time_diff_us(time_since_last_movement, get_absolute_time()) > 500000) { // resets rpm counter if no motor movement for .5 seconds
        rpm = 0;
        motorstate_counter = 0;
    }
}