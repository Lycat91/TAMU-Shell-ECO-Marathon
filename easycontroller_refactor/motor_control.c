#include <stdio.h>
#include <stdlib.h>

#include "pico/stdlib.h"
#include "hardware/pwm.h"
#include "hardware/clocks.h"
#include "hardware/irq.h"
#include "hardware/adc.h"
#include "hardware/gpio.h"
#include "hardware/sync.h"

#include "motor_user_config.h"
#include "motor_pins.h"
#include "motor_state.h"
#include "motor_control.h"

// Forward declarations for local helpers
void writePhases(uint ah, uint bh, uint ch, uint al, uint bl, uint cl);

void on_adc_fifo(void) {
    // This interrupt is where the magic happens. This is fired once the ADC conversions have finished (roughly 6us for 3 conversions)
    // This reads the hall sensors, determines the motor state to switch to, and reads the current sensors and throttle to
    // determine the desired duty cycle. This takes ~7us to complete.

    uint32_t flags = save_and_disable_interrupts(); // Disable interrupts for the time-critical reading ADC section. USB interrupts may interfere

    adc_run(false);             // Stop the ADC from free running
    gpio_put(FLAG_PIN, 1);      // For debugging, toggle the flag pin

    fifo_level = adc_fifo_get_level();
    adc_isense = adc_fifo_get();    // Read the ADC values into the registers
    adc_vsense = adc_fifo_get();
    adc_throttle = adc_fifo_get();

    restore_interrupts(flags);      // Re-enable interrupts

    if (fifo_level != 3) {
        // The RP2040 ADC can occasionally return an unexpected number of samples. Abort if not exactly 3.
        return;
    }

    prev_motorstate = motorState;       // keeps track of previous motor state for rpm counting
    hall = get_halls();                 // Read the hall sensors
    motorState = hallToMotor[hall];     // Convert the current hall reading to the desired motor state

    // RPM counting variable
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
        rpm = (motorstate_counter * 60.0f * 1e6f) / (dt_us * 144.0f); // adjust 144 if needed
        motorstate_counter = 0;
    }

    if (absolute_time_diff_us(time_since_last_movement, get_absolute_time()) > 500000) { // resets rpm counter if no motor movement for .5 seconds
        rpm = 0;
        motorstate_counter = 0;
    }

    throttle = ((adc_throttle - THROTTLE_LOW) * 256) / (THROTTLE_HIGH - THROTTLE_LOW);  // Scale the throttle value read from the ADC
    throttle = MAX(0, MIN(255, throttle));      // Clamp to 0-255

    current_ma = (adc_isense - adc_bias) * CURRENT_SCALING;     // Since the current sensor is bidirectional, subtract the zero-current value and scale
    current_ma_smoothed = (current_ma + (199 * current_ma_smoothed)) / 200;

    voltage_mv = adc_vsense * VOLTAGE_SCALING;  // Calculate the bus voltage

    if (CURRENT_CONTROL) {
        prev_current_target_ma = current_target_ma;
        int user_current_target_ma = throttle * PHASE_MAX_CURRENT_MA / 256;  // Calculate the user-demanded phase current

        int battery_current_limit_ma;
        if (duty_cycle == 0) {
            battery_current_limit_ma = BATTERY_MAX_CURRENT_MA;
        } else {
            battery_current_limit_ma = BATTERY_MAX_CURRENT_MA * DUTY_CYCLE_MAX / duty_cycle;
        }

        current_target_ma = MIN(user_current_target_ma, battery_current_limit_ma);

        if (throttle == 0) {
            duty_cycle = 0;         // If zero throttle, ignore the current control loop and turn all transistors off
            ticks_since_init = 0;   // Reset the timer since the transistors were turned on
        } else {
            ticks_since_init++;
        }

        //////////////////////////// ECO MODE /////////////////////////////
        if (adc_throttle > 2000) {
            current_target_ma = ECO_CURRENT_ma;
        }

        ////////////////////////// Smart Cruise ////////////////////////////
        if (adc_throttle > 2000) {
            current_target_ma = prev_current_target_ma;
            smart_cruise = true;
        } else {
            smart_cruise = false;
        }

        if (smart_cruise) {
            // placeholder (kept as-is)
        }
 
        current_target_ma = MIN(current_target_ma, battery_current_limit_ma);

        duty_cycle += (current_target_ma - current_ma) / CURRENT_CONTROL_LOOP_GAIN;  // Simple integral controller
        duty_cycle = MAX(0, MIN(DUTY_CYCLE_MAX, duty_cycle));                        // Clamp

        battery_current_ma = (int)(((long long)current_ma_smoothed * duty_cycle * 6) / (DUTY_CYCLE_MAX * 10));
;

        //////////////////////// Launch Function ///////////////////////////
        if (rpm < 30 && throttle != 0) {
            duty_cycle = LAUNCH_DUTY_CYCLE;
        }

        bool do_synchronous = ticks_since_init > 16000;    // Enable synchronous switching after some delay
        writePWM(motorState, (uint)(duty_cycle / 256), do_synchronous);
    } else {
        duty_cycle = throttle * 256;    // Set duty cycle based directly on throttle
        bool do_synchronous = true;     // Note: synchronous duty-cycle control will regen if throttle decreases
        writePWM(motorState, (uint)(duty_cycle / 256), do_synchronous);
    }

    gpio_put(FLAG_PIN, 0);
}

