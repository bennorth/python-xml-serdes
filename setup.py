# -*- coding: utf-8  -*-

from setuptools import setup, find_packages

setup(
    name='XMLserdes',
    version='0.1.0',
    packages=find_packages(),
    install_requires=['lxml', 'numpy'],
    package_data = {}
)
