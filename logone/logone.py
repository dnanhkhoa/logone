#!/usr/bin/python
# -*- coding: utf-8 -*-
import json
import logging
import os
import sys
import traceback
from io import StringIO
from logging import handlers

import colorama
import coloredlogs
import requests
from requests import RequestException

# Initialize color mode for terminal if possible
colorama.init()

# Store default standard IO streams after initialization
_original_stdout = sys.stdout
_original_stderr = sys.stderr


class LogOne(object):
    def __init__(self, logger_name,
                 level=logging.WARNING,
                 use_colors=True,
                 log_format=None,
                 date_format=None,
                 level_styles=None,
                 field_styles=None):
        """
        Initialize the logger with a name and an optional level.

        :param logger_name: The name of the logger.
        :param level: The default logging level.
        :param use_colors: Use ColoredFormatter class for coloring logs or not.
        :param log_format: Use the specified format string for the handler.
        :param date_format: Use the specified date/time format.
        :param level_styles: A dictionary with custom level styles.
        :param field_styles: A dictionary with custom field styles.
        """
        # For initializing Logger instance
        self.logger = logging.getLogger(logger_name)

        if not log_format:
            log_format = '%(asctime)s.%(msecs)03d %(name)s[%(process)d] ' \
                         '%(programname)s/%(module)s/%(funcName)s[%(lineno)d] ' \
                         '%(levelname)s %(message)s'

        coloredlogs.install(level=level,
                            logger=self.logger,
                            fmt=log_format,
                            datefmt=date_format,
                            level_styles=level_styles,
                            field_styles=field_styles,
                            isatty=use_colors,
                            stream=_original_stderr)

        # For standard IO streams
        self.__stdout_wrapper = None
        self.__stderr_wrapper = None
        self.__stdout_stream = _original_stdout
        self.__stderr_stream = _original_stderr

        # For handlers
        self.__file_handler = None
        self.__loggly_handler = None
        self.__coloredlogs_handlers = list(self.logger.handlers)

        # Inherit methods from Logger class
        self.name = self.logger.name
        self.add_handler = self.logger.addHandler
        self.remove_handler = self.logger.removeHandler
        self.add_filter = self.logger.addFilter
        self.remove_filter = self.logger.removeFilter
        self.log = self.logger.log
        self.debug = self.logger.debug
        self.info = self.logger.info
        self.warning = self.logger.warning
        self.error = self.logger.error
        self.exception = self.logger.exception
        self.critical = self.logger.critical

    def set_level(self, level):
        """
        Set the logging level of this logger.

        :param level: must be an int or a str.
        """
        for handler in self.__coloredlogs_handlers:
            handler.setLevel(level=level)

        self.logger.setLevel(level=level)

    def disable_logger(self, disabled=True):
        """
        Disable all logging calls.
        """
        # Disable standard IO streams
        if disabled:
            sys.stdout = _original_stdout
            sys.stderr = _original_stderr
        else:
            sys.stdout = self.__stdout_stream
            sys.stderr = self.__stderr_stream

        # Disable handlers
        self.logger.disabled = disabled

    def redirect_stdout(self, enabled=True, log_level=logging.INFO):
        """
        Redirect sys.stdout to file-like object.
        """
        if enabled:
            if self.__stdout_wrapper:
                self.__stdout_wrapper.update_log_level(log_level=log_level)
            else:
                self.__stdout_wrapper = StdOutWrapper(logger=self.logger, log_level=log_level)

            self.__stdout_stream = self.__stdout_wrapper
        else:
            self.__stdout_stream = _original_stdout

        # Assign the new stream to sys.stdout
        sys.stdout = self.__stdout_stream

    def redirect_stderr(self, enabled=True, log_level=logging.ERROR):
        """
        Redirect sys.stderr to file-like object.
        """
        if enabled:
            if self.__stderr_wrapper:
                self.__stderr_wrapper.update_log_level(log_level=log_level)
            else:
                self.__stderr_wrapper = StdErrWrapper(logger=self.logger, log_level=log_level)

            self.__stderr_stream = self.__stderr_wrapper
        else:
            self.__stderr_stream = _original_stderr

        # Assign the new stream to sys.stderr
        sys.stderr = self.__stderr_stream

    def use_file(self, enabled=True,
                 file_name=None,
                 level=logging.WARNING,
                 when='d',
                 interval=1,
                 backup_count=30,
                 delay=False,
                 utc=False,
                 at_time=None,
                 log_format=None,
                 date_format=None):
        """
        Handler for logging to a file, rotating the log file at certain timed intervals.
        """
        if enabled:
            if not self.__file_handler:
                assert file_name, 'File name is missing!'

                # Create new TimedRotatingFileHandler instance
                self.__file_handler = TimedRotatingFileHandler(filename=file_name,
                                                               when=when,
                                                               interval=interval,
                                                               backupCount=backup_count,
                                                               encoding='UTF-8',
                                                               delay=delay,
                                                               utc=utc,
                                                               atTime=at_time)

                # Use this format for default case
                if not log_format:
                    log_format = '%(asctime)s %(name)s[%(process)d] ' \
                                 '%(programname)s/%(module)s/%(funcName)s[%(lineno)d] ' \
                                 '%(levelname)s %(message)s'

                # Set formatter
                formatter = logging.Formatter(fmt=log_format, datefmt=date_format)
                self.__file_handler.setFormatter(fmt=formatter)

                # Set level for this handler
                self.__file_handler.setLevel(level=level)

                # Add this handler to logger
                self.add_handler(hdlr=self.__file_handler)
        elif self.__file_handler:
            # Remove handler from logger
            self.remove_handler(hdlr=self.__file_handler)
            self.__file_handler = None

    def use_loggly(self, enabled=True,
                   loggly_token=None,
                   loggly_tag=None,
                   level=logging.WARNING,
                   log_format=None,
                   date_format=None):
        """
        Enable handler for sending the record to Loggly service.
        """
        if enabled:
            if not self.__loggly_handler:
                assert loggly_token, 'Loggly token is missing!'

                # Use logger name for default Loggly tag
                if not loggly_tag:
                    loggly_tag = self.name

                # Create new LogglyHandler instance
                self.__loggly_handler = LogglyHandler(token=loggly_token, tag=loggly_tag)

                # Use this format for default case
                if not log_format:
                    log_format = '{"name":"%(name)s","process":"%(process)d",' \
                                 '"levelname":"%(levelname)s","time":"%(asctime)s",' \
                                 '"filename":"%(filename)s","programname":"%(programname)s",' \
                                 '"module":"%(module)s","funcName":"%(funcName)s",' \
                                 '"lineno":"%(lineno)d","message":"%(message)s"}'

                # Set formatter
                formatter = logging.Formatter(fmt=log_format, datefmt=date_format)
                self.__loggly_handler.setFormatter(fmt=formatter)

                # Set level for this handler
                self.__loggly_handler.setLevel(level=level)

                # Add this handler to logger
                self.add_handler(hdlr=self.__loggly_handler)
        elif self.__loggly_handler:
            # Remove handler from logger
            self.remove_handler(hdlr=self.__loggly_handler)
            self.__loggly_handler = None

    def __repr__(self):
        return self.logger.__repr__()


