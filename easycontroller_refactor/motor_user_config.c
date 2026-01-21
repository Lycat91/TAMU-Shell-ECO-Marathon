#include "motor_user_config.h"

// Begin user config section ---------------------------

const bool IDENTIFY_HALLS_ON_BOOT = false;   // If true, controller will initialize the hall table by slowly spinning the motor
const bool IDENTIFY_HALLS_REVERSE = false;  // If true, will initialize the hall table to spin the motor backwards
const bool COMPUTER_CONTROL = true;         // If true will enable throttle control via serial communication

int LAUNCH_DUTY_CYCLE = 6553;
int PHASE_MAX_CURRENT_MA = 15000;
int BATTERY_MAX_CURRENT_MA = 15000;

const int THROTTLE_LOW = 700;
const int THROTTLE_HIGH = 2000;

int ECO_CURRENT_ma = 6000;
float rpmtomph = 0.04767f; // Conversion from rpm to mph

// Correct Hall Table !!!DO NOT CHANGE!!!
uint8_t hallToMotor[8] = {255, 3, 1, 2, 5, 4, 0, 255};

const bool CURRENT_CONTROL = true;          // Use current control or duty cycle control

const int CURRENT_CONTROL_LOOP_GAIN = 200;  // Adjusts the speed of the current control loop

// End user config section -----------------------------

const int HALL_IDENTIFY_DUTY_CYCLE = 25;
