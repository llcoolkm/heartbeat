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
from time import time, ctime, sleep
import sys

# HB server port
port = 9999
# HB timeout interval
interval = 30

class heartbeatdict:
    """ Manage the heartbeat dictionary """

    def __init__(self):
        self.heartbeatdict= {}
        if __debug__:
            self.heartbeatdict['127.0.0.1'] = time()
        self.dictlock = Lock()

    def __repr__(self):
        list = ''
        self.dictlock.acquire()
        for key in self.heartbeatdict.keys():
            list.append('IP address: {} - Last heartbeat: {}'
                .format(key, ctime(self.heartbeatdict[key])))
        self.dictlock.release()
        return list

    def update(self, entry):
        """ Create or update a dictionary entry """
        self.dictlock.acquire()
        self.heartbeatdict[entry] = time()
        self.dictlock.release()

    def getsilent(self, howpast):
        """ Returns a list of entries older than howPast """
        silent = []
        when = time() - howPast
        self.dictlock.acquire()
        for key in self.beatDict.keys():
            if self.beatDict[key] < when:
                silent.append(key)
        self.dictlock.release()
        return silent

class beatrec(Thread):
    """ Receive UDP packets, log them in heartbeat dictionary """

    def __init__(self, goOnEvent, updateDictFunc, port):
        Thread._ _init_ _(self)
        self.goOnEvent = goOnEvent
        self.updateDictFunc = updateDictFunc
        self.port = port
        self.recSocket = socket(AF_INET, SOCK_DGRAM)
        self.recSocket.bind(('', port))

    def _ _repr_ _(self):
        return "Heartbeat Server on port: %d\n" % self.port

    def run(self):
        while self.goonevent.isset():
            if __debug__:
                print "Waiting to receive..."
            data, addr = self.recsocket.recvfrom(6)
            if __debug__:
                print "Received packet from " + `addr`
            self.updatedictfunc(addr[0])

def main(  ):
    """ Listen to the heartbeats and detect inactive clients """

    global port, interval
    if len(sys.argv)>1:
        HBPORT=sys.argv[1]
    if len(sys.argv)>2:
        CHECKWAIT=sys.argv[2]

    beatRecGoOnEvent = Event(  )
    beatRecGoOnEvent.set(  )
    beatDictObject = Beatdict(  )
    beatRecThread = BeatRec(beatRecGoOnEvent, beatDictObject.update, HBPORT)

    beatrecthread.start()
    print('--- HeartBeat Server ---')
    print('Listening on port {}. Ctrl-c to stop'.format(port))

    while True:
        try:
            if _ _debug_ _:
                print "Beat Dictionary"
                print `beatDictObject`
            silent = beatDictObject.extractSilent(CHECKWAIT)
            if silent:
                print "Silent clients"
                print `silent`
            sleep(CHECKWAIT)
        except KeyboardInterrupt:
            print "Exiting."
            beatRecGoOnEvent.clear(  )
            beatRecThread.join(  )

if _ _name_ _ == '_ _main_ _':
    main(  )

