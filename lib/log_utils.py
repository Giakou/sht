#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
WIP
"""

import logging

COLORS = {
    'CRITICAL': '\x1b[31;1m',  # bold red
    'FATAL': '\x1b[31;1m',  # bold red
    'ERROR': '\x1b[31;20m',  # red
    'WARNING': '\x1b[33;20m',  # yellow
    'WARN': '\x1b[33;20m',  # yellow
    'INFO': '\x1b[0;34m',  # blue
    'DEBUG': '\x1B[32m',  # green
    'RESET': '\033[0m',
    'GRAY': '\033[90m',
    'GREEN': '\x1B[32m'
}


class ColoredFormatter(logging.Formatter):
    def format(self, record):
        message = record.getMessage()
        message_color = COLORS[record.levelname] + message + COLORS['RESET']
        record.msg = message_color
        # Set the color via the attribute, because record.asctime is formatted again internally
        # without the color because self.usesTime() == True
        self.datefmt = COLORS['GREEN'] + '%m/%d/%Y %I:%M:%S'
        record.asctime = self.formatTime(record, self.datefmt) + COLORS['RESET']
        levelname = record.levelname
        record.levelname = COLORS['GRAY'] + levelname + COLORS['RESET']
        return super().format(record)


def get_logger(loglevel='INFO'):
    logger = logging.getLogger()
    try:
        logger.setLevel(eval(f'logging.{loglevel}'))
    except AttributeError:
        logger.setLevel(logging.INFO)
    # create console handler with a higher log level
    ch = logging.StreamHandler()
    try:
        ch.setLevel(eval(f'logging.{loglevel}'))
    except AttributeError:
        ch.setLevel(logging.INFO)
    ch.setFormatter(ColoredFormatter(fmt='{asctime} {levelname} {message}', datefmt='%m/%d/%Y %I:%M:%S', style='{'))
    # Check if the logger has handlers already before adding one
    if logger.hasHandlers():
        logger.handlers.clear()
    logger.addHandler(ch)
    return logger