import logging
import os
import serial
import threading
import queue

class SerialHandler(object):
    """Handle serial RX and TX

    This class handles all serial communication via application-public RX
    and TX queues which are used by other application services.

    This class is largely based off of an example from pyserial:
    https://github.com/pyserial/pyserial/blob/master/examples/rfc2217_server.py

    """

    def __init__(self, _port, _baudrate, _timeout):

        self._write_lock = threading.Lock()     # Safety first

        self._alive = False     # Made true on r/w thread spawn

        self.rx_queue = queue.Queue(maxsize=50)
        self.tx_queue = queue.PriorityQueue(maxsize=50) # Priority 0: heartbeat, Priority 1: otherwise

        self.rx_lock = threading.Lock()
        self.tx_lock = threading.Lock()

        self.port = _port
        self.baudrate = _baudrate
        self.timeout = _timeout

        self.serial = None

        self._alive = True


    def stop(self):
        """Stop and close connection"""
        logging.info('Stopping serial handler...')
        self._alive = False

    def connect(self):
        """Connect to serial port"""
        while True:
            try:
                if not "DEVELOPMENT" in os.environ: # Don't connect to serial while in development
                    self.serial = serial.Serial(self.port, self.baudrate, timeout=self.timeout)
                    logging.info("Connected to serial")
                else:
                    logging.info("In development mode, not connecting to serial")
                break
            except serial.SerialException:
                logging.error("Failed to connect to serial device. Retrying connection...")
                time.sleep(3)

    def reader(self):
        """Loop forever and accept messages from autopilot into RX queue"""

        logging.debug('Serial reader thread started')
        while self._alive:
            try:
                data = self.serial.readline()
                if data:
                    logging.debug('RX: %s', data)
                    logging.debug('[1] RX queue size: %i', self.rx_queue.qsize())
                    self.rx_lock.acquire()
                    self.rx_queue.put(data)
                    self.rx_lock.release()
                    logging.debug('[2] RX queue size: %i', self.rx_queue.qsize())
            except:
                logging.exception('Serial read failure') # Probably get disconnected
                break

        self._alive = False
        logging.error('Serial reader thread terminated')

    def writer(self):
        """Loop forever and write messages from TX queue"""

        logging.debug('Serial writer thread started')

        while self._alive:
            while not self.tx_queue.empty():
                try:
                    self.tx_lock.acquire()
                    logging.debug('[1] TX queue size: %i', self.tx_queue.qsize())
                    data = self.tx_queue.get() # Get message in PriorityQueue tuple (0,'0x00')
                    self.tx_lock.release()
                    logging.debug('TX: %s', data[1])
                    logging.debug('[2] TX queue size: %i', self.tx_queue.qsize())
                    self.serial.write(data[1])
                except:
                    logging.exception('Serial write failure') # Probably get disconnected
                    break

        self._alive = False
        logging.error('Serial writer thread terminated')
