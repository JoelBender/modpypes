#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Client
======

This executable module is a console application for generating
read and write MODBUS PDUs.
"""

import math

from bacpypes.debugging import class_debugging, ModuleLogger
from bacpypes.consolecmd import ConsoleCmd
from bacpypes.consolelogging import ArgumentParser

from bacpypes.comm import Client, bind
from bacpypes.core import run

from .pdu import ExceptionResponse, \
    ReadCoilsRequest, ReadCoilsResponse, \
    ReadDiscreteInputsRequest, ReadDiscreteInputsResponse, \
    ReadMultipleRegistersRequest, ReadMultipleRegistersResponse, \
    ModbusStruct
from .app import ModbusClient, ModbusException

# some debugging
_debug = 0
_log = ModuleLogger(globals())


#
#   ConsoleClient
#


@class_debugging
class ConsoleClient(ConsoleCmd, Client):

    """
    Console Client
    """

    def __init__(self):
        if _debug: ConsoleClient._debug("__init__")
        ConsoleCmd.__init__(self)

        # no current request
        self.req = None

    def do_read(self, args):
        """read <addr> <unitID> <register> [ <count> ]

        :param addr: IP address of the MODBUS/TCP device or gateway
        :param unitID: unit identifier
        :param register: register in 5-digit or 6-digit format
        :param count: number of registers to read, defaults to one

        This command generates a :class:`ReadCoilsRequest`,
        :class:`ReadDiscreteInputsRequest`, :class:`ReadInputRegistersRequest`,
        or :class:`ReadMultipleRegistersRequest` depending on the address
        prefix; 0, 1, 3, or 4.
        """
        args = args.split()
        if _debug: ConsoleClient._debug("do_read %r", args)

        if (len(args) < 3):
            print("address, unit and register required")
            return

        # get the address and unit
        addr, unitID, register = args[:3]
        unitID = int(unitID)
        if _debug: ConsoleClient._debug("    - addr, unitID: %r, %r", addr, unitID)

        # get the register and count
        register = int(register)
        if len(args) == 4:
            rcount = int(args[3])
        else:
            rcount = 1
        if _debug: ConsoleClient._debug("    - register, rcount: %r, %r", register, rcount)

        # decode the register into a type
        digits = int(math.log10(register)) + 1
        if digits < 4:
            # must be a coil
            registerType = 0
        elif digits == 5:
            registerType = register // 10000
            register = register % 10000
        elif digits == 6:
            registerType = register // 100000
            register = register % 100000
        else:
            print("5 or 6 digit addresses please")
            return
        if _debug: ConsoleClient._debug("    - registerType, register: %r, %r", registerType, register)

        # build a request
        if registerType == 0:
            # coil
            req = ReadCoilsRequest(register - 1, rcount)
        elif registerType == 1:
            # discrete inputs
            req = ReadDiscreteInputsRequest(register - 1, 1)
        elif registerType == 3:
            # input register
            req = ReadInputRegistersRequest(register - 1, 1)
        elif registerType == 4:
            # holding register
            req = ReadMultipleRegistersRequest(register - 1, rcount)
        else:
            print("unsupported register type")
            return

        # set the destination
        req.pduDestination = (addr, 502)
        req.mpduUnitID = unitID
        if _debug: ConsoleClient._debug("    - req: %r", req)

        # save the request
        self.req = req

        # send it along
        self.request(req)

    def do_write(self, args):
        """write <addr> <unitID> <register> <value>

        :param addr: IP address of the MODBUS/TCP device or gateway
        :param unitID: unit identifier
        :param register: register in 5-digit or 6-digit format
        :param value: value to write

        This command generates a :class:`WriteSingleCoil`,
        or :class:`WriteSingleRegisterRequest` depending on the address
        prefix; 0 or 4.
        """
        args = args.split()
        if _debug: ConsoleClient._debug("do_read %r", args)

        if (len(args) < 3):
            print("address, unit and register required")
            return

        # get the address and unit
        addr, unitID, register = args[:3]
        unitID = int(unitID)
        if _debug: ConsoleClient._debug("    - addr, unitID: %r, %r", addr, unitID)

        # get the register and count
        register = int(register)
        if len(args) == 4:
            rcount = int(args[3])
        else:
            rcount = 1
        if _debug: ConsoleClient._debug("    - register, rcount: %r, %r", register, rcount)

        # decode the register into a type
        digits = int(math.log10(register)) + 1
        if digits < 4:
            # must be a coil
            registerType = 0
        elif digits == 5:
            registerType = register // 10000
            register = register % 10000
        elif digits == 6:
            registerType = register // 100000
            register = register % 100000
        else:
            print("5 or 6 digit addresses please")
            return
        if _debug: ConsoleClient._debug("    - registerType, register: %r, %r", registerType, register)

        # build a request
        if registerType == 0:
            # coil
            req = WriteSingleCoilRequest(register - 1, value)
        elif registerType == 4:
            # holding register
            req = WriteSingleRegisterRequest(register - 1, value)
        else:
            print("unsupported register type")
            return

        # set the destination
        req.pduDestination = (addr, 502)
        req.mpduUnitID = unitID
        if _debug: ConsoleClient._debug("    - req: %r", req)

        # save the request
        self.req = req

        # send it along
        self.request(req)

    def confirmation(self, pdu):
        """Prints out the contents of the response from the
        device.
        """

        if _debug: ConsoleClient._debug("confirmation %r", pdu)

        # exceptions
        if isinstance(pdu, ExceptionResponse):
            print(ModbusException(pdu.exceptionCode))

        # read responses
        elif isinstance(pdu, ReadCoilsResponse):
            print("  ::=" + str(pdu.bits))

        elif isinstance(pdu, ReadDiscreteInputsResponse):
            print("  ::=" + str(pdu.bits))

        elif isinstance(pdu, ReadInputRegistersResponse):
            print("  ::=" + str(pdu.registers))

        elif isinstance(pdu, ReadMultipleRegistersResponse):
            print("  ::=" + str(pdu.registers))

            for dtype, codec in ModbusStruct.items():
                try:
                    value = codec.unpack(pdu.registers)
                    print("   " + dtype + " ::= " + str(value))
                except Exception as err:
                    if _debug: ConsoleClient._debug("unpack exception %r: %r", codec, err)

        # write responses
        elif isinstance(pdu, WriteSingleCoilResponse):
            print("  ::=" + str(pdu.bits))

        elif isinstance(pdu, WriteSingleRegisterResponse):
            print("  ::=" + str(pdu.bits))

        else:
            raise TypeError("unsupported response")


#
#   main
#


def main():
    try:
        # parse the command line arguments
        parser = ArgumentParser(description=__doc__)

        # now parse the arguments
        args = parser.parse_args()

        if _debug: _log.debug("initialization")
        if _debug: _log.debug("    - args: %r", args)

        # local IO functions
        bind(ConsoleClient(), ModbusClient())

        _log.debug("running")

        run()

    except Exception as err:
        _log.exception("an error has occurred: %s" % (err,))
    finally:
        _log.debug("finally")

if __name__ == "__main__":
    main()
