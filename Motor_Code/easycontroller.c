#include <stdio.h>
#include <stdlib.h> 
#include "pico/stdlib.h"
#include "hardware/pwm.h"
#include "hardware/clocks.h"
#include "hardware/irq.h"
#include "hardware/adc.h"
#include "hardware/gpio.h"
#include "hardware/sync.h"
#include "hardware/uart.h"

#define UART_ID   uart1
#define TX_PIN    4       
#define RX_PIN    5       
#define BAUD_RATE 115200

// Begin user config section ---------------------------

const bool IDENTIFY_HALLS_ON_BOOT = false;   
const bool IDENTIFY_HALLS_REVERSE = false;  
const bool COMPUTER_CONTROL = true;       
int LAUNCH_DUTY_CYCLE = 6553;
int PHASE_MAX_CURRENT_MA = 15000;
int BATTERY_MAX_CURRENT_MA = 15000;
const int THROTTLE_LOW = 700;               
const int THROTTLE_HIGH = 2000;
int ECO_CURRENT_ma=6000;
uint8_t hallToMotor[8] = {255, 3, 1, 2, 5, 4, 0, 255}; 
const bool CURRENT_CONTROL = true;          
const int CURRENT_CONTROL_LOOP_GAIN = 200;  
// End user config section -----------------------------

const uint LED_PIN = 25;
const uint AH_PIN = 16;
const uint AL_PIN = 17;
const uint BH_PIN = 18;
const uint BL_PIN = 19;
const uint CH_PIN = 20;
const uint CL_PIN = 21;
const uint HALL_1_PIN = 13;
const uint HALL_2_PIN = 14;
const uint HALL_3_PIN = 15;
const uint ISENSE_PIN = 26;
const uint VSENSE_PIN = 27;
const uint THROTTLE_PIN = 28;

const uint A_PWM_SLICE = 0;
const uint B_PWM_SLICE = 1;
const uint C_PWM_SLICE = 2;
 
const uint F_PWM = 16000;                                           
const uint FLAG_PIN = 2;
const uint HALL_OVERSAMPLE = 8;

const int DUTY_CYCLE_MAX = 65535;
const int CURRENT_SCALING = 3.3 / 0.0005 / 20 / 4096 * 1000;         
const int VOLTAGE_SCALING = 3.3 / 4096 * (47 + 2.2) / 2.2 * 1000;    
const int ADC_BIAS_OVERSAMPLE = 1000;

const int HALL_IDENTIFY_DUTY_CYCLE = 25;

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
volatile int throttle = 0;  
int motorstate_counter = 0;
int prev_motorstate = 0;
int rpm = 0;



uint get_halls();
void writePWM(uint motorState, uint duty, bool synchronous);
uint8_t read_throttle();

void on_adc_fifo() {
    
    uint32_t flags = save_and_disable_interrupts();

    adc_run(false);             
    gpio_put(FLAG_PIN, 1);      

    fifo_level = adc_fifo_get_level();
    adc_isense = adc_fifo_get();    
    adc_vsense = adc_fifo_get();
    adc_throttle = adc_fifo_get();

    restore_interrupts(flags);      

    if(fifo_level != 3) {
        return;
    }

    prev_motorstate = motorState;       
    hall = get_halls();                 
    motorState = hallToMotor[hall];     
    if (motorState != prev_motorstate){
        motorstate_counter += 1;
    }
    
    throttle = ((adc_throttle - THROTTLE_LOW) * 256) / (THROTTLE_HIGH - THROTTLE_LOW);  
    throttle = MAX(0, MIN(255, throttle));      

    


    current_ma = (adc_isense - adc_bias) * CURRENT_SCALING;     
    voltage_mv = adc_vsense * VOLTAGE_SCALING;  

    if(CURRENT_CONTROL) {
        int user_current_target_ma = throttle * PHASE_MAX_CURRENT_MA / 256;  
        int battery_current_limit_ma = BATTERY_MAX_CURRENT_MA * DUTY_CYCLE_MAX / duty_cycle;  
        current_target_ma = MIN(user_current_target_ma, battery_current_limit_ma);

        if (throttle == 0)
        {
            duty_cycle = 0;     
            ticks_since_init = 0;   
        }
        else
            ticks_since_init++;
        
        
            
        if (adc_throttle > 2000){
            current_target_ma=ECO_CURRENT_ma;
        }

        duty_cycle += (current_target_ma - current_ma) / CURRENT_CONTROL_LOOP_GAIN;  
        duty_cycle = MAX(0, MIN(DUTY_CYCLE_MAX, duty_cycle));   
        

        
        if(rpm < 30 && throttle != 0){
            duty_cycle = LAUNCH_DUTY_CYCLE; 
        }
     

        bool do_synchronous = ticks_since_init > 16000;    
        writePWM(motorState, (uint)(duty_cycle / 256), do_synchronous);
    }
    else {
        duty_cycle = throttle * 256;    
        bool do_synchronous = true;     
        writePWM(motorState, (uint)(duty_cycle / 256), do_synchronous);
    }

    gpio_put(FLAG_PIN, 0);
}

