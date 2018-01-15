#!/usr/bin/python
# -*- coding: utf-8 -*-
import logone

# Indicate `DEBUG` level (or higher) for the root logger
logone.set_level(level=logone.DEBUG)

# Now, we can log anything to the root logger
logone.debug('Quick zephyrs blow, vexing daft Jim')
logone.info('How quickly daft jumping zebras vex')


def main():
    # Create a new logger if you do not want to use the root logger
    logger = logone.get_logger('example')
    logger.set_level(logone.DEBUG)

    # Log something to the logger
    logger.debug('Debug message')
    logger.info('Info message')
    logger.warning('Warn message')

    # Set up the logger for logging `DEBUG` messages or higher to `example.log` file
    # Learn more at: https://docs.python.org/3/library/logging.handlers.html#logging.handlers.TimedRotatingFileHandler
    logger.use_file(enabled=True, file_name='logs/example.log', level=logone.DEBUG,
                    when='d', interval=1, backup_count=10)

    # Set up the logger for logging `DEBUG` messages or higher to Loggly service in real-time
    logger.use_loggly(enabled=True, level=logone.DEBUG,
                      loggly_token='YOUR-CUSTOMER-TOKEN', loggly_tag='Python,Example')

    # Log something to the logger, file, and Loggly service
    logger.error('Error message')
    logger.critical('Critical message')

    # Redirect stdout stream to the logger as `INFO` messages (for `print` function,...)
    logger.redirect_stdout(enabled=True, log_level=logone.INFO)
    # Redirect stderr stream to the logger as `ERROR` messages (for unexpected error,...)
    logger.redirect_stderr(enabled=True, log_level=logone.ERROR)

    # These will be written to stdout stream and then redirected to the logger
    print('Jackdaws love my big sphinx of quartz')

    value = 20
    print('Value = ', value)

    # ZeroDivisionError exception will be written to stderr stream and then redirected to the logger
    value = 1 / 0
    print(value)


if __name__ == '__main__':
    main()
