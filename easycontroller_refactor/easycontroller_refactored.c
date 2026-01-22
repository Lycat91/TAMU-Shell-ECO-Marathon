#include <stdio.h>
#include <stdlib.h>

#include "pico/stdlib.h"
#include "hardware/uart.h"
#include "hardware/pwm.h"

#include "motor_user_config.h"
#include "motor_pins.h"
#include "motor_state.h"
#include "motor_hw.h"
#include "motor_control.h"
#include "UART.h"


int main(void) {
    printf("Hello from Pico!\n");

    init_hardware();

    // UART init
    uart_init(UART_ID, BAUD_RATE);
    gpio_set_function(TX_PIN, GPIO_FUNC_UART);
    gpio_set_function(RX_PIN, GPIO_FUNC_UART);

    printf("Hello from Pico!\n");


    if (IDENTIFY_HALLS_ON_BOOT) {
        identify_halls();
        wait_for_serial_command("Hall identification done. Review table above.");
    }

    sleep_ms(1000);

    // Enables interrupts, starting motor commutation (unchanged)
    pwm_set_irq_enabled(A_PWM_SLICE, true);

    // Smart cruise
    float target_speed = 16.0f;
    float cruise_error = 1.0f;
    float cruise_increment = 250.0f;

    while (true) {
        gpio_put(LED_PIN, !gpio_get(LED_PIN));
        check_serial_input_for_Phase_Current();

        send_telemetry_uart();

        sleep_ms(250);
        int speed = (int)(rpm * rpmtomph);

        if (smart_cruise == true) {
            if (rpm * rpmtomph > (target_speed - cruise_error) && speed < (target_speed + cruise_error)) {
                continue;
            } else if (speed < (target_speed - cruise_error) && current_target_ma < PHASE_MAX_CURRENT_MA) {
                current_target_ma += (int)cruise_increment;
            } else if (speed > (target_speed + cruise_error) && current_target_ma > 200) {
                current_target_ma -= (int)cruise_increment;
            }
        }


        printf(
            "rpm:%6f | mph:%6.2f | smoothed_ma:%6d | current_ma:%6d | target_ma:%6d | battery_ma:%6d | throttle_norm:%3d%% | throttle_raw:%3d | duty_norm:%3d%% | motor_state:%d | motor_ticks:%9d\n",
            rpm,
            rpm * rpmtomph,
            current_ma_smoothed,
            current_ma,
            current_target_ma,
            battery_current_ma,
            throttle * 100 / 255,
            throttle,
            duty_cycle * 100 / DUTY_CYCLE_MAX,
            motorState,
            motor_ticks);
    }

    return 0;
}
