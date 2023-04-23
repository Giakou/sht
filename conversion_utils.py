#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Helper library for value conversion
"""

import math

# Magnus coefficients from
# https://sensirion.com/media/documents/8AB2AD38/61642ADD/Sensirion_AppNotes_Humidity_Sensors_Introduction_to_Relative_Humidit.pdf
MC = {
    'water': {
        'alpha': 6.112,  # in hPa
        'beta': 17.62,
        'lambda': 243.12  # in degrees Celsius
    },
    'ice': {
        'alpha': 6.112,  # in hPa
        'beta': 22.46,
        'lambda': 272.62  # in degrees Celsius
    }
}

# Waiting times based on repeatability setting in seconds
WT = {
    'high': 0.016,
    'medium': 0.007,
    'low': 0.005
}


def hex_to_bytes(cmd):
    """Returns a list of hex bytes from hex number"""
    return [int(hex(b), 0) for b in divmod(cmd, 0x100)]


def temp(temp_digital):
    """Calculate temperature from data"""
    # Significant digits based on the SHT85 resolution of 0.01 degrees Celsius
    return round(-45 + 175 * temp_digital / (2**16 - 1), 2)


def relative_humidity(rh_digital):
    """Calculate relative humidity from data"""
    # Significant digits based on the SHT85 resolution of 0.01 %RH
    rh_analog = round(100 * rh_digital / (2**16 - 1), 2)
    # Make sure that relative humidity never returns a 0% value, otherwise the dew point calculation will fail
    rh_analog = 1e-3 if rh_analog < 0.01 else rh_analog
    return rh_analog


def dew_point(t, rh):
    """Calculate dew point from temperature and relative humidity using Magnus formula. For more info:
    https://sensirion.com/media/documents/8AB2AD38/61642ADD/Sensirion_AppNotes_Humidity_Sensors_Introduction_to_Relative_Humidit.pdf"""

    t_range = 'water' if t >= 0 else 'ice'
    # Define some custom constants to make the Magnus formula more readable
    c1 = MC[t_range]['beta'] * t / (MC[t_range]['lambda'] + t)
    c2 = math.log(rh / 100.0)

    # Magnus formula for calculating the dew point
    dew_p = MC[t_range]['lambda'] * (c2 + c1) / (MC[t_range]['beta'] - c2 - c1)
    return round(dew_p, 2)
