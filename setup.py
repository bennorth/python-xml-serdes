# -*- coding: utf-8  -*-

import re
from setuptools import setup, find_packages

__version__ = re.findall(r"__version__\s*\=\s*'([\w\.\-]+)'",
                         open('xmlserdes/_version.py').read())[0]


setup(
    name='xml-serdes',
    version=__version__,
    packages=find_packages(),
    install_requires=['lxml', 'numpy', 'six'],
    package_data = {}
)
