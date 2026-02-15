#include "motor_state.h"
#include "motor_user_config.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "pico/stdlib.h"
#include "pico/bootrom.h"

#define MAX_MSG_LEN 128
#define MAX_TOKENS 5

int adc_isense = 0;
int adc_vsense = 0;
int adc_throttle = 0;

int adc_bias = 0;
int duty_cycle = 0;
int voltage_mv = 0;
int current_ma = 0;
int current_target_ma = 0;
int hall = 0;
int test_current_ma = 1000; 
int test_time_us = 5000000; // 5 seconds
uint motorState = 0;
int fifo_level = 0;
uint64_t ticks_since_init = 0;

volatile int throttle = 0;  // 0-255

int motorstate_counter = 0;
int prev_motorstate = 0;
volatile float rpm = 0.0f;
float speed;
float prev_speed;
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
absolute_time_t time_since_at_target_speed = 0;



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


void enter_bootloader(void) {
    reset_usb_boot(0, 0); // jumps to BOOTSEL without unplugging
}

// Global or static variables to persist between function calls
char input_buffer[MAX_MSG_LEN];
int buffer_idx = 0;
char *tokens[MAX_TOKENS];
int token_count = 0;

/**
 * Non-blocking function to read serial and tokenize by comma
 * Returns true if a full message was processed, false otherwise.
 */

 // Keep your global variables as they are
// input_buffer, buffer_idx, tokens, token_count, etc.

bool read_serial_input() {
    while (true) {
        int c = getchar_timeout_us(0); // Non-blocking read

        if (c == PICO_ERROR_TIMEOUT) {
            return false; // SILENTLY return. Do not print here!
        }

        // --- DEBUG: Uncomment this ONLY if you suspect hardware issues ---
        // printf("Debug Char: %c (%d)\n", c, c); 
        // ----------------------------------------------------------------

        // Check for end of line (Enter key)
        if (c == '\n' || c == '\r') {
            if (buffer_idx > 0) { // Only process if we have data
                input_buffer[buffer_idx] = '\0'; // Seal the string

                // Tokenize the string
                token_count = 0;
                char *token = strtok(input_buffer, ",");
                while (token != NULL && token_count < MAX_TOKENS) {
                    tokens[token_count++] = token;
                    token = strtok(NULL, ",");
                }

                buffer_idx = 0; // Reset for next message
                return true;    // MESSAGE READY!
            }
            else {
                // Ignore empty enter key presses
                buffer_idx = 0;
                continue; 
            }
        } 
        else {
            // Store character if there is space
            if (buffer_idx < MAX_MSG_LEN - 1) {
                // Optional: Only allow valid characters to keep buffer clean
                if(c >= 32 && c <= 126) { 
                    input_buffer[buffer_idx++] = (char)c;
                }
            }
        }
    }
}

void process_serial_input() {
    // This ONLY runs if process_serial_input returns true (End of Line detected)
    if (read_serial_input()) { 
        
        printf(">>> Processing Command: [%s]\n", tokens[0]);

        if (strcmp(tokens[0], "BOOT") == 0) {
            printf(">>> Jumping to Bootloader...\n");
            enter_bootloader();
        } 
        else if (strcmp(tokens[0], "kp") == 0) {
            kp = strtof(tokens[1], NULL);
            printf(">>> kp updated to: %.4f\n", kp);
        } 
        else if (strcmp(tokens[0], "ki") == 0) {
            ki = strtof(tokens[1], NULL); 
            printf(">>> ki updated to: %.4f\n", ki);
        } 
        else if (strcmp(tokens[0], "kd") == 0) {
            kd = strtof(tokens[1], NULL);
            printf(">>> kd updated to: %.4f\n", kd);
        } 
        else if (strcmp(tokens[0], "BATTERY_MAX_CURRENT_MA") == 0) {
            BATTERY_MAX_CURRENT_MA = (int)strtof(tokens[1], NULL);
            printf(">>> Battery Max Current updated: %d\n", BATTERY_MAX_CURRENT_MA);
        }
         else if (strcmp(tokens[0], "LAUNCH_DUTY_CYCLE") == 0) {
            LAUNCH_DUTY_CYCLE = (int)strtof(tokens[1], NULL);
            printf(">>> Battery Max Current updated: %d\n", BATTERY_MAX_CURRENT_MA);
        }
        else if (strcmp(tokens[0], "cruise_error") == 0) {
            cruise_error = (int)strtof(tokens[1], NULL);
            printf(">>> Battery Max Current updated: %d\n", BATTERY_MAX_CURRENT_MA);
        }
        else if (strcmp(tokens[0], "help") == 0){
            printf(">>> Commands: BOOT, kp, ki, kd, BATTERY_MAX_CURRENT_MA, LAUNCH_DUTY_CYCLE, cruise_error\n");
        }
        else {
            printf(">>> Unknown command: %s\n", tokens[0]);
        }
    }
    // Do NOT put printf here, or it will flood your console 1000x per second
}