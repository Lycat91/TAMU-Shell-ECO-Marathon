#pragma once

#include <stdint.h>
#include <stdbool.h>

// -----------------------------------------------------------------------------
// User-configurable settings
// -----------------------------------------------------------------------------

extern const bool IDENTIFY_HALLS_ON_BOOT;   // If true, controller will initialize the hall table by slowly spinning the motor
extern const bool IDENTIFY_HALLS_REVERSE;  // If true, will initialize the hall table to spin the motor backwards
extern const bool COMPUTER_CONTROL;        // If true will enable throttle control via serial communication

extern int LAUNCH_DUTY_CYCLE;
extern int PHASE_MAX_CURRENT_MA;
extern int BATTERY_MAX_CURRENT_MA;
extern const int THROTTLE_LOW;
extern const int THROTTLE_HIGH;
extern int ECO_CURRENT_ma;
extern float rpmtomph;                    // Conversion from rpm to mph

extern uint8_t hallToMotor[8];            // Hall-to-commutation-state table (DO NOT CHANGE TABLE VALUES)

extern const bool CURRENT_CONTROL;        // Use current control or duty cycle control
extern const int CURRENT_CONTROL_LOOP_GAIN;

extern const int HALL_IDENTIFY_DUTY_CYCLE;
