#pragma once

#include "hardware/uart.h"

void send_telemetry_uart();
void read_telemetry();
void parse_telemetry();

int target_speed;

char message_from_DIS[128]; // Assuming a max message length of 128 characters
char message_to_DIS[64];
int msg_len;
bool msg_ready;
int target_speed;