void on_pwm_wrap() {
    

    gpio_put(FLAG_PIN, 1);     
    adc_select_input(0);        
    adc_run(true);             
    pwm_clear_irq(A_PWM_SLICE); 
    while(!adc_fifo_is_empty()) 
        adc_fifo_get();

    gpio_put(FLAG_PIN, 0);
}

void writePhases(uint ah, uint bh, uint ch, uint al, uint bl, uint cl)
{
    pwm_set_both_levels(A_PWM_SLICE, ah, 255 - al);
    pwm_set_both_levels(B_PWM_SLICE, bh, 255 - bl);
    pwm_set_both_levels(C_PWM_SLICE, ch, 255 - cl);
}

void writePWM(uint motorState, uint duty, bool synchronous)
{
    if(duty == 0 || duty > 255)     
        motorState = 255;

    
    if(duty > 245)
        duty = 255;

    uint complement = 0;
    if(synchronous)
    {
        complement = MAX(0, 248 - (int)duty);    
    }

    if(motorState == 0)                         
        writePhases(0, duty, 0, 255, complement, 0);
    else if(motorState == 1)                   
        writePhases(0, 0, duty, 255, 0, complement);
    else if(motorState == 2)                    
        writePhases(0, 0, duty, 0, 255, complement);
    else if(motorState == 3)                    
        writePhases(duty, 0, 0, complement, 255, 0);
    else if(motorState == 4)                    
        writePhases(duty, 0, 0, complement, 0, 255);
    else if(motorState == 5)                   
        writePhases(0, duty, 0, 0, complement, 255);
    else                                        
        writePhases(0, 0, 0, 0, 0, 0);
}

void init_hardware() {

    stdio_init_all();

    gpio_init(LED_PIN);  
    gpio_set_dir(LED_PIN, GPIO_OUT);
    gpio_init(FLAG_PIN);
    gpio_set_dir(FLAG_PIN, GPIO_OUT);

    gpio_init(HALL_1_PIN);  
    gpio_set_dir(HALL_1_PIN, GPIO_IN);
    gpio_init(HALL_2_PIN);
    gpio_set_dir(HALL_2_PIN, GPIO_IN);
    gpio_init(HALL_3_PIN);
    gpio_set_dir(HALL_3_PIN, GPIO_IN);

    gpio_set_function(AH_PIN, GPIO_FUNC_PWM);   
    gpio_set_function(AL_PIN, GPIO_FUNC_PWM);
    gpio_set_function(BH_PIN, GPIO_FUNC_PWM);
    gpio_set_function(BL_PIN, GPIO_FUNC_PWM);
    gpio_set_function(CH_PIN, GPIO_FUNC_PWM);
    gpio_set_function(CL_PIN, GPIO_FUNC_PWM);

    adc_init();
    adc_gpio_init(ISENSE_PIN);  
    adc_gpio_init(VSENSE_PIN);
    adc_gpio_init(THROTTLE_PIN);

    sleep_ms(100);
    for(uint i = 0; i < ADC_BIAS_OVERSAMPLE; i++)   
    {
        adc_select_input(0);
        adc_bias += adc_read();
    }
    adc_bias /= ADC_BIAS_OVERSAMPLE;

    adc_set_round_robin(0b111);     
    adc_fifo_setup(true, false, 3, false, false);   
    irq_set_exclusive_handler(ADC_IRQ_FIFO, on_adc_fifo); 
    irq_set_priority(ADC_IRQ_FIFO, 0);
    adc_irq_set_enabled(true);
    irq_set_enabled(ADC_IRQ_FIFO, true);

    pwm_clear_irq(A_PWM_SLICE);   
    irq_set_exclusive_handler(PWM_IRQ_WRAP, on_pwm_wrap);  
    irq_set_priority(PWM_IRQ_WRAP, 0);
    irq_set_enabled(PWM_IRQ_WRAP, true);

    float pwm_divider = (float)(clock_get_hz(clk_sys)) / (F_PWM * 255 * 2);     
    pwm_config config = pwm_get_default_config();
    pwm_config_set_clkdiv(&config, pwm_divider);
    pwm_config_set_wrap(&config, 255 - 1);     
    pwm_config_set_phase_correct(&config, true);  
    pwm_config_set_output_polarity(&config, false, true);  

    writePhases(0, 0, 0, 0, 0, 0); 

    pwm_init(A_PWM_SLICE, &config, false);
    pwm_init(B_PWM_SLICE, &config, false);
    pwm_init(C_PWM_SLICE, &config, false);

    pwm_set_mask_enabled(0x07);
}

