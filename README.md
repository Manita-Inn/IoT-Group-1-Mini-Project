# IoT-Group1-Mini-Project

## Introduction
The Smart Parking System is an Internet of Things (IoT) solution designed to improve parking management by automatically detecting vehicle presence and controlling parking gates. The system uses an ESP32 microcontroller connected to multiple sensors and actuators to monitor parking availability and manage entry and exit gates.

The system provides real-time parking information through multiple interfaces, including a web dashboard, a mobile application using Blynk IoT Platform, and a notification system through Telegram. By integrating sensors, automation and cloud communication, the system improves parking efficiency and reduces the time drivers spend searching for available parking spaces. 

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

The Smart Parking System is designed using an IoT-based architecture where sensors collect real-time data, the microcontroller processes the information, and multiple platforms allow monitoring and control.
![](https://github.com/Manita-Inn/IoT-Group-1-Mini-Project/blob/487d83e3aa27cbdd059c3cbaf850ad3486605011/System%20Architecture.png)

The system consists of four main layers: sensing layer, processing layer, communication layer, and application layer.

**1. Sensing Layer**
> The sensing layer consists of multiple sensors responsible for collecting environmental and operational data from the parking area. These sensors continuously provide input to the ESP32 microcontroller.
* **Ultrasonic Sensor:** Vehicle Detection
> The ultrasonic sensor is installed at the parking entrance to detect incoming vehicles. The sensor measures the distance between itself and an object by sending ultrasonic sound waves and measuring the echo time. Inside the system, it performs the following tasks:
  1. Detects when a vehicle approaches the parking entrance
  2. Triggers the gate opening process if parking slots are available
  3. Prevents unnecessary gate opening when no vehicle is present
  > Operational Logic:
  1. The sensor continuously measures distance.
  2. If the detected distance is less than 10 cm, a vehicle is considered present.
  3. The system then checks parking slot availability.
  4. If a slot is available, the gate opens automatically.
  5. This allows the parking system to operate without manual intervention.

* **IR Sensor:** Parking Slot Detection
> Three IR sensors are installed at each parking slot to detect whether a vehicle is occupying the slot. Function in the System:
  1. Monitor individual parking spaces
  2. Determine the number of available parking slots
  3. Update the parking slot display
  4. Provide real-time information to the web dashboard and Blynk application
  > Operational Logic:
  1. Sensor Value is 0 > Slot is empty
  2. Sensor Value is 1 > Slot is Occupied

* **DHT11 Sensor:** Environmental Monitoring
> The DHT11 sensor measures temperature and humidity in the parking environment. Although it is not required for parking operations, it provides useful environmental data for monitoring the parking area. The data is used for:
  1. Displaying environmental conditions on the LCD screen
  2. Sending temperature and humidity data to the Blynk application
  3. Providing environmental monitoring through Telegram commands



**2. Processing Layer**

**3. Actuation Layer**

**4. IoT Communication Layer**






## Software Architecture 
!()[https://github.com/Manita-Inn/IoT-Group-1-Mini-Project/blob/51471eebc59868aa3f48107e3c81660432b93f3c/Software%20Architecture.png]

## IoT integration 

## Working Process Explanation 

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
