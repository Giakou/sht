#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
SHT85 Python wrapper library of smbus2
"""

import time
import os
import yaml
import functools
import warnings

import conversion_utils as cu
import sht
import smbus2

warnings.simplefilter('always')


def printer(func):
    """Decorator function to Inform the user that write/read command was successful"""
    @functools.wraps(func)
    def wrapper(self, **kwargs):
        func(self, **kwargs)
        print('Done!')
    return wrapper


class SHT85(sht.SHT):
    """SHT85 class"""
    def __init__(self, bus, rep, mps):
        """Constructor"""
        super().__init__('sht85_cmd_register_lut.yaml', bus)

        self._addr = 0x44
        # Assertion checks
        assert rep in self._lut['single_shot'].keys(), f'Repetition number "{rep}" is not allowed, ' \
                                                       'only "high", "medium" or "low"!'
        assert mps in self._lut['periodic'].keys(), f'Measurements per second number "{mps}" is not allowed, ' \
                                                    'only "0.5", "1", "2", "4", "10"!'

        self.rep = rep
        self.mps = mps
        self.t = None
        self.rh = None
        self.dp = None

    def __enter__(self):
        """Enter handler"""
        return self

    def __exit__(self):
        """Exit handler"""
        self.close()

    def close(self):
        """Close the I2C connection"""
        self.bus.close()

    @property
    def sn(self):
        return self._sn(cmd=0x3682)

    @property
    def status(self):
        """Read Status Register"""
        self.write_i2c_block_data_sht(self._lut['status'])
        status_read = self.read_i2c_block_data_sht(3)
        status = status_read[0] << 8 | status_read[1]
        status_to_bit = f'{status:016b}'
        status_dict = {
            'Checksum status': status_to_bit[0],
            'Command status': status_to_bit[1],
            'System reset': status_to_bit[4],
            'T tracking alert': status_to_bit[10],
            'RH tracking alert': status_to_bit[11],
            'Heater status': status_to_bit[13],
            'Alert pending status': status_to_bit[15]
        }
        return status_dict

    def check_status_for_non_default(self):
        """Check Status Register for non-default values"""
        status = self.status
        default_status_dict = {
            'Checksum status': '0',
            'Command status': '0',
            'System reset': '0',
            'T tracking alert': '0',
            'RH tracking alert': '0',
            'Heater status': '0',
            'Alert pending status': '0'
        }
        non_default_status_dict = {key: value for key, value in status.items() if value != default_status_dict[key]}
        for key, value in non_default_status_dict.items():
            if key == 'Checksum status':
                warnings.warn('Checksum of last write transfer failed!')
            elif key == 'Command status':
                warnings.warn('Last command not processed! It was either invalid or failed the integrated command '
                              'checksum!')
            elif key == 'System reset':
                warnings.warn('no reset detected since last "clearstatus register" command!')
            elif key == 'T tracking alert':
                warnings.warn('T tracking alert!')
            elif key == 'RH tracking alert':
                warnings.warn('RH tracking alert!')
            elif key == 'Heater status':
                warnings.warn('Heater is ON!')
            elif key == 'Alert pending status':
                warnings.warn('At least one pending alert!')

    def read_data(self):
        """Readout data for Periodic Mode or ART feature and update the properties"""
        # The measurement data consists of 6 bytes (2 for each measurement value and 1 for each checksum)
        self.data = self.read_i2c_block_data_sht(6)
        temp_digital = self.data[0] << 8 | self.data[1]
        self.t = cu.temp(temp_digital)
        rh_digital = self.data[3] << 8 | self.data[4]
        self.rh = cu.relative_humidity(rh_digital)
        self.check_crc(self.data)
        self.dp = cu.dew_point(self.t, self.rh)

    def crc8(self, buffer):
        """CRC-8 checksum calculation from data"""
        # Initialize the checksum with a byte full of 1s
        crc = 0xFF
        # Polynomial to divide with
        polynomial = 0x131
        for byte in buffer:
            # Perform XOR operation between the crc and the byte
            crc ^= byte
            for _ in range(8):
                # Extract the leftmost bit of the CRC register
                bit = crc & 0x80
                # Shift the crc register by one bit to the left
                crc <<= 1
                # If leftmost bit is 1 perform XOR between CRC and polynomial
                if bit:
                    crc ^= polynomial
            # Mask the original value to ensure that it remains within the range of 8 bits (final XOR)
            crc ^= 0x00
        return crc

    def single_shot(self):
        """Single Shot Data Acquisition Mode"""
        self.write_i2c_block_data_sht(self._lut['single_shot'][self.rep])
        self.read_data()

    @printer
    def periodic(self):
        """Start Periodic Data Acquisition Mode"""
        print(f'Initiating Periodic Data Acquisition with frequency of "{self.mps} Hz" and "{self.rep}" repetition...')
        self.write_i2c_block_data_sht(self._lut['periodic'][self.mps][self.rep])

    @printer
    def fetch(self):
        """Fetch command to transmit the measurement data. After the transmission the data memory is cleared"""
        print('Fetching data...')
        self.write_i2c_block_data_sht(0xE000)

    @printer
    def art(self):
        """Start the Accelerated Response Time (ART) feature"""
        print('Activating Accelerated Response Time (ART)...')
        self.write_i2c_block_data_sht(0x2B32)

    @printer
    def stop(self):
        """Break command to stop Periodic Data Acquisition Mode or ART feature"""
        print('Issuing Break Command...')
        self.write_i2c_block_data_sht(0x3093)

    @printer
    def reset(self):
        """Apply Soft Reset"""
        self.stop()
        print('Applying Soft Reset...')
        self.write_i2c_block_data_sht(0x30A2)

    @printer
    def enable_heater(self):
        """Enable heater"""
        print('Enabling heater...')
        self.write_i2c_block_data_sht(0x306D)

    @printer
    def disable_heater(self):
        """Disable heater"""
        print('Disabling heater...')
        self.write_i2c_block_data_sht(0x3066)

    @printer
    def clear_status(self):
        """Clear Status Register"""
        print('Clearing Status Register...')
        self.write_i2c_block_data_sht(0x3041)
