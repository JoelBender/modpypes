#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Server
======

This executable module is a console application for presenting itself as a
MODBUS server accepting read and write MODBUS PDUs.
"""

import math

from bacpypes.debugging import bacpypes_debugging, ModuleLogger
from bacpypes.consolecmd import ConsoleCmd
from bacpypes.consolelogging import ArgumentParser

from bacpypes.comm import Client, bind
from bacpypes.core import run

from .pdu import ExceptionResponse, \
    ReadCoilsRequest, ReadCoilsResponse, \
    ReadDiscreteInputsRequest, ReadDiscreteInputsResponse, \
    ReadMultipleRegistersRequest, ReadMultipleRegistersResponse, \
    ModbusStruct
from .app import ModbusServer, ModbusException

# some debugging
_debug = 0
_log = ModuleLogger(globals())


#
#   ConsoleServer
#


@bacpypes_debugging
class ConsoleServer(ConsoleCmd, Client):

    """
    Console Server
    """

    def __init__(self):
        if _debug: ConsoleServer._debug("__init__")
        ConsoleCmd.__init__(self)

#
#   main
#

def main():
    # parse the command line arguments
    parser = ArgumentParser(description=__doc__)

    # now parse the arguments
    args = parser.parse_args()

    if _debug: _log.debug("initialization")
    if _debug: _log.debug("    - args: %r", args)

    # local IO functions
    bind(ConsoleServer(), ModbusServer())

    _log.debug("running")

    run()

    _log.debug("fini")

if __name__ == "__main__":
    main()

