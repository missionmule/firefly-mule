import serial
import time
import logging
import os
import hashlib

class XBee(object):

    """Wake up data station when we've reached it

    This class implements XBee communication to wake up the data station when
    the UAV has arrived over it and is ready to download. Using XBee RF, we
    instruct the data station's microcontroller to boot the data station computer
    and initiate the download over Wi-Fi.

    Todo:
        * Wake up data station when on the way so it's ready when we arrive

    """

    def __init__(self, serial_port="/dev/ttyUSB0"):

        self.xbee_port = None
        self.encode = None
        self.decode = None
        self.data_station_id = None
        self.serial_port = serial_port

        self.preamble_out = 'street'
        self.preamble_in = 'cat'

        # TODO: make single dictionary
        self.encode = {
            'POWER_ON' : '1',
            'POWER_OFF' : '2',
            'EXTEND_TIME' : '3'
        }
        self.decode = {
            '1' : 'POWER_ON',
            '2' : 'POWER_OFF',
            '3' : 'EXTEND_TIME'
        }

    def connect(self):
        while True:
            try:
                if (os.getenv('DEVELOPMENT') == 'False' and os.getenv('TESTING') == 'False') or (os.getenv('DEVELOPMENT') == None and os.getenv('TESTING') == None):
                    self.xbee_port = serial.Serial(self.serial_port, 57600, timeout=5)
                    logging.info("Connected to XBee")
                elif os.getenv('TESTING') == 'True': # Create a loopback to test locally
                    self.xbee_port = serial.serial_for_url('loop://', timeout=5)
                else: # Don't connect to XBee while in development
                    logging.info("In development mode, not connecting to XBee")
                break
            except serial.SerialException:
                logging.error("Failed to connect to xBee device. Retrying connection...")
                time.sleep(3)

    def send_command(self, data_station_id, command):

        # Immediately return False if in development (XBee not actually connected)
        if os.getenv('DEVELOPMENT') == 'True':
            return False

        # Update hash with new data_station_id
        hash = hashlib.md5()
        hash.update(data_station_id.encode('utf-8'))

        # Get MD5 hash to 3 hex characters
        identity_code = hash.hexdigest()[0:3]

        logging.debug("XBee TX: %s" % self.preamble_out)
        self.xbee_port.write(self.preamble_out.encode('utf-8'))

        logging.debug("XBee TX: %s" % identity_code)
        self.xbee_port.write(identity_code.encode('utf-8'))

        logging.debug("XBee TX: %s" % self.encode[command])
        self.xbee_port.write(self.encode[command].encode('utf-8'))

    def acknowledge(self, data_station_id, command):
        """
        Called after command is sent
        """

        iden_match = False
        identity_index = 0

        preamble_success = False
        preamble_index = 0

        # Update hash with new data_station_id
        hash = hashlib.md5()
        hash.update(data_station_id.encode('utf-8'))

        # Get MD5 hash to 3 hex characters
        identity_code = hash.hexdigest()[0:3]

        command_code = self.encode[command]

        while (self.xbee_port.in_waiting > 0): # There's something in the XBee buffer
            incoming_byte = self.xbee_port.read().decode('utf-8') # Read a byte at a time
            logging.debug("XBee RX: %s" % incoming_byte)

            # Third pass: Read command
            if (iden_match == True):
                return (incoming_byte == command_code)

            # Second pass: Check for identity match
            elif (preamble_success == True):
                if (incoming_byte == identity_code[identity_index]):
                    identity_index += 1
                else:
                    preamble_success = False
                    preamble_index = 0

                iden_match = (identity_index == 3)

            # First pass: Check for preamble match
            elif (incoming_byte == self.preamble_in[preamble_index]):
                preamble_index+=1
                preamble_success = (preamble_index == 3)

            # Reset
            else:
                iden_match = False
                preamble_success = False
                preamble_index = 0
                identity_index = 0

        return False # Unsuccessful ACK
