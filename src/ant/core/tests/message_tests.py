# -*- coding: utf-8 -*-
# pylint: disable=missing-docstring, invalid-name
##############################################################################
#
# Copyright (c) 2011, Martín Raúl Villalba
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.
#
##############################################################################

from __future__ import division, absolute_import, print_function, unicode_literals

import unittest

from ant.core.exceptions import MessageError
from ant.core.constants import MESSAGE_SYSTEM_RESET, MESSAGE_CHANNEL_ASSIGN
from ant.core.message import Message
from ant.core import message as msg


class MessageTest(unittest.TestCase):
    def setUp(self):
        self.message = Message(type_=0x00)

    def test_get_payload(self):
        with self.assertRaises(MessageError):
            self.message.payload = b'\xFF' * 15
        self.message.payload = b'\x11' * 5
        self.assertEquals(self.message.payload, b'\x11' * 5)

    def test_get_setType(self):
        with self.assertRaises(MessageError):
            Message(-1)
        with self.assertRaises(MessageError):
            Message(300)
        self.message.type = 0x23
        self.assertEquals(self.message.type, 0x23)

    def test_getChecksum(self):
        self.message = Message(type_=MESSAGE_SYSTEM_RESET, payload=bytearray(1))
        self.assertEquals(self.message.checksum, 0xEF)
        self.message = Message(type_=MESSAGE_CHANNEL_ASSIGN,
                               payload=bytearray(3))
        self.assertEquals(self.message.checksum, 0xE5)

    def test_size(self):
        self.message.payload = b'\x11' * 7
        self.assertEquals(len(self.message), 11)

    def test_encode(self):
        self.message = Message(type_=MESSAGE_CHANNEL_ASSIGN,
                               payload=bytearray(3))
        self.assertEqual(self.message.encode(),
                         b'\xA4\x03\x42\x00\x00\x00\xE5')

    def test_decode(self):
        self.assertRaises(MessageError, Message.decode,
                          b'\xA5\x03\x42\x00\x00\x00\xE5')
        self.assertRaises(MessageError, Message.decode,
                          b'\xA4\x14\x42' + (b'\x00' * 20) + b'\xE5')
        self.assertRaises(MessageError, Message.decode,
                          b'\xA4\x03\x42\x01\x02\xF3\xE5')
        msg_ = Message.decode(b'\xA4\x03\x42\x00\x00\x00\xE5')
        self.assertEqual(len(msg_), 7)
        self.assertEqual(msg_.type, MESSAGE_CHANNEL_ASSIGN)
        self.assertEqual(msg_.payload, b'\x00' * 3)
        self.assertEqual(msg_.checksum, 0xE5)
        
        handler = Message.decode(b'\xA4\x03\x42\x00\x00\x00\xE5')
        self.assertTrue(isinstance(handler, msg.ChannelAssignMessage))
        self.assertRaises(MessageError, Message.decode,
                          b'\xA4\x03\xFF\x00\x00\x00\xE5')
        self.assertRaises(MessageError, Message.decode,
                          b'\xA4\x03\x42')
        self.assertRaises(MessageError, Message.decode,
                          b'\xA4\x05\x42\x00\x00\x00\x00')


class ChannelMessageTest(unittest.TestCase):
    def setUp(self):
        self.message = msg.ChannelMessage(type_=MESSAGE_SYSTEM_RESET)

    def test_get_ChannelNumber(self):
        self.assertEquals(self.message.channelNumber, 0)
        self.message.channelNumber = 3
        self.assertEquals(self.message.channelNumber, 3)


class ChannelUnassignMessageTest(unittest.TestCase):
    # No currently defined methods need testing
    pass


class ChannelAssignMessageTest(unittest.TestCase):
    def setUp(self):
        self.message = msg.ChannelAssignMessage()

    def test_get_channelType(self):
        self.message.channelType = 0x10
        self.assertEquals(self.message.channelType, 0x10)

    def test_get_networkNumber(self):
        self.message.networkNumber = 0x11
        self.assertEquals(self.message.networkNumber, 0x11)

    def test_payload(self):
        self.message.channelNumber = 0x01
        self.message.channelType = 0x02
        self.message.networkNumber = 0x03
        self.assertEquals(self.message.payload, b'\x01\x02\x03')


