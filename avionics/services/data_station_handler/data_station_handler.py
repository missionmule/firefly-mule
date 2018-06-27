import logging
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
        self.download_thread = None
        self._alive = True

    def run(self, rx_lock, is_downloading):
        """Loop forever and handle downloads as data stations are reached"""

        while self._alive:

            if not self.rx_queue.empty():    # You've got mail!

                # Update system status (used by heartbeat)
                is_downloading.set()

                # Get data station ID as message from rx_queue
                rx_lock.acquire()
                data_station_id = self.rx_queue.get()
                rx_lock.release()

                # # Wake up data station
                # self.xbee.send_command(data_station_id, 'POWER_ON')
                # while not self.xbee.acknowledge():
                #     self.xbee.send_command(data_station_id, 'POWER_ON')

                # Create a download worker with reference to current_data_station
                # if not "DEVELOPMENT" in os.environ: # This is the real world (ahhh!)
                #
                #     download_worker = Download(data_station_id,
                #                                self.connection_timeout_millis,
                #                                self.read_write_timeout_millis)
                #
                #
                #     try:
                #         # This throws an error if the connection times out
                #         download_worker.connect()
                #
                #         # Spawn download thread
                #         self.download_thread = threading.Thread(target=download_worker.start)
                #         self.download_thread.start()
                #
                #         # Attempt to join the thread after timeout, if still alive the download timed out
                #         self.download_thread.join(self.overall_timeout_millis)
                #
                #         if download_thread.is_alive():
                #             logging.info("Download timeout: Download cancelled")
                #         else:
                #             logging.info("Download complete")
                #
                #     except Exception as e:
                #         logging.error(e)
                #
                # else: # Simulate download

                r = random.randint(1,100)
                logging.debug('Simulating download for %i seconds', r)
                time.sleep(r) # "Download" for random time between 10 and 100 seconds

                # Mark task as complete, even if it fails
                self.rx_queue.task_done()

                # Update system status (for heartbeat)
                is_downloading.clear() # Analagous to is_downloading = False

            else:
                time.sleep(1)   # Check RX queue again in 1 second

        logging.error("Data station handler terminated")

    def stop(self):
        logging.info("Stopping data station handler...")
        self._alive = False
        #self.download_thread.join()
