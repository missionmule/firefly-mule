# Hardware System Tests
This code is made to conduct system-level tests on the BirdsEyeView payload. Right Using an Arduino, the BirdsEyeView FireFly6 Pro is emulated in order to simulate a flight from the perspective of the Payload's Raspberry Pi.

## Materials

* Arduino
* Jumper Wires
* Power Supply

## Test Setup

1) Connect payload to 5V power, ensuring at least 2A current supply.
2) Connect the UART pins of the payload to the Arduino 
    * Arduino RX (Pin 10) ---> RPi TX
    * Arduino TX (Pin 11) ---> RPi RX
3) Connect the payload's GND line to the Arduino's GND line.
4) Start the payloads software with `make run` in the firefly-mule directory.
5) Upload the desired .ino code to the Arduino and monitor the serial terminal.
    * The test duration can be edited at the top of the arduino sketch by changing the value of the `int testLength` variable.
