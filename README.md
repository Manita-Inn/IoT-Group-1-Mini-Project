# IoT-Group1-Mini-Project

## Introduction
The Smart Parking System is an Internet of Things (IoT) solution designed to improve parking management by automatically detecting vehicle presence and controlling parking gates. The system uses an ESP32 microcontroller connected to multiple sensors and actuators to monitor parking availability and manage entry and exit gates.

The system provides real-time parking information through multiple interfaces, including a web dashboard, a mobile application using Blynk IoT Platform, and a notification system through Telegram. By integrating sensors, automation and cloud communication, the system improves parking efficiency and reduces the time drivers spend searching for available parking spaces. 

FULL DEMONSTRATION VIDEO: [WATCH HERE](https://youtu.be/sLV1_WT_iFk?feature=shared)

## Hardware Description
![HARDWARE COMPONENT](https://github.com/Manita-Inn/IoT-Group-1-Mini-Project/blob/3f306e3b8b9d920574e5af4ac8b0bd4cdad72533/Hardware%20components.png)
The hardware components used in this project include sensors for detecting vehicles, displays for showing parking information and actuators for controlling gates.
* **Main Controller:** ESP32 Microcontroller - Handles all sensors inputs, gate control, WiFi communication and system logic
* **Sensors:**
  * DHT11 Temperature and Humidity Sensor - Measures temperatrue and humidity for environmental monitoring
  * HC-SR04 Ultrasonic Distance Sensor - Detects vehicles approaching the entrance gate
  * IR Sensors: detect vehicle presence in parking slots - used for slot availability detection     and exit detection
* **Actuators:**
  * Servo Motors: control entry and exit gates.
* **Displays:** 
  * TM1637 4-Digit Display Module - Displays the number of available parking spaces
  * I2C 16x2 LCD Display - Displays
* **Supporting components:**
  * Power Supply / USB Cable: provides power to the ESP32 and the connected modules
  * Jumper wires: used to connect sensors, displays and actuators to the ESP32 pins 

## System Architecture
![](https://github.com/Manita-Inn/IoT-Group-1-Mini-Project/blob/487d83e3aa27cbdd059c3cbaf850ad3486605011/System%20Architecture.png)

The Smart Parking System follows a layered IoT architecture where sensors collect real-time data, the ESP32 processes it, and multiple platforms provide monitoring and control.

### Architecture Overview

| Layer                | Description |
|---------------------|------------|
| Sensing Layer       | Collects real-time environmental and parking data |
| Processing Layer    | Processes data and controls system behavior |
| Communication Layer | Transfers data via WiFi to external platforms |
| Application Layer   | Provides user interfaces for monitoring and control |

---

### 1. Sensing Layer

#### Sensor Overview

| Sensor        | Location        | Purpose                  | Output |
|--------------|----------------|--------------------------|--------|
| Ultrasonic   | Entrance       | Detect incoming vehicles | < 10 cm → Vehicle detected |
| IR Sensors   | Parking slots  | Detect slot occupancy    | 0 = Empty, 1 = Occupied |
| Exit IR      | Exit gate      | Detect exiting vehicles  | Triggers gate opening |
| DHT11        | Parking area   | Measure temperature & humidity | Environmental data |

#### Key Functions
- Detect vehicles at the entrance  
- Monitor parking slot occupancy  
- Detect vehicles exiting the parking area  
- Measure environmental conditions  

#### Important Logic
- Vehicle is detected when distance < 10 cm  
- Slot status is determined by IR sensor values  
- Exit sensor triggers automatic gate opening  

> Detailed behavior is explained in the *Working Process Explanation* section.

---

### 2. Processing Layer

The ESP32 microcontroller (running MicroPython) acts as the central controller of the system.

#### Core Functions

| Function            | Description |
|--------------------|------------|
| Sensor Reading     | Collects data from all sensors |
| Slot Calculation   | Determines available parking slots |
| Gate Control       | Controls entry and exit gates |
| Access Control     | Prevents entry when parking is full |
| Data Transmission  | Sends data to IoT platforms |

#### Gate Control Logic

| Condition                        | Action |
|---------------------------------|--------|
| Vehicle detected + slot available | Open entry gate |
| Parking full                    | Keep entry gate closed |
| Vehicle detected at exit sensor | Open exit gate |

#### Actuators

| Component     | Function |
|--------------|---------|
| Entry Servo  | Controls entry gate |
| Exit Servo   | Controls exit gate |

#### Display System

| Display Type | Purpose |
|-------------|--------|
| LCD 16x2    | Shows system status, temperature, and humidity |
| TM1637      | Shows available parking slots |

---

### 3. Communication Layer

This layer enables communication between the ESP32 and external platforms via WiFi.

#### Functions

| Function           | Description |
|-------------------|------------|
| Data Transmission | Sends parking and environmental data |
| Remote Commands   | Receives user inputs from platforms |
| Web Hosting       | Hosts the web dashboard |
| Notifications     | Sends updates to users |

#### Data Transmitted
- Parking slot availability  
- Gate status  
- Temperature and humidity  

---

### 4. Application Layer

This layer provides user interaction through multiple platforms.

#### Platform Overview

| Platform        | Purpose              | Key Features |
|----------------|---------------------|-------------|
| Telegram Bot   | Command interface    | Remote monitoring, status checking |
| Web Dashboard  | Real-time monitoring | Slot display, gate status, environment data |
| Blynk App      | Mobile monitoring    | Live data, remote access |

---

#### Telegram Bot
The Telegram bot provides a command-based interface for users to interact with the system and check real-time information.

![](https://github.com/Manita-Inn/IoT-Group-1-Mini-Project/blob/54e21dcd48edbfa9077dad40fc6cb220947e1a63/Telegram%20Bot%20commands.jpg)

---

#### Web Dashboard
The ESP32 hosts a web server that provides a dashboard accessible via browser using its IP address.

**Features:**
- Real-time parking availability  
- Gate status monitoring  
- Temperature and humidity display  
- Manual control options  

![](https://github.com/Manita-Inn/IoT-Group-1-Mini-Project/blob/28fe1ff99aad8fdb4b5646f14a18fad55969542c/Web%20Dashboard.jpg)

---

#### Blynk Mobile Application
The Blynk app provides a mobile-friendly interface for monitoring the system.

**Features:**
- Available parking slots  
- Environmental data  
- Gate status  
- Remote access  

![](https://github.com/Manita-Inn/IoT-Group-1-Mini-Project/blob/9d4abc83f06885281cae606588e6fbb30a500044/Blynk%20App.jpg)

## Software Architecture 
![](https://github.com/Manita-Inn/IoT-Group-1-Mini-Project/blob/51471eebc59868aa3f48107e3c81660432b93f3c/Software%20Architecture.png)

The software architecture of the Smart Parking System follows a continuous control loop. After system initialization, the ESP32 connects to WiFi and IoT platforms. The system continuously reads sensor data, calculates parking slot availability, and determines whether the gate should open or remain closed. The software also updates local displays and sends real-time data to cloud platforms such as Blynk IoT Platform and the web dashboard. In addition, the system listens for user commands from Telegram to provide parking status and environmental information.

## IoT integration 
![](https://github.com/Manita-Inn/IoT-Group-1-Mini-Project/blob/03a1d6292ad987619b3911938a6fdfa271052ebf/IoT%20Integration.png)

## IoT Integration & Communication

The system integrates multiple IoT platforms to enable remote monitoring and interaction.

### IoT Platforms

| Platform        | Description                          | User Capabilities |
|----------------|--------------------------------------|------------------|
| Blynk App      | ESP32 sends data via Blynk API       | View slots, monitor temperature & humidity, check system status |
| Web Dashboard  | Browser-based interface hosted by ESP32 | View real-time slots, gate status, environmental data |
| Telegram Bot   | Command-based messaging interface    | Send commands and interact with system |

---

### Communication Flow

| Component | Method Used            | Purpose |
|----------|------------------------|--------|
| Blynk    | Blynk API              | Send parking and environmental data |
| Web      | HTTP Requests          | Serve dashboard data |
| Telegram | Telegram Bot API       | Enable command-based interaction |

---

### User Access

| Access Method | Platform Used |
|--------------|--------------|
| Mobile App   | Blynk |
| Web Browser  | Web Dashboard |
| Messaging    | Telegram Bot |

## Working Process Explanation 
The system operates continuously through the following steps:
1. The ESP32 initializes and connects to WiFi
2. Sensors detect vehicle presence and parking occupancy
3. The system calculates available parking slots
4. If a vehicle arrives:
   * Gate opens if slots are available
   * Gate remains closed if parking is full
5. Exit sensor detects leaving vehicles and opens exit gate
6. Displays update parking information
7. Data is sent to IoT platforms
8. Users can monitor the system remotely
This process repeats in real time to ensure accurate and automated parking control.

## Smart Feature
![](https://github.com/Manita-Inn/IoT-Group-1-Mini-Project/blob/e4e89e5bdcca3371027a097438f5471125937fd6/Smart%20Feature.jpg)
One of the smart features of this system is automatic gate control based on parking slot availability. The system continuously monitors the parking slots using sensors. If all slots are occupied, the entrance gate will remain closed even when a vehicle approaches, preventing additional vehicles from entering the parking area. 

## Challenges Faced
During the development of the Smart Parking System, several challenges were encountered while integrating the hardware and software components.
* Brownout errors: These occurred when multiple components, especially the servo motors, consumed high current simultaneously, causing the microcontroller to reset.
* Unstable TM1637 connections: The TM1637 display occasionally experienced unstable connections due to loose pins, which caused the display to flicker or stop updating.
* Messy wiring: With multiple sensors and modules connected to the microcontroller, managing the wiring became challenging. Careful organization was required to prevent connection errors.
* LCD display issues: The LCD initially did not display any output, which required hardware adjustment using the onboard potentiometer (screw adjustment) to correctly set the screen contrast.
* Servo angle calibration: Determining the correct angle for the servo motors to properly open and close the gates required several tests and adjustments.
* System integration complexity: Integrating multiple systems including sensor code, Telegram communication, the Blynk IoT Platform, and the web dashboard into a single program caused delays and required extensive debugging.
* IR Sensor Testing: While testing the demo, the IR sensors must indicate the absence of sunlight, as they detect infrared light. In sunlight, the sensors activate both lights, so we have to find a location without sunlight to ensure the IR sensors operate accurately.

## Future Improvements
* Increasing parking capacity: The system can be expanded to support more parking slots by adding additional sensors and extending the detection logic.
* Camera-based vehicle detection: Integrating computer vision technology could allow the system to recognize vehicles and read license plates for more advanced parking management.
* More powerful microcontroller: Using a stronger microcontroller with higher processing power and better power management could improve system stability and performance.
* Smart lighting system: Installing lights around the parking area could improve energy efficiency. The lights would automatically turn off when no vehicles are present and turn on when a vehicle enters the parking lot.
