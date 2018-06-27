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

    def __init__(self, _port, _baudrate):

        self._write_lock = threading.Lock()     # Safety first

        self._alive = False     # Made true on r/w thread spawn

        self.rx_queue = queue.Queue()
        self.tx_queue = queue.PriorityQueue() # Priority 0: heartbeat, Priority 1: otherwise

        self.rx_lock = threading.Lock()
        self.tx_lock = threading.Lock()

        self.serial_lock = threading.Lock()

        self.port = _port
        self.baudrate = _baudrate

        self.serial = None

    def connect(self):
        """Connect to serial port"""
        while True:
            try:
                if not "DEVELOPMENT" in os.environ: # Don't connect to serial while in development
                    self.serial = serial.Serial(self.port, self.baudrate)
                    logging.info("Connected to serial")
                else:
                    logging.info("In development mode, not connecting to serial")
                break
            except serial.SerialException:
                logging.error("Failed to connect to serial device. Retrying connection...")
                time.sleep(3)

    def run(self):
        """Spawn infinite looping reader and writer threads"""

        self._alive = True

        while self._alive:
            # Read anything waiting
            try:
                data = self.serial.readline()
                if data:
                    logging.debug('RX: %s', data)
                    self.rx_lock.acquire()
                    self.rx_queue.put(data)
                    self.rx_lock.release()
            except:
                logging.exception('Serial read failure') # Probably get disconnected
                break

            try:
                if not self.tx_queue.empty():
                    self.tx_lock.acquire()
                    data = self.tx_queue.get() # Get message in PriorityQueue tuple (0,'0x00')
                    self.tx_lock.release()
                    logging.debug('TX: %s', data[1])
                    self.serial.write(data[1])
            except:
                logging.exception('Serial write failure') # Probably get disconnected
                break

            self._stop()


    def _reader(self):
        """Loop forever and accept messages from autopilot into RX queue"""

        logging.debug('Serial reader thread started')
        while self._alive:
            try:
                data = self.serial.readline()
                if data:
                    logging.debug('RX: %s', data)
                    self.rx_lock.acquire()
                    self.rx_queue.put(data)
                    self.rx_lock.release()
            except:
                logging.exception('Serial read failure') # Probably get disconnected
                break

        self._alive = False
        logging.debug('Serial reader thread terminated')

    def _writer(self):
        """Loop forever and write messages from TX queue"""

        logging.debug('Serial writer thread started')

        while self._alive:
            while not self.tx_queue.empty():
                try:
                    self.tx_lock.acquire()
                    data = self.tx_queue.get() # Get message in PriorityQueue tuple (0,'0x00')
                    self.tx_lock.release()
                    logging.debug('TX: %s', data[1])
                    self.serial.write(data[1])
                except:
                    logging.exception('Serial write failure') # Probably get disconnected
                    break

        logging.debug('Serial writer thread terminated')
        self._stop()

    def _stop(self):
        """Stop and close connection"""
        logging.debug('Stopping serial connection')
        if self._alive:
            self._alive = False
            self.thread_read.join()
            self.thread_write.join()
