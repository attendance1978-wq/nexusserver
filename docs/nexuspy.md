# nexuspy: Python environment management

nexuspy is the environment manager built into NexusServer (since 26.4.0). It creates
and manages virtual environments in one place, so you can name them, pick the Python
version, lock them, clone them and run commands inside them.

```bash
nexuspy --version
nexuspy create web flask requests          # env "web" with two packages
nexuspy create legacy --python 3.9         # choose the interpreter
nexuspy list
nexuspy run web -- python app.py           # no activation needed
```

Same thing without the console script: `python -m nexusserver.nexuspy ...`.

## Where things live

`~/.nexuspy/envs/<name>/` is an ordinary `venv` directory plus a small `nexuspy.json`
(creation time, interpreter). Change the location with `--home DIR` or the `NEXUSPY_HOME`
environment variable. Environment names are 1-64 characters: letters, digits, `.`, `_`, `-`,
starting with a letter or digit.

## Commands

| Command | What it does |
| --- | --- |
| `pythons [--json]` | List Python 3 interpreters found on `PATH` |
| `create NAME [pkgs...] [--python SPEC] [-r FILE] [--system-site-packages] [--no-pip]` | Create an environment, optionally installing packages |
| `list [--json]` / `info NAME` | Show environments |
| `remove NAME [-y]` | Delete an environment (asks first unless `-y`) |
| `install NAME [pkgs...] [-r FILE] [-U]` / `uninstall NAME pkgs...` | Manage packages |
| `packages NAME [--json]` / `freeze NAME` | Inspect what is installed |
| `lock NAME [-o FILE]` | Write pinned requirements (default `nexuspy.lock`) |
| `sync NAME [FILE]` | Install exactly what a lock file lists |
| `clone SOURCE TARGET` | Same interpreter and packages under a new name |
| `run NAME -- CMD...` | Run a command with the environment active; exits with its status |
| `shell NAME` | Interactive subshell with the environment active |
| `activate NAME [--shell bash\|zsh\|fish\|powershell\|cmd]` | Print the activation command |
| `path NAME` | Print the environment's Python path |
| `use NAME` / `current` | Bind a directory to an environment (`.nexuspy-env`) |
| `doctor NAME` | Health checks; non-zero exit if one fails |
| `serve` | Start the management API (below) |

`--python` accepts a version prefix (`3.11`, `3.12.3`, `python3.10`) or a path to an executable.
`nexuspy pythons` shows what it can find.

Activating in your current shell is something only the shell can do, so nexuspy prints the command:

```bash
eval "$(nexuspy activate web)"       # bash / zsh
nexuspy activate web --shell powershell
```

## Typical workflows

```bash
# Reproducible environment
nexuspy create api -r requirements.txt
nexuspy lock api                      # commit nexuspy.lock
nexuspy create ci --python 3.11 && nexuspy sync ci nexuspy.lock

# Per-project default
cd myproject && nexuspy use api       # writes .nexuspy-env
nexuspy current                       # -> api
```

## Python API

```python
from nexusserver.nexuspy import EnvManager

manager = EnvManager()                               # or EnvManager("/some/home")
env = manager.create("web", python="3.12", packages=["flask"])
manager.install("web", ["requests>=2.31"])
manager.packages("web")                              # [{"name": "flask", "version": "3.0.0"}, ...]
manager.lock("web", "nexuspy.lock")
result = manager.run("web", ["python", "-c", "import flask"], capture=True)
manager.clone("web", "web-test")
manager.remove("web-test")
```

Errors derive from `NexusPyError`: `InvalidName`, `EnvNotFound`, `EnvExists`,
`InterpreterNotFound`, and `CommandFailed` (has `.returncode` and `.output`, the tail of pip's output).

## HTTP API

```bash
nexuspy serve                          # prints a random token; listens on 127.0.0.1:8750
NEXUSPY_TOKEN=... nexuspy serve --port 9000
```

Every endpoint except `GET /health` needs `Authorization: Bearer <token>`.

| Method and path | Body | Result |
| --- | --- | --- |
| `GET /health` | | `{"status": "ok"}` |
| `GET /pythons` | | interpreters |
| `GET /envs` | | environments |
| `POST /envs` | `{"name", "python"?, "packages"?, "system_site_packages"?}` | `201` + environment |
| `GET /envs/<name>` | | environment |
| `DELETE /envs/<name>` | | `204` |
| `GET /envs/<name>/packages` | | installed packages |
| `GET /envs/<name>/freeze` | | pinned requirements |
| `POST /envs/<name>/install` | `{"packages": [...], "upgrade"?}` | installed + package list |
| `POST /envs/<name>/uninstall` | `{"packages": [...]}` | |
| `GET /envs/<name>/doctor` | | `{"ok", "checks"}` |

Errors are JSON: `400` bad input, `404` unknown environment, `409` already exists, `422` pip or venv failed
(with an `output` field), `429` rate limited (120 requests/minute).

**Security.** Installing a package runs code from that package, so anyone with the token can run code
as the server's user. nexuspy therefore refuses non-loopback addresses unless you pass `--allow-remote`;
only do that behind TLS and with a strong token. The API accepts package names, versions and local paths,
but never pip options (such as `--index-url`), and it has no endpoint that reads arbitrary server files.

## Limits

- It manages `venv`-style environments and the interpreters already installed. It does not download or
  build Python versions (install them with your OS, python.org, or similar, then `nexuspy pythons`).
- `lock` records `pip freeze` output (exact versions, no hashes, no dependency resolution beyond pip's).
- `nexuspy shell` and `activate` depend on your shell; `run` works everywhere.
