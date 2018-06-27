import logging
import time

class Heartbeat(object):

    def __init__(self, _is_downloading, _tx_queue, _frequency_millis=1000):

        self.is_downloading = _is_downloading
        self.tx_queue = _tx_queue
        self.frequency_millis = _frequency_millis          # Frequency of heartbeat in milliseconds

    def run(self, tx_lock):
        logging.info('Heartbeat initiated')

        while True:
            if (self.is_downloading):
                tx_lock.acquire()
                self.tx_queue.put((0,'\x01')) # Tuple with 0 (top) prority
                tx_lock.release()
                logging.debug('Heartbeat: downloading')
            else:
                tx_lock.acquire()
                self.tx_queue.put((0,'\x00')) # Tuple with 0 (top) prority
                tx_lock.release()
                logging.debug('Heartbeat: idle')
            time.sleep(self.frequency_millis / 1000)

        logging.error('Heartbeat terminated')
