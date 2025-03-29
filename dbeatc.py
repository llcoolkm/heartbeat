#!/usr/bin/env python3
#
# Sends an UDP packet to the heartbeat server every X seconds.
#
# ./dbeatc.py <server> <port> <interval>
#
# -----------------------------------------------------------------------------

from datetime import datetime
from socket import socket, AF_INET, SOCK_DGRAM
import sys
from time import time, sleep

# Defaults
server = '127.0.0.1'
port = 9999
interval = 20

# Arguments
if len(sys.argv) == 1:
    print('Usage: ./dbeatc.py <server> <port> <interval>')
    sys.exit(0)
if len(sys.argv) > 1:
    server = str(sys.argv[1])
if len(sys.argv) > 2:
    port = int(sys.argv[2])
if len(sys.argv) > 3:
    interval = int(sys.argv[3])

print('--- Heartbeat client ---')
print(f'Sending heartbeat every {interval} second to server {server}:{port}')

# Bind a socket
csocket = socket(AF_INET, SOCK_DGRAM)

# Forever send our heartbeat
while True:
    try:
        csocket.sendto('BEAT'.encode(), (server, port))
        print(f'Sent beat: {datetime.fromtimestamp(
            time()).strftime('%Y-%m-%d %H:%M:%S')}')
        sleep(interval)
    except KeyboardInterrupt:
        sys.exit(0)
