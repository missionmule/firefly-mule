import logging
import threading

from .sftp import SFTPClient
from .timer import Timer

class Download(threading.Thread):

    """
    An instance of this class is created when the payload is notified that
    the UAV has reached the data station. It handles downloading (and errors)
    and then exits when the download is complete.
    """

    def __init__(self, _data_station_id, _connection_timeout_millis=120000, _redownload_request=False):

        super(Download, self).__init__()

        self.__data_station_id = _data_station_id # Reference to DataStation object monitored by Navigation
        self.__connection_timeout_millis = _connection_timeout_millis
        self._redownload_request = _redownload_request # TODO: set based on web server status

        # TODO: change this to dynamically distribute required certificate
        self.__sftp = SFTPClient('pi', 'raspberry', self.__data_station_id)

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
        if self.__redownload_request == True:
            # Flight operator has ordered redownload of previously downloaded data
            self.__sftp.downloadTmpFieldData()
        else:
            # Remove data that has been placed in /.tmp/ to await removal on
            # the UAV's second pass
            self.__sftp.deleteTmpFieldData()

        # Prioritizes field data transfer over log data
        self.__sftp.downloadNewFieldData()
        #self.__sftp.downloadAllLogData()

        logging.info("Download complete")

        logging.debug("Beginning removal of successfully transferred files...")

        # Removes only files that are successfully transferred to vehicle
        # TODO: uncomment this out when system is more stable
        # self.__sftp.deleteAllFieldData()
        # self.__sftp.deleteAllLogData()

        #logging.info("Removal of successfully transferred files complete")

        # Close connection to data station
        logging.debug("Closing SFTP connection...")
        self.__sftp.close()


    def run(self):
        self._connect()
        self._start()
