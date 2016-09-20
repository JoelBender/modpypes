#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This executable module is a console application for presenting itself as a
MODBUS server accepting read and write MODBUS PDUs.
"""

import os
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

# settings
SERVER_HOST = os.getenv("SERVER_HOST", "")
SERVER_PORT = int(os.getenv("SERVER_PORT", 502))

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
    parser.add_argument(
        "--host", type=str,
        help="address of host (default {!r})".format(SERVER_HOST),
        default=SERVER_HOST,
        )
    parser.add_argument(
        "--port", type=int,
        help="server port (default {!r})".format(SERVER_PORT),
        default=SERVER_PORT,
        )
    args = parser.parse_args()

    if _debug: _log.debug("initialization")
    if _debug: _log.debug("    - args: %r", args)

    # local IO functions
    bind(ConsoleServer(), ModbusServer(port=args.port))

    _log.debug("running")

    run()

    _log.debug("fini")

if __name__ == "__main__":
    main()

