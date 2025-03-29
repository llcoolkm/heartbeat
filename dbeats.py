#!/usr/bin/env python3
#
# Heartbeat server
#
# Listen on a port for BEAT clients to send a heartbeat. When a client has
# sent it first heartbeat it is registered in a dictionary and if a client
# then has not sent a heartbeat in TIMEOUT second it is logged as dead in the
# heartbeat logfile.
#
# ./dbeats.py <port>
#
# -----------------------------------------------------------------------------

from datetime import datetime
from socket import socket, AF_INET, SOCK_DGRAM, gethostname
import sys
from threading import Lock, Thread, Event
from time import time, sleep

import logging
import smtplib

# Defaults
port = 9999
timeout = 60
logfile = 'heartbeat.log'
loglevel = 'INFO'
smtphost = 'localhost'
smtpport = 1025
smtpfrom = 'km@grogg.org'
smtprcvr = 'km@grogg.org'


# -----------------------------------------------------------------------------

class heartbeatdictionary:
    """The dictionary of heartbeats"""


# -----------------------------------------------------------------------------
    def __init__(self) -> None:

        # Initialize the dictionary
        self.dictionary = {}
        # Store the dictionary lock
        self.lock = Lock()

        return None

# ------------------------------------------------------------------------------

    def getclients(self):
        """Return a list of known clients and last heartbeat"""
        clients = []

        # Create a list of keys
        self.lock.acquire()
        for key in self.dictionary.keys():
            clients.append([key, self.isotime(self.dictionary[key][0]),
                            self.dictionary[key][1]])
        self.lock.release()

        return clients

# ------------------------------------------------------------------------------

    def getaliveclients(self):
        """Return a list of alive clients and last heartbeat"""
        clients = []

        # Create a list of keys
        self.lock.acquire()
        for key in self.dictionary.keys():
            # Only return alive clients
            if self.dictionary[key][1] > 0:
                clients.append([key, self.isotime(self.dictionary[key][0])])
        self.lock.release()

        return clients

# ------------------------------------------------------------------------------

    def getdeadclients(self, timeout: int):
        """Returns a list of dead clients older than timeout and not previously
        reported as dead"""
        clients = []
        when = time() - timeout

        # Extract timed out entries
        self.lock.acquire()
        for key in self.dictionary.keys():
            if self.dictionary[key][0] < when:
                clients.append([key, self.isotime(self.dictionary[key][0]),
                                self.dictionary[key][1]])
                # Set dead clients to 0, this way we can distinguish recently
                # deceased for alerting purposes
                self.dictionary[key][1] = 0

        self.lock.release()

        return clients

# ------------------------------------------------------------------------------

    def update(self, entry: str) -> None:
        """Create or update heartbeat entry"""
        self.lock.acquire()
        self.dictionary[entry] = [time(), 1]
        self.lock.release()

        return None

# -----------------------------------------------------------------------------

    def isotime(self, time: int) -> str:
        """Convert epoch to isotime"""
        return f'{datetime.fromtimestamp(time).strftime('%Y-%m-%d%H:%M:%S')}'


# -----------------------------------------------------------------------------

class receiveheartbeat(Thread):
    """
    A thread class that listens to heartbeats and logs them in the heartbeat
    dictionary
    """


# -----------------------------------------------------------------------------

    def __init__(self, running: Event, updatedict, port: int) -> None:
        Thread.__init__(self)
        self.running = running
        self.updatedict = updatedict
        self.port = port
        self.ssocket = socket(AF_INET, SOCK_DGRAM)
        self.ssocket.bind(('', port))

        return None

# -----------------------------------------------------------------------------

    def __repr__(self) -> str:
        """Describe ourself"""
        return f'Heartbeat server listening on port {self.port}'

# -----------------------------------------------------------------------------

    def run(self) -> None:
        """Wait on the socket as long as the thread running event is set"""

        while self.running.is_set():
            # Wait wait wait for that socket to return
            address = self.ssocket.recvfrom(6)[1][0]

            # We got something!
            if __debug__:
                print(f'Received packet from {address}')
            self.updatedict(address)

        return None


# -----------------------------------------------------------------------------

def main() -> None:
    """Listen to the heartbeats and report inactive clients"""

    global port, timeout, logfile, loglevel
    global smtphost, smtpport, smtpfrom, smtprcvr

    # Setup logging
    logger = logging.getLogger('heartbeat')
    logger.setLevel(loglevel)
    formatter = logging.Formatter(
        '%(asctime)s %(name)s (%(levelname)s): %(message)s')

    # Log to file
    fh = logging.FileHandler(logfile)
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    # Decide heartbeat timeout and server listening port
    if len(sys.argv) == 1:
        print('Usage: ./dbeats.py <port> <timeout>')
        sys.exit(0)
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
    if len(sys.argv) > 2:
        timeout = int(sys.argv[2])

    # Create and set the thread event object
    heartbeatevent = Event()
    heartbeatevent.set()

    # Instantiate a heartbeat dictionary
    heartbeats = heartbeatdictionary()

    # Start listening to heartbeats
    heartbeatthread = receiveheartbeat(heartbeatevent, heartbeats.update, port)
    heartbeatthread.start()
    print('--- Heartbeat server ---')
    print(f'Listening on port {port} with timeout {timeout}. Ctrl-c to stop')
    logger.info(f'STARTED on PORT {port} with TIMEOUT {timeout} and '
                f'LOGLEVEL {loglevel}')

    # Main loop which checks for dead clients every INTERVAL
    while True:
        try:
            # Print addresses where heartbeats are heard
            aliveclients = heartbeats.getaliveclients()
            if aliveclients:
                print('--- Alive clients ---')
                for client_name, client_beat in aliveclients:
                    print(f'{client_name} (Last heartbeat: {client_beat})')
                    logger.info(f'ALIVE {client_name} ({client_beat})')

            # Print addresses where heartbeats have gone quiet
            deadclients = heartbeats.getdeadclients(timeout)
            if deadclients:
                print('--- Dead clients ---')
                for client_name, client_beat, client_dead in deadclients:
                    print(f'{client_name} (Last heartbeat: {client_beat})')
                    logger.info(f'DEAD {client_name} ({client_beat})')
                    # Send an alert if the client is recently deceased
                    if client_dead > 0:
                        sendalert(client_name, client_beat)

            # Nothing!
            if not aliveclients and not deadclients:
                print('No heartbeats yet... it\'s quiet out there')

            sleep(timeout)

        # Exit on ctrl-c but will only work if the server socket receives one
        # final packet
        except KeyboardInterrupt:
            print('Exiting...')
            heartbeatevent.clear()
            heartbeatthread.join()
            sys.exit(0)


# -----------------------------------------------------------------------------

def sendalert(client_name: str, client_beat: str) -> None:
    """Send email alert"""

    hostname = gethostname()
    message = f"""Subject: Heartbeat ALERT {client_name} is DOWN

{client_name} is DOWN since {client_beat}

/heartbeat server on {hostname}
"""

    try:
        smtpserver = smtplib.SMTP(smtphost, smtpport)
        smtpserver.ehlo()
        smtpserver.sendmail(smtpfrom, smtprcvr, message)
    except Exception as e:
        print(e)
#    finally:
#        if smtpserver:
#            smtpserver.quit()

    return None


# -----------------------------------------------------------------------------

if __name__ == '__main__':
    main()
