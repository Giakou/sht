#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test script for basic SHT85 functionality
"""

import sht85
import time

if __name__ == '__main__':
    # Create SHT85 object
    mysensor = sht85.SHT85(bus=1, mps=1, rep='high')

    # Check S/N
    print('serial number = ', mysensor.sn())
    time.sleep(0.5e-3)

    # Start periodic measurement
    mysensor.periodic()
    time.sleep(1)

    try:
        while True:
            t, rh = mysensor.read_data()
            dp = mysensor.dew_point(t, rh)
            print(f'Temperature = {t} deg')
            print(f'Relative Humidity = {rh}%')
            print(f'Dew Point = {dp} degrees')
            time.sleep(mysensor.mps)

    except (KeyboardInterrupt, SystemExit):
        print("Killing Thread...")
        time.sleep(0.5e-3)
    finally:
        mysensor.stop()
