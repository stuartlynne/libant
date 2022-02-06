#!/usr/bin/env python3

# vim: textwidth=0 shiftwidth=4 tabstop=4

import os
os.environ['PYUSB_DEBUG'] = 'info'

from time import sleep
import sys
from libAnt.drivers.usb import USBDriver
from libAnt.loggers.pcap import PcapLogger
from libAnt.node import Node
from libAnt.profiles.factory import Factory

from usb.core import find, util, USBError
from usb.util import find_descriptor, endpoint_direction, claim_interface, dispose_resources, release_interface

import platform 
from multiprocessing import Process, freeze_support, Queue
from queue import Empty


#print('list: sleep', file=sys.stderr)
#sleep(120)
#exit()


def eCallback(e):
    raise (e)

#pids = [0x1008, 0x1009]

#dev.reset()
#try:
#except:
#    print('main: cannot find a device', file=sys.stderr)
#    exit()

#with Node(USBDriver(vid=0x0FCF, pid=0x1008, logger=PcapLogger(logFile='log.pcap')), 'MyNode') as n:


class Ant(Process):
    def success(self, msg):
        print('success: %s' % (msg), file=sys.stderr)
        self.outQueue.put(msg)

    def failure(self, msg):
        print('failure: %s' % (msg), file=sys.stderr)
        self.outQueue.put(msg)

    def is_ant_device(self, dev):
        pids = [0x1008, 0x1009]
        print('is_ant_device: dev: 0x%04x' % (dev.idProduct), file=sys.stderr)
        return dev.idProduct in pids

    def __init__(self, detach=True, outQueue=None, inQueue=None):
        print('Ant::__init__', file=sys.stderr)
        super(Ant, self).__init__()
        self.outQueue = outQueue
        self.inQueue = inQueue
        self.stopFlag = False
        self.detach = detach
        self.finished = False
        self._n = None
        self.dev = None
        print('Ant::__init__ finised', file=sys.stderr)

    def info(self):
        print('Ant::stop', file=sys.stderr)
        if self._n is None:
            print('Ant::info: _n.stop() is None', file=sys.stderr)

    def stop(self):
        print('Ant::stop', file=sys.stderr)
        self.stopFlag = True
        if self._n is not None:
            print('Ant::stop: _n.stop() interface', file=sys.stderr)
            self._n.stop()
        else:
            print('Ant::stop: _n is None', file=sys.stderr)
        if self.dev is not None:
            print('Ant::stop: release interface', file=sys.stderr)
            release_interface(self.dev, 0)
        else:
            print('Ant::stop: dev is None', file=sys.stderr)

    def run(self):
        # import usb.core
        # from usb.backend import libusb1
        # be = libusb1.get_backend()
        # dev = usb.core.find(backend=be)

        print('Ant::run', file=sys.stderr)
        list = find(idVendor=0x0fcf, find_all=True, custom_match=self.is_ant_device)

        foundFlag = False

        for dev in list:
            print('Ant::run list %s' % (dev.__dict__), file=sys.stderr)
            print('Ant::run:list[0x%04x:0x%04x][%s:%s:%s] %s %s' %
                (dev.idVendor, dev.idProduct, dev.address, dev.bus, dev.port_number, dev.manufacturer, dev.product), file=sys.stderr)

            # Detach kernel driver
            if platform.system() == 'Linux':
                if self.detach and dev.is_kernel_driver_active(0):
                    print('Ant::run:list: is_kernel_driver_active is True', file=sys.stderr)
                    try:
                        dev.detach_kernel_driver(0)
                    except USBError as e:
                        raise DriverException("Could not detach kernel driver")
                    except NotImplementedError:
                        pass  # for non unix systems

            print('Ant::run:list: set configuration', file=sys.stderr)
            try:
                dev.set_configuration()
            except USBError as e:
                print('Ant::run:list: set configuration failed e: %s' % (e), file=sys.stderr)
                continue

            print('Ant::run:list: claim interface', file=sys.stderr)
            try:
                self.dev = dev
                claim_interface(self.dev, 0)
                foundFlag = True
                break
            except USBError as e:
                print('Ant::run:list: set configuration failed e: %s ----' % (e), file=sys.stderr)
                continue


        if foundFlag is False: 
            print('Ant::run:Cannot find device', file=sys.stderr)
            self.finished = True
            return
            #exit(1)

        print('main: found device', file=sys.stderr)
        #print('main: ant %s' % (ant.__dict__), file=sys.stderr)
        u = USBDriver(vid=None, pid=None, dev=self.dev, logger=PcapLogger(logFile='log.pcap'))
        self._n = Node(u, 'MyNode')

        self._n.enableRxScanMode()
        print('Ant::run: n.start', file=sys.stderr)
        self._n.start(self.success, self.failure)
        print('Ant::run: n.start exited', file=sys.stderr)
        while True:
            try:
                try:
                    message = self.inQueue.get(block=False, timeout=0)
                    print('Ant::run: message %s' % (message), file=sys.stderr)
                    break
                except Empty:
                    print('Ant::run: empty', file=sys.stderr)
                    sleep(2)
            except KeyboardInterrupt:
                print('Ant::run: KeyboardInterrupt', file=sys.stderr)
                break
                

        print('Ant::run: calling _n.stop', file=sys.stderr)
        self._n.stop()
        print('Ant::run: calling _n.stop exited', file=sys.stderr)



if __name__ == '__main__':
    print('main: %s' %(platform.system()), file=sys.stderr)

    # N.B. this is required for Windows pyinstaller, and the 
    # subsequent calls to instantiate a process must be made immediately after this 
    # in this call frame, i.e. do not call out to another function.
    #
    if platform.system() == 'Windows':
        freeze_support()
    print('main: calling Node', file=sys.stderr)

    print('main: calling enableRxScanMode', file=sys.stderr)
    outQueue= Queue()
    inQueue= Queue()
    ant = Ant(outQueue=outQueue, inQueue=inQueue)
    print('main: ant created', file=sys.stderr)
    ant.start()
    print('main: ant started', file=sys.stderr)
    print('main: ant %s' % (ant.__dict__), file=sys.stderr)
    while True:
        try:
            try:
                message = outQueue.get(block=False, timeout=0)
                print('main: message %s' % (message), file=sys.stderr)
            except Empty:
                print('main: empty', file=sys.stderr)
                sleep(1)
        except KeyboardInterrupt:
            print('main: KeyboardInterrupt', file=sys.stderr)
            inQueue.put('stop')
            break
        except Exception as e:
            print('main: exception e: %s' %(e), file=sys.stderr)
            break

    #print('main: ant.stop', file=sys.stderr)
    #print('main: ant %s' % (ant.__dict__), file=sys.stderr)
    #ant.stop() 
    print('main: sleep', file=sys.stderr)
    sleep(2)
    print('main: ant.join', file=sys.stderr)
    ant.join()
    print('main: finished', file=sys.stderr)
    sleep(2)

