#include "pico/stdlib.h"
#include "hardware/uart.h"
#include <stdio.h>
#include <string.h>

#define UART_ID   uart1
#define TX_PIN    8        // UART1 TX (default pin)
#define RX_PIN    9        // UART1 RX (default pin)
#define BAUD_RATE 115200

int main() {
    stdio_init_all();

    // Initialize UART1
    uart_init(UART_ID, BAUD_RATE);
    gpio_set_function(TX_PIN, GPIO_FUNC_UART);
    gpio_set_function(RX_PIN, GPIO_FUNC_UART);

    // Optional: disable buffering for immediate output
    setvbuf(stdout, NULL, _IONBF, 0);

    int counter = 0;
    char message[64];

    while (true) {
        counter++;

        // Print to USB console (if enabled in CMake)
        printf("Counter (USB): %d\n", counter);

        // Send over UART1 to the other Pico
        snprintf(message, sizeof(message), "counter=%d\n", counter);
        printf(message);
        uart_puts(UART_ID, message);

        sleep_ms(250);
    }
}
