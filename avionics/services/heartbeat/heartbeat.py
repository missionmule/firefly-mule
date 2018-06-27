import logging
import time

class Heartbeat(object):

    def __init__(self, _tx_queue, _frequency_millis=1000):

        self.tx_queue = _tx_queue
        self.frequency_millis = _frequency_millis          # Frequency of heartbeat in milliseconds
        self._alive = True

    def run(self, tx_lock, is_downloading):
        logging.info('Heartbeat initiated')

        while self._alive:
            if (is_downloading):
                tx_lock.acquire()
                self.tx_queue.put((0,'\x01')) # Tuple with 0 (top) prority
                tx_lock.release()
                logging.debug('Heartbeat: downloading')
            else:
                tx_lock.acquire()
                self.tx_queue.put((0,b'\x00')) # Tuple with 0 (top) prority
                tx_lock.release()
                logging.debug('Heartbeat: idle')
            time.sleep(self.frequency_millis / 1000)

        logging.error('Heartbeat terminated')

    def stop(self):
        self._alive = False
