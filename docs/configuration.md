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
| `keep_alive` | `True` | Reuse a connection for several requests |
| `keep_alive_timeout` | `5.0` | Idle seconds before a kept-alive connection is closed |
| `max_keepalive_requests` | `100` | Requests per connection before it is closed |
| `reload` | `False` | Set by `--reload`; you normally do not set it yourself |
| `debug` | `False` | Debug logging and error details in 500 bodies |
| `extra` | `{}` | Your own settings |

## CLI

```
nexusserver [-h] [--host HOST] [--port PORT] [--workers N] [--debug] [--reload] [--version] app
```

Flags override the app's `Config`.

### `--reload`

`nexusserver mymodule:app --reload` runs the server in a child process and restarts it
when any `.py` file under the current directory changes (polling every 0.5 s; hidden
folders, `__pycache__`, `venv`, `node_modules`, `build` and `dist` are skipped). It is for
development only. If the server crashes it waits for the next edit instead of exiting.

### Keep-alive

With keep-alive on, a connection occupies one worker thread while it is idle. If many
clients hold connections open, raise `max_workers` or lower `keep_alive_timeout`; set
`keep_alive=False` to close every connection after one response. Pipelined requests
are answered in order. `Connection: close` from the client (and HTTP/1.0 without
`keep-alive`) is honoured.

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
