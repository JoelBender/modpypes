#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Client
======

This executable module is a console application for generating
read and write MODBUS PDUs.
"""

import math

from bacpypes.debugging import bacpypes_debugging, ModuleLogger
from bacpypes.consolecmd import ConsoleCmd
from bacpypes.consolelogging import ArgumentParser

from bacpypes.comm import Client, bind
from bacpypes.core import run
from bacpypes.iocb import IOCB, IOController, IOQController

from .pdu import ExceptionResponse, \
    ReadCoilsRequest, ReadCoilsResponse, \
    ReadDiscreteInputsRequest, ReadDiscreteInputsResponse, \
    ReadInputRegistersRequest, ReadInputRegistersResponse, \
    ReadMultipleRegistersRequest, ReadMultipleRegistersResponse, \
    WriteSingleCoilRequest, WriteSingleCoilResponse, \
    WriteSingleRegisterRequest, WriteSingleRegisterResponse, \
    ModbusStruct
from .app import ModbusClient

# some debugging
_debug = 0
_log = ModuleLogger(globals())

#
#   QController
#

@bacpypes_debugging
class QController(IOQController):

    def __init__(self, request_fn, address):
        """Initialize an application controller.  To process requests it only
        needs the function to call that sends an APDU down the stack, the address
        parameter is to help with debugging."""
        if _debug: QController._debug("__init__ %r %r", request_fn, address)
        IOQController.__init__(self, str(address))

        # save a reference to the request function
        self.request_fn = request_fn
        self.address = address

    def process_io(self, iocb):
        """Called to start processing a request.  This is called immediately
        when the controller is idle, otherwise this is called for the next IOCB
        when the current request has been satisfied."""
        if _debug: QController._debug("process_io %r", iocb)

        # this is now an active request
        self.active_io(iocb)

        # send the request
        self.request_fn(iocb.args[0])

#
#   Controller
#

@bacpypes_debugging
class Controller(Client, IOController):

    def __init__(self):
        if _debug: Controller._debug("__init__")
        Client.__init__(self)
        IOController.__init__(self)

        # controllers for each address
        self.controllers = {}

    def process_io(self, iocb):
        if _debug: Controller._debug("process_io %r", iocb)

        # get the destination address from the pdu
        destination_address = iocb.args[0].pduDestination
        if _debug: Controller._debug("    - destination_address: %r", destination_address)

        # look up the controller
        controller = self.controllers.get(destination_address, None)
        if not controller:
            controller = QController(self.request, destination_address)
            self.controllers[destination_address] = controller
        if _debug: Controller._debug("    - controller: %r", controller)

        # ask the controller to process or queue the request
        controller.request_io(iocb)

    def request(self, pdu):
        if _debug: Controller._debug("request %r", pdu)

        # send it downstream
        super(Controller, self).request(pdu)

    def confirmation(self, pdu):
        if _debug: Controller._debug("confirmation %r", pdu)

        # get the source address
        source_address = pdu.pduSource
        if _debug: Controller._debug("    - source_address: %r", source_address)

        # look up the controller
        controller = self.controllers.get(source_address, None)
        if not controller:
            Controller._debug("no controller for %r" % (source_address,))
            return
        if _debug: Controller._debug("    - controller: %r", controller)

        # make sure it has an active iocb
        if not controller.active_iocb:
            Controller._debug("no active request for %r" % (source_address,))
            return

        # complete or abort the request
        if isinstance(pdu, ExceptionResponse):
            controller.abort_io(controller.active_iocb, pdu)
        else:
            controller.complete_io(controller.active_iocb, pdu)

        # if the queue is empty and idle, forget about the controller
        if not controller.ioQueue.queue and not controller.active_iocb:
            if _debug: Controller._debug("    - controller queue is empty")
            del self.controllers[source_address]


#
#   ConsoleClient
#

@bacpypes_debugging
class ConsoleClient(ConsoleCmd):

    """
    Console Client
    """

    def __init__(self, controller):
        if _debug: ConsoleClient._debug("__init__")
        ConsoleCmd.__init__(self)

        # save the controller
        self.controller = controller

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

        # get the address and unit, and register
        addr, unitID, register = args[:3]

        # address might have a port
        if ':' in addr:
            addr, port = addr.split(':')
            server_address = (addr, int(port))
        else:
            server_address = (addr, 502)

        # unit identifier
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
        req.pduDestination = server_address
        req.mpduUnitID = unitID
        if _debug: ConsoleClient._debug("    - req: %r", req)

        # make an IOCB
        iocb = IOCB(req)
        if _debug: ConsoleClient._debug("    - iocb: %r", iocb)

        # submit the request
        self.controller.request_io(iocb)

        # wait for the response
        iocb.wait()
        iocb.debug_contents()

        # exceptions
        if iocb.ioError:
            print(iocb.ioError)

        # read responses
        elif isinstance(iocb.ioResponse, ReadCoilsResponse):
            print("  ::= " + str(iocb.ioResponse.bits))

        elif isinstance(iocb.ioResponse, ReadDiscreteInputsResponse):
            print("  ::= " + str(iocb.ioResponse.bits))

        elif isinstance(iocb.ioResponse, ReadInputRegistersResponse):
            print("  ::= " + str(iocb.ioResponse.registers))

        elif isinstance(iocb.ioResponse, ReadMultipleRegistersResponse):
            print("  ::= " + str(iocb.ioResponse.registers))

            for dtype, codec in ModbusStruct.items():
                try:
                    value = codec.unpack(iocb.ioResponse.registers)
                    print("   " + dtype + " ::= " + str(value))
                except Exception as err:
                    if _debug: ConsoleClient._debug("unpack exception %r: %r", codec, err)
        else:
            raise TypeError("unsupported response")


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
        if _debug: ConsoleClient._debug("do_write %r", args)

        if (len(args) < 3):
            print("address, unit and register required")
            return

        # get the address and unit
        addr, unitID, register, value = args

        # address might have a port
        if ':' in addr:
            addr, port = addr.split(':')
            server_address = (addr, int(port))
        else:
            server_address = (addr, 502)

        # unit identifier
        unitID = int(unitID)
        if _debug: ConsoleClient._debug("    - addr, unitID: %r, %r", server_address, unitID)

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

        # value
        value = int(value)
        if _debug: ConsoleClient._debug("    - value: %r", value)

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
        req.pduDestination = server_address
        req.mpduUnitID = unitID
        if _debug: ConsoleClient._debug("    - req: %r", req)

        # make an IOCB
        iocb = IOCB(req)
        if _debug: ConsoleClient._debug("    - iocb: %r", iocb)

        # submit the request
        self.controller.request_io(iocb)

        # wait for the response
        iocb.wait()

        # exceptions
        if iocb.ioError:
            print(iocb.ioError)

        # write responses
        elif isinstance(iocb.ioResponse, WriteSingleCoilResponse):
            print("  ::= " + str(iocb.ioResponse.bits))

        elif isinstance(iocb.ioResponse, WriteSingleRegisterResponse):
            print("  ::= " + str(iocb.ioResponse.value))

        else:
            raise TypeError("unsupported response")

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

    # make a controller
    this_controller = Controller()
    if _debug: _log.debug("    - this_controller: %r", this_controller)

    this_console = ConsoleClient(this_controller)
    if _debug: _log.debug("    - this_console: %r", this_console)

    # local IO functions
    bind(this_controller, ModbusClient())

    _log.debug("running")

    run()

    _log.debug("fini")

if __name__ == "__main__":
    main()

