import os
import queue
import threading
import time
import unittest
import sqlite3

from avionics.services.data_station_handler import DataStationHandler
from avionics.services.data_station_handler.database import Database

class TestDataStationHandler(unittest.TestCase):

    def setUp(self):
        self._rx_queue = queue.Queue()
        self._rx_lock = threading.Lock()
        self._is_downloading = threading.Event()

        # One second connection timeout, read/write timeout, and 2 second overall timeout
        self._data_station_handler = DataStationHandler(1000, 1000, 2000, self._rx_queue)
        self._data_station_handler.connect()

        self.db = Database()

    def tearDown(self):
        self._data_station_handler.stop()

        # Clear test database
        os.remove('avionics.db')

    def test_clears_rx_queue(self):
        """Data station handler clears RX queue as it receives station IDs"""

        self._rx_queue.put('123')

        self._data_station_handler._wake_download_and_sleep(self._rx_lock, self._is_downloading)

        self.assertEquals(self._rx_queue.qsize(), 0)

    def test_sets_up_database(self):
        """Data station handler sets up the database"""

        self.assertTrue(os.path.exists('avionics.db'))

    def test_database_insert_data_station(self):
        """Data station properly inserted into the database"""

        self.db.insert_data_station('123')

        conn = sqlite3.connect('avionics.db')
        c = conn.cursor()

        id = ('123',)
        c.execute('SELECT 1 FROM stations WHERE station_id=? LIMIT 1', id)

        data_station_exists = c.fetchone() is not None

        conn.close()

        self.assertTrue(data_station_exists)

    def test_database_insert_new_flight(self):
        """New flight ID properly created"""

        flight_id = self.db.insert_new_flight()

        conn = sqlite3.connect('avionics.db')
        c = conn.cursor()

        id = (flight_id,)
        c.execute('SELECT 1 FROM flights WHERE flight_id=? LIMIT 1', id)

        flight_exists = c.fetchone() is not None

        conn.close()

        self.assertTrue(flight_exists)

    def test_database_add_station_to_flight(self):
        """Data station properly added to flight"""
        flight_id = self.db.insert_new_flight()
        station_id = '123'

        self.db.add_station_to_flight(station_id, flight_id)

        conn = sqlite3.connect('avionics.db')
        c = conn.cursor()

        ids = (flight_id, station_id,)
        c.execute('SELECT 1 FROM flights_stations WHERE flight_id=? AND station_id=? LIMIT 1', ids)

        station_exists = c.fetchone() is not None

        conn.close()

        self.assertTrue(station_exists)

    def test_database_get_redownload_request_false(self):
        """Database retrieves redownload request when false"""

        conn = sqlite3.connect('avionics.db')
        c = conn.cursor()

        station_id = '123'

        id = (station_id,)

        c.execute('''INSERT INTO stations (station_id, last_visited, redownload)
                     VALUES (?, datetime('now'), 0)''', id)

        c.execute('SELECT * FROM stations WHERE station_id=? LIMIT 1', id)

        print(c.fetchone())

        conn.commit()
        conn.close()

        print(self.db.get_redownload_request(station_id))

        self.assertFalse(self.db.get_redownload_request(station_id))

    def test_database_get_redownload_request_true(self):
        """Database retrieves redownload request when true"""

        conn = sqlite3.connect('avionics.db')
        c = conn.cursor()

        station_id = '123'

        id = (station_id,)

        c.execute('''INSERT INTO stations (station_id, last_visited, redownload)
                     VALUES (?, datetime('now'), 1)''', id)

        c.execute('SELECT * FROM stations WHERE station_id=? LIMIT 1', id)

        print(c.fetchone())

        conn.commit()
        conn.close()

        self.assertTrue(self.db.get_redownload_request(station_id))
