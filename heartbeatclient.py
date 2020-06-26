#!/usr/bin/python3
#
# Sends an UDP packet to the heartbeat server every X seconds.
#
# ./pyheartbeatc.py <server> <port>
#
#------------------------------------------------------------------------------
from socket import socket, AF_INET, SOCK_DGRAM
from time import time, ctime, sleep
import sys

# HB server IP
server = '127.0.0.1'
# HB server port
port = 9999
# HB send interval
interval = 10

if len(sys.argv)>1:
    server=sys.argv[1]
if len(sys.argv)>2:
    port=sys.argv[2]

print('--- pyHeartBeat client ---')
print('Sending heartbeat every {} second to server {}:{}'.format(interval, server, port))

hbsocket = socket(AF_INET, SOCK_DGRAM)
while True:
    hbsocket.sendto('PING'.encode(), (server, port))
    print('Time: {}'.format(ctime(time())))
    sleep(interval)

