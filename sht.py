#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import yaml
import time
import smbus2

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

    @property
    def lut(self):
        """Get the LUT with the cmd register addresses"""
        return self._lut

    @property
    def bus(self):
        """Get the smbus instance"""
        return self._bus

    @property
    def _sn(self, sn_register, crc_check=True):
        """Output of the serial number"""
        buffer = self.read_i2c_block_data(self._addr, sn_register, 6)
        self.check_crc(buffer, kw='sn')
        return (buffer[0] << 24) + (buffer[1] << 16) + (buffer[3] << 8) + buffer[4]

    def write_i2c_block_data_sht(self, slave_addr, register, data):
        """Wrapper function for writing block data to SHT85 sensor"""
        self.bus.write_i2c_block_data(slave_addr, register, data)
        time.sleep(cu.WT[self.rep])

    def interface_reset(self, addr):
        print('Interface reset...')
        # Toggling SDA
        for i in range(9):
            self.bus.write_byte(addr, 0xFF)
            time.sleep(0.01)

        # Send the Start sequence before the next command
        self.bus.write_byte(addr, 0x35)
        self.bus.write_byte(addr, 0x17)