class ChannelIDMessageTest(unittest.TestCase):
    def setUp(self):
        self.message = msg.ChannelIDMessage()

    def test_get_deviceNumber(self):
        self.message.deviceNumber = 0x10FA
        self.assertEquals(self.message.deviceNumber, 0x10FA)

    def test_get_deviceType(self):
        self.message.deviceType = 0x10
        self.assertEquals(self.message.deviceType, 0x10)

    def test_get_transmissionType(self):
        self.message.transmissionType = 0x11
        self.assertEquals(self.message.transmissionType, 0x11)

    def test_payload(self):
        self.message.channelNumber = 0x01
        self.message.deviceNumber = 0x0302
        self.message.deviceType = 0x04
        self.message.transmissionType = 0x05
        self.assertEquals(self.message.payload, b'\x01\x02\x03\x04\x05')


class ChannelPeriodMessageTest(unittest.TestCase):
    def setUp(self):
        self.message = msg.ChannelPeriodMessage()

    def test_get_channelPeriod(self):
        self.message.channelPeriod = 0x10FA
        self.assertEquals(self.message.channelPeriod, 0x10FA)

    def test_payload(self):
        self.message.channelNumber = 0x01
        self.message.channelPeriod = 0x0302
        self.assertEquals(self.message.payload, b'\x01\x02\x03')


class ChannelSearchTimeoutMessageTest(unittest.TestCase):
    def setUp(self):
        self.message = msg.ChannelSearchTimeoutMessage()

    def test_get_setTimeout(self):
        self.message.timeout = 0x10
        self.assertEquals(self.message.timeout, 0x10)

    def test_payload(self):
        self.message.channelNumber = 0x01
        self.message.timeout = 0x02
        self.assertEquals(self.message.payload, b'\x01\x02')


class ChannelFrequencyMessageTest(unittest.TestCase):
    def setUp(self):
        self.message = msg.ChannelFrequencyMessage()

    def test_get_setFrequency(self):
        self.message.frequency = 22
        self.assertEquals(self.message.frequency, 22)

    def test_payload(self):
        self.message.channelNumber = 0x01
        self.message.frequency = 0x02
        self.assertEquals(self.message.payload, b'\x01\x02')


class ChannelTXPowerMessageTest(unittest.TestCase):
    def setUp(self):
        self.message = msg.ChannelTXPowerMessage()

    def test_get_setPower(self):
        self.message.power = 0xFA
        self.assertEquals(self.message.power, 0xFA)

    def test_payload(self):
        self.message.channelNumber = 0x01
        self.message.power = 0x02
        self.assertEquals(self.message.payload, b'\x01\x02')


class NetworkKeyMessageTest(unittest.TestCase):
    def setUp(self):
        self.message = msg.NetworkKeyMessage()

    def test_get_setNumber(self):
        self.message.number = 0xFA
        self.assertEquals(self.message.number, 0xFA)

    def test_get_setKey(self):
        self.message.key = b'\xFD' * 8
        self.assertEquals(self.message.key, b'\xFD' * 8)

    def test_payload(self):
        self.message.number = 0x01
        self.message.key = b'\x02\x03\x04\x05\x06\x07\x08\x09'
        self.assertEquals(self.message.payload,
                          b'\x01\x02\x03\x04\x05\x06\x07\x08\x09')


class TXPowerMessageTest(unittest.TestCase):
    def setUp(self):
        self.message = msg.TXPowerMessage()

    def test_get_setPower(self):
        self.message.power = 0xFA
        self.assertEquals(self.message.power, 0xFA)

    def test_payload(self):
        self.message.power = 0x01
        self.assertEquals(self.message.payload, b'\x00\x01')


class SystemResetMessageTest(unittest.TestCase):
    # No currently defined methods need testing
    pass


class ChannelOpenMessageTest(unittest.TestCase):
    # No currently defined methods need testing
    pass


class ChannelCloseMessageTest(unittest.TestCase):
    # No currently defined methods need testing
    pass


class ChannelRequestMessageTest(unittest.TestCase):
    def setUp(self):
        self.message = msg.ChannelRequestMessage()

    def test_get_messageID(self):
        with self.assertRaises(MessageError):
            self.message.messageID = 0xFFFF
        self.message.messageID = 0xFA
        self.assertEquals(self.message.messageID, 0xFA)

    def test_payload(self):
        self.message.channelNumber = 0x01
        self.message.messageID = 0x02
        self.assertEquals(self.message.payload, b'\x01\x02')


