import threading
from queue import Queue, Empty
from time import sleep
import sys

from libAnt.message import *
from libAnt.drivers.driver import Driver, DriverException


class Network:
    def __init__(self, key: bytes = b'\x00' * 8, name: str = None):
        self.key = key
        self.name = name
        self.number = 0

    def __str__(self):
        return self.name


class Pump(threading.Thread):
    def __init__(self, driver: Driver, initMessages, out: Queue, onSucces, onFailure):
        super().__init__()
        self._stopper = threading.Event()
        self._driver = driver
        self._out = out
        self._initMessages = initMessages
        self._waiters = []
        self._onSuccess = onSucces
        self._onFailure = onFailure

    def stop(self):
        self._driver.abort()
        self._stopper.set()

    def stopped(self):
        return self._stopper.isSet()

    def run(self):
        print('Pump::run: started' , file=sys.stderr)
        while not self.stopped():
            try:
                print('Pump::run: with _driver' , file=sys.stderr)
                with self._driver as d:
                    # Startup
                    rst = SystemResetMessage()
                    print('Pump::run: rst: %s' % (rst), file=sys.stderr)
                    self._waiters.append(rst)
                    print('Pump::run: calling write', file=sys.stderr)
                    rc = d.write(rst, timeout=1000)
                    print('Pump::run: rc: %s' % (rc), file=sys.stderr)
                    for m in self._initMessages:
                        print('Pump::run: m: %s' % (m), file=sys.stderr)
                        self._waiters.append(m)
                        d.write(m)

                    while not self.stopped():
                        #  Write
                        try:
                            outMsg = self._out.get(block=False)
                            self._waiters.append(outMsg)
                            d.write(outMsg)
                        except Empty:
                            #print('Pump::run: Empty', file=sys.stderr)
                            pass

                        # Read
                        try:
                            msg = d.read(timeout=1)
                            if msg.type == MESSAGE_CHANNEL_EVENT:
                                print('Pump::run: m: %s MESSAGE_CHANNEL_EVENT' % (msg), file=sys.stderr)
                                # This is a response to our outgoing message
                                for w in self._waiters:
                                    if w.type == msg.content[1]:  # ACK
                                        self._waiters.remove(w)
                                        #  TODO: Call waiter callback from tuple (waiter, callback)
                                        break
                            elif msg.type == MESSAGE_CHANNEL_BROADCAST_DATA:
                                #print('Pump::run: m: %s MESSAGE_CHANNEL_BROADCAST_DATA' % (msg), file=sys.stderr)
                                bmsg = BroadcastMessage(msg.type, msg.content).build(msg.content)
                                self._onSuccess(bmsg)
                        except Empty:
                            pass
            except DriverException as e:
                print('Pump::run: driver exception e: %s ' %(e) , file=sys.stderr)
                self._onFailure(e)
                return
            except Exception as e:
                print('Pump::run: exception e: %s ' %(e) , file=sys.stderr)
                #self._onFailure(e)
                return
            except:
                print('Pump::run: exception unknown: ' , file=sys.stderr)
                pass
            self._waiters.clear()
            sleep(1)


class Node:
    def __init__(self, driver: Driver, name: str = None):
        print('Node::__init__: name: %s' % (name), file=sys.stderr)
        self._driver = driver
        self._name = name
        self._out = Queue()
        self._init = []
        self._pump = None
        self._configMessages = Queue()
        print('Node::__init__: finished' , file=sys.stderr)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()

    def start(self, onSuccess, onFailure):
        print('Node::start: ', file=sys.stderr)
        if not self.isRunning():
            print('Node::start call Pump : ', file=sys.stderr)
            self._pump = Pump(self._driver, self._init, self._out, onSuccess, onFailure)
            print('Node::start Pump.start : ', file=sys.stderr)
            self._pump.start()
            print('Node::start Pump.start finished: ', file=sys.stderr)

    def enableRxScanMode(self, networkKey=ANTPLUS_NETWORK_KEY, channelType=CHANNEL_TYPE_ONEWAY_RECEIVE,
                         frequency: int = 2457, rxTimestamp: bool = True, rssi: bool = True, channelId: bool = True):
        self._init.append(SystemResetMessage())
        self._init.append(SystemResetMessage())
        self._init.append(SystemResetMessage())
        self._init.append(SetNetworkKeyMessage(0, networkKey))
        self._init.append(AssignChannelMessage(0, channelType))
        self._init.append(SetChannelIdMessage(0))
        self._init.append(SetChannelRfFrequencyMessage(0, frequency))
        self._init.append(EnableExtendedMessagesMessage())
        self._init.append(LibConfigMessage(rxTimestamp, rssi, channelId))
        self._init.append(OpenRxScanModeMessage())

    def stop(self):
        print('Pump::__init__: stop:' , file=sys.stderr)
        if self.isRunning():
            self._pump.stop()
            self._pump.join()

    def isRunning(self):
        print('Pump::__init__: isRunning:' , file=sys.stderr)
        if self._pump is None:
            return False
        return self._pump.is_alive()

    def getCapabilities(self):
        pass
