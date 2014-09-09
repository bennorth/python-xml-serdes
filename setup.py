# -*- coding: utf-8  -*-

from setuptools import setup, find_packages

setup(
    name='xml-serdes',
    version='0.1.1',
    packages=find_packages(),
    install_requires=['lxml', 'numpy'],
    package_data = {}
)
