#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import yaml
import time
import smbus2
import functools
import warnings

import conversion_utils as cu


class SHT:

    def __init__(self, cmd_register_lut_yaml, bus):
        # Open LUT with the command register addresses
        with open(os.path.join(os.path.dirname(__file__), cmd_register_lut_yaml), 'r') as file:
            self._lut = yaml.safe_load(file)

        # Assertion checks
        assert bus not in [0, 2], f'Bus number "{bus}" is not allowed, because they are reserved! Choose another one! '

        # Define properties
        self._bus = smbus2.SMBus(bus)
        self._addr = None
        self.check_crc_bool = True

    def calculate_crc(method, kw):
        """Decorator function to check crc"""
        @functools.wraps(method)
        def wrapper(self, **kwargs):
            method(self, **kwargs)
            if self.check_crc_bool:
                self.check_crc(kw)
        return wrapper

    def crc8(self):
        raise NotImplementedError('This function needs to be overwritten by the child class!')

    def check_crc(self, kw='data'):
        """CRC-8 checksum verification"""
        if self.data[2] != self.crc8(self.data[0:2]):
            if kw == 'data':
                warnings.warn('CRC Error in temperature measurement!')
            else:
                warnings.warn('CRC Error in the first word!')
        if self.data[5] != self.crc8(self.data[3:5]):
            if kw == 'data':
                warnings.warn('CRC Error in relative humidity measurement!')
            else:
                warnings.warn('CRC Error in the second word!')
        if self.data[2] == self.crc8(self.data[0:2]) and self.data[5] == self.crc8(self.data[3:5]):
            print('CRC is good')

    @property
    def lut(self):
        """Get the LUT with the cmd register addresses"""
        return self._lut

    @property
    def bus(self):
        """Get the smbus instance"""
        return self._bus

    @property
    def addr(self):
        """Get the slave address instance"""
        return self._addr

    @addr.setter
    def addr(self):
        """Get the slave address instance"""
        raise AttributeError("The hex address of the slave device is fixed and cannot be modified!")

    @calculate_crc(kw='sn')
    def _sn(self, cmd):
        """Output of the serial number"""
        self.write_i2c_block_data_sht(cmd)
        self.data = self.read_i2c_block_data_sht(6)
        return (self.data[0] << 24) + (self.data[1] << 16) + (self.data[3] << 8) + self.data[4]

    def read_i2c_block_data_sht(self, length=32):
        return self.bus.read_i2c_block_data(self.addr, 0x00, length)

    def write_i2c_block_data_sht(self, cmd):
        """Wrapper function for writing block data to SHT85 sensor"""
        cmd = cu.hex_to_bytes(cmd)
        self.bus.write_i2c_block_data(self.addr, register=cmd[0], data=cmd[1:])
        time.sleep(cu.WT[self.rep])

    def general_call_reset(self):
        """General Call mode to rese all devices on the same I2C bus line (not device specific!). This command only
        works if the device is able to process I2C commands."""
        print('Applying General Call Reset... This is not device specific!')
        self.bus.write_byte(0x00, 0x06)

    def interface_reset(self, addr):
        print('Interface reset...')
        # Toggling SDA
        for i in range(9):
            self.bus.write_byte(addr, 0xFF)
            time.sleep(0.01)

        # Send the Start sequence before the next command
        self.bus.write_byte(addr, 0x35)
        self.bus.write_byte(addr, 0x17)

