import logging
import threading
import time

from .sftp import SFTPClient
from .timer import Timer
from .database import Database

class Download(threading.Thread):

    """
    An instance of this class is created when the payload is notified that
    the UAV has reached the data station. It handles downloading (and errors)
    and then exits when the download is complete.
    """

    def __init__(self, _data_station_id, _redownload_request, _flight_id, _connection_timeout_millis=120000):

        super(Download, self).__init__()

        self.successful_downloads = 0
        self.total_files = 0
        self.did_connect = False
        self.did_find_device = False
        self.total_data_downloaded_mb = 0
        self.download_speed_mbps = 0
        self.connection_time_s = 0
        self.download_time_s = 0

        self._data_station_id = _data_station_id
        self._connection_timeout_millis = _connection_timeout_millis
        self._redownload_request = _redownload_request
        self._flight_id = _flight_id

        # TODO: pull from private file
        self._sftp = SFTPClient('pi', 'raspberry', self._data_station_id, self._flight_id)

        self.db = Database()

    def _connect(self):
        # Try to connect until SFTP client is connected or timeout event happens
        data_station_connection_timer = Timer()
        while not self._sftp.is_connected:

            connection_timeout_s = self.db.get_timeout('connection')

            self.connection_time_s = data_station_connection_timer.time_elapsed()

            if data_station_connection_timer.time_elapsed() > connection_timeout_s:
                logging.error("Connection to data station %s failed permanently" % (self._data_station_id))
                break

            # Sets low level SSH socket read/write timeout for all operations (listdir, get, etc)
            self._sftp.connect()

            # Without this, the service spins when the data station is booted,
            # but not yet accepting SSH connections
            time.sleep(0.5)

        # Throw an error to tell navigation to continue on
        if not self._sftp.is_connected:
            raise Exception("Connection Timeout")
        else:
            self.did_connect = True


    def _start(self):
        """
        For desired data station:
            1) Download field data and data station logs to drone
            2) Delete successfully transferred field data and logs from data station
        """
        # Handle two-pass data deletion: either redownload or delete previously
        # downloaded data (which can be identified by its existance in the `/.tmp/` directory)

        new_files_downloaded = 0
        old_files_downloaded = 0

        old_data_downloaded_mb = 0
        new_data_downloaded_mb = 0

        new_files_to_download = 0
        old_files_to_download = 0

        data_station_download_timer = Timer()

        if self._redownload_request == True:
            # Flight operator has ordered redownload of previously downloaded data
            old_files_downloaded, old_files_to_download, old_data_downloaded_mb = self._sftp.downloadTmpFieldData()
        else:
            # Remove data that has been placed in /.tmp/ to await removal on
            # the UAV's second pass
            self._sftp.deleteTmpFieldData()

        # Prioritizes field data transfer over log data
        new_files_downloaded, new_files_to_download, self.did_find_device, new_data_downloaded_mb = self._sftp.downloadNewFieldData()
        #self._sftp.downloadAllLogData()

        self.download_time_s = data_station_download_timer.time_elapsed()

        # Get total mb downloaded
        self.total_data_downloaded_mb = old_data_downloaded_mb + new_data_downloaded_mb

        # Calculate bitrate in Mbps (mb*s*8 bits/byte)
        self.download_speed_mbps = self.total_data_downloaded_mb/self.download_time_s * 8

        # Calculate percent of files downloaded and round down to the nearest integer
        successful_downloads = new_files_downloaded + old_files_downloaded
        total_files = new_files_to_download + old_files_to_download

        # Avoid divide by zero error when no files exist
        if total_files == 0:
            percent_downloaded = 100
        else:
            percent_downloaded = int(successful_downloads/total_files)

        # SQLite behaves odly when its accessed in a multithreaded environment
        # Instead, we perform the update from the central DataStationHandler
        self.successful_downloads = successful_downloads
        self.total_files = total_files

        logging.info("Total Files: %s" % total_files)
        logging.info("Successfully Downloaded: %s" % successful_downloads)

        logging.info("Download complete [%s percent downloaded]" % percent_downloaded)

        # Close connection to data station
        logging.debug("Closing SFTP connection...")
        self._sftp.close()


    def run(self):
        self._connect()
        self._start()
