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

    def __init__(self, _connection_timeout_millis, _read_write_timeout_millis, _rx_queue):
        self.is_downloading = False
        self.connection_timeout_millis = _connection_timeout_millis
        self.read_write_timeout_millis = _read_write_timeout_millis
        self.rx_queue = _rx_queue
        self.xbee = XBee()

    def run(self, rx_lock):
        """Loop forever and handle downloads as data stations are reached"""

        while True:

            if not self.rx_queue.empty():    # You've got mail!

                # Update system status (used by heartbeat)
                self.is_downloading = True

                # Get data station ID as message from rx_queue
                rx_lock.acquire()
                data_station_id = rx_queue.get()
                rx_lock.release()

                # Wake up data station
                self.xbee.send_command(data_station_id, 'POWER_ON')
                while not self.xbee.acknowledge():
                    self.xbee.send_command(data_station_id, 'POWER_ON')

                # Create a download worker with reference to current_data_station
                download_worker = Download(data_station_id,
                                           self.DOWNLOAD_CONNECTION_TIMEOUT_SECONDS,
                                           self.DOWNLOAD_READ_WRITE_TIMEOUT_SECONDS)

                try:
                    # This throws an error if the connection times out
                    download_worker.connect()

                    # Spawn download thread
                    download_thread = threading.Thread(target=download_worker.start)
                    download_thread.start()

                    # Attempt to join the thread after timeout, if still alive the download timed out
                    download_thread.join(self.OVERALL_DOWNLOAD_TIMEOUT_SECONDS)

                    if download_thread.is_alive():
                        logging.info("Download timeout: Download cancelled")
                    else:
                        logging.info("Download complete")

                except Exception as e:
                    logging.error(e)

                # Mark task as complete, even if it fails
                rx_queue.task_done()

                # Update system status (for heartbeat)
                self.is_downloading = False

            else:
                time.sleep(1)   # Check RX queue again in 1 second
