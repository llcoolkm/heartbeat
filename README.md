# heartbeat

A tiny UDP heartbeat server and client written in Python 3. No
dependencies, no install — drop the two scripts wherever they are needed
and run them.

## How it works

Each client periodically sends a `BEAT` UDP packet to the server. The
server tracks every source address it has heard from. If a client falls
silent for longer than the configured timeout it is reported as **DEAD**
and an email alert is sent. When a previously dead client beats again
it is reported as **RECOVERED** and a recovery alert is sent.

## Server

```
./dbeats.py [port] [timeout] [options]
```

Positional arguments:

- `port` — UDP port to listen on (default `9999`)
- `timeout` — seconds before a silent client is considered dead (default `60`)

Options:

- `--logfile PATH` — log file (default `heartbeat.log`)
- `--loglevel LEVEL` — `DEBUG`, `INFO`, `WARNING`, ... (default `INFO`)
- `--smtp-host HOST` — SMTP relay (default `localhost`)
- `--smtp-port PORT` — SMTP port (default `1025`)
- `--smtp-from ADDR` — alert sender (default `heartbeat@localhost`)
- `--smtp-to ADDR` — alert recipient (default `root@localhost`)

Example:

```
./dbeats.py 9999 60 --smtp-host mail.example.org --smtp-to ops@example.org
```

## Client

```
./dbeatc.py [server] [port] [interval]
```

Positional arguments:

- `server` — server address (default `127.0.0.1`)
- `port` — server port (default `9999`)
- `interval` — seconds between beats (default `20`)

Example:

```
./dbeatc.py heartbeat.example.org 9999 30
```

The interval should be comfortably shorter than the server timeout.

## Tests

```
uv sync --extra dev
uv run pytest
```
