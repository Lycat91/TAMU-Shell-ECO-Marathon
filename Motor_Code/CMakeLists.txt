cmake_minimum_required(VERSION 3.13)

include(pico_sdk_import.cmake)

project(myproject_test C CXX ASM)
set(CMAKE_C_STANDARD 11)
set(CMAKE_CXX_STANDARD 17)

pico_sdk_init()

#easycontroller 

add_executable(easycontroller
	easycontroller.c
	)

target_link_libraries(easycontroller pico_stdlib hardware_pwm hardware_adc)

pico_enable_stdio_usb(easycontroller 1)	# Enable USB printf output
pico_enable_stdio_uart(easycontroller 0)	# Disable serial printf output

pico_add_extra_outputs(easycontroller)

#easycontroller_debug

add_executable(easycontroller_debug
    easycontroller_debug.c
)

target_link_libraries(easycontroller_debug pico_stdlib hardware_pwm hardware_adc)

pico_enable_stdio_usb(easycontroller_debug 1)
pico_enable_stdio_uart(easycontroller_debug 0)

pico_add_extra_outputs(easycontroller_debug)

