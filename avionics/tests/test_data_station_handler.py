import queue
import threading
import time
import unittest

from avionics.services.data_station_handler import DataStationHandler

class TestDataStationHandler(unittest.TestCase):

    def setUp(self):
        self._rx_queue = queue.Queue()
        self._rx_lock = threading.Lock()
        self._is_downloading = threading.Event()

        # One second connection timeout, read/write timeout, and 2 second overall timeout
        self._data_station_handler = DataStationHandler(1000, 1000, 2000, self._rx_queue)
        self._data_station_handler.connect()

    def tearDown(self):
        self._data_station_handler.stop()

    def test_clears_rx_queue(self):
        """Data station handler clears RX queue as it receives station IDs"""

        self._rx_queue.put('streetcat')

        self._data_station_handler._wake_and_download(self._rx_lock, self._is_downloading)

        self.assertEquals(self._rx_queue.qsize(), 0)
