import logging
import time
import sqlite3

class Database(object):

    def __init__(self):
        # Instead of instantiating the connection here, we create and destroy
        # a database connection with each call because SQLite is just reading/editing
        # a local file so we don't need a persistent connection.
        # ...It also simplifies things. :)
        pass

    def insert_data_station(self, data_station_id):
        """Inserts a data station into the database

        Checks for a data station in `stations` table and then updates or
        inserts a new data station row as necessary.
        """

        conn = sqlite3.connect('/var/lib/avionics.db')
        c = conn.cursor()

        id = (data_station_id,)
        c.execute('SELECT 1 FROM stations WHERE station_id=? LIMIT 1', id)

        if conn.fetchone() is not None: # If the station already exists, just update timestamp
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

        conn = sqlite3.connect('/var/lib/avionics.db')
        c = conn.cursor()

        c.execute('''INSERT INTO flights (timestamp)
                     VALUES (datetime('now'))''')

        return c.lastrowid

    def add_station_to_flight(self, data_station_id, flight_id):
        """Adds the provided data station ID to the current flight

        This method pairs a new data station ID with an existing flight ID and
        initializes the percent downloaded to 0.
        """

        conn = sqlite3.connect('/var/lib/avionics.db')
        c = conn.cursor()

        item = (flight_id, data_station_id,)

        c.execute('''INSERT INTO flights_stations (flight_id, station_id, successful_downloads, total_files)
                     VALUES (?, ?, 0, 0)''', item)

        conn.commit()
        conn.close()

    def update_flight_station_stats(self, data_station_id, flight_id, successful_downloads, total_files):
        """Updates the percent of data downloaded for a specific data station"""

        conn = sqlite3.connect('/var/lib/avionics.db')
        c = conn.cursor()

        item = (successful_downloads, total_files, data_station_id, flight_id, )

        c.execute('''UPDATE flights_stations
                     SET successful_downloads=?, total_files=?
                     WHERE (station_id=? AND flight_id=?)''', item)

        conn.commit()
        conn.close()

    def get_redownload_request(self, data_station_id):
        """Returns data station redownload request bolean for specific data station"""

        conn = sqlite3.connect('/var/lib/avionics.db')
        c = conn.cursor()

        item = (data_station_id,)

        c.execute('''SELECT redownload
                     FROM stations
                     WHERE station_id=?
                     LIMIT 1''', item)

        # SQLite stores the redownload boolean as 0/1 integer so we must convert
        # the integer to a boolean here
        redownload = Boolean(c.fetchone())

        conn.close()

        return redownload
