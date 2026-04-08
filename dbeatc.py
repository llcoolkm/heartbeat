#!/usr/bin/env python3
"""
Heartbeat client.

Sends a UDP BEAT packet to the heartbeat server every interval seconds.
"""

from __future__ import annotations

import argparse
import socket
import sys
from datetime import datetime
from time import sleep


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='UDP heartbeat client')
    parser.add_argument('server', nargs='?', default='127.0.0.1',
                        help='server address (default: 127.0.0.1)')
    parser.add_argument('port', nargs='?', type=int, default=9999,
                        help='server port (default: 9999)')
    parser.add_argument('interval', nargs='?', type=int, default=20,
                        help='seconds between beats (default: 20)')
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    print(f'Heartbeat client -> {args.server}:{args.port} '
          f'every {args.interval}s')

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        while True:
            try:
                sock.sendto(b'BEAT', (args.server, args.port))
                stamp = datetime.now().isoformat(sep=' ', timespec='seconds')
                print(f'Sent beat: {stamp}')
            except OSError as e:
                print(f'Send failed: {e}', file=sys.stderr)
            sleep(args.interval)
    except KeyboardInterrupt:
        return 0
    finally:
        sock.close()


if __name__ == '__main__':
    sys.exit(main())
