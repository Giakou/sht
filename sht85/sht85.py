#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
SHT85 Python wrapper library of smbus2
"""

import functools

import lib.conversion_utils as cu
import log_utils
import sht

logger = log_utils.get_logger()


def printer(func):
    """Decorator function to Inform the user that write/read command was successful"""
    @functools.wraps(func)
    def wrapper(self, **kwargs):
        func(self, **kwargs)
        logger.debug('Done!')
    return wrapper


class SHT85(sht.SHT):
    """SHT85 class"""
    def __init__(self, bus, rep, mps):
        """Constructor"""
        super().__init__(bus)

        self._addr = 0x44
        # Assertion checks
        assert rep in ['high', 'medium', 'low'], f'Repetition number "{rep}" is not allowed, ' \
                                                 'only "high", "medium" or "low"!'
        assert mps in [0.5, 1, 2, 4, 10], f'Measurements per second number "{mps}" is not allowed, '\
                                          'only 0.5, 1, 2, 4, 10!'

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
        return self._sn(cmd=[0x36, 0x82])

    @sn.setter
    def sn(self, value):
        raise AttributeError("The S/N of the slave device is unique and cannot be modified!")

    @property
    def status(self):
        """Read Status Register"""
        self.write_i2c_block_data_sht([0xF3, 0x2D])
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
                logger.warning('Checksum of last write transfer failed!')
            elif key == 'Command status':
                logger.warning('Last command not processed! It was either invalid or failed the integrated command '
                              'checksum!')
            elif key == 'System reset':
                logger.warning('no reset detected since last "clearstatus register" command!')
            elif key == 'T tracking alert':
                logger.warning('T tracking alert!')
            elif key == 'RH tracking alert':
                logger.warning('RH tracking alert!')
            elif key == 'Heater status':
                logger.warningn('Heater is ON!')
            elif key == 'Alert pending status':
                logger.warning('At least one pending alert!')

    @sht.SHT.calculate_crc(kw='data')
    def read_data(self):
        """Readout data for Periodic Mode or ART feature and update the properties"""
        # The measurement data consists of 6 bytes (2 for each measurement value and 1 for each checksum)
        self.data = self.read_i2c_block_data_sht(6)
        temp_digital = self.data[0] << 8 | self.data[1]
        self.t = cu.temp(temp_digital)
        rh_digital = self.data[3] << 8 | self.data[4]
        self.rh = cu.relative_humidity(rh_digital)
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
        rep_code = {
            'high': [0x24, 0x00],
            'medium': [0x24, 0x0B],
            'low': [0x24, 0x16]
        }
        self.write_i2c_block_data_sht(rep_code[self.rep])
        self.read_data()

    @printer
    def periodic(self):
        """Start Periodic Data Acquisition Mode"""
        periodic_code = {
            0.5: {
                'high': [0x20, 0x32],
                'medium': [0x20, 0x24],
                'low': [0x20, 0x2F]
            },
            1: {
                'high': [0x21, 0x30],
                'medium': [0x21, 0x26],
                'low': [0x21, 0x2D]
            },
            2: {
                'high': [0x22, 0x36],
                'medium': [0x22, 0x20],
                'low': [0x22, 0x2B]
            },
            4: {
                'high': [0x23, 0x34],
                'medium': [0x23, 0x22],
                'low': [0x23, 0x29]
            },
            10: {
                'high': [0x27, 0x37],
                'medium': [0x27, 0x21],
                'low': [0x27, 0x2A]
            }
        }
        logger.debug(f'Initiating Periodic Data Acquisition with frequency of "{self.mps} Hz" and '
                    f'"{self.rep}" repetition...')
        self.write_i2c_block_data_sht(periodic_code[self.mps][self.rep])

    @printer
    def fetch(self):
        """Fetch command to transmit the measurement data. After the transmission the data memory is cleared"""
        logger.debug('Fetching data...')
        self.write_i2c_block_data_sht([0xE0, 0x00])

    @printer
    def art(self):
        """Start the Accelerated Response Time (ART) feature"""
        logger.info('Activating Accelerated Response Time (ART)...')
        self.write_i2c_block_data_sht([0x2B, 0x32])

    @printer
    def stop(self):
        """Break command to stop Periodic Data Acquisition Mode or ART feature"""
        logger.info('Issuing Break Command...')
        self.write_i2c_block_data_sht([0x30, 0x93])

    @printer
    def reset(self):
        """Apply Soft Reset"""
        self.stop()
        logger.debug('Applying Soft Reset...')
        self.write_i2c_block_data_sht([0x30, 0xA2])

    @printer
    def enable_heater(self):
        """Enable heater"""
        logger.warning('Enabling heater...')
        self.write_i2c_block_data_sht([0x30, 0x6D])

    @printer
    def disable_heater(self):
        """Disable heater"""
        logger.info('Disabling heater...')
        self.write_i2c_block_data_sht([0x30, 0x66])

    @printer
    def clear_status(self):
        """Clear Status Register"""
        logger.info('Clearing Status Register...')
        self.write_i2c_block_data_sht([0x30, 0x41])
