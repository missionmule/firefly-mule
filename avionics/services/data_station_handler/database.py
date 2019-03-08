import logging
import os
import time
import sqlite3

class Database(object):

    def __init__(self):
        # Instead of instantiating a global connection here, we create and destroy
        # a database connection with each call because SQLite is just reading/editing
        # a local file so we don't need a persistent connection.
        # ...It also simplifies things. :)

        if not (os.getenv('TESTING') == 'True'):
            self.db_path = '/var/lib/avionics.db';
        else:
            self.db_path = 'avionics.db';

        # Ensure that the database exists and the full schema is there
        conn = sqlite3.connect(self.db_path);
        c = conn.cursor()

        c.execute('''CREATE TABLE IF NOT EXISTS
                     flights(flight_id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp DATETIME)''')

        c.execute('''CREATE TABLE IF NOT EXISTS
                     stations(station_id INTEGER PRIMARY KEY, last_visited DATETIME, redownload INTEGER)''')

        c.execute('''CREATE TABLE IF NOT EXISTS
                     flights_stations(flight_id INTEGER, station_id INTEGER, successful_downloads INTEGER, total_files INTEGER, did_wake_up_ack INTEGER, did_connect INTEGER, did_find_device INTEGER, did_shutdown_ack INTEGER)''')

        conn.commit()
        conn.close()

    def insert_data_station(self, data_station_id):
        """Inserts a data station into the database

        Checks for a data station in `stations` table and then updates or
        inserts a new data station row as necessary.
        """

        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        id = (int(data_station_id),)
        c.execute('SELECT 1 FROM stations WHERE station_id=? LIMIT 1', id)

        if c.fetchone() is not None: # If the station already exists, just update timestamp
            c.execute('''UPDATE stations
                         SET last_visited=datetime('now')
                         WHERE station_id=?''', id)
        else: # Otherwise, add the station
            c.execute('''INSERT INTO stations (station_id, last_visited, redownload)
                         VALUES (?, datetime('now'), 0)''', id)

        conn.commit()
        conn.close()

    def insert_new_flight(self):
        """Creates a new flight and returns the flight ID"""

        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        c.execute('''INSERT INTO flights (timestamp)
                     VALUES (datetime('now'))''')

        flight_id = c.lastrowid

        conn.commit()
        conn.close()

        return flight_id

    def add_station_to_flight(self, data_station_id, flight_id):
        """Adds the provided data station ID to the current flight

        This method pairs a new data station ID with an existing flight ID and
        initializes the percent downloaded to 0.
        """

        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        item = (int(flight_id), int(data_station_id),)

        c.execute('''INSERT INTO flights_stations (flight_id, station_id, successful_downloads, total_files, did_wake_up_ack, did_connect, did_find_device, did_shutdown_ack)
                     VALUES (?, ?, 0, 0, 0, 0, 0, 0)''', item)

        conn.commit()
        conn.close()

    def update_flight_station_stats(self, data_station_id, flight_id, successful_downloads, total_files, did_wake_up_ack, did_connect, did_find_device, did_shutdown_ack):
        """Updates the percent of data downloaded for a specific data station"""

        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        item = (successful_downloads, total_files, did_wake_up_ack, did_connect, did_find_device, did_shutdown_ack, data_station_id, flight_id, )

        c.execute('''UPDATE flights_stations
                     SET successful_downloads=?, total_files=?, did_wake_up_ack=?, did_connect=?, did_find_device=?, did_shutdown_ack=?
                     WHERE (station_id=? AND flight_id=?)''', item)

        conn.commit()
        conn.close()

    def get_redownload_request(self, data_station_id):
        """Returns data station redownload request bolean for specific data station"""

        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        item = (data_station_id,)

        c.execute('''SELECT redownload
                     FROM stations
                     WHERE station_id=?
                     LIMIT 1''', item)

        # SQLite stores the redownload boolean as 0/1 integer so we must convert
        # the integer to a boolean here
        redownload = bool(c.fetchone()[0])

        conn.close()

        return redownload
