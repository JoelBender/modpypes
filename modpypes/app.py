#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Application
===========
"""

import sys
import struct

from bacpypes.debugging import bacpypes_debugging, ModuleLogger

from bacpypes.comm import PDU, Client, Server, ApplicationServiceElement, bind
from bacpypes.tcp import TCPClientDirector, TCPServerDirector, StreamToPacket
from bacpypes.iocb import SieveClientController, CTRL_IDLE, ABORTED

from .pdu import MPDU, request_types, response_types, ExceptionResponse

# some debugging
_debug = 0
_log = ModuleLogger(globals())


#
#   ModbusException
#


class ModbusException(RuntimeError):

    """Helper class for exceptions."""

    _exceptionText = {
        ExceptionResponse.ILLEGAL_FUNCTION: "illegal function",
        ExceptionResponse.ILLEGAL_DATA_ADDRESS: "illegal data address",
        ExceptionResponse.ILLEGAL_DATA_VALUE: "illegal data value",
        ExceptionResponse.ILLEGAL_RESPONSE_LENGTH: "illegal response length",
        ExceptionResponse.ACKNOWLEDGE: "acknowledge",
        ExceptionResponse.SLAVE_DEVICE_BUSY: "slave device busy",
        ExceptionResponse.NEGATIVE_ACKNOWLEDGE: "negative acknowledge",
        ExceptionResponse.MEMORY_PARITY_ERROR: "memory parity error",
        ExceptionResponse.GATEWAY_PATH_UNAVAILABLE:
        "gateway path unavailable",
        ExceptionResponse.GATEWAY_TARGET_DEVICE_FAILED_TO_RESPOND:
        "gateway target device failed to respond",
        }

    def __init__(self, errCode, *args):
        self.errCode = errCode
        text = ModbusException._exceptionText.get(
            errCode,
            "unknown exception %d" % errCode,
            )
        self.args = (text,) + args

#
#   stream_to_packet
#

def stream_to_packet(data):
    """
    Chop a stream of data into MODBUS packets.

    :param data: stream of data
    :returns: a tuple of the data that is a packet with the remaining
        data, or ``None``
    """
    if len(data) < 6:
        return None

    # unpack the length
    pktlen = struct.unpack(">H", data[4:6])[0] + 6
    if (len(data) < pktlen):
        return None

    return (data[:pktlen], data[pktlen:])


#
#   ModbusClient
#

@bacpypes_debugging
class ModbusClient(Client, Server):

    """This class simplifies building MODBUS client applications.  All of
    the PDUs are MODBUS.
    """

    def __init__(self, **kwargs):
        """Initialize a MODBUS client."""
        if _debug: ModbusClient._debug("__init__ %r", kwargs)
        Client.__init__(self)
        Server.__init__(self)

        # create and bind the client side
        self.director = TCPClientDirector(**kwargs)
        bind(self, StreamToPacket(stream_to_packet), self.director)

    def indication(self, req):
        """Got a request from the application."""
        if _debug: ModbusClient._debug("indication %r", req)

        # encode it as a generic MPDU
        mpdu = MPDU()
        req.encode(mpdu)
        if _debug: ModbusClient._debug("    - mpdu: %r", mpdu)

        # encode it as a PDU
        pdu = PDU()
        mpdu.encode(pdu)
        if _debug: ModbusClient._debug("    - pdu: %r", pdu)

        # pass it along to the device
        self.request(pdu)

    def confirmation(self, pdu):
        """Got a response from the server."""
        if _debug: ModbusClient._debug("confirmation %r", pdu)

        # pass through errors
        if isinstance(pdu, Exception):
            self.response(pdu)
            return

        # generic decode
        mpdu = MPDU()
        mpdu.decode(pdu)
        if _debug: ModbusClient._debug("    - mpdu: %r", mpdu)

        # we don't know anything but MODBUS
        if (mpdu.mpduProtocolID != 0):
            return

        # may be sending a problem
        if (mpdu.mpduFunctionCode >= 128):
            klass = ExceptionResponse
        else:
            klass = response_types.get(mpdu.mpduFunctionCode, None)
            if not klass:
                return

        resp = klass()
        resp.decode(mpdu)
        if _debug: ModbusClient._debug("    - resp: %r", resp)

        # pass it along to the application
        self.response(resp)

#
#   ModbusClientASE
#

@bacpypes_debugging
class ModbusClientASE(ApplicationServiceElement):

    def __init__(self, client_controller):
        if _debug: ModbusClientASE._debug("__init__ %r", client_controller)

        # save the controller reference
        self.client_controller = client_controller

    def indication(self, add_actor=None, del_actor=None, actor_error=None, error=None):
        if add_actor:
            if _debug: ModbusClientASE._debug("indication add_actor=%r", add_actor)

        if del_actor:
            if _debug: ModbusClientASE._debug("indication del_actor=%r", del_actor)

            # tell the controller to abort all current and pending requests
            self.client_controller.abort(del_actor.peer, RuntimeError("connection closed"))

        if actor_error:
            if _debug: ModbusClientASE._debug("indication actor_error=%r error=%r", actor_error, error)

            # tell the controller to abort all current and pending requests
            self.client_controller.abort(actor_error.peer, error)

            # tell the director to close
            self.elementService.disconnect(actor_error.peer)

#
#   ModbusClientController
#

@bacpypes_debugging
class ModbusClientController(SieveClientController):

    def __init__(self, connect_timeout=None, idle_timeout=None):
        if _debug: ModbusClientController._debug("__init__")
        SieveClientController.__init__(self)

        # create and bind to a client which is already bound to a director
        self.client = ModbusClient(connect_timeout=connect_timeout, idle_timeout=idle_timeout)
        bind(self, self.client)

        # create an application service element referencing this controller and
        # bound to the TCPClientDirector
        self.client_ase = ModbusClientASE(self)
        bind(self.client_ase, self.client.director)

    def abort(self, address, err):
        if _debug: ModbusClientController._debug("abort %r %r", address, err)

        # look up the queue
        queue = self.queues.get(address, None)
        if not queue:
            if _debug: ModbusClientController._debug("    - no queue: %r" % (address,))
            return
        if _debug: ModbusClientController._debug("    - queue: %r", queue)

        # if it has an active iocb, abort it
        if queue.active_iocb:
            if _debug: ModbusClientController._debug("    - active_iocb: %r", queue.active_iocb)
            iocb = queue.active_iocb

            # change the state
            iocb.ioState = ABORTED
            iocb.ioError = err

            # notify the client
            iocb.trigger()

        # abort the rest in the queue
        while True:
            iocb = queue.ioQueue.get(block=0)
            if not iocb:
                break
            if _debug: ModbusClientController._debug("    - iocb: %r", iocb)

            # change the state
            iocb.ioState = ABORTED
            iocb.ioError = err

            # notify the client
            iocb.trigger()

        if (self.state != CTRL_IDLE):
            if _debug: ModbusClientController._debug("    - busy after aborts")

        # if the queue is empty and idle, forget about the controller
        if not queue.ioQueue.queue and not queue.active_iocb:
            if _debug: SieveClientController._debug("    - queue is empty")
            del self.queues[address]

#
#   ModbusServer
#

@bacpypes_debugging
class ModbusServer(Client, Server):

    def __init__(self, host='', port=502, **kwargs):
        if _debug: ModbusServer._debug("__init__ host=%r port=%r %r", host, port, kwargs)
        Client.__init__(self)
        Server.__init__(self)

        # create and bind
        self.serverDirector = TCPServerDirector((host, port), **kwargs)
        bind(self, StreamToPacket(stream_to_packet), self.serverDirector)

    def confirmation(self, pdu):
        """This is a request from a client."""
        if _debug: ModbusServer._debug("confirmation %r", pdu)

        # pass through errors
        if isinstance(pdu, Exception):
            self.response(pdu)
            return

        # generic decoding
        mpdu = MPDU()
        mpdu.decode(pdu)
        if _debug: ModbusServer._debug("    - mpdu: %r", mpdu)

        # we don't know anything but MODBUS
        if (mpdu.mpduProtocolID != 0):
            return

        # clients shouldn't be sending exceptions
        if (mpdu.mpduFunctionCode >= 128):
            return

        # map the function code
        klass = request_types.get(mpdu.mpduFunctionCode, None)
        if not klass:
            # create an error for now
            resp = ExceptionResponse(
                mpdu.mpduFunctionCode,
                ExceptionResponse.ILLEGAL_FUNCTION,
                )

            # match the transaction information
            resp.pduDestination = mpdu.pduSource
            resp.mpduTransactionID = mpdu.mpduTransactionID
            if _debug: ModbusServer._debug("    - resp: %r", resp)

            # return the response to the device
            self.request(resp)

        req = klass()
        req.decode(mpdu)
        if _debug: ModbusServer._debug("    - req: %r", req)

        # pass it along to the application
        self.response(req)

    def indication(self, resp):
        """This is a response from the application."""
        if _debug: ModbusServer._debug("indication %r", resp)

        # encode as a generic MPDU
        mpdu = MPDU()
        resp.encode(mpdu)
        if _debug: ModbusServer._debug("    - mpdu: %r", mpdu)

        # encode as a generic PDU
        pdu = PDU()
        mpdu.encode(pdu)
        if _debug: ModbusServer._debug("    - pdu: %r", pdu)

        # return the response to the device
        self.request(pdu)
