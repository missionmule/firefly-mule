import logging
import serial
import sys
import threading
import queue

from services import DataStationHandler
from services import Heartbeat
from services import SerialHandler

def setup_logging():
    # Set up logging [Logging levels in order of seriousness: DEBUG < INFO < WARNING < ERROR < CRITICAL]
    logging.basicConfig(filename='flight.log',
                        level=logging.DEBUG,
                        format='%(asctime)s.%(msecs)03d %(levelname)s \t%(message)s',
                        datefmt="%d %b %Y %H:%M:%S")

    # Log to STDOUT
    # TODO: only log to stdout in debug mode to speed things up
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s.%(msecs)03d %(levelname)s %(message)s')
    ch.setFormatter(formatter)
    logging.getLogger().addHandler(ch)

def main():
    logging.info('\n\n--- mission start ---')

    # Serial handler with public rx and tx queues
    ser = SerialHandler(port='/dev/ttyAMA0', baudrate=57600, timeout=1)
    ser.connect()

    # Data station communication handling
    dl = DataStationHandler(20000,20000, 60000, ser.rx_queue)

    # Heartbeat pushed to serial tx_queue every 500ms
    hb = Heartbeat(dl.is_downloading, ser.tx_queue, 500)

    thread_data_station_handler = threading.Thread(target=dl.run, args=(ser.rx_lock,))
    thread_data_station_handler.daemon = True
    thread_data_station_handler.name = 'Data Station Communication Handler'
    thread_data_station_handler.start()

    thread_heartbeat = threading.Thread(target=hb.run, args=(ser.tx_lock,))
    thread_heartbeat.daemon = True
    thread_heartbeat.name = 'Heartbeat'
    thread_heartbeat.start()

    thread_serial_handler = threading.Thread(target=ser.run)
    thread_serial_handler.daemon = True
    thread_serial_handler.name = 'Serial Communication Handler'
    thread_serial_handler.start()

    while True:
        pass    # Let the threads do their work

if __name__ == "__main__":
    setup_logging()
    main()
