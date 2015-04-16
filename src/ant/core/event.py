# -*- coding: utf-8 -*-
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

MAX_ACK_QUEUE = 25
MAX_MSG_QUEUE = 25

import thread
import time

from ant.core.constants import *
from ant.core.message import Message, ChannelEventMessage
from ant.core.exceptions import MessageError


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

    go = True
    buffer_ = ''
    while go:
        with evm.running_lock:
            if not evm.running:
                go = False

        buffer_ += evm.driver.read(20)
        if len(buffer_) == 0:
            continue
        buffer_, messages = ProcessBuffer(buffer_)

        with evm.callbacks_lock:
            for message in messages:
                for callback in evm.callbacks:
                    try:
                        callback.process(message)
                    except Exception, e:
                        pass

        time.sleep(0.002)

    with evm.pump_lock:
        evm.pump = False


class EventCallback(object):
    def process(self, msg):
        pass


class AckCallback(EventCallback):
    def __init__(self, evm):
        self.evm = evm

    def process(self, msg):
        if isinstance(msg, ChannelEventMessage):
            evm = self.evm
            with evm.ack_lock:
                evm.ack.append(msg)
                if len(evm.ack) > MAX_ACK_QUEUE:
                    evm.ack = evm.ack[-MAX_ACK_QUEUE:]


class MsgCallback(EventCallback):
    def __init__(self, evm):
        self.evm = evm

    def process(self, msg):
        evm = self.evm
        with evm.msg_lock:
            evm.msg.append(msg)
            if len(evm.msg) > MAX_MSG_QUEUE:
                evm.msg = evm.msg[-MAX_MSG_QUEUE:]


class EventMachine(object):
    callbacks_lock = thread.allocate_lock()
    running_lock = thread.allocate_lock()
    pump_lock = thread.allocate_lock()
    ack_lock = thread.allocate_lock()
    msg_lock = thread.allocate_lock()

    def __init__(self, driver):
        self.driver = driver
        self.callbacks = []
        self.running = False
        self.pump = False
        self.ack = []
        self.msg = []
        self.registerCallback(AckCallback(self))
        self.registerCallback(MsgCallback(self))

    def registerCallback(self, callback):
        with self.callbacks_lock:
            callbacks = self.callbacks
            if callback not in callbacks:
                callbacks.append(callback)

    def removeCallback(self, callback):
        with self.callbacks_lock:
            callbacks = self.callbacks
            if callback in callbacks:
                callbacks.remove(callback)

    def waitForAck(self, msg):
        while True:
            with self.ack_lock:
                for emsg in self.ack:
                    if msg.type != emsg.getMessageID():
                        continue
                    self.ack.remove(emsg)
                    return emsg.getMessageCode()
                time.sleep(0.002)

    def waitForMessage(self, class_):
        while True:
            with self.msg_lock:
                for emsg in self.msg:
                    if not isinstance(emsg, class_):
                        continue
                    self.msg.remove(emsg)
                    return emsg
            time.sleep(0.002)

    def start(self, driver=None):
        with self.running_lock:
            if self.running:
                return
            self.running = True
            if driver is not None:
                self.driver = driver
            
            thread.start_new_thread(EventPump, (self,))
            while True:
                with self.pump_lock:
                    if self.pump:
                        break
                time.sleep(0.001)

    def stop(self):
        with self.running_lock:
            if not self.running:
                return
            self.running = False

        while True:
            with self.pump_lock:
                if not self.pump:
                    break
            time.sleep(0.001)
