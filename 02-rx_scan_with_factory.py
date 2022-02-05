#!/usr/bin/env python3

# vim: textwidth=0 shiftwidth=4 tabstop=4

import os
os.environ['PYUSB_DEBUG'] = 'debug'

from time import sleep
import sys
from libAnt.drivers.usb import USBDriver
from libAnt.loggers.pcap import PcapLogger
from libAnt.node import Node
from libAnt.profiles.factory import Factory

from usb.core import find, util, USBError
from usb.util import find_descriptor, endpoint_direction, claim_interface, dispose_resources, release_interface

from multiprocessing import Process


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

print('main: calling Node', file=sys.stderr)

print('main: calling enableRxScanMode', file=sys.stderr)

class Ant(Process):
    def callback(self, msg):
        print('callback: %s' % (msg), file=sys.stderr)

    def is_ant_device(self, dev):
        pids = [0x1008, 0x1009]
        print('is_ant_device: dev: 0x%04x' % (dev.idProduct), file=sys.stderr)
        return dev.idProduct in pids

    def __init__(self, detach=True):
        print('Ant::__init__', file=sys.stderr)
        super(Ant, self).__init__()
        self.stopFlag = False
        self.detach = detach
        self.finished = False
        self._n = None
        self.dev = None
        print('Ant::__init__ finised', file=sys.stderr)

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
            #print('Ant::list %s' % (dev.__dict__), file=sys.stderr)
            print('Ant::__init__:list[0x%04x:0x%04x][%d:%d:%d] %s %s' % 
                (dev.idVendor, dev.idProduct, dev.address, dev.bus, dev.port_number, dev.manufacturer, dev.product), file=sys.stderr)

            # Detach kernel driver
            if self.detach and dev.is_kernel_driver_active(0):
                print('Ant::__init__:list: is_kernel_driver_active is True', file=sys.stderr)
                try:
                    dev.detach_kernel_driver(0)
                except USBError as e:
                    raise DriverException("Could not detach kernel driver")
                except NotImplementedError:
                    pass  # for non unix systems

            print('Ant::__init__:list: set configuration', file=sys.stderr)
            try:
                dev.set_configuration()
            except USBError as e:
                print('Ant::__init__:list: set configuration failed e: %s' % (e), file=sys.stderr)
                continue

            print('Ant::__init__:list: claim interface', file=sys.stderr)
            try:
                self.dev = dev
                claim_interface(self.dev, 0)
                foundFlag = True
                break
            except USBError as e:
                print('Ant::__init__:list: set configuration failed e: %s ----' % (e), file=sys.stderr)
                continue


        if foundFlag is False: 
            print('Ant::__init__:Cannot find device', file=sys.stderr)
            self.finished = True
            return
            #exit(1)

        print('main: found device', file=sys.stderr)
        #print('main: ant %s' % (ant.__dict__), file=sys.stderr)
        u = USBDriver(vid=None, pid=None, dev=self.dev, logger=PcapLogger(logFile='log.pcap'))
        self._n = Node(u, 'MyNode')

        self._n.enableRxScanMode()
        print('Ant::__init__: creating Factory', file=sys.stderr)
        f = Factory(self.callback)
        print('Ant::__init__: n.start', file=sys.stderr)
        self._n.start(f.parseMessage, self.callback)
        print('Ant::__init__: n.start exited', file=sys.stderr)


ant = Ant()
print('main: ant created', file=sys.stderr)
ant.start()
print('main: ant started', file=sys.stderr)
print('main: ant %s' % (ant.__dict__), file=sys.stderr)
while ant.finished is False:
    try:
        print('main: sleeping', file=sys.stderr)
        sleep(4)
    except KeyboardInterrupt:
        print('main: KeyboardInterrupt', file=sys.stderr)
        break
    except Exception as e:
        print('main: exception e: %s' %(e), file=sys.stderr)
        break

print('main: ant.stop', file=sys.stderr)
print('main: ant %s' % (ant.__dict__), file=sys.stderr)
ant.stop() 
print('main: ant.join', file=sys.stderr)
ant.join()
print('main: finished', file=sys.stderr)
sleep(2)

