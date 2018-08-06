import logging

from .sftp import SFTPClient
from .timer import Timer

class Download():

    """
    An instance of this class is created when the payload is notified that
    the UAV has reached the data station. It handles downloading (and errors)
    and then exits when the download is complete.
    """

    def __init__(self, _data_station_id, _connection_timeout_millis=1000):

        #super(Download, self).__init__()

        self.__data_station_id = _data_station_id # Reference to DataStation object monitored by Navigation
        self.__connection_timeout_millis = _connection_timeout_millis

        # TODO: change this to dynamically distribute required certificate
        self.__sftp = SFTPClient('pi', 'raspberry', self.__data_station_id)

    def _connect(self):
        print("In connect")
        # Try to connect until SFTP client is connected or timeout event happens
        data_station_connection_timer = Timer()
        while not self.__sftp.is_connected:

            if data_station_connection_timer.time_elapsed() > 10000:
                logging.error("Connection to data station %s failed permanently" % (self.__data_station_id))
                print("permanent failure")
                break

            # Sets low level SSH socket read/write timeout for all operations (listdir, get, etc)
            self.__sftp.connect(timeout=(1000))

        print("After connection")
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

        print("Beginning download...")
        #self.__data_station.download_started = True

        # Prioritizes field data transfer over log data
        self.__sftp.downloadAllFieldData()
        #self.__sftp.downloadAllLogData()

        logging.info("Download complete")

        logging.debug("Beginning removal of successfully transferred files...")

        # Removes only files that are successfully transferred to vehicle
        # TODO: uncomment this out when system is more stable
        # self.__sftp.deleteAllFieldData()
        # self.__sftp.deleteAllLogData()

        logging.info("Removal of successfully transferred files complete")

        # Close connection to data station
        self.__sftp.close()

        # Mark download as complete so Navigation service knows to continue mission
        #self.__data_station.download_complete = True


    def run(self):
        self._connect()
        self._start()
