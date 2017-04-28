#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Protocol Data Units
===================
"""

import struct

from bacpypes.debugging import bacpypes_debugging, DebugContents, ModuleLogger

from bacpypes.comm import PDUData, PCI
from bacpypes.errors import DecodingError

# some debugging
_debug = 0
_log = ModuleLogger(globals())

# a dictionary of functions and classes
request_types = {}
response_types = {}

def register_request_type(klass):
    request_types[klass.functionCode] = klass

def register_response_type(klass):
    response_types[klass.functionCode] = klass

#
#   Packing and Unpacking Functions
#

def _packBitsToString(bits):
    barry = []
    i = packed = 0
    for bit in bits:
        if bit:
            packed += 128
        i += 1
        if i == 8:
            barry.append(packed)
            i = packed = 0
        else:
            packed >>= 1
    if i > 0 and i < 8:
        packed >>= 7 - i
        barry.append(packed)
    return struct.pack("B" * len(barry), *barry)

def _unpackBitsFromString(string):
    barry = struct.unpack("B" * len(string), string)
    bits = []
    for byte in barry:
        for bit in range(8):
            bits.append((byte & 1) == 1)
            byte >>= 1
    return bits

#
#   _Struct
#

class _Struct:

    """
    This is an abstract class for functions that pack and unpack the
    variably encoded portion of a PDU.  Each of the derived classes
    produces or consumes a number of 16-registers.
    """

    registerLength = None

    def pack(self, value):
        raise NotImplementedError("pack is not implemented in %s" % (self.__class__.__name__,))

    def unpack(self, registers):
        raise NotImplementedError("unpack is not implemented in %s" % (self.__class__.__name__,))

@bacpypes_debugging
class Byte(_Struct):

    """
    This class packs and unpacks a register as an unsigned octet.
    """

    registerLength = 1

    def pack(self, value):
        if _debug: Byte._debug("pack %r", value)

        return [value & 0xFF]

    def unpack(self, registers):
        if _debug: Byte._debug("unpack %r", registers)

        return registers[0]

@bacpypes_debugging
class Int(_Struct):

    """
    This class packs and unpacks a register as a 16-bit signed integer.
    """

    registerLength = 1

    def pack(self, value):
        if _debug: Int._debug("pack %r", value)

        return [value & 0xFFFF]

    def unpack(self, registers):
        if _debug: Int._debug("unpack %r", registers)

        value = registers[0]
        if (value & 0x8000):
            value = (-1 << 16) | value

        return value

@bacpypes_debugging
class UnsignedInt(_Struct):

    """
    This class packs and unpacks a register as a 16-bit unsigned integer.
    """

    registerLength = 1

    def pack(self, value):
        if _debug: UnsignedInt._debug("pack %r", value)

        return [value & 0xFF]

    def unpack(self, registers):
        if _debug: UnsignedInt._debug("unpack %r", registers)

        return registers[0]

@bacpypes_debugging
class DoubleInt(_Struct):

    """
    This class packs and unpacks a pair of registers as a 32-bit signed integer.
    """

    registerLength = 2

    def pack(self, value):
        if _debug: DoubleInt._debug("pack %r", value)

        return [(value >> 16) & 0xFFFF, value & 0xFFFF]

    def unpack(self, registers):
        if _debug: DoubleInt._debug("unpack %r", registers)

        value = (registers[0] << 16) | registers[1]
        if (value & 0x80000000):
            value = (-1 << 32) | value

        return value

@bacpypes_debugging
class UnsignedDoubleInt(_Struct):

    """
    This class packs and unpacks a pair of registers as a 32-bit unsigned integer.
    """

    registerLength = 2

    def pack(self, value):
        if _debug: UnsignedDoubleInt._debug("pack %r", value)

        return [(value >> 16) & 0xFFFF, value & 0xFFFF]

    def unpack(self, registers):
        if _debug: UnsignedDoubleInt._debug("unpack %r", registers)

        return (registers[0] << 16) | registers[1]

@bacpypes_debugging
class Real(_Struct):

    registerLength = 2

    def pack(self, value):
        if _debug: Real._debug("pack %r", value)

        # make sure it's a float
        if not isinstance(value, float):
            if _debug: Real._error("packing error: %r is not a float", value)
            value = 0.0

        registers = struct.unpack(">HH", struct.pack(">f", value))
        return [registers[1], registers[0]]

    def unpack(self, registers):
        if _debug: Real._debug("unpack %r", registers)

        value, = struct.unpack(">f", struct.pack(">HH", registers[1], registers[0]))
        return value

@bacpypes_debugging
class ROCReal(_Struct):

    registerLength = 1

    def pack(self, value):
        if _debug: ROCReal._debug("pack %r", value)
        raise NotImplementedError("packing ROCReal is not supported")

    def unpack(self, registers):
        if _debug: ROCReal._debug("unpack %r", registers)

        # byte-swap the registers
        r0, r1 = registers
        r0 = ((r0 & 0xFF00) >> 8) | ((r0 & 0x00FF) << 8)
        r1 = ((r1 & 0xFF00) >> 8) | ((r1 & 0x00FF) << 8)

        value, = struct.unpack(">f", struct.pack(">HH", r1, r0))
        return value

@bacpypes_debugging
class BigEndianDoubleInt(_Struct):

    """
    This class packs and unpacks a pair of registers as a bit endian 32-bit signed integer.
    """

    registerLength = 2

    def pack(self, value):
        if _debug: BigEndianDoubleInt._debug("pack %r", value)

        return [value & 0xFFFF, (value >> 16) & 0xFFFF]

    def unpack(self, registers):
        if _debug: BigEndianDoubleInt._debug("unpack %r", registers)

        value = (registers[1] << 16) | registers[0]
        if (value & 0x80000000):
            value = (-1 << 32) | value

        return value

@bacpypes_debugging
class BigEndianUnsignedDoubleInt(_Struct):

    """
    This class packs and unpacks a pair of registers as a bit endian 32-bit unsigned integer.
    """

    registerLength = 2

    def pack(self, value):
        if _debug: BigEndianUnsignedDoubleInt._debug("pack %r", value)

        return [value & 0xFFFF, (value >> 16) & 0xFFFF]

    def unpack(self, registers):
        if _debug: BigEndianUnsignedDoubleInt._debug("unpack %r", registers)

        return (registers[1] << 16) | registers[0]

@bacpypes_debugging
class BigEndianReal(_Struct):

    registerLength = 2

    def pack(self, value):
        if _debug: BigEndianReal._debug("pack %r", value)

        # make sure it's a float
        if not isinstance(value, float):
            BigEndianReal._error("packing error: %r is not a float", value)
            value = 0.0

        registers = struct.unpack(">HH", struct.pack(">f", value))
        return [registers[0], registers[1]]

    def unpack(self, registers):
        if _debug: BigEndianReal._debug("unpack %r", registers)

        value, = struct.unpack(">f", struct.pack(">HH", registers[0], registers[1]))
        return value

@bacpypes_debugging
class String(_Struct):

    """
    This class packs and unpacks a list of registers as a null terminated string.
    """

    def __init__(self, registerLength=6):
       if _debug: String._debug("__init__ %r", registerLength)

       # save the length
       self.registerLength = registerLength

    def pack(self, value):
        if _debug: String._debug("pack %r", value)
        raise NotImplementedError("packing strings is not implemeted")

    def unpack(self, registers):
        if _debug: String._debug("unpack %r", registers)

        octets = []
        for reg in registers:
            octets.append(reg >> 8)
            octets.append(reg & 0xFF)

        value = ''.join(chr(c) for c in octets)
        value = value[:value.find('\x00')]
        return value

@bacpypes_debugging
class BigEndianString(_Struct):

    """
    This class packs and unpacks a list of registers as a null terminated string.
    """

    def __init__(self, registerLength=6):
       if _debug: String._debug("__init__ %r", registerLength)

       # save the length
       self.registerLength = registerLength

    def pack(self, value):
        if _debug: String._debug("pack %r", value)
        raise NotImplementedError("packing strings is not implemeted")

    def unpack(self, registers):
        if _debug: String._debug("unpack %r", registers)

        octets = []
        for reg in registers:
            octets.append(reg & 0xFF)
            octets.append(reg >> 8)

        value = ''.join(chr(c) for c in octets)
        value = value[:value.find('\x00')]
        return value

#
#   ModbusStruct
#

ModbusStruct = {
    'byte': Byte(),
    'int': Int(),
    'uint': UnsignedInt(),
    'dint': DoubleInt(),
    'udint': UnsignedDoubleInt(),
    'real': Real(),
    'roc-real': ROCReal(),
    'be-dint': BigEndianDoubleInt(),
    'be-udint': BigEndianUnsignedDoubleInt(),
    'be-real': BigEndianReal(),
    'str': String(),
    'be-str': BigEndianString(),
    }

#
#  MPCI
#

@bacpypes_debugging
class MPCI(PCI, DebugContents):

    """
    This class contains the MODBUS protocol control information which
    is the 8 octet header at the front of all MODBUS PDUs.
    """

    _debug_contents = (
        'mpduTransactionID',
        'mpduProtocolID',
        'mpduLength',
        'mpduUnitID',
        'mpduFunctionCode',
        )

    readCoils                       = 1
    readDiscreteInputs              = 2
    readMultipleRegisters           = 3
    readInputRegisters              = 4
    writeSingleCoil                 = 5
    writeSingleRegister             = 6
    writeMultipleCoils              = 15
    writeMultipleRegisters          = 16
    readWriteMultipleRegisters      = 23
    announceMaster                  = 100
    registerSlave                   = 105

    def __init__(self, *args, **kwargs):
        if _debug: MPCI._debug("__init__ %r %r", args, kwargs)
        PCI.__init__(self, *args, **kwargs)
        self.mpduTransactionID = 0
        self.mpduProtocolID = 0
        self.mpduLength = None
        self.mpduUnitID = 0
        self.mpduFunctionCode = None

    def update(self, mpci):
        if _debug: MPCI._debug("update %r", mpci)

        PCI.update(self, mpci)
        self.mpduTransactionID = mpci.mpduTransactionID
        self.mpduProtocolID = mpci.mpduProtocolID
        self.mpduLength = mpci.mpduLength
        self.mpduUnitID = mpci.mpduUnitID
        self.mpduFunctionCode = mpci.mpduFunctionCode

    def encode(self, pdu):
        """Encode the contents into the PDU."""
        if _debug: MPCI._debug("encode %r", pdu)

        PCI.update(pdu, self)

        pdu.put_short(self.mpduTransactionID)
        pdu.put_short(self.mpduProtocolID)
        pdu.put_short(self.mpduLength)
        pdu.put(self.mpduUnitID)
        pdu.put(self.mpduFunctionCode)

    def decode(self, pdu):
        """Decode the contents of the PDU."""
        if _debug: MPCI._debug("decode %r", pdu)

        PCI.update(self, pdu)

        self.mpduTransactionID = pdu.get_short()
        self.mpduProtocolID = pdu.get_short()
        self.mpduLength = pdu.get_short()
        self.mpduUnitID = pdu.get()
        self.mpduFunctionCode = pdu.get()

        # check the length
        if self.mpduLength != len(pdu.pduData) + 2:
            raise DecodingError("invalid length")

#
#   MPDU
#

@bacpypes_debugging
class MPDU(MPCI, PDUData):

    """
    This class is a generic MODBUS PDU.  It inherits the :class:`MPCI`
    layer and the more generic PDU data functions.
    """

    def __init__(self, *args, **kwargs):
        if _debug: MPDU._debug("__init__ %r %r", args, kwargs)

        MPCI.__init__(self, **kwargs)
        PDUData.__init__(self, *args)

    def encode(self, pdu):
        if _debug: MPDU._debug("encode %r", pdu)

        MPCI.encode(self, pdu)
        pdu.put_data(self.pduData)

    def decode(self, pdu):
        if _debug: MPDU._debug("decode %r", pdu)

        MPCI.decode(self, pdu)
        self.pduData = pdu.get_data(len(pdu.pduData))

#------------------------------

@bacpypes_debugging
class ReadBitsRequestBase(MPCI, DebugContents):

    """
    Base class for messages requesting bit values.  This is inherited by
    both :class:`ReadCoilsRequest` and :class:`ReadDiscreteInputsRequest`.
    """

    _debug_contents = ('address', 'count')

    def __init__(self, address, count, **kwargs):
        if _debug: ReadBitsRequestBase._debug("__init__ %r %r %r", address, count, kwargs)

        MPCI.__init__(self, **kwargs)
        self.address = address
        self.count = count

    def encode(self, pdu):
        if _debug: ReadBitsRequestBase._debug("encode %r", pdu)

        MPCI.update(pdu, self)
        pdu.put_short(self.address)
        pdu.put_short(self.count)
        pdu.mpduLength = len(pdu.pduData) + 2

    def decode(self, pdu):
        if _debug: ReadBitsRequestBase._debug("decode %r", pdu)

        MPCI.update(self, pdu)
        self.address = pdu.get_short()
        self.count = pdu.get_short()

@bacpypes_debugging
class ReadBitsResponseBase(MPCI, DebugContents):

    """
    Base class for messages that are responses to reading bit values.
    This is inherited by both :class:`ReadCoilsResponse` and
    :class:`ReadDiscreteInputsResponse`.
    """

    _debug_contents = ('bits',)

    def __init__(self, values=None, **kwargs):
        if _debug: ReadBitsResponseBase._debug("__init__ %r %r", values, kwargs)

        MPCI.__init__(self, **kwargs)
        if values is not None:
            self.bits = values
        else:
            self.bits = []

    def encode(self, pdu):
        if _debug: ReadBitsResponseBase._debug("encode %r", pdu)

        MPCI.update(pdu, self)

        stringbits = _packBitsToString(self.bits)
        if _debug: ReadBitsResponseBase._debug("    - stringbits: %r", stringbits)

        pdu.put(len(stringbits))
        pdu.put_data(stringbits)
        pdu.mpduLength = len(pdu.pduData) + 2

    def decode(self, pdu):
        if _debug: ReadBitsResponseBase._debug("decode %r", pdu)

        MPCI.update(self, pdu)
        datalen = pdu.get()
        self.bits = _unpackBitsFromString(pdu.get_data(datalen))

@bacpypes_debugging
class ReadRegistersRequestBase(MPCI, DebugContents):

    """
    Base class for messages requesting register values.
    This is inherited by both :class:`ReadMultipleRegistersRequest` and
    :class:`ReadInputRegistersRequest`.
    """

    _debug_contents = ('address', 'count')

    def __init__(self, address=None, count=None, **kwargs):
        if _debug: ReadRegistersRequestBase._debug("__init__ %r %r %r", address, count, kwargs)

        MPCI.__init__(self, **kwargs)
        self.address = address
        self.count = count

    def encode(self, pdu):
        if _debug: ReadRegistersRequestBase._debug("encode %r", pdu)

        MPCI.update(pdu, self)
        pdu.put_short(self.address)
        pdu.put_short(self.count)
        pdu.mpduLength = len(pdu.pduData) + 2

    def decode(self, pdu):
        if _debug: ReadRegistersRequestBase._debug("decode %r", pdu)

        MPCI.update(self, pdu)
        self.address = pdu.get_short()
        self.count = pdu.get_short()

@bacpypes_debugging
class ReadRegistersResponseBase(MPCI, DebugContents):

    """
    Base class for messages requesting register values.
    This is inherited by both :class:`ReadMultipleRegistersResponse` and
    :class:`ReadInputRegistersResponse`.
    """

    _debug_contents = ('registers',)

    def __init__(self, values=None, **kwargs):
        if _debug: ReadRegistersResponseBase._debug("__init__ %r %r", values, kwargs)

        MPCI.__init__(self, **kwargs)
        if values is not None:
            self.registers = values
        else:
            self.registers = []

    def encode(self, pdu):
        if _debug: ReadRegistersResponseBase._debug("encode %r", pdu)

        MPCI.update(pdu, self)
        pdu.put(len(self.registers) * 2)
        for reg in self.registers:
            pdu.put_short(reg)
        pdu.mpduLength = len(pdu.pduData) + 2

    def decode(self, pdu):
        if _debug: ReadRegistersResponseBase._debug("decode %r", pdu)

        MPCI.update(self, pdu)
        datalen = pdu.get()
        self.registers = []
        for i in range(datalen // 2):
            self.registers.append(pdu.get_short())

@bacpypes_debugging
class ReadWriteValueBase(MPCI, DebugContents):

    """
    Base class for messages reading and writing values.  This class is
    inherted by :class:`WriteSingleCoilRequest`, :class:`WriteSingleCoilResponse`,
    :class:`WriteSingleRegisterRequest`,  and :class:`WriteSingleRegisterResponse`.
    """

    _debug_contents = ('address', 'value')

    def __init__(self, address=None, value=None, **kwargs):
        if _debug: ReadWriteValueBase._debug("__init__ %r %r %r", address, value, kwargs)

        MPCI.__init__(self, **kwargs)
        self.address = address
        self.value = value

    def encode(self, pdu):
        if _debug: ReadWriteValueBase._debug("encode %r", pdu)

        MPCI.update(pdu, self)
        pdu.put_short(self.address)
        pdu.put_short(self.value)
        pdu.mpduLength = len(pdu.pduData) + 2

    def decode(self, pdu):
        if _debug: ReadWriteValueBase._debug("decode %r", pdu)

        MPCI.update(self, pdu)
        self.address = pdu.get_short()
        self.value = pdu.get_short()

#------------------------------

#
#   ReadCoils
#

@bacpypes_debugging
class ReadCoilsRequest(ReadBitsRequestBase):

    """
    Read Coils Request
    """

    functionCode = MPCI.readCoils

    def __init__(self, address=None, count=None, **kwargs):
        if _debug: ReadCoilsRequest._debug("__init__ %r %r %r", address, count, kwargs)

        ReadBitsRequestBase.__init__(self, address, count, **kwargs)
        self.mpduFunctionCode = ReadCoilsRequest.functionCode

register_request_type(ReadCoilsRequest)

@bacpypes_debugging
class ReadCoilsResponse(ReadBitsResponseBase):

    """
    Read Coils Response
    """

    functionCode = MPCI.readCoils

    def __init__(self, values=None, **kwargs):
        if _debug: ReadCoilsResponse._debug("__init__ %r %r", values, kwargs)

        ReadBitsResponseBase.__init__(self, values, **kwargs)
        self.mpduFunctionCode = ReadCoilsResponse.functionCode

register_response_type(ReadCoilsResponse)

#
#   ReadDescreteInputs
#

@bacpypes_debugging
class ReadDiscreteInputsRequest(ReadBitsRequestBase):

    """
    Read Discrete Inputs Request
    """

    functionCode = MPCI.readDiscreteInputs

    def __init__(self, address=None, count=None, **kwargs):
        if _debug: ReadDiscreteInputsRequest._debug("__init__ %r %r %r", address, count, kwargs)

        ReadBitsRequestBase.__init__(self, address, count, **kwargs)
        self.mpduFunctionCode = ReadDiscreteInputsRequest.functionCode

register_request_type(ReadDiscreteInputsRequest)

@bacpypes_debugging
class ReadDiscreteInputsResponse(ReadBitsResponseBase):

    """
    Read Discrete Inputs Response
    """

    functionCode = MPCI.readDiscreteInputs

    def __init__(self, values=None, **kwargs):
        if _debug: ReadDiscreteInputsResponse._debug("__init__ %r %r", values, kwargs)

        ReadBitsResponseBase.__init__(self, values, **kwargs)
        self.mpduFunctionCode = ReadDiscreteInputsResponse.functionCode

register_response_type(ReadDiscreteInputsResponse)

#
#   ReadMultipleRegisters
#

@bacpypes_debugging
class ReadMultipleRegistersRequest(ReadRegistersRequestBase):

    """
    Read Multiple Registers Request
    """

    functionCode = MPCI.readMultipleRegisters

    def __init__(self, address=None, count=None, **kwargs):
        if _debug: ReadMultipleRegistersRequest._debug("__init__ %r %r %r", address, count, kwargs)

        ReadRegistersRequestBase.__init__(self, address, count, **kwargs)
        self.mpduFunctionCode = ReadMultipleRegistersRequest.functionCode

register_request_type(ReadMultipleRegistersRequest)

@bacpypes_debugging
class ReadMultipleRegistersResponse(ReadRegistersResponseBase):

    """
    Read Multiple Registers Response
    """

    functionCode = MPCI.readMultipleRegisters

    def __init__(self, values=None, **kwargs):
        if _debug: ReadMultipleRegistersResponse._debug("__init__ %r %r", values, kwargs)

        ReadRegistersResponseBase.__init__(self, values, **kwargs)
        self.mpduFunctionCode = ReadMultipleRegistersResponse.functionCode

register_response_type(ReadMultipleRegistersResponse)

#
#   ReadInputRegisters
#

@bacpypes_debugging
class ReadInputRegistersRequest(ReadRegistersRequestBase):

    """
    Read Input Registers Request
    """

    functionCode = MPCI.readInputRegisters

    def __init__(self, address=None, count=None, **kwargs):
        if _debug: ReadInputRegistersRequest._debug("__init__ %r %r %r", address, count, kwargs)

        ReadRegistersRequestBase.__init__(self, address, count, **kwargs)
        self.mpduFunctionCode = ReadInputRegistersRequest.functionCode

register_request_type(ReadInputRegistersRequest)

@bacpypes_debugging
class ReadInputRegistersResponse(ReadRegistersResponseBase):

    """
    Read Input Registers Response
    """

    functionCode = MPCI.readInputRegisters

    def __init__(self, values=None, **kwargs):
        if _debug: ReadInputRegistersResponse._debug("__init__ %r %r", values, kwargs)

        ReadRegistersResponseBase.__init__(self, values, **kwargs)
        self.mpduFunctionCode = ReadInputRegistersResponse.functionCode

register_response_type(ReadInputRegistersResponse)

#
#   WriteSingleCoil
#

@bacpypes_debugging
class WriteSingleCoilRequest(ReadWriteValueBase):

    """
    Write Single Coil Request
    """

    functionCode = MPCI.writeSingleCoil

    def __init__(self, address=None, value=None, **kwargs):
        if _debug: WriteSingleCoilRequest._debug("__init__ %r %r %r", address, value, kwargs)

        ReadWriteValueBase.__init__(self, address, value, **kwargs)
        self.mpduFunctionCode = WriteSingleCoilRequest.functionCode

register_request_type(WriteSingleCoilRequest)

@bacpypes_debugging
class WriteSingleCoilResponse(ReadWriteValueBase):

    """
    Write Single Coil Response
    """

    functionCode = MPCI.writeSingleCoil

    def __init__(self, address=None, value=None, **kwargs):
        if _debug: WriteSingleCoilResponse._debug("__init__ %r %r %r", address, value, kwargs)

        ReadWriteValueBase.__init__(self, address, value, **kwargs)
        self.mpduFunctionCode = WriteSingleCoilResponse.functionCode

register_response_type(WriteSingleCoilResponse)

#
#   WriteSingleRegister
#

@bacpypes_debugging
class WriteSingleRegisterRequest(ReadWriteValueBase):

    """
    Write Single Register Request
    """

    functionCode = MPCI.writeSingleRegister

    def __init__(self, address=None, value=None, **kwargs):
        if _debug: WriteSingleRegisterRequest._debug("__init__ %r %r %r", address, value, kwargs)

        ReadWriteValueBase.__init__(self, address, value, **kwargs)
        self.mpduFunctionCode = WriteSingleRegisterRequest.functionCode

register_request_type(WriteSingleRegisterRequest)

@bacpypes_debugging
class WriteSingleRegisterResponse(ReadWriteValueBase):

    """
    Write Single Register Response
    """

    functionCode = MPCI.writeSingleRegister

    def __init__(self, address=None, value=None, **kwargs):
        if _debug: WriteSingleRegisterResponse._debug("__init__ %r %r %r", address, value, kwargs)

        ReadWriteValueBase.__init__(self, address, value, **kwargs)
        self.mpduFunctionCode = WriteSingleRegisterResponse.functionCode

register_response_type(WriteSingleRegisterResponse)

#
#   WriteMultipleCoils
#

@bacpypes_debugging
class WriteMultipleCoilsRequest(MPCI, DebugContents):

    """
    Write Multiple Coils Request
    """

    _debug_contents = ('address', 'count', 'coils')

    functionCode = MPCI.writeMultipleCoils

    def __init__(self, address=None, count=None, coils=None, **kwargs):
        if _debug: WriteMultipleCoilsRequest._debug("__init__ %r %r %r %r", address, count, coils, kwargs)

        MPCI.__init__(self, **kwargs)
        self.mpduFunctionCode = WriteMultipleCoilsRequest.functionCode
        self.address = address
        self.count = count
        if coils is not None:
            self.coils = coils
        else:
            self.coils = [False] * count

    def encode(self, pdu):
        if _debug: WriteMultipleCoilsRequest._debug("encode %r", pdu)

        MPCI.update(pdu, self)

        pdu.put_short(self.address)
        pdu.put_short(self.count)

        stringbits = _packBitsToString(self.coils)
        pdu.put(len(stringbits))
        pdu.put_data(stringbits)
        pdu.mpduLength = len(pdu.pduData) + 2

    def decode(self, pdu):
        if _debug: WriteMultipleCoilsRequest._debug("decode %r", pdu)

        MPCI.update(self, pdu)

        self.address = pdu.get_short()
        self.count = pdu.get_short()

        datalen = pdu.get()
        coils = _unpackBitsFromString(pdu.get_data(datalen))
        self.coils = coils[:self.count]

register_request_type(WriteMultipleCoilsRequest)

@bacpypes_debugging
class WriteMultipleCoilsResponse(MPCI, DebugContents):

    """
    Write Multiple Coils Response
    """

    _debug_contents = ('address', 'count')

    functionCode = MPCI.writeMultipleCoils

    def __init__(self, address=None, count=None, **kwargs):
        if _debug: WriteMultipleCoilsResponse._debug("__init__ %r %r %r", address, count, kwargs)

        MPCI.__init__(self, **kwargs)
        self.mpduFunctionCode = WriteMultipleCoilsResponse.functionCode
        self.address = address
        self.count = count

    def encode(self, pdu):
        if _debug: WriteMultipleCoilsResponse._debug("encode %r", pdu)

        MPCI.update(pdu, self)
        pdu.put_short(self.address)
        pdu.put_short(self.count)
        pdu.mpduLength = len(pdu.pduData) + 2

    def decode(self, pdu):
        if _debug: WriteMultipleCoilsResponse._debug("decode %r", pdu)

        MPCI.update(self, pdu)
        self.address = pdu.get_short()
        self.count = pdu.get_short()

register_response_type(WriteMultipleCoilsResponse)

#
#   WriteMultipleRegisters
#

@bacpypes_debugging
class WriteMultipleRegistersRequest(MPCI, DebugContents):

    """
    Write Multiple Registers Request
    """

    _debug_contents = ('address', 'count', 'registers')

    functionCode = MPCI.writeMultipleRegisters

    def __init__(self, address=None, count=None, registers=None, **kwargs):
        if _debug: WriteMultipleRegistersRequest._debug("__init__ %r %r %r %r", address, count, registers, kwargs)

        MPCI.__init__(self, **kwargs)
        self.mpduFunctionCode = WriteMultipleRegistersRequest.functionCode
        self.address = address
        self.count = count
        if registers is not None:
            self.registers = registers
        elif count is not None:
            self.registers = [0] * self.count
        else:
            self.registers = None

    def encode(self, pdu):
        if _debug: WriteMultipleRegistersRequest._debug("encode %r", pdu)

        MPCI.update(pdu, self)
        pdu.put_short(self.address)
        pdu.put_short(self.count)

        pdu.put(len(self.registers) * 2)
        for reg in self.registers:
            pdu.put_short(reg)
        pdu.mpduLength = len(pdu.pduData) + 2

    def decode(self, pdu):
        if _debug: WriteMultipleRegistersRequest._debug("decode %r", pdu)

        MPCI.update(self, pdu)

        self.address = pdu.get_short()
        self.count = pdu.get_short()

        datalen = pdu.get()
        self.registers = []
        for i in range(datalen // 2):
            self.registers.append(pdu.get_short())

register_request_type(WriteMultipleRegistersRequest)

@bacpypes_debugging
class WriteMultipleRegistersResponse(MPCI, DebugContents):

    """
    Write Multiple Registers Response
    """

    _debug_contents = ('address', 'count')

    functionCode = MPCI.writeMultipleRegisters

    def __init__(self, address=None, count=None, **kwargs):
        if _debug: WriteMultipleRegistersResponse._debug("__init__ %r %r %r", address, count, kwargs)

        MPCI.__init__(self, **kwargs)
        self.mpduFunctionCode = WriteMultipleRegistersResponse.functionCode
        self.address = address
        self.count = count

    def encode(self, pdu):
        if _debug: WriteMultipleRegistersResponse._debug("encode %r", pdu)

        MPCI.update(pdu, self)
        pdu.put_short(self.address)
        pdu.put_short(self.count)
        pdu.mpduLength = len(pdu.pduData) + 2

    def decode(self, pdu):
        if _debug: WriteMultipleRegistersResponse._debug("decode %r", pdu)

        MPCI.update(self, pdu)
        self.address = pdu.get_short()
        self.count = pdu.get_short()

register_response_type(WriteMultipleRegistersResponse)

#
#   ReadWriteMultipleRegistersRequest
#

@bacpypes_debugging
class ReadWriteMultipleRegistersRequest(MPCI, DebugContents):

    """
    Read Write Multiple Registers Request
    """

    _debug_contents = ('raddress', 'rcount', 'waddress', 'wcount', 'registers')

    functionCode = MPCI.readWriteMultipleRegisters

    def __init__(self, raddress=None, rcount=None, waddress=None, wcount=None, registers=None, **kwargs):
        if _debug: ReadWriteMultipleRegistersRequest._debug("__init__ %r %r %r %r %r %r", raddress, rcount, waddress, wcount, registers, kwargs)

        MPCI.__init__(self, **kwargs)
        self.mpduFunctionCode = ReadWriteMultipleRegistersRequest.functionCode
        self.raddress = raddress
        self.rcount = rcount
        self.waddress = waddress
        self.wcount = wcount
        if registers is not None:
            self.registers = registers
        else:
            self.registers = [0] * wcount

    def encode(self, pdu):
        if _debug: ReadWriteMultipleRegistersRequest._debug("encode %r", pdu)

        MPCI.update(pdu, self)

        pdu.put_short(self.raddress)
        pdu.put_short(self.rcount)
        pdu.put_short(self.waddress)
        pdu.put_short(self.wcount)

        pdu.put(len(self.registers) * 2)
        for reg in self.registers:
            pdu.put_short(reg)
        pdu.mpduLength = len(pdu.pduData) + 2

    def decode(self, pdu):
        if _debug: ReadWriteMultipleRegistersRequest._debug("decode %r", pdu)

        MPCI.update(self, pdu)
        self.raddress = pdu.get_short()
        self.rcount = pdu.get_short()
        self.waddress = pdu.get_short()
        self.wcount = pdu.get_short()

        datalen = pdu.get()
        self.registers = []
        for i in range(datalen // 2):
            self.registers.append(pdu.get_short())

register_request_type(ReadWriteMultipleRegistersRequest)

@bacpypes_debugging
class ReadWriteMultipleRegistersResponse(MPCI, DebugContents):

    """
    Read Write Multiple Registers Response
    """

    _debug_contents = ('registers',)

    functionCode = MPCI.readWriteMultipleRegisters

    def __init__(self, registers=None, **kwargs):
        if _debug: ReadWriteMultipleRegistersResponse._debug("__init__ %r %r", registers, kwargs)

        MPCI.__init__(self, **kwargs)
        self.mpduFunctionCode = ReadWriteMultipleRegistersResponse.functionCode
        if registers is not None:
            self.registers = registers
        else:
            self.registers = []

    def encode(self, pdu):
        if _debug: ReadWriteMultipleRegistersResponse._debug("encode %r", pdu)

        MPCI.update(pdu, self)
        pdu.put(len(self.registers) * 2)
        for reg in self.registers:
            pdu.put_short(reg)
        pdu.mpduLength = len(pdu.pduData) + 2

    def decode(self, pdu):
        if _debug: ReadWriteMultipleRegistersResponse._debug("decode %r", pdu)

        MPCI.update(self, pdu)
        datalen = pdu.get()
        self.registers = []
        for i in range(datalen // 2):
            self.registers.append(pdu.get_short())

register_response_type(ReadWriteMultipleRegistersResponse)

#
#   ExceptionResponse
#

@bacpypes_debugging
class ExceptionResponse(MPCI, DebugContents):

    """
    Exception Response
    """

    _debug_contents = ('exceptionCode',)

    ILLEGAL_FUNCTION                        = 0x01
    ILLEGAL_DATA_ADDRESS                    = 0x02
    ILLEGAL_DATA_VALUE                      = 0x03
    ILLEGAL_RESPONSE_LENGTH                 = 0x04
    ACKNOWLEDGE                             = 0x05
    SLAVE_DEVICE_BUSY                       = 0x06
    NEGATIVE_ACKNOWLEDGE                    = 0x07
    MEMORY_PARITY_ERROR                     = 0x08
    GATEWAY_PATH_UNAVAILABLE                = 0x0A
    GATEWAY_TARGET_DEVICE_FAILED_TO_RESPOND = 0x0B

    def __init__(self, function=None, exceptionCode=None, **kwargs):
        if _debug: ExceptionResponse._debug("__init__ %r %r %r", function, exceptionCode, kwargs)

        MPCI.__init__(self, **kwargs)
        if function is not None:
            self.mpduFunctionCode = function + 128
        else:
            self.mpduFunctionCode = None
        self.exceptionCode = exceptionCode

    def encode(self, pdu):
        if _debug: ExceptionResponse._debug("encode %r", pdu)

        MPCI.update(pdu, self)
        pdu.put(self.exceptionCode)
        pdu.mpduLength = len(pdu.pduData) + 2

    def decode(self, pdu):
        if _debug: ExceptionResponse._debug("decode %r", pdu)

        MPCI.update(self, pdu)
        self.exceptionCode = pdu.get()

