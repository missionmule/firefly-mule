import logging
import os
import random
import time
import threading

from .download import Download
from .xbee import XBee

class DataStationHandler(object):
    """Communication handler for data stations (XBee station wakeup and SFTP download)

    This class manages downstream interfacing between payload and data
    station.

    SFTP Download:
        Each download is spawned as a worker thread to isolate the effect
        of failure in case of unexpected socket exceptions.

    XBee Wakeup:
        When the UAV arrives at a data station, the station is woken up with
        an XBee RF signal codifying its data station UUID.

    """

    def __init__(self, _connection_timeout_millis, _read_write_timeout_millis,
        _overall_timeout_millis, _rx_queue):

        self.connection_timeout_millis = _connection_timeout_millis
        self.read_write_timeout_millis = _read_write_timeout_millis
        self.overall_timeout_millis = _overall_timeout_millis
        self.rx_queue = _rx_queue
        self.xbee = XBee()
        self._alive = True

    def connect(self):
        self.xbee.connect()

    def run(self, rx_lock, is_downloading):
        """Loop forever and handle downloads as data stations are reached"""

        while self._alive:

            if not self.rx_queue.empty():    # You've got mail!

                self._wake_and_download(rx_lock, is_downloading)

            else:
                time.sleep(1)   # Check RX queue again in 1 second

        logging.error("Data station handler terminated")

    def stop(self):
        logging.info("Stopping data station handler...")
        self._alive = False

    def _wake_and_download(self, rx_lock, is_downloading):
        # Update system status (used by heartbeat)
        is_downloading.set()

        # Get data station ID as message from rx_queue
        rx_lock.acquire()
        data_station_id = self.rx_queue.get()
        rx_lock.release()

        logging.info('Data station arrival: %s', data_station_id)

        # Wake up data station
        self.xbee.send_command(data_station_id, 'POWER_ON')

        # TODO: ensure this does not block if data station does not respond
        if (os.getenv('TESTING') == 'False'):
            while not self.xbee.acknowledge(data_station_id, 'POWER_ON'):
                self.xbee.send_command(data_station_id, 'POWER_ON')

        # Don't actually download
        if (os.getenv('TESTING') == 'True'):
            r = random.randint(10,20)

            logging.debug('Simulating download for %i seconds', r)
            time.sleep(r) # "Download" for random time between 10 and 100 seconds

        else: # This is the real world (ahhh!)
            # '.local' ensures visibility on the network
            download_worker = Download(data_station_id+'.local',
                                       self.connection_timeout_millis)

            try:
                # This throws an error if the connection times out
                download_worker.start()

                # Attempt to join the thread after timeout.
                # If still alive the download timed out.
                download_worker.join(self.overall_timeout_millis)

                if download_worker.is_alive():
                    logging.info("Download timeout: Download cancelled")
                else:
                    logging.info("Download complete")

            except Exception as e:
                logging.error(e)


        # Mark task as complete, even if it fails
        self.rx_queue.task_done()

        # Update system status (for heartbeat)
        is_downloading.clear() # Analagous to is_downloading = False
