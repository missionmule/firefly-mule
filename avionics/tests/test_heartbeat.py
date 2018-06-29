
import queue
import time
import threading
import unittest

from avionics.services.heartbeat import Heartbeat

class TestHeartbeat(unittest.TestCase):

    def __init__(self, *args, **kwargs):
        super(TestHeartbeat, self).__init__(*args, **kwargs)

        self._tx_queue = queue.PriorityQueue()
        self._tx_lock = threading.Lock()
        self._is_downloading = threading.Event()

        self._heartbeat = Heartbeat(self._tx_queue)

        self._thread_heartbeat = threading.Thread(target=self._heartbeat.run,
            args=(self._tx_lock, self._is_downloading))
        self._thread_heartbeat.daemon = True
        self._thread_heartbeat.name = 'Heartbeat'

    def setUp(self):
        self._thread_heartbeat.start()

    def tearDown(self):
        self._heartbeat.stop()
        self._thread_heartbeat.join()

    def test_frequency(self):
        """Heartbeat ticks at least once per second on average"""

        before = time.time() # Start timer

        for i in range(10): # Listen for 10 messages
            self._tx_queue.get(block=True, timeout=1) # Blocks until something is in the queue

        after = time.time() # How long has it been?

        self.assertTrue(after - before <= 10)


    def test_idle_message(self):
        """Heartbeat sends 'x00' when system is idle"""

        self._is_downloading.clear()
        self._tx_queue.queue.clear()

        message = self._tx_queue.get(block=True, timeout=3)    # Wait for new message

        self.assertEquals(message[1], b'\x00')


    def test_idle_message_priority(self):
        """Heartbeat sends idle message with top prority (Priority: 0)"""

        self._is_downloading.clear()

        self._tx_queue.queue.clear()
        message = self._tx_queue.get(block=True, timeout=3)    # Wait for new message

        self.assertEquals(message[0], 0)


    def test_downloading_message(self):
        """Heartbeat sends 'x01' when system is downloading"""

        self._is_downloading.set() # Set is_downloading flag to true

        self._tx_queue.queue.clear()
        message = self._tx_queue.get(block=True, timeout=3) # Wait for new message

        self.assertEquals(message[1], b'\x01')

    def test_downloading_message_priority(self):
        """Heartbeat sends downloading message with top prority (Priority: 0)"""

        self._is_downloading.clear()

        self._tx_queue.queue.clear()
        message = self._tx_queue.get(block=True, timeout=3)    # Wait for new message

        self.assertEquals(message[0], 0)
