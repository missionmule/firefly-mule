from stat import S_ISDIR
import socket
import traceback
import logging

import paramiko
import os
import binascii

class SFTPClient(object):

    # Ensure pi users on payload and data station computers have r/w access to these directories
    REMOTE_ROOT_DATA_DIRECTORY = '/media/'
    LOCAL_ROOT_DATA_DIRECTORY = '/srv/'

    REMOTE_FIELD_DATA_SOURCE = REMOTE_ROOT_DATA_DIRECTORY + ''               # Location relative to SFTP root directory where the field data files are located; current SFTP root from pi@cameratrap.local /home/pi/
    LOCAL_FIELD_DATA_DESTINATION = LOCAL_ROOT_DATA_DIRECTORY + 'field/'      # Where downloaded data station field data will be kept

    # REMOTE_LOG_SOURCE = REMOTE_ROOT_DATA_DIRECTORY+'logs/'                   # Location relative to SFTP root directory where the data station log files are located
    # LOCAL_LOG_DESTINATION = LOCAL_ROOT_DATA_DIRECTORY + 'logs/'              # Where downloaded data station logs will be kept

    # Paramiko client configuration
    PORT = 22
    USE_GSS_API = False
    DO_GSS_API_KEY_EXCHANGE = False

    __host_key_type = None
    __host_key = None

    __sftp = None                                       # Our SFTP client
    __transport = None                                  # Paramiko transport

    __hostname = None
    __username = None
    __password = None

    is_connected = False

    def __init__(self, _username, _password, _hostname, _flight_id):

        # Update destination directories to include hostname for data differentiation
        self.__hostname, self.__network_suffix = _hostname.split('.')
        self.LOCAL_FIELD_DATA_DESTINATION = os.path.join(self.LOCAL_ROOT_DATA_DIRECTORY, str(_flight_id), self.__hostname)
        # self.LOCAL_LOG_DESTINATION = '%s/%s/%s/' % (self.LOCAL_ROOT_DATA_DIRECTORY, _flight_id, self.__hostname)

        # TODO: change from password to public key cryptography
        # Login credentials
        self.__username = _username
        self.__password = _password
        self.__hostname = _hostname

        host_keys = paramiko.util.load_host_keys(os.path.expanduser('/home/pi/.ssh/known_hosts'))
        logging.getLogger("paramiko").setLevel(logging.INFO)

        if self.__hostname in host_keys:
            self.__hostkeytype = host_keys[self.__hostname].keys()[0]
            self.__hostkey = host_keys[self.__hostname][self.__hostkeytype]

    def connect(self, timeout=60000):
        # now, connect and use paramiko Transport to negotiate SSH2 across the connection
        logging.info("Connecting to data station... [hostname: %s]" % (self.__hostname))

        # Timeout is handled by Navigation.
        try:
            self.__transport = paramiko.Transport((self.__hostname, self.PORT)) # Speeds up download speed

            # Compress files on data station before sending over Wi-Fi to drone
            self.__transport.connect(self.__host_key, self.__username, self.__password,
                                     gss_host=socket.getfqdn(self.__hostname),
                                     gss_auth = self.USE_GSS_API,
                                     gss_kex = self.DO_GSS_API_KEY_EXCHANGE)

            self.__sftp = paramiko.SFTPClient.from_transport(self.__transport)

            self.__sftp.get_channel().settimeout(timeout/1000) # Timeout in seconds on read/write operations on underlying SSH channel
            logging.info("Connection established to data station: %s" % (self.__hostname))

            # Ensure remote root data directory exists
            try:
                self.__sftp.mkdir(self.REMOTE_ROOT_DATA_DIRECTORY)
            except IOError:
                logging.debug(
                    '{0} remote root data directory already exists'.format(self.REMOTE_FIELD_DATA_SOURCE))

            # Ensure remote field data directory exists
            try:
                self.__sftp.mkdir(self.REMOTE_FIELD_DATA_SOURCE)
            except IOError:
                logging.debug(
                    '{0} remote field data directory already exists'.format(self.REMOTE_FIELD_DATA_SOURCE))

            # # Ensure remote log directory exists
            # try:
            #     self.__sftp.mkdir(self.REMOTE_LOG_SOURCE)
            # except IOError:
            #     logging.debug('{0} remote log directory already exists'.format(self.REMOTE_LOG_SOURCE))

            # `os.makedirs()` recursively creates entire file path so ./data/ is created in the process of creating
            # local destination directory (./data/field/)

            # Ensure local field data directory exists
            if not os.path.exists(self.LOCAL_FIELD_DATA_DESTINATION):
                os.makedirs(self.LOCAL_FIELD_DATA_DESTINATION)

            # # Ensure local log data directory exists
            # if not os.path.exists(self.LOCAL_LOG_DESTINATION):
            #     os.makedirs(self.LOCAL_LOG_DESTINATION)

            self.is_connected = True

        except Exception as e:
            logging.warn('Connection to data station %s failed' % (self.__hostname))
            logging.debug(e)


    # -----------------------
    # General utility methods with robust connection timeout handling
    # -----------------------

    def getRemoteFileList(self, remote_path):

        # Ensure there's something to fetch
        try:
            self.__sftp.mkdir(remote_path)
        except IOError:
            logging.debug('{0} remote field data directory already exists'.format(remote_path))
        except socket.timeout:
            logging.error("Listing remote directories timeout")

        directory_contents = []
        try:
            directory_contents = self.__sftp.listdir(remote_path)
        except IOError as e:
            logging.error(e)
        except socket.timeout:
            logging.error("Listing remote directories timeout")

        return directory_contents

    def downloadFile(self, remote_path, local_destination, file_name):
        """
        Download remote file to given local destination
        """
        logging.info("Downloading file: %s" % (file_name))
        try:
            self.__sftp.get(os.path.join(remote_path,file_name), os.path.join(local_destination,file_name))
        except IOError as e:
            logging.error(e)
        except socket.timeout:
            logging.error("Listing remote directories timeout")

    def moveFileToTmp(self, remote_path, file_name):
        """
        Move file to /.tmp/ directory on sensor to await second pass deletion
        """
        logging.info("Moving to /.tmp/: %s" % (file_name))

        # TODO: Eliminate the need for a .tmp directory creation with each move
        # Make sure '.tmp' exists in current directory
        try:
            self.__sftp.mkdir(os.path.join(remote_path, '.tmp'))
        except IOError:
            logging.debug('{0} remote log directory already exists'.format(os.path.join(remote_path, '.tmp')))

        oldpath = os.path.join(remote_path, file_name)
        newpath = os.path.join(remote_path, '.tmp', file_name)
        self.__sftp.rename(oldpath, newpath)

    def deleteFile(self, remote_path, file_name):
        """
        Delete file from given path on remote data station
        """
        logging.info("Deleting file from data station: %s" % (os.path.join(remote_path,file_name)))
        try:
            self.__sftp.remove(os.path.join(remote_path,file_name))
        except IOError as e:
            logging.error(e)
        except socket.timeout:
            logging.error("Listing remote directories timeout")

    # NOTICE: Make sure to close the SFTP connection after download is complete
    def close(self):
        logging.debug("Closing connection to data station... [hostname: %s]" % (self.__hostname))
        self.__sftp.close()
        logging.info("Connection to data station closed [hostname: %s]" % (self.__hostname))


    # -----------------------
    # Field data methods
    # -----------------------

    def _walk(self, remote_path):
        path=remote_path
        files=[]
        folders=[]

        for f in self.__sftp.listdir_attr(remote_path):
            if S_ISDIR(f.st_mode):
                folders.append(f.filename)
            else:
                files.append(f.filename)

        if files:
            yield path, files

        for folder in folders:
            new_path = os.path.join(remote_path, folder)
            for x in self._walk(new_path):
                yield x

    # TODO: ensure this handles files with same name in different directories
    def downloadNewFieldData(self):
        """
        Download all data station field data
        Recurses from /media/ dir to download all data

        Returns number of files to be downloaded as well as files successfully downloaded.
        """

        num_files_to_download = 0
        num_files_downloaded = 0

        for path, files in self._walk(self.REMOTE_FIELD_DATA_SOURCE):
            if not (path.endswith('.tmp') or path.endswith('.tmp/')):

                # Loop through all files and count number to be downloaded
                # This is separate from the loop below to account for inaccurate
                # counts as a result of a failed download or download timeout.
                for file in files:
                    if (not file.startswith('.')) and (file.endswith('.JPG') or file.endswith('.JPEG') or file.endswith('.jpg') or file.endswith('.jpeg')):
                        num_files_to_download+=1

                # Download files
                for file in files:
                    if (not file.startswith('.')) and (file.endswith('.JPG') or file.endswith('.JPEG') or file.endswith('.jpg') or file.endswith('.jpeg')):
                        try:
                            self.downloadFile(path, self.LOCAL_FIELD_DATA_DESTINATION, file)
                            self.moveFileToTmp(path, file)
                            num_files_downloaded+=1
                        except: # Don't move file to tmp if error is raised in download
                            pass

        return num_files_downloaded, num_files_to_download

    def downloadTmpFieldData(self):
        """
        Download data from /.tmp/ directory on sensor
        This method is called when the flight operator has requested a redownload
        of previously downloaded data (which has since been moved to the /.tmp/
        directory to await deletion on the second pass of the UAV).

        Returns number of files to be downloaded as well as files successfully downloaded.
        """

        num_files_to_download = 0
        num_files_downloaded = 0

        for path, files in self._walk(self.REMOTE_FIELD_DATA_SOURCE):

            # Recurse into /media/ and download only `.tmp` directories
            if path.endswith('.tmp') or path.endswith('.tmp/'):
                # Loop through all files and count number to be downloaded
                # This is separate from the loop below to account for inaccurate
                # counts as a result of a failed download or download timeout.

                for file in files:
                    if (not file.startswith('.')) and (file.endswith('.JPG') or file.endswith('.JPEG') or file.endswith('.jpg') or file.endswith('.jpeg')):
                        num_files_to_download+=1

                for file in files:
                    if (not file.startswith('.')) and (file.endswith('.JPG') or file.endswith('.JPEG') or file.endswith('.jpg') or file.endswith('.jpeg')):
                        try:
                            self.downloadFile(path, self.LOCAL_FIELD_DATA_DESTINATION, file)
                            num_files_downloaded+=1
                        except:
                            pass

        return num_files_downloaded, num_files_to_download

    def deleteTmpFieldData(self):
        """
        Delete all data from /.tmp/ directory on sensor file system
        This data was moved to the /.tmp/ directory following a successful
        download and this method is called unless the flight operator has ordered
        a redownload of previously downloaded data.
        """
        for path, files in self._walk(self.REMOTE_FIELD_DATA_SOURCE):
            if path.endswith('.tmp') or path.endswith('.tmp/'):
                for file in files:
                    self.deleteFile(path, file)

    # -----------------------
    # Log data methods
    # -----------------------

    def downloadAllLogData(self):
        """
        Download all data station log data
        """
        pass
        # file_list = self.getRemoteFileList(self.REMOTE_LOG_SOURCE)
        # if not file_list:
        #     logging.info("No log files to download")
        # else:
        #     logging.info("Downloading %i log files..." % (len(file_list)))
        #     # Download all files
        #     for file_name in file_list:
        #         self.downloadFile(self.REMOTE_LOG_SOURCE, self.LOCAL_LOG_DESTINATION, file_name)

    def deleteAllLogData(self):
        """
        Remove successfully downloaded log files
        """
        pass
        # logging.debug("Beginning data station log removal")
        # for file_name in os.listdir(self.LOCAL_LOG_DESTINATION): # List newly downloaded files
        #     self.deleteFile(self.REMOTE_LOG_SOURCE, file_name)
        # logging.info("Field data removal complete")
