#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

import sys
import threading
from logging import CRITICAL, FATAL, ERROR, WARNING, WARN, INFO, DEBUG, NOTSET

from .logone import LogOne

# Customize print function to support automatic stdout flushing for Python 3
if sys.version_info[:2] >= (3, 3):
    import builtins
    import functools

    builtins.print = functools.partial(print, flush=True)

# Export functions
__all__ = ['levels', 'get_logger', 'logger', 'add_handler', 'remove_handler',
           'add_filter', 'remove_filter', 'log', 'debug', 'info', 'warning',
           'error', 'exception', 'critical', 'set_level', 'disable_logger',
           'redirect_stdout', 'redirect_stderr', 'use_file', 'use_loggly']

# Information
__author__ = "Duong Nguyen Anh Khoa <dnanhkhoa@live.com>"
__status__ = "production"
__date__ = "15 January 2018"

# Private variables
__instance = LogOne(logger_name=__name__)

__loggers = {__name__: __instance}

__lock = threading.Lock()

# Public variables and functions
levels = [CRITICAL, FATAL, ERROR, WARNING, WARN, INFO, DEBUG, NOTSET]

logger = __instance.logger
add_handler = __instance.add_handler
remove_handler = __instance.remove_handler
add_filter = __instance.add_filter
remove_filter = __instance.remove_filter
log = __instance.log
debug = __instance.debug
info = __instance.info
warning = __instance.warning
error = __instance.error
exception = __instance.exception
critical = __instance.critical
set_level = __instance.set_level
disable_logger = __instance.disable_logger
redirect_stdout = __instance.redirect_stdout
redirect_stderr = __instance.redirect_stderr
use_file = __instance.use_file
use_loggly = __instance.use_loggly


def get_logger(logger_name):
    """
    Return a logger with the specified name, creating it if necessary.
    """

    # Use default global logger
    if logger_name is None:
        return __instance

    assert isinstance(logger_name, str), 'Logger name must be a string!'

    with __lock:
        if logger_name in __loggers:
            return __loggers[logger_name]

        logger_instance = LogOne(logger_name=logger_name)
        __loggers[logger_name] = logger_instance
        return logger_instance
