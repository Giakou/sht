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
    print('serial number = ', mysensor.sn)

    try:
        while True:
            # Single shot mode is preferred due to less current consumption (x8-x200) in idle state
            mysensor.single_shot()
            print(f'Temperature = {mysensor.t} °C')
            print(f'Relative Humidity = {mysensor.rh}%')
            print(f'Dew Point = {mysensor.dp} °C')
            time.sleep(mysensor.mps)

    except (KeyboardInterrupt, SystemExit):
        print("Killing Thread...")
    finally:
        mysensor.stop()