class ChannelBroadcastDataMessageTest(unittest.TestCase):
    # No currently defined methods need testing
    pass


class ChannelAcknowledgedDataMessageTest(unittest.TestCase):
    # No currently defined methods need testing
    pass


class ChannelBurstDataMessageTest(unittest.TestCase):
    # No currently defined methods need testing
    pass


class ChannelEventMessageTest(unittest.TestCase):
    def setUp(self):
        self.message = msg.ChannelEventMessage()

    def test_get_messageID(self):
        with self.assertRaises(MessageError):
            self.message.messageID = 0xFFFF
        self.message.messageID = 0xFA
        self.assertEquals(self.message.messageID, 0xFA)

    def test_get_messageCode(self):
        with self.assertRaises(MessageError):
            self.message.messageCode = 0xFFFF
        self.message.messageCode = 0xFA
        self.assertEquals(self.message.messageCode, 0xFA)

    def test_payload(self):
        self.message.channelNumber = 0x01
        self.message.messageID = 0x02
        self.message.messageCode = 0x03
        self.assertEquals(self.message.payload, b'\x01\x02\x03')


class ChannelStatusMessageTest(unittest.TestCase):
    def setUp(self):
        self.message = msg.ChannelStatusMessage()

    def test_get_status(self):
        with self.assertRaises(MessageError):
            self.message.status = 0xFFFF
        self.message.status = 0xFA
        self.assertEquals(self.message.status, 0xFA)

    def test_payload(self):
        self.message.channelNumber = 0x01
        self.message.status = 0x02
        self.assertEquals(self.message.payload, b'\x01\x02')


class VersionMessageTest(unittest.TestCase):
    def setUp(self):
        self.message = msg.VersionMessage()

    def test_get_version(self):
        with self.assertRaises(MessageError):
            self.message.version =  '1234'
        self.message.version = b'\xAB' * 9
        self.assertEquals(self.message.version, b'\xAB' * 9)

    def test_payload(self):
        self.message.version = b'\x01' * 9
        self.assertEquals(self.message.payload, b'\x01' * 9)


class CapabilitiesMessageTest(unittest.TestCase):
    def setUp(self):
        self.message = msg.CapabilitiesMessage()

    def test_get_maxChannels(self):
        with self.assertRaises(MessageError):
            self.message.maxChannels = 0xFFFF
        self.message.maxChannels = 0xFA
        self.assertEquals(self.message.maxChannels, 0xFA)

    def test_get_maxNetworks(self):
        with self.assertRaises(MessageError):
            self.message.maxNetworks = 0xFFFF
        self.message.maxNetworks = 0xFA
        self.assertEquals(self.message.maxNetworks, 0xFA)

    def test_get_stdOptions(self):
        with self.assertRaises(MessageError):
            self.message.stdOptions = 0xFFFF
        self.message.stdOptions = 0xFA
        self.assertEquals(self.message.stdOptions, 0xFA)

    def test_get_advOptions(self):
        with self.assertRaises(MessageError):
            self.message.advOptions = 0xFFFF
        self.message.advOptions = 0xFA
        self.assertEquals(self.message.advOptions, 0xFA)

    def test_get_advOptions2(self):
        with self.assertRaises(MessageError):
            self.message.advOptions2 = 0xFFFF
        self.message.advOptions2 = 0xFA
        self.assertEquals(self.message.advOptions2, 0xFA)
        self.message = msg.CapabilitiesMessage(adv_opts2=None)
        self.assertEquals(len(self.message.payload), 4)

    def test_payload(self):
        self.message.maxChannels = 0x01
        self.message.maxNetworks = 0x02
        self.message.stdOptions = 0x03
        self.message.advOptions = 0x04
        self.message.advOptions2 = 0x05
        self.assertEquals(self.message.payload, b'\x01\x02\x03\x04\x05')


class SerialNumberMessageTest(unittest.TestCase):
    def setUp(self):
        self.message = msg.SerialNumberMessage()

    def test_get_serialNumber(self):
        with self.assertRaises(MessageError):
            self.message.serialNumber = b'\xFF' * 8
        self.message.serialNumber = b'\xFA\xFB\xFC\xFD'
        self.assertEquals(self.message.serialNumber, b'\xFA\xFB\xFC\xFD')

    def test_payload(self):
        self.message.serialNumber = b'\x01\x02\x03\x04'
        self.assertEquals(self.message.payload, b'\x01\x02\x03\x04')
