#!/usr/bin/env python3
from time import sleep
import sys
from libAnt.drivers.serial import SerialDriver
from libAnt.node import Node
from libAnt.profiles.factory import Factory



def callback(msg):
    print('callback: %s' % (msg), file=sys.stderr)


def eCallback(e):
    raise e


with Node(SerialDriver('/dev/ttyUSB0'), 'SerialNode1') as n:
    n.enableRxScanMode()
    f = Factory(callback)
    n.start(f.parseMessage, eCallback)
    sleep(30)  # Listen for 30sec
