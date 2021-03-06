#!/usr/bin/python3
#
# Heartbeat server
#
# Listen on a port for BEAT clients to send a heartbeat. When a client has
# sent it first heartbeat it is registered in a dictionary and if a client
# then has not sent a heartbeat in TIMEOUT second it is logged as dead in the
# heartbeat logfile.
#
# ./heartbeatserver.py <port>
#
#------------------------------------------------------------------------------
from socket import socket, gethostbyname, AF_INET, SOCK_DGRAM, gethostname
from threading import Lock, Thread, Event
from time import time, sleep
from datetime import datetime
import sys
import logging
import smtplib

# Listening port
port = 9999
# Heartbeat timeout interval
timeout = 60
# Logfile
logfile = 'heartbeat.log'
# Loglevel
loglevel = 'INFO'
# SMTP server
smtphost = 'localhost'
smtpport = 1025
smtpfrom = 'km@grogg.org'
smtprcvr = 'km@grogg.org'


# class heartbeatdictionary: {{{
#------------------------------------------------------------------------------
class heartbeatdictionary:
    """The dictionary of heartbeats"""

# def __init__(self): {{{
#------------------------------------------------------------------------------
    def __init__(self):

        # Initialize the dictionary
        self.dictionary = {}
        # Store the dictionary lock
        self.lock = Lock()

        return None


# }}}
# def getclients(self): {{{
#------------------------------------------------------------------------------
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

# def getaliveclients(self): {{{
#------------------------------------------------------------------------------
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


# }}}
# def getdeadclients(self, entry): {{{
#------------------------------------------------------------------------------
    def getdeadclients(self, timeout):
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


#}}}
# def update(self, entry): {{{
#------------------------------------------------------------------------------
    def update(self, entry):
        """Create or update heartbeat entry"""
        self.lock.acquire()
        self.dictionary[entry] = [time(), 1]
        self.lock.release()

        return None


# }}}
# def isotime(self, time): {{{
#------------------------------------------------------------------------------
    def isotime(self, time):
        """Convert epoch to isotime"""
        return '{}'.format(datetime.fromtimestamp(time).strftime('%Y-%m-%d %H:%M:%S'))

# }}}
# }}}
# class receiveheartbeat(Thread): {{{
#------------------------------------------------------------------------------
class receiveheartbeat(Thread):
    """
    A thread class that listens to heartbeats and logs them in the heartbeat
    dictionary
    """


# def __init__(self, heartbeatevent, updatedict, port): {{{
#------------------------------------------------------------------------------
    def __init__(self, running, updatedict, port):
        Thread.__init__(self)
        self.running = running
        self.updatedict = updatedict
        self.port = port
        self.ssocket = socket(AF_INET, SOCK_DGRAM)
        self.ssocket.bind(('', port))

        return None


# }}}
# def __repr__(self): {{{
#------------------------------------------------------------------------------
    def __repr__(self):
        """Describe ourself"""
        return "Heartbeat server listening port {}".format(self.port)


# }}}
# def run(self): {{{
#------------------------------------------------------------------------------
    def run(self):
        """Wait on the socket as long as the thread running event is set"""

        while self.running.is_set():
            # Wait wait wait for that socket to return
            data, address = self.ssocket.recvfrom(6)
            address = address[0]

            # We got something!
            if __debug__:
                print("Received packet from {}".format(address))
            self.updatedict(address)

        return


# }}}
# }}}
# def main(): {{{
#------------------------------------------------------------------------------
def main():
    """Listen to the heartbeats and report inactive clients"""

    global port, timeout, logfile, loglevel
    global smtphost, smtpport, smtpfrom, smtprcvr

    # Setup logging
    logger = logging.getLogger('heartbeat')
    logger.setLevel(loglevel)
    formatter = logging.Formatter('%(asctime)s %(name)s (%(levelname)s): %(message)s')

    # Log to file
    fh = logging.FileHandler(logfile)
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    # Decide heartbeat timeout and server listening port
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
    print('Listening on port {} with timeout {}. Ctrl-c to stop'.format(port, timeout))
    logger.info('STARTED on PORT {} with TIMEOUT {} and LOGLEVEL {}'
        .format(port, timeout, loglevel))

    # Main loop which checks for dead clients every INTERVAL
    while True:
        try:
            # Print addresses where heartbeats are heard
            aliveclients = heartbeats.getaliveclients()
            if aliveclients:
                print("--- alive clients ---")
                for client in aliveclients:
                    print('{0[0]} (Last heartbeat: {0[1]})'.format(client))
                    logger.info('ALIVE {0[0]} ({0[1]})'.format(client))

            # Print addresses where heartbeats have gone quiet
            deadclients = heartbeats.getdeadclients(timeout)
            if deadclients:
                print("--- dead clients ---")
                for client in deadclients:
                    print("{0[0]} (Last heartbeat: {0[1]})".format(client))
                    logger.info('DEAD {0[0]} ({0[1]})'.format(client))
                    # Only send an alert when the heartbeat goes silent
                    if client[2] > 0:
                        sendalert(client)

            # Nothing!
            if not aliveclients and not deadclients:
                print("No heartbeats yet... it's quiet out there")

            sleep(timeout)

        # Exit on ctrl-c but will only work if the server socket receives one
        # final packet
        except KeyboardInterrupt:
            print("Exiting...")
            heartbeatevent.clear()
            heartbeatthread.join()
            sys.exit(0)
    return None


# }}}
# def sendalert(client): {{{
#------------------------------------------------------------------------------
def sendalert(client):
    """Send email alert"""

    hostname = gethostname()
    message = """Subject: TELGE Heartbeat ALERT {client} is DOWN

{client} is DOWN since {isotime}

/heartbeat server on {hostname}
"""

    try:
        smtpserver = smtplib.SMTP(smtphost, smtpport)
        smtpserver.ehlo()
        smtpserver.sendmail(smtpfrom, smtprcvr, message
            .format(client=client[0], isotime=client[1], hostname=hostname))
    except Exception as e:
        print(e)
#    finally:
#        if smtpserver:
#            smtpserver.quit() 

    return None


if __name__ == '__main__':
    main()

# }}}
