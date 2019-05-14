import queue
import logging
import sys
import threading

from avionics.services import DataStationHandler

logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s.%(msecs)03d %(levelname)s \t%(message)s',
                        datefmt="%d %b %Y %H:%M:%S")

rx_lock = threading.Lock()
is_downloading = threading.Event()
rx_queue = queue.Queue(maxsize=50)

dsh = DataStationHandler(120000, 120000, 900000, rx_queue)
dsh.connect()

while True:
    s = input("Enter data station ID: ")
    rx_queue.put(s)
    dsh._wake_download_and_sleep(rx_lock, is_downloading)