uint get_halls() {
    uint hallCounts[] = {0, 0, 0};
    for(uint i = 0; i < HALL_OVERSAMPLE; i++)
    {
        hallCounts[0] += gpio_get(HALL_1_PIN);
        hallCounts[1] += gpio_get(HALL_2_PIN);
        hallCounts[2] += gpio_get(HALL_3_PIN);
    }

    uint hall_raw = 0;
    for(uint i = 0; i < 3; i++)
        if (hallCounts[i] > HALL_OVERSAMPLE / 2)    
            hall_raw |= 1<<i;                     

    return hall_raw;    
}

void identify_halls()
{
    sleep_ms(2000);
    for(uint i = 0; i < 6; i++)
    {
        for(uint j = 0; j < 1000; j++)       
        {
            sleep_us(500);
            writePWM(i, HALL_IDENTIFY_DUTY_CYCLE, false);
            printf("%u\n", i);
            sleep_us(500);
            writePWM((i + 1) % 6, HALL_IDENTIFY_DUTY_CYCLE, false);     
        }

        if(IDENTIFY_HALLS_REVERSE)
            hallToMotor[get_halls()] = (i + 5) % 6; 
        else
            hallToMotor[get_halls()] = (i + 2) % 6;   
    }

    writePWM(0, 0, false);     

    printf("hallToMotor array:\n");    
    for(uint8_t i = 0; i < 8; i++)
        printf("%d, ", hallToMotor[i]);
    printf("\nIf any values are 255 except the first and last, auto-identify failed. Otherwise, save this table in code.\n");
}




void wait_for_serial_command(const char *message) {
    printf("%s\n", message);
    printf("Type any key + Enter to continue...\n");

    int c = getchar(); 
    (void)c;       
}


void check_serial_input_for_Phase_Current() {
    static char buf[8];
    static int idx = 0;

    
    int c;
    while ((c = getchar_timeout_us(0)) != PICO_ERROR_TIMEOUT) {
        if (c == '\n' || c == '\r') {
            if (idx > 0) {
                buf[idx] = '\0';
                int val = atoi(buf);
                if (val > 0 && val < 21001){
                    PHASE_MAX_CURRENT_MA = val;
                }
                idx = 0; 
            }
        } else if (idx < (int)(sizeof(buf) - 1)) {
            buf[idx++] = (char)c;
        }
    }
}



int main() {

    init_hardware();

    uart_init(UART_ID, BAUD_RATE);
    gpio_set_function(TX_PIN, GPIO_FUNC_UART);
    gpio_set_function(RX_PIN, GPIO_FUNC_UART);
    char message[64];

    int signal = 's';
    int duty_cycle_norm = 0;
    int throttle_norm = 0;
    int eco;

    sleep_ms(1000);

    pwm_set_irq_enabled(A_PWM_SLICE, true); 
    
    while (true) {
        gpio_put(LED_PIN, !gpio_get(LED_PIN));  
        rpm = (motorstate_counter * 4 * 60) / 23 / 6;
        motorstate_counter = 0;
        check_serial_input_for_Phase_Current(); 
        duty_cycle_norm = duty_cycle*100/DUTY_CYCLE_MAX;
        throttle_norm = throttle*100/255;
        int UARTvoltage_mv=voltage_mv/100;
        if (throttle_norm >= 90){
            eco = 1;
        }
        else
        { 
            eco = 0;
        }
        snprintf(message, sizeof(message), "%c%03d%06d%03d%03d%03d%1d\n", signal, UARTvoltage_mv, current_ma, rpm, duty_cycle_norm, throttle_norm,eco);
        uart_puts(UART_ID, message);
        sleep_ms(250);
    }

    return 0;
}