void on_pwm_wrap(void) {
    // This interrupt is triggered when the A_PWM slice reaches 0 (the middle of the PWM cycle)
    // This allows us to start ADC conversions while the high-side FETs are on.

    gpio_put(FLAG_PIN, 1);      // Toggle the flag pin high for debugging

    adc_select_input(0);        // Force the ADC to start with input 0
    adc_run(true);              // Start the ADC
    pwm_clear_irq(A_PWM_SLICE); // Clear this interrupt flag

    while (!adc_fifo_is_empty()) // Clear out the ADC fifo, in case it still has samples in it
        adc_fifo_get();

    gpio_put(FLAG_PIN, 0);
}

void writePhases(uint ah, uint bh, uint ch, uint al, uint bl, uint cl) {
    // Set the timer registers for each PWM slice. The lowside values are inverted,
    // since the PWM slices were already configured to invert the lowside pin.
    pwm_set_both_levels(A_PWM_SLICE, ah, 255 - al);
    pwm_set_both_levels(B_PWM_SLICE, bh, 255 - bl);
    pwm_set_both_levels(C_PWM_SLICE, ch, 255 - cl);
}

void writePWM(uint motorState_in, uint duty, bool synchronous) {
    // Switch the transistors given a desired electrical state and duty cycle
    // motorState: desired electrical position, range of 0-5
    // duty: desired duty cycle, range of 0-255
    // synchronous: perfom synchronous (low-side and high-side alternating) or non-synchronous switching (high-side only)

    uint motorState_local = motorState_in;

    if (duty == 0 || duty > 255)     // If zero throttle, turn both low-sides and high-sides off
        motorState_local = 255;

    // Clamp near-100% duty cycles to avoid bootstrap discharge issues
    if (duty > 245)
        duty = 255;

    uint complement = 0;
    if (synchronous) {
        complement = MAX(0, 248 - (int)duty);    // Provide switching deadtime by having duty + complement < 255
    }

    if (motorState_local == 0)                         // LOW A, HIGH B
        writePhases(0, duty, 0, 255, complement, 0);
    else if (motorState_local == 1)                    // LOW A, HIGH C
        writePhases(0, 0, duty, 255, 0, complement);
    else if (motorState_local == 2)                    // LOW B, HIGH C
        writePhases(0, 0, duty, 0, 255, complement);
    else if (motorState_local == 3)                    // LOW B, HIGH A
        writePhases(duty, 0, 0, complement, 255, 0);
    else if (motorState_local == 4)                    // LOW C, HIGH A
        writePhases(duty, 0, 0, complement, 0, 255);
    else if (motorState_local == 5)                    // LOW C, HIGH B
        writePhases(0, duty, 0, 0, complement, 255);
    else                                                // All transistors off
        writePhases(0, 0, 0, 0, 0, 0);
}

uint get_halls(void) {
    // Read the hall sensors with oversampling.

    uint hallCounts[] = {0, 0, 0};
    for (uint i = 0; i < HALL_OVERSAMPLE; i++) {
        hallCounts[0] += gpio_get(HALL_1_PIN);
        hallCounts[1] += gpio_get(HALL_2_PIN);
        hallCounts[2] += gpio_get(HALL_3_PIN);
    }

    uint hall_raw = 0;
    for (uint i = 0; i < 3; i++)
        if (hallCounts[i] > HALL_OVERSAMPLE / 2)
            hall_raw |= 1 << i;

    return hall_raw; // Range 0-7 (0 and 7 invalid)
}

void identify_halls(void) {
    sleep_ms(2000);
    for (uint i = 0; i < 6; i++) {
        for (uint j = 0; j < 1000; j++) {
            sleep_us(500);
            writePWM(i, HALL_IDENTIFY_DUTY_CYCLE, false);
            printf("%u\n", i);
            sleep_us(500);
            writePWM((i + 1) % 6, HALL_IDENTIFY_DUTY_CYCLE, false);
        }

        if (IDENTIFY_HALLS_REVERSE)
            hallToMotor[get_halls()] = (i + 5) % 6;
        else
            hallToMotor[get_halls()] = (i + 2) % 6;
    }

    writePWM(0, 0, false);

    printf("hallToMotor array:\n");
    for (uint8_t i = 0; i < 8; i++)
        printf("%d, ", hallToMotor[i]);
    printf("\nIf any values are 255 except the first and last, auto-identify failed. Otherwise, save this table in code.\n");
}

void commutate_open_loop(void) {
    int state = 0;
    while (true) {
        writePWM(state % 6, 25, false);
        printf("State = %d\n", state % 6);
        sleep_ms(50);
        state++;
    }
}


