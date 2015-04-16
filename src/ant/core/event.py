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
#
# Beware s/he who enters: uncommented, non unit-tested,
# don't-fix-it-if-it-ain't-broken kind of threaded code ahead.
#

from __future__ import division, absolute_import, print_function, unicode_literals

from time import sleep
from threading import Lock, Thread

from ant.core.constants import MESSAGE_TX_SYNC
from ant.core.message import Message, ChannelEventMessage
from ant.core.exceptions import MessageError

MAX_ACK_QUEUE = 25
MAX_MSG_QUEUE = 25


def ProcessBuffer(buffer_):
    messages = []
    
    while len(buffer_) > 0:
        try:
            msg = Message.decode(buffer_)
            messages.append(msg)
            buffer_ = buffer_[len(msg):]
        except MessageError as err:
            if err.internal is not Message.INCOMPLETE:
                i, length = 1, len(buffer_)
                # move to the next SYNC byte
                while i < length and ord(buffer_[i]) != MESSAGE_TX_SYNC:
                    i += 1
                buffer_ = buffer_[i:]
            else:
                break
    
    return (buffer_, messages)


def EventPump(evm):
    with evm.pump_lock:
        evm.pump = True
    
    buffer_ = b''
    while True:
        with evm.running_lock:
            if not evm.running:
                break
        
        buffer_ += evm.driver.read(20)
        if len(buffer_) == 0:
            continue
        buffer_, messages = ProcessBuffer(buffer_)
        
        with evm.callbacks_lock:
            for message in messages:
                for callback in evm.callbacks:
                    try:
                        callback.process(message)
                    except Exception:
                        pass
        sleep(0.002)
    
    with evm.pump_lock:
        evm.pump = False


class EventCallback(object):
    def process(self, msg):
        raise NotImplementedError()


class AckCallback(EventCallback):
    def __init__(self, evm):
        self.evm = evm
    
    def process(self, msg):
        if isinstance(msg, ChannelEventMessage):
            evm = self.evm
            with evm.ack_lock:
                ack = evm.ack
                ack.append(msg)
                if len(ack) > MAX_ACK_QUEUE:
                    evm.ack = ack[-MAX_ACK_QUEUE:]


class MsgCallback(EventCallback):
    def __init__(self, evm):
        self.evm = evm
    
    def process(self, msg):
        evm = self.evm
        with evm.msg_lock:
            emsg = evm.msg
            emsg.append(msg)
            if len(emsg) > MAX_MSG_QUEUE:
                evm.msg = emsg[-MAX_MSG_QUEUE:]


class EventMachine(object):
    callbacks_lock = Lock()
    running_lock = Lock()
    pump_lock = Lock()
    ack_lock = Lock()
    msg_lock = Lock()
    
    def __init__(self, driver):
        self.driver = driver
        self.callbacks = set()
        self.running = False
        self.pump = False
        self.ack = []
        self.msg = []
        self.registerCallback(AckCallback(self))
        self.registerCallback(MsgCallback(self))
    
    def registerCallback(self, callback):
        with self.callbacks_lock:
            self.callbacks.add(callback)
    
    def removeCallback(self, callback):
        with self.callbacks_lock:
            try:
                self.callbacks.remove(callback)
            except KeyError:
                pass
    
    def waitForAck(self, msg):
        type_, ack = msg.type, self.ack
        while True:
            with self.ack_lock:
                for emsg in ack:
                    if type_ == emsg.messageID:
                        ack.remove(emsg)
                        return emsg.messageCode
            sleep(0.002)
    
    def waitForMessage(self, class_):
        msg = self.msg
        while True:
            with self.msg_lock:
                for emsg in msg:
                    if isinstance(emsg, class_):
                        msg.remove(emsg)
                        return emsg
            sleep(0.002)
    
    def start(self, driver=None):
        with self.running_lock:
            if self.running:
                return
            self.running = True
            
            if driver is not None:
                self.driver = driver
            
            Thread(target=EventPump, args=(self,)).start()
            while True:
                with self.pump_lock:
                    if self.pump:
                        break
                sleep(0.001)
    
    def stop(self):
        with self.running_lock:
            if not self.running:
                return
            self.running = False
        
        while True:
            with self.pump_lock:
                if not self.pump:
                    break
            sleep(0.001)
