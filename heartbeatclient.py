#!/usr/bin/python3
#
# Sends an UDP packet to the heartbeat server every X seconds.
#
# ./pyheartbeatc.py <server> <port>
#
#------------------------------------------------------------------------------
from socket import socket, AF_INET, SOCK_DGRAM
from time import time, sleep
from datetime import datetime
import sys

# Heartbeat server IP
server = '127.0.0.1'
# Heartbeat server port
port = 9999
# Heartbeat send interval
interval = 20

if len(sys.argv)>1:
    server=str(sys.argv[1])
if len(sys.argv)>2:
    port=int(sys.argv[2])

print('--- Heartbeat client ---')
print('Sending heartbeat every {} second to server {}:{}'.format(interval,
    server, port))

# Bind a socket
csocket = socket(AF_INET, SOCK_DGRAM)

# Forever send our heartbeat
while True:
    try:
        csocket.sendto('BEAT'.encode(), (server, port))
        print('Sent beat: {}'.format(
            datetime.fromtimestamp(time()).strftime('%Y-%m-%d %H:%M:%S')))
        sleep(interval)
    except KeyboardInterrupt:
        sys.exit(0)

