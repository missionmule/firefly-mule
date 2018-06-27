import serial
import time
import logging
import os


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
        self.data_station_idens = None

        self.preamble_out = ['s', 't', 'r', 'e', 'e', 't']
        self.preamble_in = ['c', 'a', 't']

        while True:
            try:
                if not "DEVELOPMENT" in os.environ: # Don't connect to XBee while in development
                    self.xbee_port = serial.Serial(serial_port, 9600, timeout=5)
                    logging.info("Connected to XBee")
                else:
                    logging.info("In development mode, not connecting to XBee")
                break
            except serial.SerialException:
                logging.error("Failed to connect to xBee device. Retrying connection...")
                time.sleep(3)

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

        self.data_station_idens = self.read_iden_map()

    def read_iden_map(self):
        return {
            'street_cat' : '01',
            'demon_cat' : '02'
        }

    def send_command(self, identity, command):

        # Immediately return False if in development (XBee not actually connected)
        if "DEVELOPMENT" in os.environ:
            return False

        logging.debug("XBee TX: %s" % self.preamble_out)
        self.xbee_port.write(self.preamble_out.encode('utf-8'))

        logging.debug("XBee TX: %s" % self.data_station_idens[identity])
        self.xbee_port.write(self.data_station_idens[identity].encode('utf-8'))

        logging.debug("XBee TX: %s" % self.encode[command])
        self.xbee_port.write(self.encode[command].encode('utf-8'))

    def acknowledge(self, identity, command):
        """
        Called after command is sent
        """

        iden_match = False
        identity_index = 0

        preamble_success = False
        preamble_index = 0

        identity_code = self.data_station_idens[identity]
        command_code = self.encode[command]

        while (self.xbee_port.in_waiting > 0): # There's something in the XBee buffer
            incoming_byte = self.xbee_port.read().decode('utf-8') # Read a byte at a time
            logging.debug("XBee TX: %s" % incoming_byte)

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

                iden_match = (identity_index == 2)

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
