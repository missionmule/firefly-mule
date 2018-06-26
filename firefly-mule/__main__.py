import logging
import sys
import queue

from .services import DataStationHandler
from .services import Heartbeat
from .services import SerialHandler

def setup_logging():
    # Set up logging [Logging levels in order of seriousness: DEBUG < INFO < WARNING < ERROR < CRITICAL]
    logging.basicConfig(filename='flight-log.log',
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

    # Data station communication handling
    dl = DataStationHandler(20000,20000)

    # Serial handler with public rx and tx queues
    ser = SerialHandler(
        serial.Serial(port='/dev/ttyAMA0', baudrate=57600, timeout=1),
        dl.is_downloading)

    # Heartbeat pushed to serial tx_queue every 500ms
    hb = Heartbeat(dl.is_downloading, ser.tx_queue, 500)

    thread_data_station_handler = threading.Thread(target=dl.run, args=(ser.rx_lock))
    thread_data_station_handler.daemon = True
    thread_data_station_handler.name = 'Data Station Communication Handler'
    thread_data_station_handler.start()

    thread_heartbeat = threading.Thread(target=hb.run, args=(ser.tx_lock))
    thread_heartbeat.daemon = True
    thread_heartbeat.name = 'Heartbeat'
    thread_heartbeat.start()

    thread_serial_handler = threading.Thread(target=ser.run)
    thread_serial_handler.daemon = True
    thread_serial_handler.name = 'Serial Communication Handler'
    thread_serial_handler.start()

if __name__ == "__main__":
    setup_logging()
    main()
