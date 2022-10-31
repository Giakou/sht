#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
SHT85 Python wrapper library of Adafruit_PureIO.smbus
"""

from Adafruit_PureIO import smbus
import time
import math
import yaml
import functools


def hex_bytes(cmd):
    """Returns a list of hex bytes from hex number"""
    return [int(hex(b), 0) for b in divmod(cmd, 0x100)]


def temp(data):
    """Calculate temperature from data"""
    t = data[0] << 8 | data[1]
    # Significant digits based on the SHT85 resolution of 0.01 degrees Celsius
    return round(-45 + 175 * t / (2**16 - 1), 2)


def relative_humidity(data):
    """Calculate relative humidity from data"""
    rh = data[3] << 8 | data[4]
    # Significant digits based on the SHT85 resolution of 0.01 %RH
    return round(100 * rh / (2**16 - 1), 2)


def sn(data):
    """Extract S/N from data"""
    return data[0] << 16 | data[4]


def printer(func):
    """Decorator function to Inform the user that write/read command was successful"""
    @functools.wraps(func)
    def wrapper(self, **kwargs):
        func(self, **kwargs)
        print('Done!')
    return wrapper


class SHT85:
    """SHT85 class"""
    def __init__(self, bus, rep, mps):
        """Constructor"""

        # Open LUT with the command register addresses
        with open('sht85_cmd_register_lut.yaml', 'r') as file:
            self._lut = yaml.safe_load(file)

        # Assertion checks
        assert bus not in [0, 2], f'Bus number "{bus}" is not allowed, because they are reserved! Choose another one! '
        assert rep in self._lut['single_shot'].keys(), f'Repetition number "{rep}" is not allowed, ' \
                                                       'only "high", "medium" or "low"!'
        assert mps in self._lut['periodic'].keys(), f'Measurements per second number "{mps}" is not allowed, ' \
                                                    'only "0.5", "1", "2", "4", "10"!'

        # Define properties
        self.bus = smbus.SMBus(bus)
        self.rep = rep
        self.mps = mps

    def write_i2c_block_data_sht85(self, cmd):
        """Wrapper function for writing block data to SHT85 sensor"""
        self.bus.write_i2c_block_data(self._lut['address'], hex_bytes(cmd)[0], hex_bytes(cmd)[1:])

    def read_i2c_block_data_sht85(self, length=32):
        """Wrapper function for reading block data from SHT85 sensor"""
        return self.bus.read_i2c_block_data(self._lut['address'], self._lut['read'], length)

    def read_data(self, length=6):
        """Readout data for Periodic Mode or ART feature"""
        data = self.read_i2c_block_data_sht85(length)
        return temp(data), relative_humidity(data)

    def single_shot(self):
        """Single Shot Data Acquisition Mode"""
        self.write_i2c_block_data_sht85(self._lut['single_shot'][self.rep])
        time.sleep(0.5)
        self.read_data()

    @printer
    def periodic(self):
        """Start Periodic Data Acquisition Mode"""
        print(f'Initiating Periodic Data Acquisition with frequency of "{self.mps} Hz" and "{self.rep}" repetition...')
        self.write_i2c_block_data_sht85(self._lut['periodic'][self.mps][self.rep])
        time.sleep(0.5e-3)

    @printer
    def art(self):
        """Start the Accelerated Response Time (ART) feature"""
        print('Activating Accelerated Response Time (ART)...')
        self.write_i2c_block_data_sht85(self._lut['acc_resp_time'])

    @printer
    def stop(self):
        """Break command to stop Periodic Data Acquisition Mode or ART feature"""
        print('Stopping Periodic Data Acquisition...')
        self.write_i2c_block_data_sht85(self._lut['stop'])

    @printer
    def reset(self):
        """Apply Soft Reset"""
        print('Applying Soft Reset...')
        self.write_i2c_block_data_sht85(self._lut['soft_reset'])

    @printer
    def heater(self, heat='enable'):
        """Enable/disable heater"""
        print(f'{heat} heater...')
        assert heat in self._lut['heater'].keys(), 'You can only "enable" or "disable" the heater!'
        self.write_i2c_block_data_sht85(self._lut['heater'][heat])

    def status(self):
        """Read Status Register"""
        self.write_i2c_block_data_sht85(self._lut['status'])
        time.sleep(0.5e-3)
        status_read = self.read_i2c_block_data_sht85(3)
        status_to_bit = bin(status_read[0] << 8 | status_read[1])
        status_dict = {
            'checksum status': status_to_bit[0],
            'Command status': status_to_bit[1],
            'System reset': status_to_bit[4],
            'T tracking alert': status_to_bit[10],
            'RH tracking alert': status_to_bit[11],
            'Heater status': status_to_bit[13],
            'Alert pending status': status_to_bit[15]
        }
        return status_dict

    @printer
    def clear(self):
        """Clear Status Register"""
        print('Clearing Register Status...')
        self.write_i2c_block_data_sht85(self._lut['clear_status'])

    def sn(self):
        """Output of the serial number"""
        self.write_i2c_block_data_sht85(self._lut['sn'])
        time.sleep(0.5e-3)
        data = self.read_i2c_block_data_sht85(6)
        return sn(data)

    def dew_point(self, t, rh):
        """Calculate dew point from temperature and relative humidity"""
        t_range = 'water' if t >= 0 else 'ice'
        tn = dict(water=243.12, ice=272.62)[t_range]
        m = dict(water=17.62, ice=22.46)[t_range]

        dew_p = tn * (math.log(rh / 100.0) + (m * t) / (tn + t)) / (m - math.log(rh / 100.0) - m * t / (tn + t))
        return round(dew_p, 4)
