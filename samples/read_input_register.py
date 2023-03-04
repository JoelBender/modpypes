"""
Read Input Registers
"""

import os

from bacpypes.debugging import bacpypes_debugging, ModuleLogger
from bacpypes.consolelogging import ArgumentParser

from bacpypes.core import run, deferred
from bacpypes.comm import Client, bind

from modpypes.pdu import (
    ExceptionResponse,
    ReadInputRegistersRequest,
    ReadInputRegistersResponse,
    ModbusStruct,
)
from modpypes.app import ModbusClient

# some debugging
_debug = 0
_log = ModuleLogger(globals())

# settings
CONNECT_TIMEOUT = int(os.getenv("CONNECT_TIMEOUT", 0)) or None
IDLE_TIMEOUT = int(os.getenv("IDLE_TIMEOUT", 0)) or None

#
#   ReadClient
#


@bacpypes_debugging
class ReadClient(Client):

    """
    Read Client
    """

    def __init__(self):
        if _debug:
            ReadClient._debug("__init__")
        Client.__init__(self)

    def read_input_registers(self, addr, unit_id, register, count):
        """
        Read an input register.
        """
        if _debug:
            ReadClient._debug(
                "read_input_registers %r %r %r %r", addr, unit_id, register, count
            )

        # address might have a port
        if ":" in addr:
            addr, port = addr.split(":")
            server_address = (addr, int(port))
        else:
            server_address = (addr, 502)

        # build a request
        req = ReadInputRegistersRequest(register - 1, count)

        # set the destination
        req.pduDestination = server_address
        req.mpduUnitID = unit_id
        if _debug:
            ReadClient._debug("    - req: %r", req)

        # send the request
        self.request(req)

    def confirmation(self, resp):
        if _debug:
            ReadClient._debug("confirmation %r", resp)

        # read responses
        if isinstance(resp, ExceptionResponse):
            print("  ::= " + str(resp))

        elif isinstance(resp, ReadInputRegistersResponse):
            print("  ::= " + str(resp.registers))

            for dtype, codec in ModbusStruct.items():
                try:
                    value = codec.unpack(resp.registers)
                    print("   " + dtype + " ::= " + str(value))
                except Exception as err:
                    if _debug:
                        ReadClient._debug("unpack exception %r: %r", codec, err)

        else:
            raise TypeError("unsupported response")


#
#   main
#


def main():
    # parse the command line arguments
    parser = ArgumentParser(description=__doc__)

    # connection timeout paramters
    parser.add_argument(
        "--connect-timeout",
        nargs="?",
        type=int,
        help="idle connection timeout",
        default=CONNECT_TIMEOUT,
    )
    parser.add_argument(
        "--idle-timeout",
        nargs="?",
        type=int,
        help="idle connection timeout",
        default=IDLE_TIMEOUT,
    )

    # now parse the arguments
    args = parser.parse_args()

    if _debug:
        _log.debug("initialization")
    if _debug:
        _log.debug("    - args: %r", args)

    # make a controller
    controller = ModbusClient(
        connect_timeout=args.connect_timeout,
        idle_timeout=args.idle_timeout,
    )
    if _debug:
        _log.debug("    - controller: %r", controller)

    # make a client
    read_client = ReadClient()
    if _debug:
        _log.debug("    - read_client: %r", read_client)

    # bind the client "on top" of the controller as a "stack"
    bind(read_client, controller)

    # read something when the stack is ready
    deferred(read_client.read_input_registers, "10.0.1.70", 1, 1016, 1)

    _log.debug("running")

    run()

    _log.debug("fini")


if __name__ == "__main__":
    main()
