#!/usr/bin/env python
# -*- coding: utf-8 -*-


import os
import re

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup


requirements = [
    'bacpypes'
]

test_requirements = [
    # TODO: put package test requirements here
]

# read in the __init__.py file, extract the metadata
init_py = open(os.path.join('modpypes', '__init__.py')).read()
metadata = dict(re.findall("__([a-z]+)__ = '([^']+)'", init_py))

setup(
    name='modpypes',
    version=metadata['version'],
    description="Python library for MODBUS based on BACpypes",
    long_description="See GitHub for more information",
    author=metadata['author'],
    author_email=metadata['email'],
    url='https://github.com/JoelBender/modpypes',
    packages=[
        'modpypes',
    ],
    package_dir={
        'modpypes': 'modpypes',
        },
    include_package_data=True,
    install_requires=requirements,
    license="MIT",
    zip_safe=False,
    keywords='modpypes',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Natural Language :: English',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: System :: Networking',
        'Topic :: Utilities',
    ],
    test_suite='tests',
    tests_require=test_requirements
)
