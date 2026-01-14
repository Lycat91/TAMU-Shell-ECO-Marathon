# Shell Eco-Marathon 2025–2026  
## Motor Controller & Driver Information System (DIS)

This repository contains the embedded software developed by a team of four senior **Electrical Engineering** students at **Texas A&M University** for participation in the **2025–2026 Shell Eco-Marathon** competition.

Our project focuses on high-efficiency electric vehicle control through a custom motor control stack and a real-time Driver Information System (DIS), designed to help the driver achieve maximum energy efficiency during competition runs.

---

## Project Overview

This repository includes all firmware used to:

- Control an **MIT open-source motor controller**
- Interface with vehicle sensors and peripherals
- Transmit real-time performance data to a **Driver Information System (DIS)**
- Optimize motor efficiency, torque delivery, and power usage for endurance racing

We have made **substantial modifications** to the original open-source motor controller firmware to better suit the requirements of Shell Eco-Marathon racing, including performance tuning, communication improvements, and system-level integration with the DIS.

---

## Key Features

### Motor Controller Enhancements
- Performance-focused modifications to the original control algorithms
- Improved efficiency tuning for low-power endurance racing
- Custom logic for competition-specific operating conditions
- Enhanced reliability and fault handling for on-track operation

### Driver Information System (DIS)
- Real-time feedback to the driver to encourage efficient driving behavior
- Displays key vehicle metrics such as:
  - Vehicle speed
  - Motor state and power usage
  - System status and alerts
- Designed to minimize driver distraction while maximizing actionable insight

### UART Communication System
- High-speed, low-latency **UART communication** between the motor controller and DIS
- Efficient packet structure for rapid data transmission
- Robust communication designed for embedded automotive environments

---

## Open-Source Acknowledgment

This project is based on and extends the following MIT-licensed open-source motor controller:

**EasyController3**  
Created by **Patrick Grady**  
GitHub Repository: https://github.com/pgrady3/EasyController3

We gratefully acknowledge the original author for providing a robust and well-documented foundation for advanced motor control development. All original licensing terms are respected, and this repository remains compliant with the MIT License.

---

## Competition Context

**Shell Eco-Marathon** is an international engineering competition that challenges student teams to design, build, and operate the most energy-efficient vehicles possible.  
This software plays a critical role in achieving competitive efficiency by tightly integrating motor control, telemetry, and driver feedback.

---

## Team

Senior Electrical Engineering Students  
**Texas A&M University**  
- Lucas Ybarra
- Alfredo Rivas Vazquez
- Alejandro Cantu
- James DePoy
- Shell Eco-Marathon 2025–2026



