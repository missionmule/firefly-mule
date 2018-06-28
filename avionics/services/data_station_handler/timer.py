"""
General utilities (functions and objects) used for data mule mission code.
"""

import time

class Timer(object):
    """
    Timer function that monitors time elapsed when started.
    """
    def __init__(self):
        self.start_timer()

    def start_timer(self):
        """Start the timer"""
        self.start = time.time()

    def time_elapsed(self):
        """Return the time elapsed since the timer was started"""
        return time.time()-self.start

    def time_stamp(self):
        """Create and return a time stamp string for logging purposes"""
        seconds = self.time_elapsed()
        mins, secs = divmod(seconds, 60)
        hours, mins = divmod(mins, 60)
        return "%d:%02d:%02d: " % (hours, mins, secs)
