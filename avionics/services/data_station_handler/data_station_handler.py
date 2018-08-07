import logging
import os
import random
import time
import threading

from .timer import Timer
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
        an XBee RF signal including its data station ID ('redwood', 'streetcat', etc.)

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
                self._wake_download_and_sleep(rx_lock, is_downloading)
            else:
                time.sleep(1)   # Check RX queue again in 1 second

        logging.error("Data station handler terminated")

    def stop(self):
        logging.info("Stopping data station handler...")
        self._alive = False

    def _wake_download_and_sleep(self, rx_lock, is_downloading):
        # Update system status (used by heartbeat)
        is_downloading.set()

        # Get data station ID as message from rx_queue
        rx_lock.acquire()
        data_station_id = self.rx_queue.get().strip() # Removes invisible characters
        rx_lock.release()

        logging.info('Data station arrival: %s', data_station_id)

        # Wake up data station
        logging.info('Waking up over XBee...')
        self.xbee.send_command(data_station_id, 'POWER_ON')

        xbee_wake_command_timer = Timer()
        wakeup_successful = True
        if not (os.getenv('TESTING') == 'True'):
            while not self.xbee.acknowledge(data_station_id, 'POWER_ON'):
                logging.debug("POWER_ON data station %s", data_station_id)
                self.xbee.send_command(data_station_id, 'POWER_ON')
                time.sleep(0.5) # Try again in 0.5s

                # Will try shutting down data station over XBee for 2 min before moving on
                if xbee_wake_command_timer.time_elapsed() > 120:
                    wakeup_successful = False
                    logging.error("POWER_ON command ACK failure. Moving on...")
                    break

        # Don't actually download
        if (os.getenv('TESTING') == 'True'):
            r = random.randint(10,20)

            logging.debug('Simulating download for %i seconds', r)
            time.sleep(r) # "Download" for random time between 10 and 100 seconds

        # Only try download if wakeup was successful
        elif (wakeup_successful): # This is the real world (ahhh!)
            # '.local' ensures visibility on the network

            logging.info('XBee ACK received, beginning download...')

            download_worker = Download(data_station_id.strip()+'.local',
                                       self.connection_timeout_millis)

            try:
                # This throws an error if the connection times out
                download_worker.start()

                # Attempt to join the thread after timeout.
                # If still alive the download timed out.
                download_worker.join(self.overall_timeout_millis/1000)

                if download_worker.is_alive():
                    logging.info("Download timeout: Download cancelled")
                else:
                    logging.info("Download complete")

            except Exception as e:
                logging.error(e)

        # Wake up data station
        logging.info('Shutting down data station %s...', data_station_id)
        self.xbee.send_command(data_station_id, 'POWER_OFF')

        xbee_sleep_command_timer = Timer()
        # If the data station actually turned on and we're not in test mode, shut it down
        if not (os.getenv('TESTING') == 'True') and (wakeup_successful == True):
            while not self.xbee.acknowledge(data_station_id, 'POWER_OFF'):
                logging.debug("POWER_OFF data station %s", data_station_id)
                self.xbee.send_command(data_station_id, 'POWER_OFF')
                time.sleep(0.5) # Try again in 0.5s

                # Will try shutting down data station over XBee for 60 seconds before moving on
                if xbee_sleep_command_timer.time_elapsed() > 60:
                    logging.error("POWER_OFF command ACK failure. Moving on...")
                    break

        # Mark task as complete, even if it fails
        self.rx_queue.task_done()

        # Update system status (for heartbeat)
        is_downloading.clear() # Analagous to is_downloading = False
