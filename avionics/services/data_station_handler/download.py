from .sftp import SFTPClient
from .timer import Timer

class Download(object):

    """
    An instance of this class is created when the payload is notified that
    the UAV has reached the data station. It handles downloading (and errors)
    and then exits when the download is complete.
    """

    CONNECTION_TIMEOUT_SECONDS = 0
    READ_WRITE_TIMEOUT_SECONDS = 0

    __sftp = None
    __data_station = None

    is_connected = False

    def __init__(self, _data_station, _connection_timeout=10, _read_write_timeout=10):

        self.__data_station = _data_station # Reference to DataStation object monitored by Navigation
        self.CONNECTION_TIMEOUT_SECONDS = _connection_timeout
        self.READ_WRITE_TIMEOUT_SECONDS = 2

        # TODO: change this to dynamically distribute required certificate
        self.__sftp = SFTPClient('pi', 'raspberry', str(self.__data_station.identity))

    def connect(self):
        # Try to connect until SFTP client is connected or timeout event happens
        data_station_connection_timer = Timer()
        while not self.__sftp.is_connected:

            if data_station_connection_timer.time_elapsed() > self.CONNECTION_TIMEOUT_SECONDS:
                logging.error("Connection to data station %s failed permanently" % (self.__data_station.identity))
                break

            # Sets low level SSH socket read/write timeout for all operations (listdir, get, etc)
            self.__sftp.connect(timeout=self.CONNECTION_TIMEOUT_SECONDS)

            time.sleep(1)

        # Whatever the status of SFTP connection after this while loop runs
        self.is_connected = self.__sftp.is_connected

        # Throw an error to tell navigation to continue on
        if not self.is_connected:
            raise Exception("Connection Timeout")

    def start(self):
        """
        For desired data station:
            1) Download field data and data station logs to drone
            2) Delete successfully transferred field data and logs from data station
        """

        logging.debug("Beginning download...")
        self.__data_station.download_started = True

        # Prioritizes field data transfer over log data
        self.__sftp.downloadAllFieldData()
        self.__sftp.downloadAllLogData()

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
        self.__data_station.download_complete = True
