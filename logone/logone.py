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

_logone_src = os.path.normpath(os.path.dirname(os.path.abspath(__file__)))


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
                self.__stdout_wrapper = StdOutWrapper(logger=self, log_level=log_level)

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
                self.__stderr_wrapper = StdErrWrapper(logger=self, log_level=log_level)

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
                kwargs = {
                    'filename': file_name,
                    'when': when,
                    'interval': interval,
                    'backupCount': backup_count,
                    'encoding': 'UTF-8',
                    'delay': delay,
                    'utc': utc,
                }

                if sys.version_info[0] >= 3:
                    kwargs['atTime'] = at_time

                self.__file_handler = TimedRotatingFileHandler(**kwargs)

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

    @staticmethod
    def __find_caller(stack_info=False):
        """
        Find the stack frame of the caller so that we can note the source file name,
        line number and function name.
        """
        frame = logging.currentframe()
        # On some versions of IronPython, currentframe() returns None if
        # IronPython isn't run with -X:Frames.
        if frame:
            frame = frame.f_back

        caller_info = '(unknown file)', 0, '(unknown function)', None

        while hasattr(frame, 'f_code'):
            co = frame.f_code
            if _logone_src in os.path.normcase(co.co_filename):
                frame = frame.f_back
                continue

            tb_info = None
            if stack_info:
                with StringIO() as _buffer:
                    _buffer.write('Traceback (most recent call last):\n')
                    traceback.print_stack(frame, file=_buffer)
                    tb_info = _buffer.getvalue().strip()

            caller_info = co.co_filename, frame.f_lineno, co.co_name, tb_info
            break
        return caller_info

    def _log(self, level, msg, *args, **kwargs):
        """
        Log 'msg % args' with the integer severity 'level'.

        To pass exception information, use the keyword argument exc_info with
        a true value, e.g.

        logger.log(level, "We have a %s", "mysterious problem", exc_info=1)
        """
        if not isinstance(level, int):
            if logging.raiseExceptions:
                raise TypeError('Level must be an integer!')
            else:
                return

        if self.logger.isEnabledFor(level=level):
            """
            Low-level logging routine which creates a LogRecord and then calls
            all the handlers of this logger to handle the record.
            """
            exc_info = kwargs.get('exc_info', None)
            extra = kwargs.get('extra', None)
            stack_info = kwargs.get('stack_info', False)
            record_filter = kwargs.get('record_filter', None)

            tb_info = None
            if _logone_src:
                # IronPython doesn't track Python frames, so findCaller raises an
                # exception on some versions of IronPython. We trap it here so that
                # IronPython can use logging.
                try:
                    fn, lno, func, tb_info = self.__find_caller(stack_info=stack_info)
                except ValueError:  # pragma: no cover
                    fn, lno, func = '(unknown file)', 0, '(unknown function)'
            else:  # pragma: no cover
                fn, lno, func = '(unknown file)', 0, '(unknown function)'

            if exc_info:
                if sys.version_info[0] >= 3:
                    if isinstance(exc_info, BaseException):
                        # noinspection PyUnresolvedReferences
                        exc_info = type(exc_info), exc_info, exc_info.__traceback__
                    elif not isinstance(exc_info, tuple):
                        exc_info = sys.exc_info()
                else:
                    if not isinstance(exc_info, tuple):
                        exc_info = sys.exc_info()

            if sys.version_info[0] >= 3:
                # noinspection PyArgumentList
                record = self.logger.makeRecord(self.name, level, fn, lno, msg, args,
                                                exc_info, func, extra, tb_info)
            else:
                record = self.logger.makeRecord(self.name, level, fn, lno, msg, args,
                                                exc_info, func, extra)

            if record_filter:
                record = record_filter(record)

            self.logger.handle(record=record)

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
        return super(TimedRotatingFileHandler, self)._open()


class LogglyHandler(logging.Handler):
    def __init__(self, token, tag):
        self.__loggly_api = 'https://logs-01.loggly.com/inputs/%s/tag/%s' % (token, tag)

        super(LogglyHandler, self).__init__()

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
        self.__buffer = StringIO()

        if sys.version_info[0] >= 3:
            def __write(_buffer):
                """
                Write the given buffer to the temporary buffer.
                """
                self.__buffer.write(_buffer)
        else:
            def __write(_buffer):
                """
                Write the given buffer to log.
                """
                _buffer = _buffer.strip()
                # Ignore the empty buffer
                if len(_buffer) > 0:
                    # Flush messages after log() called
                    # noinspection PyProtectedMember
                    self.__logger._log(level=self.__log_level, msg=_buffer)

        self.write = __write

    def update_log_level(self, log_level=logging.INFO):
        """
        Update the logging level of this stream.
        """
        self.__log_level = log_level

    def flush(self):
        """
        Flush the buffer, if applicable.
        """
        if self.__buffer.tell() > 0:
            # Write the buffer to log
            # noinspection PyProtectedMember
            self.__logger._log(level=self.__log_level, msg=self.__buffer.getvalue().strip())
            # Remove the old buffer
            self.__buffer.truncate(0)
            self.__buffer.seek(0)


class StdErrWrapper(object):
    """
    Fake file-like stream object that redirects stderr to a logger instance.
    """

    def __init__(self, logger, log_level=logging.ERROR):
        self.__logger = logger
        self.__log_level = log_level
        self.__buffer = StringIO()

        if sys.version_info[0] >= 3:
            def __write(_buffer):
                """
                Write the given buffer to the temporary buffer.
                """
                self.__buffer.write(_buffer)
        else:
            def __write(_buffer):
                """
                Write the given buffer to log.
                """
                _buffer = _buffer.decode('UTF-8')
                self.__buffer.write(_buffer)

                if _buffer == '\n':
                    self.flush()

        self.write = __write

    def update_log_level(self, log_level=logging.ERROR):
        """
        Update the logging level of this stream.
        """
        self.__log_level = log_level

    @staticmethod
    def __filter_record(record):
        msg = record.msg.strip()
        msg = msg.splitlines()[-1]
        msg = msg.split(': ')[1:]
        record.msg = ''.join(msg) + '\n' + record.msg
        return record

    def flush(self):
        """
        Flush the buffer, if applicable.
        """
        if self.__buffer.tell() > 0:
            # Write the buffer to log
            # noinspection PyProtectedMember
            self.__logger._log(level=self.__log_level, msg=self.__buffer.getvalue().strip(),
                               record_filter=StdErrWrapper.__filter_record)
            # Remove the old buffer
            self.__buffer.truncate(0)
            self.__buffer.seek(0)
