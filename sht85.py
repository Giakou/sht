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
        super().__init__()
        # Open LUT with the command register addresses
        with open(os.path.join(os.path.dirname(__file__), 'sht85_cmd_register_lut.yaml'), 'r') as file:
            self._lut = yaml.safe_load(file)

        # Assertion checks
        assert bus not in [0, 2], f'Bus number "{bus}" is not allowed, because they are reserved! Choose another one! '
        assert rep in self._lut['single_shot'].keys(), f'Repetition number "{rep}" is not allowed, ' \
                                                       'only "high", "medium" or "low"!'
        assert mps in self._lut['periodic'].keys(), f'Measurements per second number "{mps}" is not allowed, ' \
                                                    'only "0.5", "1", "2", "4", "10"!'

        # Define properties
        self.bus = smbus2.SMBus(bus)
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
        """Output of the serial number"""
        self.write_i2c_block_data_sht85(self._lut['sn'])
        buffer = self.read_i2c_block_data_sht85(6)
        self.check_crc(buffer, kw='sn')
        return (buffer[0] << 24) + (buffer[1] << 16) + (buffer[3] << 8) + buffer[4]

    @property
    def status(self):
        """Read Status Register"""
        self.write_i2c_block_data_sht85(self._lut['status'])
        status_read = self.read_i2c_block_data_sht85(3)
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
            'System reset': '1',
            'T tracking alert': '0',
            'RH tracking alert': '0',
            'Heater status': '0',
            'Alert pending status': '1'
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
                warnings.warn('No pending alerts!')

    def write_i2c_block_data_sht85(self, cmd):
        """Wrapper function for writing block data to SHT85 sensor"""
        self.bus.write_i2c_block_data(self._lut['address'], cu.hex_bytes(cmd)[0], cu.hex_bytes(cmd)[1:])
        time.sleep(cu.WT[self.rep])

    def read_i2c_block_data_sht85(self, length=32):
        """Wrapper function for reading block data from SHT85 sensor"""
        return self.bus.read_i2c_block_data(self._lut['address'], self._lut['read'], length)

    def read_data(self):
        """Readout data for Periodic Mode or ART feature and update the properties"""
        # The measurement data consists of 6 bytes (2 for each measurement value and 1 for each checksum)
        data = self.read_i2c_block_data_sht85(6)
        temp_digital = data[0] << 8 | data[1]
        self.t = cu.temp(temp_digital)
        rh_digital = data[3] << 8 | data[4]
        self.rh = cu.relative_humidity(rh_digital)
        self.check_crc(data)
        self.dp = cu.dew_point(self.t, self.rh)

    def crc8(self, buffer):
        """CRC-8 checksum verification"""
        # Initialize the checksum
        crc = 0xFF
        for byte in buffer:
            # Perform XOR operation between the crc and the byte
            crc ^= byte
            for _ in range(8):
                if crc & 0x80:
                    crc = (crc << 1) ^ 0x31
                else:
                    crc = crc << 1
            return crc & 0xFF  # return the bottom 8 bits

    def check_crc(self, buffer, kw='data'):
        if buffer[2] != self.crc8(buffer[0:2]):
            if kw == 'data':
                warnings.warn('CRC Error in temperature measurement!')
            else:
                warnings.warn('CRC Error in the first word!')
        if buffer[5] != self.crc8(buffer[3:5]):
            if kw == 'data':
                warnings.warn('CRC Error in relative humidity measurement!')
            else:
                warnings.warn('CRC Error in the second word!')

    def single_shot(self):
        """Single Shot Data Acquisition Mode"""
        self.write_i2c_block_data_sht85(self._lut['single_shot'][self.rep])
        self.read_data()

    @printer
    def periodic(self):
        """Start Periodic Data Acquisition Mode"""
        print(f'Initiating Periodic Data Acquisition with frequency of "{self.mps} Hz" and "{self.rep}" repetition...')
        self.write_i2c_block_data_sht85(self._lut['periodic'][self.mps][self.rep])

    @printer
    def fetch(self):
        """Fetch command to transmit the measurement data. After the transmission the data memory is cleared"""
        print('Fetching data...')
        self.write_i2c_block_data_sht85(self._lut['fetch'])

    @printer
    def art(self):
        """Start the Accelerated Response Time (ART) feature"""
        print('Activating Accelerated Response Time (ART)...')
        self.write_i2c_block_data_sht85(self._lut['acc_resp_time'])

    @printer
    def stop(self):
        """Break command to stop Periodic Data Acquisition Mode or ART feature"""
        print('Issuing Break Command...')
        self.write_i2c_block_data_sht85(self._lut['stop'])

    @printer
    def reset(self):
        """Apply Soft Reset"""
        self.stop()
        print('Applying Soft Reset...')
        self.write_i2c_block_data_sht85(self._lut['soft_reset'])

    @printer
    def general_call_reset(self):
        """General Call mode to rese all devices on the same I2C bus line (not device specific!). This command only
        works if the device is able to process I2C commands."""
        print('Applying General Call Reset... This is not device specific!')
        # TODO: Does SHT85 actually support receiving commands via the I2C broadcast address? The line below should
        #  work, but it does not
        self.bus.write_byte(self._lut['general_call_reset']['address'], self._lut['general_call_reset']['second_byte'])

    @printer
    def heater(self, heat='enable'):
        """Enable/disable heater"""
        print(f'{heat} heater...')
        assert heat in self._lut['heater'].keys(), 'You can only "enable" or "disable" the heater!'
        self.write_i2c_block_data_sht85(self._lut['heater'][heat])

    @printer
    def clear(self):
        """Clear Status Register"""
        print('Clearing Register Status...')
        self.write_i2c_block_data_sht85(self._lut['clear_status'])
