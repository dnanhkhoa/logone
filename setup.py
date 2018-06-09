#!/usr/bin/python
# -*- coding: utf-8 -*-
import os

from setuptools import setup


def readme(file_name):
    if os.path.isfile(file_name):
        with open(file_name, 'rb') as f:
            return f.read().decode('UTF-8')
    return None


setup(name='logone',
      version='0.1.7',
      description='A simple logger which supports for logging stdout and '
                  'stderr streams to console, file, and Loggly for Python.',
      long_description=readme(file_name='README.md'),
      keywords='logone logger logging loggly telegram stream log file stdout stderr',
      url='https://github.com/dnanhkhoa/logone',
      author='Duong Nguyen Anh Khoa',
      author_email='dnanhkhoa@live.com',
      license='MIT',
      packages=['logone'],
      zip_safe=False,
      install_requires=['coloredlogs', 'colorama', 'requests'])
