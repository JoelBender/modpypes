#!/bin/bash

sudo python setup.py bdist_egg
sudo python setup.py bdist_wheel
twine upload dist/*

