#!/usr/bin/python3
#
# Heartbeat server
#
# While the BeatLog thread logs each UDP packet in a dictionary, the main
# thread periodically scans the dictionary and prints the IP addresses of the
# clients that sent at least one packet during the run, but have
# not sent any packet since a time longer than the definition of the timeout.
#
# ./heartbeatserver.py <port>
#
#------------------------------------------------------------------------------
from socket import socket, gethostbyname, AF_INET, SOCK_DGRAM
from threading import Lock, Thread, Event
from time import time, sleep
from datetime import datetime
import sys

# Listening port
port = 9999
# Heartbeat timeout interval
timeout = 10

# class heartbeatdictionary: {{{
#------------------------------------------------------------------------------
class heartbeatdictionary:
    """ The dictionary of heartbeats """

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
        """ Return a list of clients and last heartbeat """

        clients = []

        # Create a list of keys
        self.lock.acquire()
        for key in self.dictionary.keys():
            clients.append('{} (last heartbeat: {})'
                .format(key, self.isotime(self.dictionary[key])))
        self.lock.release()

        return clients


# }}}
# def update(self, entry): {{{
#------------------------------------------------------------------------------
    def update(self, entry):
        """ Create or update heartbeat entry """

        self.lock.acquire()
        self.dictionary[entry] = time()
        self.lock.release()

        return None


# }}}
# def getdead(self, entry): {{{
#------------------------------------------------------------------------------
    def getdead(self, timeout):
        """ Returns a list of entries older than timeout """

        dead = []
        when = time() - timeout

        # Extract timed out entries
        self.lock.acquire()
        for key in self.dictionary.keys():
            if self.dictionary[key] < when:
                dead.append([key, self.isotime(self.dictionary[key])])
        self.lock.release()

        return dead


#}}}
# def isotime(self, time): {{{
#------------------------------------------------------------------------------
    def isotime(self, time):
        """ Convert epoch to isotime """
        return '{}'.format(datetime.fromtimestamp(time).strftime('%Y-%m-%d %H:%M:%S'))

# }}}
# }}}
# class receiveheartbeat(Thread): {{{
#------------------------------------------------------------------------------
class receiveheartbeat(Thread):
    """ A thread class that listens to heartbeats and logs them in the
    heartbeat dictionary """


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
        """ Describe ourself """
        return "Heartbeat server listening port {}".format(self.port)


# }}}
# def run(self): {{{
#------------------------------------------------------------------------------
    def run(self):
        """ Wait on the socket as long as the thread running event is set """

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
    """ Listen to the heartbeats and report inactive clients """

    # Decide heartbeat timeout and server listening port
    global port, timeout
    if len(sys.argv)>1:
        port=int(sys.argv[1])
    if len(sys.argv)>2:
        timeout=int(sys.argv[2])

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

    # Main loop which checks for dead clients every INTERVAL
    while True:
        try:
            # Print heartbeats that have been heard
            clients = heartbeats.getclients()
            if clients:
                print("--- Known heartbeat clients ---")
                print('\n'.join(heartbeats.getclients()))
            else:
                print("No heartbeats yet... it's very quiet out there")

            # Check for dead clients and print them
            dead = heartbeats.getdead(timeout)
            if dead:
                print("--- Missing heartbeat clients ---")
                for client in dead:
                    print("{0[0]} (last heartbeat: {0[1]})".format(client))
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
# def handle_silent(): {{{
#------------------------------------------------------------------------------
def handle_silent():
    """  """

    return None



if __name__ == '__main__':
    main()

# }}}
