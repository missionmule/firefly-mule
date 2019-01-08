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

        self.start_delimiter = '~' # 0x7E in ASCII

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

        identity_code = data_station_id

        logging.debug("XBee TX: %s" % self.start_delimiter)
        self.xbee_port.write(self.start_delimiter.encode('utf-8'))

        logging.debug("XBee TX: %s" % identity_code)
        self.xbee_port.write(identity_code.encode('utf-8'))

        logging.debug("XBee TX: %s" % self.encode[command])
        self.xbee_port.write(self.encode[command].encode('utf-8'))

    def acknowledge(self, data_station_id, command):
        """
        Called after command is sent
        """

        # Mimic successful ACK
        if (os.getenv('DEVELOPMENT') == 'True'):
            time.sleep(5)
            return True

        iden_match = False
        identity_index = 0

        start_delimiter_success = False

        identity_code = data_station_id

        command_code = self.encode[command]

        while (self.xbee_port.in_waiting > 0): # There's something in the XBee buffer
            incoming_byte = self.xbee_port.read().decode('utf-8') # Read a byte at a time
            logging.debug("XBee RX: %s" % incoming_byte)

            # Third pass: Read command
            if (iden_match == True):
                logging.debug("XBee ACK success: %s", str(incoming_byte == command_code))
                return (incoming_byte == command_code)

            # Second pass: Check for identity match
            elif (start_delimiter_success == True):
                logging.debug("XBee checking ID")
                if (incoming_byte == identity_code[identity_index]):
                    identity_index += 1
                else:
                    start_delimiter_success = False

                iden_match = (identity_index == 3)

            # First pass: Check for start delimiter match
            elif (incoming_byte == self.start_delimiter):
                logging.debug("XBee checking start delimiter")
                start_delimiter_success = True

            # Reset
            else:
                iden_match = False
                start_delimiter_success = False
                identity_index = 0

        return False # Unsuccessful ACK

# XBee hardware isolation debug test
if __name__ == '__main__':
    xbee = XBee(serial_port="/dev/ttyUSB0")

    xbee.connect()

    target_station = raw_input("Enter target station ID: ")

    while True:
        print("---Command Options---")
        print("   POWER_ON : 1")
        print("   POWER_OFF : 2")
        print("   EXTEND_TIME: 3")
        cmd = input("Enter desired Command: ")

        if (cmd == '1'):
            command = 'POWER_ON'
        elif (cmd == '2'):
            command = 'POWER_OFF'
        else:
            command = 'EXTEND_TIME'

        xbee.send_command(target_station, command)
        time.sleep(1)

        if xbee.acknowledge(target_station, command):
            print("Acknowledge\n")
        else:
            print("Not acknowledged\n")
