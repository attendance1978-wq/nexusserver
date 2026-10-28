"""The ``nexuspy`` command line."""

from __future__ import annotations

import argparse
import json
import os
import secrets
import sys
from pathlib import Path

from .._version import LTS, __version__
from .core import EnvManager
from .errors import CommandFailed, NexusPyError
from .pythons import discover_pythons


def _emit(data) -> None:
    print(json.dumps(data, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="nexuspy", description="Python environment management (part of NexusServer).")
    parser.add_argument("--version", action="version", version=f"nexuspy {__version__}" + (" (LTS)" if LTS else ""))
    parser.add_argument("--home", help="nexuspy home directory (default: $NEXUSPY_HOME or ~/.nexuspy)")
    sub = parser.add_subparsers(dest="command", metavar="<command>")

    def add(name, help, **kw):
        return sub.add_parser(name, help=help, description=help, **kw)

    add("pythons", "List Python interpreters found on this machine").add_argument("--json", action="store_true")

    p = add("create", "Create an environment")
    p.add_argument("name")
    p.add_argument("packages", nargs="*", help="packages to install right away")
    p.add_argument("--python", help="interpreter: version like 3.11, or a path (default: the running Python)")
    p.add_argument("-r", "--requirements", help="requirements file to install")
    p.add_argument("--system-site-packages", action="store_true")
    p.add_argument("--no-pip", action="store_true", help="create without pip")

    add("list", "List environments").add_argument("--json", action="store_true")
    add("info", "Show one environment").add_argument("name")
    p = add("remove", "Delete an environment")
    p.add_argument("name")
    p.add_argument("-y", "--yes", action="store_true", help="do not ask for confirmation")

    p = add("install", "Install packages into an environment")
    p.add_argument("name")
    p.add_argument("packages", nargs="*")
    p.add_argument("-r", "--requirements")
    p.add_argument("-U", "--upgrade", action="store_true")
    p = add("uninstall", "Remove packages from an environment")
    p.add_argument("name")
    p.add_argument("packages", nargs="+")
    p = add("packages", "List installed packages")
    p.add_argument("name")
    p.add_argument("--json", action="store_true")
    add("freeze", "Print pinned requirements").add_argument("name")
    p = add("lock", "Write pinned requirements to a lock file")
    p.add_argument("name")
    p.add_argument("-o", "--output", default="nexuspy.lock")
    p = add("sync", "Install exactly what a lock file lists")
    p.add_argument("name")
    p.add_argument("lockfile", nargs="?", default="nexuspy.lock")
    p = add("clone", "Copy an environment")
    p.add_argument("source")
    p.add_argument("target")

    p = add("run", "Run a command inside an environment (use -- before the command)")
    p.add_argument("name")
    p.add_argument("cmd", nargs=argparse.REMAINDER)
    add("shell", "Open a subshell with the environment active").add_argument("name")
    p = add("activate", "Print the command that activates an environment in your shell")
    p.add_argument("name")
    p.add_argument("--shell", choices=["bash", "zsh", "fish", "powershell", "pwsh", "cmd"])
    add("path", "Print the path of an environment's Python").add_argument("name")
    p = add("use", "Bind the current directory to an environment")
    p.add_argument("name")
    add("current", "Show the environment bound to this directory")
    add("doctor", "Check an environment's health").add_argument("name")

    p = add("serve", "Run the management HTTP API (bearer-token protected)")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8750)
    p.add_argument("--token", help="API token (default: $NEXUSPY_TOKEN, else a random one is printed)")
    p.add_argument("--allow-remote", action="store_true", help="allow binding to a non-loopback address (use TLS in front!)")
    return parser


def _confirm(prompt: str) -> bool:
    try:
        return input(prompt + " [y/N] ").strip().lower() in ("y", "yes")
    except EOFError:
        return False


