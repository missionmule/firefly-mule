import logging
import os
import serial
import time
import threading
import queue

class SerialHandler(object):
    """Handle serial RX and TX

    This class handles all serial communication via application-public RX
    and TX queues which are used by other application services.

    This class is largely based off of an example from pyserial:
    https://github.com/pyserial/pyserial/blob/master/examples/rfc2217_server.py

    """

    def __init__(self, _port, _baudrate=57600, _timeout=1):

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

        if (os.getenv('DEVELOPMENT') != 'True'): # Either in production or testing
            self.serial.close()

    def connect(self):
        """Connect to serial port"""
        while True:
            try:
                if (os.getenv('TESTING') == 'True'):
                    self.serial = serial.serial_for_url('loop://', timeout=self.timeout)
                    logging.info("Testing: URL loopback initiated")

                elif (os.getenv('DEVELOPMENT') == 'True'):
                    logging.info("Development: not connecting to serial")

                else: # This is the real world
                    self.serial = serial.Serial(self.port, self.baudrate, timeout=self.timeout)
                    logging.info("Connected to serial")

                break
            except serial.SerialException:
                logging.error("Failed to connect to serial device. Retrying connection...")
                time.sleep(3)

    def reader(self):
        """Loop forever and accept messages from autopilot into RX queue"""

        logging.debug('Serial reader thread started')
        while self._alive:
            self._read() # Pulled out to test

        self._alive = False
        logging.error('Serial reader thread terminated')

    def _read(self):
        try:
            if os.getenv('DEVELOPMENT') != 'True':
                data = self.serial.readline()
            else:
                data = None

            if data and data != b'\x00': # Ignore NULL bytes (sent at beginning of connection)
                logging.debug('RX: %s', data)
                self.rx_lock.acquire()
                self.rx_queue.put(data.decode())
                self.rx_lock.release()
        except:
            logging.error('Serial read failure') # Probably get disconnected
            self._alive = False

    def writer(self):
        """Loop forever and write messages from TX queue"""

        logging.debug('Serial writer thread started')

        while self._alive:
            while not self.tx_queue.empty():
                self._write()   # Pulled out to test

        self._alive = False
        logging.error('Serial writer thread terminated')

    def _write(self):
        try:
            self.tx_lock.acquire()
            data = self.tx_queue.get() # Get message in PriorityQueue tuple (0,'0x00')
            self.tx_lock.release()
            logging.debug('TX: %s', data[1])

            if (os.getenv('DEVELOPMENT') != 'True'):
                self.serial.write(data[1])

            self.tx_queue.task_done()

        except:
            logging.exception('Serial write failure') # Probably get disconnected
            self._alive = False
