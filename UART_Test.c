#include "pico/stdlib.h"
#include "hardware/uart.h"
#include <stdio.h>
#include <string.h>

#define UART_ID uart0
#define TX_PIN 0
#define RX_PIN 1
#define BAUD_RATE 115200

int main() {
    stdio_init_all();
    uart_init(UART_ID, BAUD_RATE);
    gpio_set_function(TX_PIN, GPIO_FUNC_UART);
    gpio_set_function(RX_PIN, GPIO_FUNC_UART);
    int counter =0;

    char message[64];

    while (true) {
  
        counter += 1;
        sprintf(message, "counter=%d\n", counter);
        uart_puts(UART_ID, message);

        sleep_ms(250);
    }
}
