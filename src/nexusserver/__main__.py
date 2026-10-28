"""Entry point for `python -m nexusserver` and the `nexusserver` command."""

import argparse
import importlib
import os
import sys

from ._version import LTS, __version__
from .application import Application


def main() -> None:
    parser = argparse.ArgumentParser(prog="nexusserver", description="Run a NexusServer application.")
    parser.add_argument("app", nargs="?", help="Application target, e.g. 'mypackage.app:app'")
    parser.add_argument("--host", default=None, help="Bind host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=None, help="Bind port (default: 8000)")
    parser.add_argument("--workers", type=int, default=None, help="Thread pool size (default: 16)")
    parser.add_argument("--debug", action="store_true", help="Debug logging and error details in 500 responses")
    parser.add_argument("--reload", action="store_true", help="Restart the server when .py files change (development only)")
    parser.add_argument("--version", action="version", version=f"nexusserver {__version__}" + (" (LTS)" if LTS else ""))
    args = parser.parse_args()
    if not args.app:
        parser.error("the following arguments are required: app")

    if args.reload:
        from .reload import run_with_reloader

        argv = [a for a in sys.argv[1:] if a != "--reload"]
        run_with_reloader(argv)
        return

    # The `nexusserver` console script does not put the working directory on sys.path.
    if os.getcwd() not in sys.path:
        sys.path.insert(0, os.getcwd())

    module_path, _, attr = args.app.partition(":")
    attr = attr or "app"
    try:
        module = importlib.import_module(module_path)
    except ImportError as exc:
        raise SystemExit(f"Could not import {module_path!r}: {exc}")
    try:
        app = getattr(module, attr)
    except AttributeError:
        raise SystemExit(f"Module {module_path!r} has no attribute {attr!r}")
    if not isinstance(app, Application):
        raise SystemExit(f"{args.app!r} does not resolve to an Application instance")

    if args.host:
        app.config.host = args.host
    if args.port is not None:
        app.config.port = args.port
    if args.workers:
        app.config.max_workers = args.workers
    app.config.debug = app.config.debug or args.debug

    app.run()


if __name__ == "__main__":
    main()
