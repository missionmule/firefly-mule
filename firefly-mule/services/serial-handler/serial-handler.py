import logging
import queue

class SerialHandler(object):
    """Handle serial RX and TX

    This class handles all serial communication via application-public RX
    and TX queues which are used by other application services.

    """

    def __init__(self, _serial_instance, _is_downloading):

        self._write_lock = threading.Lock()     # Safety first

        self._alive = False     # Made true on r/w thread spawn

        self.rx_queue = Queue.Queue()
        self.tx_queue = Queue.PriorityQueue() # Priority 0: heartbeat, Priority 1: otherwise

        self.rx_lock = threading.Lock()
        self.tx_lock = threading.Lock()

        self._is_downloading = _is_downloading    # Boolean controlled by download

        self.serial = _serial_instance

    def run(self):
        """Spawn infinite looping reader and writer threads"""

        self._alive = True

        self.thread_read = threading.Thread(target=self._reader())
        self.thread_read.daemon = True
        self.thread_read.name = 'Serial Reader'
        self.thread_read.start()

        self.thread_write = threading.Thread(target=self._writer())
        self.thread_write.daemon = True
        self.thread_write.name = 'Serial Writer'
        self.thread_write.start()

    def _reader(self):
        """Loop forever and accept messages from autopilot into RX queue"""
        logging.debug('Serial reader thread started')
        while self._alive:
            try:
                data = self.serial.read(self.serial.in_waiting or 1)
                if data:
                    logging.debug('RX: %s', data)
                    self.rx_lock.acquire()
                    self.rx_queue.put(b''.join(data))
                    self.rx_lock.release()
            except:
                logging.error('{}'.format(msg)) # Probably get disconnected
                break

        self._alive = False
        logging.debug('Serial reader thread terminated')

    def _writer(self):
        """Loop forever and write messages from TX queue"""

        logging.debug('Serial writer thread started')

        while self._alive:
            while not self.tx_queue.empty():
                try:
                    tx_lock.acquire()
                    msg = self.tx_queue.get()
                    tx_lock.release()

                    self.serial.write(b''.join(msg))
                except:
                    logging.error('{}'.format(msg)) # Probably get disconnected
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
