import logging
import threading

from .sftp import SFTPClient
from .timer import Timer
from ..database from Database

class Download(threading.Thread):

    """
    An instance of this class is created when the payload is notified that
    the UAV has reached the data station. It handles downloading (and errors)
    and then exits when the download is complete.
    """

    def __init__(self, _data_station_id, _connection_timeout_millis=120000, _redownload_request, _flight_id):

        super(Download, self).__init__()

        self.__data_station_id = _data_station_id
        self.__connection_timeout_millis = _connection_timeout_millis
        self._redownload_request = Boolean(_redownload_request)
        self._flight_id = _flight_id

        # TODO: pull from private file
        self.__sftp = SFTPClient('pi', 'raspberry', self.__data_station_id)
        self.db = Database()

    def _connect(self):
        # Try to connect until SFTP client is connected or timeout event happens
        data_station_connection_timer = Timer()
        while not self.__sftp.is_connected:

            if data_station_connection_timer.time_elapsed() > self.__connection_timeout_millis/1000:
                logging.error("Connection to data station %s failed permanently" % (self.__data_station_id))
                break

            # Sets low level SSH socket read/write timeout for all operations (listdir, get, etc)
            self.__sftp.connect()

            # Without this, the service spins when the data station is booted,
            # but not yet accepting SSH connections
            time.sleep(0.5)

        #self.__sftp.downloadAllFieldData()
        # Throw an error to tell navigation to continue on
        if not self.__sftp.is_connected:
            raise Exception("Connection Timeout")


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

        new_files_to_download = 0
        old_files_to_download = 0

        if self.__redownload_request == True:
            # Flight operator has ordered redownload of previously downloaded data
            old_files_downloaded, old_files_to_download = self.__sftp.downloadTmpFieldData()
        else:
            # Remove data that has been placed in /.tmp/ to await removal on
            # the UAV's second pass
            self.__sftp.deleteTmpFieldData()

        # Prioritizes field data transfer over log data
        new_files_downloaded, new_files_to_download = self.__sftp.downloadNewFieldData()
        #self.__sftp.downloadAllLogData()

        # Calculate percent of files downloaded and round down to nearest integer
        percent_downloaded = int((new_files_downloaded+old_files_downloaded)/(new_files_to_download+old_files_to_download))

        self.db.update_percent_downloaded(self._data_station_id, self._flight_id, percent_downloaded)

        logging.info("Download complete [%s% downloaded]" % percent_downloaded)

        # Close connection to data station
        logging.debug("Closing SFTP connection...")
        self.__sftp.close()


    def run(self):
        self._connect()
        self._start()
