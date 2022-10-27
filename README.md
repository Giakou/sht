# Introduction
Python wrapper library of Adafruit_PureIO.smbus for Sensirion SHT85 sensors connected to I2c pins of a Raspberrry Pi. 
This library is object-oriented, which allows controlling of multiple SHT85 sensors. Since the hexadecimal address of
the SHT85 sensors cannot be changed, multiple I2C buses need to be configured to control multiple SHT85 sensors with
the same Raspberry Pi.

## Usage
An example of a periodic query is presented in **test_run_sht85.py**.  
The code is well documented and easy to read, so please have a look there for more information.
