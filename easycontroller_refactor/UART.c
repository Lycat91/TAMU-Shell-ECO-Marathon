#include "UART.h"

#include <stdio.h>
#include "pico/stdlib.h"
#include "hardware/uart.h"

#include "motor_state.h"
#include "motor_user_config.h"
#include "motor_pins.h"

void send_telemetry_uart() {
    char message[64];
    int duty_cycle_norm = duty_cycle * 100 / DUTY_CYCLE_MAX;
    int throttle_norm   = throttle * 100 / 255;
    int UARTvoltage_mv  = voltage_mv / 100;

    int eco = (throttle_norm >= 90) ? 1 : 0;
    int signal = 's';

    snprintf(message, sizeof(message), "%c%03d%06d%03d%03d%03d%1d\n",
             signal,
             UARTvoltage_mv,
             battery_current_ma,
             (int)rpm,
             duty_cycle_norm,
             throttle_norm,
             eco);

    uart_puts(UART_ID, message);
}
