#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This executable module is a console application for presenting itself as a
MODBUS server accepting read and write MODBUS PDUs.
"""

import os
import logging

from bacpypes.debugging import bacpypes_debugging, ModuleLogger
from bacpypes.consolecmd import ConsoleCmd
from bacpypes.consolelogging import ArgumentParser

from bacpypes.comm import Client, bind
from bacpypes.core import run

from .pdu import ExceptionResponse, \
    ReadCoilsResponse, ReadDiscreteInputsResponse, ReadMultipleRegistersResponse, \
    WriteSingleCoilResponse, WriteSingleRegisterResponse, WriteMultipleRegistersResponse
from .app import ModbusServer, ModbusException

# some debugging
_debug = 0
_log = ModuleLogger(globals())
_commlog = logging.getLogger(__name__ + "._commlog")

# settings
SERVER_HOST = os.getenv("SERVER_HOST", "")
SERVER_PORT = int(os.getenv("SERVER_PORT", 502))
IDLE_TIMEOUT = int(os.getenv('IDLE_TIMEOUT', 0)) or None

#
#   SimpleServer
#


@bacpypes_debugging
class SimpleServer(Client):

    """
    Simple Server
    """

    def __init__(self, unitNumber=1):
        if _debug: SimpleServer._debug("__init__")
        Client.__init__(self)

        # save the unit number
        self.unitNumber = unitNumber

        # create some coils and registers
        self.coils = [False] * 10
        self.registers = [0] * 10

    def confirmation(self, req):
        """Got a request from a client."""
        if _debug: SimpleServer._debug("confirmation %r", req)
        _commlog.debug(">>> %r %r", req.pduSource, req)

        # if its an exception, punt
        if isinstance(req, Exception):
            if _debug: SimpleServer._debug("    - punt exceptions")
            return

        # if it's not for us, dump it
        if req.mpduUnitID != self.unitNumber:
            if _debug: SimpleServer._debug("    - not for us")
            return

        try:
            # look up a matching function
            try:
                fn = getattr(self, "do_" + req.__class__.__name__)
            except AttributeError:
                raise ModbusException(ExceptionResponse.ILLEGAL_FUNCTION)

            # try to execute it
            resp = fn(req)

        except ModbusException as err:
            # create an exception response
            resp = ExceptionResponse(req.mpduFunctionCode, err.errCode)

        # match the transaction information
        resp.pduDestination = req.pduSource
        resp.mpduTransactionID = req.mpduTransactionID
        _commlog.debug("<<< %r %r", resp.pduDestination, resp)

        # send the response back
        self.request(resp)

    def pull_coils(self, address, count):
        """Called when there is a request for the current value of a coil."""
        if _debug: SimpleServer._debug("pull_coils %r %r", address, count)

    def push_coils(self, address, count):
        """Called when a MODBUS service has changed the value of one or more coils."""
        if _debug: SimpleServer._debug("push_coils %r %r", address, count)

    def pull_registers(self, address, count):
        """Called when a MODBUS client is requesting the current value of one
        or more registers."""
        if _debug: SimpleServer._debug("pull_registers %r %r", address, count)

    def push_registers(self, address, count):
        """Called when a MODBUS service has changed the value of one or more
        registers."""
        if _debug: SimpleServer._debug("push_registers %r %r", address, count)

    # ---------- Coils ----------

    def do_ReadCoilsRequest(self, req):
        SimpleServer._debug('do_ReadCoilsRequest %r', req)
        if (req.address + req.count) > len(self.coils):
            raise ModbusException(ExceptionResponse.ILLEGAL_DATA_ADDRESS)

        self.pull_coils(req.address, req.count)

        return ReadCoilsResponse(self.coils[req.address:req.address+req.count])

    def do_WriteSingleCoilRequest(self, req):
        SimpleServer._debug('do_WriteSingleCoilRequest %r', req)
        if req.address > len(self.coils):
            raise ModbusException(ExceptionResponse.ILLEGAL_DATA_ADDRESS)

        # check the value and save it
        if (req.value == 0x0000):
            self.coils[req.address] = 0
        elif (req.value == 0xFF00):
            self.coils[req.address] = 1
        else:
            raise ModbusException(ExceptionResponse.ILLEGAL_DATA_VALUE)

        self.push_coils(req.address, 1)

        # return the new value
        return WriteSingleCoilResponse(req.address, req.value)

    # ---------- Descrete Inputs (mapped as a coil) ----------

    def do_ReadDescreteInputsRequest(self, req):
        SimpleServer._debug('do_ReadDescreteInputsRequest %r', req)
        if (req.address + req.count) > len(self.coils):
            raise ModbusException(ExceptionResponse.ILLEGAL_DATA_ADDRESS)

        self.pull_coils(req.address, req.count)

        return ReadDiscreteInputsResponse(self.coils[req.address:req.address+req.count])

    # ---------- Registers ----------

    def do_ReadMultipleRegistersRequest(self, req):
        SimpleServer._debug('do_ReadMultipleRegistersRequest %r', req)
        if (req.address + req.count) > len(self.registers):
            raise ModbusException(ExceptionResponse.ILLEGAL_DATA_ADDRESS)

        self.pull_registers(req.address, req.count)

        return ReadMultipleRegistersResponse(self.registers[req.address:req.address+req.count])

    def do_WriteSingleRegisterRequest(self, req):
        SimpleServer._debug('do_WriteSingleRegisterRequest %r', req)
        if req.address > len(self.registers):
            raise ModbusException(ExceptionResponse.ILLEGAL_DATA_ADDRESS)

        # save the value
        self.registers[req.address] = req.value

        self.push_registers(req.address, 1)

        # return the new value
        return WriteSingleRegisterResponse(req.address, req.value)

    def do_WriteMultipleRegistersRequest(self, req):
        SimpleServer._debug('do_WriteMultipleRegistersRequest %r', req)
        if (req.address + req.count) > len(self.registers):
            raise ModbusException(ExceptionResponse.ILLEGAL_DATA_ADDRESS)

        # save the values
        for i in range(req.count):
            self.registers[req.address + i] = req.registers[i]

        self.push_registers(req.address, req.count)

        return WriteMultipleRegistersResponse(req.address, req.count)

    # ---------- Input Registers (mapped as a register) ----------

    def do_ReadInputRegistersRequest(self, req):
        SimpleServer._debug('do_ReadInputRegistersRequest %r', req)
        if (req.address + req.count) > len(self.registers):
            raise ModbusException(ExceptionResponse.ILLEGAL_DATA_ADDRESS)

        self.pull_registers(req.address, req.count)

        return ReadMultipleRegistersResponse(self.registers[req.address:req.address+req.count])

#
#   main
#

def main():
    # parse the command line arguments
    parser = ArgumentParser(description=__doc__)

    # listener arguments
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

    # connection timeout arguments
    parser.add_argument(
        "--idle-timeout", nargs='?', type=int,
        help="idle connection timeout",
        default=IDLE_TIMEOUT,
        )

    args = parser.parse_args()

    if _debug: _log.debug("initialization")
    if _debug: _log.debug("    - args: %r", args)

    # local IO functions
    bind(SimpleServer(), ModbusServer(port=args.port, idle_timeout=args.idle_timeout))

    _log.debug("running")

    run()

    _log.debug("fini")

if __name__ == "__main__":
    main()

