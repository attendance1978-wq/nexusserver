"""An HTTP API for nexuspy, built on NexusServer itself.

Everything requires a bearer token (except ``/health``). Package installs run
``pip`` on the server, so treat the token like a shell password and keep this on
loopback unless you front it with TLS.
"""

from __future__ import annotations

from .. import Application, BadRequest, Config
from .._version import __version__
from ..middleware import BearerTokenMiddleware, RateLimitMiddleware
from .core import EnvManager
from .errors import (
    CommandFailed, EnvExists, EnvNotFound, InterpreterNotFound, InvalidName, NexusPyError,
)
from .pythons import discover_pythons


def _body(request) -> dict:
    data = request.json()
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise BadRequest("Expected a JSON object body")
    return data


def _string_list(value, field: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
        raise BadRequest(f"'{field}' must be a list of strings")
    return value


def create_api(manager: EnvManager, token: str, config: Config | None = None) -> Application:
    """Build the nexuspy management API application."""
    app = Application(config or Config(host="127.0.0.1", port=8750))
    app.add_middleware(RateLimitMiddleware, limit=120, window=60, exempt_paths=("/health",))
    app.add_middleware(BearerTokenMiddleware, token=token, exempt_paths=("/health",), realm="nexuspy")

    @app.errorhandler(NexusPyError)
    def nexuspy_error(request, exc):
        if isinstance(exc, EnvNotFound):
            status = 404
        elif isinstance(exc, EnvExists):
            status = 409
        elif isinstance(exc, (InvalidName, InterpreterNotFound)):
            status = 400
        elif isinstance(exc, CommandFailed):
            status = 422
        else:
            status = 500
        payload = {"error": str(exc)}
        if isinstance(exc, CommandFailed) and exc.output:
            payload["output"] = exc.output
        return payload, status

    @app.get("/health")
    def health():
        return {"status": "ok", "nexuspy": __version__}

    @app.get("/pythons")
    def pythons():
        return {"pythons": [p.to_dict() for p in discover_pythons()]}

    @app.get("/envs")
    def list_envs():
        return {"envs": [e.to_dict() for e in manager.list()]}

    @app.post("/envs")
    def create_env(request):
        data = _body(request)
        name = data.get("name")
        if not isinstance(name, str):
            raise BadRequest("'name' is required")
        info = manager.create(
            name,
            python=data.get("python"),
            packages=_string_list(data.get("packages"), "packages"),
            system_site_packages=bool(data.get("system_site_packages", False)),
        )
        return info.to_dict(), 201

    @app.get("/envs/<str:name>")
    def get_env(name: str):
        return manager.info(name).to_dict()

    @app.delete("/envs/<str:name>")
    def delete_env(name: str):
        manager.remove(name)
        return None, 204

    @app.get("/envs/<str:name>/packages")
    def packages(name: str):
        return {"packages": manager.packages(name)}

    @app.get("/envs/<str:name>/freeze")
    def freeze(name: str):
        return {"requirements": manager.freeze(name)}

    @app.post("/envs/<str:name>/install")
    def install(request, name: str):
        data = _body(request)
        specs = _string_list(data.get("packages"), "packages")
        if not specs:
            raise BadRequest("'packages' must list at least one package")
        manager.install(name, specs, upgrade=bool(data.get("upgrade", False)))
        return {"installed": specs, "packages": manager.packages(name)}

    @app.post("/envs/<str:name>/uninstall")
    def uninstall(request, name: str):
        specs = _string_list(_body(request).get("packages"), "packages")
        manager.uninstall(name, specs)
        return {"uninstalled": specs}

    @app.get("/envs/<str:name>/doctor")
    def doctor(name: str):
        checks = manager.doctor(name)
        return {"ok": all(c["ok"] for c in checks), "checks": checks}

    return app
