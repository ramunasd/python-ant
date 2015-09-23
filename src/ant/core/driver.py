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

from threading import Lock

# USB1 driver uses a USB<->Serial bridge
from serial import Serial, SerialException, SerialTimeoutException
# USB2 driver uses direct USB connection. Requires PyUSB
from usb.control import get_interface
from usb.core import USBError, find as findDeviceUSB
from usb.util import (find_descriptor, claim_interface, release_interface,
                      endpoint_direction, ENDPOINT_OUT, ENDPOINT_IN)

from ant.core.exceptions import DriverError


class Driver(object):
    def __init__(self, device, log=None, debug=False):
        self.device = device
        self.debug = debug
        self.log = log
        self._lock = Lock()
    
    def open(self):
        with self._lock:
            if self._opened:
                raise DriverError("Could not open device (already open).")
            
            self._open()
            if self.log:
                self.log.logOpen()
    
    @property
    def opened(self):
        with self._lock:
            return self._opened
    
    def close(self):
        with self._lock:
            if not self._opened:
                raise DriverError("Could not close device (not open).")
            
            self._close()
            if self.log:
                self.log.logClose()
    
    def read(self, count):
        if count <= 0:
            raise DriverError("Could not read from device (zero request).")
        if not self.opened:
            raise DriverError("Could not read from device (not open).")
        
        data = self._read(count)
        
        with self._lock:
            if self.log:
                self.log.logRead(data)
            if self.debug:
                self._dump(data, 'READ')
        return data
    
    def write(self, msg):
        data = msg.encode()
        if len(data) <= 0:
            raise DriverError("Could not write to device (no data).")
        if not self.opened:
            raise DriverError("Could not write to device (not open).")
        
        ret = self._write(data)
        
        with self._lock:
            if self.debug:
                self._dump(data, 'WRITE')
            if self.log:
                self.log.logWrite(data[0:ret])
        return ret
    
    @staticmethod
    def _dump(data, title):
        if len(data) == 0:
            return
        
        print("========== [{0}] ==========".format(title))
        
        length = 8
        line = 0
        while data:
            row = str(data[:length])
            data = data[length:]
            hex_data = [b'%02X' % ord(byte) for byte in row]
            print(b'%04X' % line, b' '.join(hex_data))
            line += length
        
        print()
    
    @property
    def _opened(self):
        raise NotImplementedError()
    
    def _open(self):
        raise NotImplementedError()
    
    def _close(self):
        raise NotImplementedError()
    
    def _read(self, count):
        raise NotImplementedError()
    
    def _write(self, data):
        raise NotImplementedError()


class USB1Driver(Driver):
    def __init__(self, device, baud_rate=115200, log=None, debug=False):
        super(USB1Driver, self).__init__(device, log, debug)
        self.device = device
        self.baud = baud_rate
        self._serial = None
    
    def _open(self):
        try:
            dev = Serial(self.device, self.baud)
        except SerialException as e:
            raise DriverError(str(e))
        
        if not dev.isOpen():
            raise DriverError("Could not open device")
        
        self._serial = dev
        self._serial.timeout = 0.01
    
    @property
    def _opened(self):
        return self._serial is not None
    
    def _close(self):
        self._serial.close()
    
    def _read(self, count):
        return self._serial.read(count)
    
    def _write(self, data):
        try:
            count = self._serial.write(data)
            self._serial.flush()
        except SerialTimeoutException as e:
            raise DriverError(str(e))
        
        return count


class USB2Driver(Driver):
    
    def __init__(self, log=None, debug=False):
        super(USB2Driver, self).__init__(log, debug)
        self._ep_out = None
        self._ep_in = None
        self._dev = None
        self._int = None
    
    def _open(self):
        # Most of this is straight from the PyUSB example documentation
        dev = findDeviceUSB(idVendor=0x0fcf, idProduct=0x1008)
        
        if dev is None:
            raise DriverError("Could not open device (not found)")
        
        # make sure the kernel driver is not active
        if dev.is_kernel_driver_active(0):
            try:
                dev.detach_kernel_driver(0)
            except USBError as e:
                exit("could not detach kernel driver: {}".format(e))
        
        dev.set_configuration()
        cfg = dev.get_active_configuration()
        interface_number = cfg[(0, 0)].bInterfaceNumber
        intf = find_descriptor(cfg,
            bInterfaceNumber=interface_number,
            bAlternateSetting=get_interface(dev, interface_number)
        )
        
        claim_interface(dev, interface_number)
        ep_out = find_descriptor(intf, custom_match= \
            lambda e: endpoint_direction(e.bEndpointAddress) == ENDPOINT_OUT
        )
        assert ep_out is not None
        
        ep_in = find_descriptor(intf, custom_match= \
            lambda e: endpoint_direction(e.bEndpointAddress) == ENDPOINT_IN
        )
        assert ep_in is not None
        
        self._ep_out = ep_out
        self._ep_in = ep_in
        self._dev = dev
        self._int = interface_number
    
    @property
    def _opened(self):
        return self._dev is not None
    
    def _close(self):
        release_interface(self._dev, self._int)
        self._dev = None
    
    def _read(self, count):
        return self._ep_in.read(count).tostring()
    
    def _write(self, data):
        return self._ep_out.write(data)