class TimedRotatingFileHandler(handlers.TimedRotatingFileHandler):
    """
    Handler for logging to a file, rotating the log file at certain timed intervals.

    If backupCount is > 0, when rollover is done, no more than backupCount
    files are kept - the oldest ones are deleted.
    """

    def _open(self):
        # Create directories to contain log files if necessary
        os.makedirs(os.path.dirname(self.baseFilename), exist_ok=True)
        return super()._open()


class LogglyHandler(logging.Handler):
    def __init__(self, token, tag):
        self.__loggly_api = 'https://logs-01.loggly.com/inputs/%s/tag/%s' % (token, tag)

        super().__init__()

    def emit(self, record):
        # Replace message with exception info
        if record.exc_info:
            msg = str(record.msg) + '\n'
            msg += ''.join(traceback.format_exception(*record.exc_info))
            record.msg = json.dumps(msg)[1: -1]
            record.exc_info = None

        # Format the record
        formatted_record = self.format(record=record)

        # Post the record to Loggly
        try:
            response = requests.post(url=self.__loggly_api, data=formatted_record, timeout=30)
            assert response.status_code == requests.codes.ok, 'Log sending failed!'
            assert response.content == b'{"response" : "ok"}', 'Log sending failed!'
        except (RequestException, AssertionError):
            self.handleError(record=record)


class StdOutWrapper(object):
    """
    Fake file-like stream object that redirects stdout to a logger instance.
    """

    def __init__(self, logger, log_level=logging.INFO):
        self.__logger = logger
        self.__log_level = log_level

    def update_log_level(self, log_level=logging.INFO):
        """
        Update the logging level of this stream.
        """
        self.__log_level = log_level

    def write(self, buffer):
        """
        Write the given buffer to log.
        """
        buffer = buffer.strip()
        # Ignore the empty buffer
        if len(buffer) > 0:
            # Flush messages after log() called
            self.__logger.log(level=self.__log_level, msg=buffer)

    def flush(self, *args, **kwargs):
        # No-op for wrapper
        pass


class StdErrWrapper(object):
    """
    Fake file-like stream object that redirects stderr to a logger instance.
    """

    def __init__(self, logger, log_level=logging.ERROR):
        self.__logger = logger
        self.__log_level = log_level
        self.__buffer = StringIO()

    def update_log_level(self, log_level=logging.ERROR):
        """
        Update the logging level of this stream.
        """
        self.__log_level = log_level

    def write(self, buffer):
        """
        Write the given buffer to the temporary buffer.
        """
        self.__buffer.write(buffer)

    def flush(self):
        """
        Flush the buffer, if applicable.
        """
        if self.__buffer.tell() > 0:
            # Write the buffer to log
            self.__logger.log(level=self.__log_level, msg=self.__buffer.getvalue())
            # Remove the old buffer
            self.__buffer.truncate(0)
            self.__buffer.seek(0)