def run(args: argparse.Namespace, manager: EnvManager) -> int:
    cmd = args.command

    if cmd == "pythons":
        pythons = discover_pythons()
        if args.json:
            _emit([p.to_dict() for p in pythons])
        else:
            for p in pythons:
                print(f"{p.version:<10} {p.path}")
        return 0

    if cmd == "create":
        info = manager.create(
            args.name, python=args.python, packages=args.packages, requirements=args.requirements,
            system_site_packages=args.system_site_packages, with_pip=not args.no_pip,
        )
        print(f"Created {info.name} (Python {info.python_version}) at {info.path}")
        print(f"Activate with:  {manager.activate_snippet(info.name)}")
        return 0

    if cmd == "list":
        envs = manager.list()
        if args.json:
            _emit([e.to_dict() for e in envs])
        elif not envs:
            print("No environments yet. Create one with: nexuspy create <name>")
        else:
            for e in envs:
                flag = "" if e.healthy else "  [broken]"
                print(f"{e.name:<24} Python {e.python_version:<10} {e.path}{flag}")
        return 0

    if cmd == "info":
        _emit(manager.info(args.name).to_dict())
        return 0

    if cmd == "remove":
        manager.info(args.name)  # fail early if missing
        if not args.yes and not _confirm(f"Delete environment {args.name!r} and everything in it?"):
            print("Aborted.")
            return 1
        manager.remove(args.name)
        print(f"Removed {args.name}")
        return 0

    if cmd == "install":
        manager.install(args.name, args.packages, requirements=args.requirements, upgrade=args.upgrade)
        print(f"Installed into {args.name}")
        return 0

    if cmd == "uninstall":
        manager.uninstall(args.name, args.packages)
        print(f"Uninstalled from {args.name}")
        return 0

    if cmd == "packages":
        packages = manager.packages(args.name)
        if args.json:
            _emit(packages)
        else:
            for pkg in packages:
                print(f"{pkg['name']:<32} {pkg['version']}")
        return 0

    if cmd == "freeze":
        print("\n".join(manager.freeze(args.name)))
        return 0

    if cmd == "lock":
        print(f"Wrote {manager.lock(args.name, args.output)}")
        return 0

    if cmd == "sync":
        manager.sync(args.name, args.lockfile)
        print(f"Synced {args.name} from {args.lockfile}")
        return 0

    if cmd == "clone":
        info = manager.clone(args.source, args.target)
        print(f"Cloned {args.source} -> {info.name} at {info.path}")
        return 0

    if cmd == "run":
        command = args.cmd[1:] if args.cmd[:1] == ["--"] else args.cmd
        if not command:
            raise NexusPyError("Usage: nexuspy run <name> -- <command> [args...]")
        return manager.run(args.name, command).returncode

    if cmd == "shell":
        return manager.shell(args.name)

    if cmd == "activate":
        print(manager.activate_snippet(args.name, args.shell))
        return 0

    if cmd == "path":
        manager.info(args.name)
        print(manager.python_path(args.name))
        return 0

    if cmd == "use":
        print(f"Bound {Path.cwd()} to {args.name} ({manager.use(args.name)})")
        return 0

    if cmd == "current":
        name = manager.current()
        if name is None:
            print("No environment bound here (use 'nexuspy use <name>').")
            return 1
        print(name)
        return 0

    if cmd == "doctor":
        checks = manager.doctor(args.name)
        for c in checks:
            print(f"[{'ok' if c['ok'] else 'FAIL'}] {c['check']}" + (f"  {c['detail']}" if c["detail"] else ""))
        return 0 if all(c["ok"] for c in checks) else 1

    if cmd == "serve":
        from .api import create_api

        loopback = args.host in ("127.0.0.1", "localhost", "::1")
        if not loopback and not args.allow_remote:
            raise NexusPyError(
                f"Refusing to listen on {args.host}: the API can install packages. "
                "Use --allow-remote only behind TLS and with a strong token."
            )
        token = args.token or os.environ.get("NEXUSPY_TOKEN")
        generated = token is None
        token = token or secrets.token_urlsafe(24)
        api = create_api(manager, token)
        api.config.host, api.config.port = args.host, args.port
        if generated:
            print(f"nexuspy API token: {token}", flush=True)
        print(f"nexuspy API on http://{args.host}:{args.port}  (Authorization: Bearer <token>)", flush=True)
        api.run()
        return 0

    return 2


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return 0
    manager = EnvManager(args.home)
    try:
        return run(args, manager)
    except CommandFailed as exc:
        print(f"nexuspy: error: {exc}", file=sys.stderr)
        if exc.output:
            print(exc.output, file=sys.stderr)
        return exc.returncode or 1
    except NexusPyError as exc:
        print(f"nexuspy: error: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())
