import time
import unittest

from avionics.services.serial_handler import SerialHandler

class TestSerialHandler(unittest.TestCase):

    def setUp(self):
        self._serial_handler = SerialHandler('loop://')
        self._serial_handler.connect()

    def tearDown(self):
        self._serial_handler.stop()

    def test_tx_queue_emptying(self):
        """Serial handler correctly empties tx_queue after writing"""

        self._serial_handler.tx_queue.put((0,'test'))

        # Should write the message and then empty the queue
        self._serial_handler._write()

        self.assertEquals(self._serial_handler.tx_queue.qsize(), 0)

    def test_communication(self):
        """Serial handler correctly sends and receives over serial"""

        self._serial_handler.tx_queue.put((0,b'testing\n'))
        self._serial_handler._write()

        time.sleep(0.1) # Simulate real physical connection

        self._serial_handler._read() # Should get whatever was sent and put it on the rx_queue
        message = self._serial_handler.rx_queue.get(block=True, timeout=3)

        self.assertEquals(message, 'testing\n')

    def test_tx_priority(self):
        """Serial handler correctly proitizes messages"""

        self._serial_handler.tx_queue.put((1,'priority1')) # Message ready to be sent
        self._serial_handler.tx_queue.put((2,'priority2-1')) # Message ready to be sent
        self._serial_handler.tx_queue.put((0,'priority0')) # Message ready to be sent
        self._serial_handler.tx_queue.put((2,'priority2-2')) # Message ready to be sent

        m1 = self._serial_handler.tx_queue.get(block=True, timeout=3)
        m2 = self._serial_handler.tx_queue.get(block=True, timeout=3)
        m3 = self._serial_handler.tx_queue.get(block=True, timeout=3)
        m4 = self._serial_handler.tx_queue.get(block=True, timeout=3)

        self.assertEquals(m1[1], 'priority0')
        self.assertEquals(m2[1], 'priority1')
        self.assertEquals(m3[1], 'priority2-1')
        self.assertEquals(m4[1], 'priority2-2')
