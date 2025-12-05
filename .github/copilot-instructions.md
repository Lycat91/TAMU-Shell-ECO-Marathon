# Motor Control Firmware - AI Coding Agent Guidelines

## Project Overview
This is a Raspberry Pi Pico-based BLDC motor controller for an electric vehicle (Shell ECO Marathon). The firmware implements real-time motor commutation with Hall sensor feedback, current control loops, and serial communication via UART.

## Architecture & Data Flow

**Core Control Loop (interrupt-driven):**
- `on_adc_fifo()` - Fires ~6μs after ADC conversions complete. This is where timing-critical logic executes:
  1. Read Hall sensors → determine motor state (0-5)
  2. Look up `hallToMotor[]` table for commutation
  3. Read current/voltage/throttle ADC values
  4. Execute current control or duty cycle logic
  5. Call `writePWM()` to switch transistors
  
- `on_pwm_wrap()` - Triggers when PWM counter reaches 0 (middle of cycle). Starts ADC conversions to ensure current readings capture high-side FET conduction.

**Key Hardware Abstraction:**
- Three-phase motor controlled via 6 PWM outputs (AH/AL, BH/BL, CH/CL pins 16-21)
- Hall sensors (pins 13-15) with oversampling to reduce noise
- Current sense (pin 26), voltage sense (pin 27), throttle (pin 28)
- UART1 at 115200 baud for serial telemetry

## Configuration & User Tuning

All tunable parameters are in the **"Begin user config section"** (lines 18-55). Key parameters:
- `IDENTIFY_HALLS_ON_BOOT` - Auto-calibrate motor commutation table on startup
- `CURRENT_CONTROL` - Toggle between current-based or duty-cycle-based control
- `PHASE_MAX_CURRENT_MA`, `BATTERY_MAX_CURRENT_MA` - Current limits (firmware enforces max 15A phase)
- `ECO_CURRENT_ma` - Eco mode current target (activated when throttle > 90%)
- `THROTTLE_LOW`, `THROTTLE_HIGH` - ADC calibration for throttle pedal (currently 700-2000)

**Critical Table:** `hallToMotor[8]` maps Hall sensor readings (0-7, with 0 and 7 invalid) to motor commutation states (0-5). **DO NOT MODIFY** unless running `identify_halls()`.

## Control Modes & Workflows

**Mode 0 (Default - Current Control):**
- Integral controller adjusts duty cycle to match target current
- Target current = throttle × `PHASE_MAX_CURRENT_MA` / 256
- Respects battery current limit via `battery_current_limit_ma` calculation
- Launch boost: duty cycle forced to `LAUNCH_DUTY_CYCLE` until rpm > 30
- Smart cruise: reads throttle > 90% to enable adaptive speed control

**Mode 1 (Open Loop):**
- Manually cycle through commutation states 0-5 at fixed duty cycle
- Useful for electrical debugging

**Mode 2 (Serial Command):**
- Accept throttle values (0-255) via serial input
- Cycles motor states with serial-controlled throttle

## Critical Implementation Patterns

**Interrupt Timing:**
- ADC interrupt priority = 0 (highest). Disable all interrupts during critical ADC reads to prevent USB interference
- PWM interrupt also priority 0. These must complete within their timing windows (~7μs for ADC, ~1.3μs for PWM)
- Use `gpio_put(FLAG_PIN, 1/0)` for oscilloscope debugging of interrupt timing

**PWM & Deadtime:**
- Phase-correct PWM (counts 0→254→0) allows firing interrupt at cycle midpoint
- Synchronous switching: complement = MAX(0, 248 - duty) provides 7-cycle deadband to prevent shoot-through
- At duty > 245, clamp to 255 (100% DC) to prevent bootstrap capacitor discharge
- Low-side PWM is inverted in hardware config

**Commutation Table Auto-Identification:**
- Calls `identify_halls()` at boot if `IDENTIFY_HALLS_ON_BOOT == true`
- PWMs between half-states (states 0↔1, 1↔2, etc.) for 1000 cycles each (~500ms per state)
- Reads Hall sensors and saves motor state offset ±1.5 electrical steps ahead
- Output array should have only 255 at indices 0 and 7; any other 255 indicates failure

**Current Measurement:**
- Raw ADC value has bias (zero-current offset) calibrated at startup: `adc_bias = average(1000 ADC samples)`
- Scaling: `current_ma = (adc_isense - adc_bias) * CURRENT_SCALING`
- Smoothing filter (exponential): `current_ma_smoothed = (current_ma + 9*smoothed) / 10`

**Serial Communication:**
- UART1 (TX=pin 4, RX=pin 5): Telemetry packet format is `s[voltage][battery_current][rpm][duty_norm][throttle_norm][eco_flag]\n`
- Non-blocking read via `getchar_timeout_us(0)` in main loop (don't block in interrupts)

## Build & Debugging

**CMake Build:**
```bash
cd Motor_Code
cmake -B build
cd build
make
```

**Output Artifacts:**
- `easycontroller.uf2` - Production build
- `easycontroller_debug.uf2` - Debug build (same logic, for iteration)
- Flash to Pico via USB mass storage or `picotool`

**Debugging Techniques:**
- Toggle FLAG_PIN (pin 2) in interrupt handlers to visualize timing with oscilloscope
- Use `printf()` output via USB (enabled in CMakeLists.txt)
- RPM calculation uses motor state change counting: 10 state changes ÷ time elapsed = one motor rotation ÷ 138 (adjustment factor)

## Common Pitfalls

1. **Assignment vs. Comparison:** Use `==` for conditionals, not `=` (e.g., `if (cruise_counter == 4)`)
2. **Hall Table Corruption:** Never modify `hallToMotor[]` without running `identify_halls()` first
3. **Bootstrap Capacitor:** High duty cycles (>245) can discharge gate driver capacitor; code clamps to 255
4. **ADC Timing:** Must start conversions during high-side FET on-time; PWM interrupt handles this
5. **Interrupt Conflicts:** USB interrupts can corrupt ADC reads; code disables all interrupts during critical section

## Future Enhancements to Watch

- Smart cruise implementation (lines 625-655): integrates current target adjustment based on speed error
- DIS device interface (separate Python module in `DIS/` directory) for wireless telemetry
- Hall sensor noise occasionally returns invalid states (0 or 7); current design ignores these via `hallToMotor[0]=hallToMotor[7]=255`
