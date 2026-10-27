# Configuration

```python
from nexusserver import Application, Config

app = Application(Config(host="0.0.0.0", port=8080, max_workers=32, debug=True))
```

| Field | Default | Meaning |
| --- | --- | --- |
| `host` | `127.0.0.1` | Bind address (`0.0.0.0` to accept outside connections) |
| `port` | `8000` | Bind port (`0` picks a free port; read it from `HTTPEngine.address`) |
| `backlog` | `128` | Listen queue length |
| `max_workers` | `16` | Thread pool size = concurrent requests |
| `max_request_size` | 16 MiB | Largest request body; larger gives 413 |
| `max_header_size` | 64 KiB | Largest request line plus headers; larger gives 431 |
| `read_timeout` | `30.0` | Seconds to wait on a client socket; then 408 |
| `request_timeout` | `30.0` | Reserved |
| `keep_alive`, `keep_alive_timeout` | `False`, `5.0` | Reserved; each connection serves one request |
| `reload` | `False` | Reserved; not implemented |
| `debug` | `False` | Debug logging and error details in 500 bodies |
| `extra` | `{}` | Your own settings |

## CLI

```
nexusserver [-h] [--host HOST] [--port PORT] [--workers N] [--debug] [--reload] [--version] app
```

Flags override the app's `Config`. `--reload` prints a warning and does nothing yet.

## Hooks

```python
@app.on_startup
def start(): ...

@app.on_shutdown
def stop(): ...
```

Startup hooks run in registration order before the socket opens; shutdown hooks
run in reverse order on exit (including Ctrl+C).

## Logging

`nexusserver` (app), `nexusserver.server` and `nexusserver.access` (one line per
request: `client METHOD path status time`). `app.run()` calls
`logging.basicConfig`; configure logging yourself before `run()` for custom output.
