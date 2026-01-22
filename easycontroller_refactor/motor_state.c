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