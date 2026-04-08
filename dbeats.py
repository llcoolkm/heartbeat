#!/usr/bin/env python3
"""
Heartbeat server.

Listens for UDP BEAT packets from heartbeat clients. Each client is tracked
by source address. When a client falls silent for longer than the configured
timeout it is reported as dead and an email alert is sent. When a previously
dead client beats again, a recovery alert is sent.
"""

from __future__ import annotations

import argparse
import logging
import smtplib
import socket
import sys
from dataclasses import dataclass
from datetime import datetime
from email.message import EmailMessage
from threading import Event, Lock, Thread
from time import sleep, time


def isotime(epoch: float) -> str:
    """Convert epoch seconds to a human-readable ISO timestamp."""
    return datetime.fromtimestamp(epoch).isoformat(sep=' ', timespec='seconds')


@dataclass
class ClientState:
    last_seen: float
    alive: bool = True


class HeartbeatDictionary:
    """Thread-safe registry of heartbeat clients."""

    def __init__(self) -> None:
        self._clients: dict[str, ClientState] = {}
        self._recovered: list[tuple[str, float]] = []
        self._lock = Lock()

    def update(self, name: str) -> None:
        """Record a heartbeat from a client."""
        with self._lock:
            now = time()
            client = self._clients.get(name)
            if client is None:
                self._clients[name] = ClientState(last_seen=now, alive=True)
                return
            if not client.alive:
                self._recovered.append((name, now))
            client.last_seen = now
            client.alive = True

    def alive_clients(self) -> list[tuple[str, float]]:
        """Return all clients currently considered alive."""
        with self._lock:
            return [(name, c.last_seen)
                    for name, c in self._clients.items() if c.alive]

    def reap(self, timeout: int) -> list[tuple[str, float]]:
        """Mark stale clients dead and return the newly-dead ones."""
        threshold = time() - timeout
        newly_dead: list[tuple[str, float]] = []
        with self._lock:
            for name, c in self._clients.items():
                if c.alive and c.last_seen < threshold:
                    c.alive = False
                    newly_dead.append((name, c.last_seen))
        return newly_dead

    def drain_recovered(self) -> list[tuple[str, float]]:
        """Return and clear the list of clients that have recovered."""
        with self._lock:
            recovered = self._recovered
            self._recovered = []
            return recovered


class HeartbeatReceiver(Thread):
    """Listens on a UDP socket and feeds heartbeats into the dictionary."""

    def __init__(self, running: Event, hbdict: HeartbeatDictionary,
                 port: int) -> None:
        super().__init__(daemon=True)
        self.running = running
        self.hbdict = hbdict
        self.port = port
        self.ssocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.ssocket.bind(('', port))
        self.ssocket.settimeout(1.0)

    def __repr__(self) -> str:
        return f'HeartbeatReceiver(port={self.port})'

    def run(self) -> None:
        log = logging.getLogger('heartbeat')
        while self.running.is_set():
            try:
                _, address = self.ssocket.recvfrom(1024)
            except socket.timeout:
                continue
            except OSError as e:
                log.error(f'socket error: {e}')
                break
            log.debug(f'Received packet from {address[0]}')
            self.hbdict.update(address[0])
        self.ssocket.close()


@dataclass
class SmtpConfig:
    host: str = 'localhost'
    port: int = 1025
    sender: str = 'heartbeat@localhost'
    recipient: str = 'root@localhost'


def send_alert(smtp: SmtpConfig, subject: str, body: str) -> None:
    """Send an email alert. Failures are logged but not raised."""
    log = logging.getLogger('heartbeat')
    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = smtp.sender
    msg['To'] = smtp.recipient
    msg.set_content(body)
    try:
        with smtplib.SMTP(smtp.host, smtp.port) as server:
            server.send_message(msg)
    except Exception as e:
        log.error(f'failed to send alert: {e}')


def alert_dead(smtp: SmtpConfig, name: str, last_seen: float) -> None:
    hostname = socket.gethostname()
    send_alert(
        smtp,
        f'Heartbeat ALERT {name} is DOWN',
        f'{name} is DOWN since {isotime(last_seen)}\n\n'
        f'/heartbeat server on {hostname}\n',
    )


def alert_recovered(smtp: SmtpConfig, name: str, recovered_at: float) -> None:
    hostname = socket.gethostname()
    send_alert(
        smtp,
        f'Heartbeat RECOVERED {name} is UP',
        f'{name} is UP again at {isotime(recovered_at)}\n\n'
        f'/heartbeat server on {hostname}\n',
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='UDP heartbeat server')
    parser.add_argument('port', nargs='?', type=int, default=9999,
                        help='UDP port to listen on (default: 9999)')
    parser.add_argument('timeout', nargs='?', type=int, default=60,
                        help='seconds before a silent client is dead '
                             '(default: 60)')
    parser.add_argument('--logfile', default='heartbeat.log')
    parser.add_argument('--loglevel', default='INFO')
    parser.add_argument('--smtp-host', default='localhost')
    parser.add_argument('--smtp-port', type=int, default=1025)
    parser.add_argument('--smtp-from', default='heartbeat@localhost')
    parser.add_argument('--smtp-to', default='root@localhost')
    return parser.parse_args(argv)


def configure_logging(logfile: str, loglevel: str) -> logging.Logger:
    logger = logging.getLogger('heartbeat')
    logger.setLevel(loglevel)
    formatter = logging.Formatter(
        '%(asctime)s %(name)s (%(levelname)s): %(message)s')
    fh = logging.FileHandler(logfile)
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    sh = logging.StreamHandler()
    sh.setFormatter(formatter)
    logger.addHandler(sh)
    return logger


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    log = configure_logging(args.logfile, args.loglevel)

    smtp = SmtpConfig(
        host=args.smtp_host, port=args.smtp_port,
        sender=args.smtp_from, recipient=args.smtp_to,
    )

    running = Event()
    running.set()
    hbdict = HeartbeatDictionary()
    receiver = HeartbeatReceiver(running, hbdict, args.port)
    receiver.start()

    log.info(f'STARTED on port {args.port} timeout {args.timeout}s '
             f'loglevel {args.loglevel}')

    try:
        while True:
            for name, ts in hbdict.alive_clients():
                log.info(f'ALIVE {name} ({isotime(ts)})')
            for name, ts in hbdict.drain_recovered():
                log.info(f'RECOVERED {name} ({isotime(ts)})')
                alert_recovered(smtp, name, ts)
            for name, ts in hbdict.reap(args.timeout):
                log.info(f'DEAD {name} ({isotime(ts)})')
                alert_dead(smtp, name, ts)
            sleep(args.timeout)
    except KeyboardInterrupt:
        log.info('Exiting...')
        running.clear()
        receiver.join()
        return 0


if __name__ == '__main__':
    sys.exit(main())
