"""nexuspy: environment manager, CLI and HTTP API. Uses real venvs; no network needed."""

import json
import os
import sys
import zipfile
from pathlib import Path

import pytest

from nexusserver import Headers
from nexusserver.http.request import Request
from nexusserver.middleware import BearerTokenMiddleware
from nexusserver.nexuspy import (
    CommandFailed, EnvExists, EnvManager, EnvNotFound, InterpreterNotFound, InvalidName,
    discover_pythons, find_python, validate_name, validate_specs,
)
from nexusserver.nexuspy.api import create_api
from nexusserver.nexuspy.cli import main as cli_main


def build_wheel(directory: Path, name="nxdemo", version="1.0") -> Path:
    """Hand-build a tiny pure-Python wheel so installs work offline."""
    wheel = directory / f"{name}-{version}-py3-none-any.whl"
    dist = f"{name}-{version}.dist-info"
    with zipfile.ZipFile(wheel, "w") as z:
        z.writestr(f"{name}.py", "VALUE = 42\n")
        z.writestr(f"{dist}/METADATA", f"Metadata-Version: 2.1\nName: {name}\nVersion: {version}\n")
        z.writestr(f"{dist}/WHEEL", "Wheel-Version: 1.0\nGenerator: test\nRoot-Is-Purelib: true\nTag: py3-none-any\n")
        z.writestr(f"{dist}/RECORD", "")
    return wheel


@pytest.fixture
def manager(tmp_path):
    return EnvManager(tmp_path / "home")


# ----- validation -----
@pytest.mark.parametrize("bad", ["", "../escape", "a/b", "-lead", "has space", ".hidden", "x" * 65, "a;b"])
def test_invalid_names_rejected(bad):
    with pytest.raises(InvalidName):
        validate_name(bad)


@pytest.mark.parametrize("good", ["a", "my-env", "proj_1.2", "A9"])
def test_valid_names(good):
    assert validate_name(good) == good


def test_specs_reject_pip_options_and_newlines():
    assert validate_specs(["requests>=2", "./pkg", "numpy==1.26.*"]) == ["requests>=2", "./pkg", "numpy==1.26.*"]
    for bad in ["--index-url=http://evil", "-e .", "a\nb", ""]:
        with pytest.raises(InvalidName):
            validate_specs([bad])
    assert validate_specs(["--pre"], allow_options=True) == ["--pre"]


# ----- interpreters -----
def test_discover_and_find_pythons():
    found = discover_pythons()
    assert found and all(p.version.startswith("3.") for p in found)
    current = find_python(None)
    assert current.version == ".".join(map(str, sys.version_info[:3]))
    prefix = f"{sys.version_info[0]}.{sys.version_info[1]}"
    assert find_python(prefix).version.startswith(prefix)
    assert find_python(f"python{prefix}").version.startswith(prefix)
    assert find_python(current.path).path == current.path
    with pytest.raises(InterpreterNotFound):
        find_python("2.7")
    with pytest.raises(InterpreterNotFound):
        find_python("/definitely/not/python")


# ----- lifecycle (no pip: fast) -----
def test_create_list_info_remove(manager):
    assert manager.list() == []
    info = manager.create("alpha", with_pip=False)
    assert info.healthy and info.python_version.startswith("3.")
    assert (Path(info.path) / "pyvenv.cfg").is_file() and manager.python_path("alpha").exists()
    assert json.loads((Path(info.path) / "nexuspy.json").read_text())["name"] == "alpha"
    assert [e.name for e in manager.list()] == ["alpha"]
    with pytest.raises(EnvExists):
        manager.create("alpha", with_pip=False)
    manager.remove("alpha")
    assert manager.list() == [] and not Path(info.path).exists()


def test_missing_env_errors(manager):
    for call in (lambda: manager.info("nope"), lambda: manager.remove("nope"),
                 lambda: manager.pip("nope", "list"), lambda: manager.run("nope", ["python"])):
        with pytest.raises(EnvNotFound):
            call()


def test_remove_refuses_foreign_and_symlinked_dirs(manager, tmp_path):
    manager.create("real", with_pip=False)
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "pyvenv.cfg").write_text("home = x\n")
    (outside / "keep.txt").write_text("precious")
    link = manager.envs_dir / "link"
    link.symlink_to(outside, target_is_directory=True)
    with pytest.raises(Exception):
        manager.remove("link")
    assert (outside / "keep.txt").exists()
    # a plain directory without pyvenv.cfg is "not an environment", so it is never deleted
    (manager.envs_dir / "notenv").mkdir()
    with pytest.raises(EnvNotFound):
        manager.remove("notenv")
    assert (manager.envs_dir / "notenv").is_dir()


def test_failed_create_leaves_nothing_behind(manager):
    with pytest.raises(InterpreterNotFound):
        manager.create("bad", python="2.7")
    assert not manager.env_path("bad").exists()


def test_create_with_packages_requires_pip(manager):
    with pytest.raises(InvalidName):
        manager.create("nopip", packages=["x"], with_pip=False)


def test_run_uses_the_environment(manager):
    manager.create("runner", with_pip=False)
    result = manager.run("runner", ["python", "-c", "import sys, os; print(sys.prefix); print(os.environ['VIRTUAL_ENV'])"],
                         capture=True)
    prefix, venv = result.stdout.split()
    assert Path(prefix) == manager.env_path("runner") == Path(venv)
    assert manager.run("runner", ["python", "-c", "raise SystemExit(7)"]).returncode == 7
    with pytest.raises(CommandFailed):
        manager.run("runner", ["definitely-not-a-command-xyz"])
    with pytest.raises(InvalidName):
        manager.run("runner", [])


def test_use_and_current(manager, tmp_path, monkeypatch):
    manager.create("proj", with_pip=False)
    project = tmp_path / "project" / "src"
    project.mkdir(parents=True)
    monkeypatch.delenv("VIRTUAL_ENV", raising=False)
    assert manager.current(project) is None
    manager.use("proj", tmp_path / "project")
    assert manager.current(project) == "proj"  # found by searching parent directories
    with pytest.raises(EnvNotFound):
        manager.use("ghost", tmp_path)


def test_activate_snippets(manager):
    manager.create("snip", with_pip=False)
    assert manager.activate_snippet("snip", "bash").startswith("source ")
    assert "Activate.ps1" in manager.activate_snippet("snip", "powershell")
    assert "activate.bat" in manager.activate_snippet("snip", "cmd")


def test_doctor(manager):
    manager.create("doc", with_pip=False)
    checks = {c["check"]: c["ok"] for c in manager.doctor("doc")}
    assert checks["python runs"] and checks["pyvenv.cfg present"] and not checks["pip works"]


# ----- pip operations (one real env with pip; offline via local wheel) -----
@pytest.fixture(scope="module")
def pip_env(tmp_path_factory):
    base = tmp_path_factory.mktemp("pipenv")
    manager = EnvManager(base / "home")
    wheel = build_wheel(base)
    manager.create("main", packages=[str(wheel)])
    return manager, wheel, base


def test_install_packages_freeze_lock(pip_env):
    manager, wheel, base = pip_env
    names = {p["name"].lower(): p["version"] for p in manager.packages("main")}
    assert names["nxdemo"] == "1.0"
    assert any(line.lower().startswith("nxdemo") for line in manager.freeze("main"))
    out = manager.run("main", ["python", "-c", "import nxdemo; print(nxdemo.VALUE)"], capture=True)
    assert out.stdout.strip() == "42"

    lock = manager.lock("main", base / "nexuspy.lock")
    text = lock.read_text()
    assert text.startswith("# nexuspy lock for main") and "nxdemo" in text
    assert all(c["ok"] for c in manager.doctor("main"))


def test_install_errors_are_reported(pip_env):
    manager, wheel, base = pip_env
    with pytest.raises(CommandFailed) as exc:
        manager.install("main", [str(base / "missing-1.0-py3-none-any.whl")])
    assert exc.value.returncode != 0 and exc.value.output
    with pytest.raises(InvalidName):
        manager.install("main", ["--index-url=http://evil.example"])
    with pytest.raises(InvalidName):
        manager.install("main")
    with pytest.raises(InvalidName):
        manager.install("main", requirements=base / "no-such-file.txt")


def test_uninstall_sync_and_clone(pip_env):
    manager, wheel, base = pip_env
    lock = manager.lock("main", base / "sync.lock")
    manager.uninstall("main", ["nxdemo"])
    assert "nxdemo" not in {p["name"].lower() for p in manager.packages("main")}
    manager.sync("main", lock)
    assert "nxdemo" in {p["name"].lower() for p in manager.packages("main")}

    cloned = manager.clone("main", "copy")
    assert cloned.python_version == manager.info("main").python_version
    assert "nxdemo" in {p["name"].lower() for p in manager.packages("copy")}
    manager.remove("copy")


# ----- CLI -----
def run_cli(tmp_path, *argv):
    return cli_main(["--home", str(tmp_path / "clihome"), *argv])


def test_cli_roundtrip(tmp_path, capsys):
    assert run_cli(tmp_path, "list") == 0
    assert "No environments yet" in capsys.readouterr().out
    assert run_cli(tmp_path, "create", "demo", "--no-pip") == 0
    assert "Created demo" in capsys.readouterr().out
    assert run_cli(tmp_path, "list", "--json") == 0
    assert json.loads(capsys.readouterr().out)[0]["name"] == "demo"
    assert run_cli(tmp_path, "path", "demo") == 0
    assert capsys.readouterr().out.strip().endswith(("python", "python.exe"))
    assert run_cli(tmp_path, "run", "demo", "--", "python", "-c", "raise SystemExit(3)") == 3
    assert run_cli(tmp_path, "pythons", "--json") == 0
    assert json.loads(capsys.readouterr().out)
    assert run_cli(tmp_path, "remove", "demo", "-y") == 0
    assert run_cli(tmp_path, "info", "demo") == 1
    assert "No environment named" in capsys.readouterr().err


def test_cli_errors_and_misc(tmp_path, capsys):
    assert run_cli(tmp_path, "create", "../evil") == 1
    assert "Invalid environment name" in capsys.readouterr().err
    assert run_cli(tmp_path, "run", "demo") == 1  # no such env
    assert cli_main([]) == 0 and "usage" in capsys.readouterr().out.lower()
    with pytest.raises(SystemExit) as exc:
        cli_main(["--version"])
    assert exc.value.code == 0
    assert "nexuspy" in capsys.readouterr().out


def test_cli_remove_needs_confirmation(tmp_path, monkeypatch, capsys):
    run_cli(tmp_path, "create", "keep", "--no-pip")
    monkeypatch.setattr("builtins.input", lambda *_: "n")
    assert run_cli(tmp_path, "remove", "keep") == 1
    assert run_cli(tmp_path, "info", "keep") == 0
    monkeypatch.setattr("builtins.input", lambda *_: "y")
    assert run_cli(tmp_path, "remove", "keep") == 0


def test_cli_serve_refuses_remote_without_flag(tmp_path, capsys):
    assert run_cli(tmp_path, "serve", "--host", "0.0.0.0") == 1
    assert "Refusing to listen" in capsys.readouterr().err


def test_cli_doctor_exit_code(tmp_path, capsys):
    run_cli(tmp_path, "create", "d", "--no-pip")
    capsys.readouterr()
    assert run_cli(tmp_path, "doctor", "d") == 1  # pip missing -> FAIL line
    assert "[FAIL] pip works" in capsys.readouterr().out


def test_nexuspy_module_entry_point():
    import subprocess
    root = Path(__file__).resolve().parent.parent
    out = subprocess.run([sys.executable, "-m", "nexusserver.nexuspy", "--version"], capture_output=True, text=True,
                         env={**os.environ, "PYTHONPATH": str(root / "src")}, timeout=30)
    assert out.stdout.startswith("nexuspy 26.")


# ----- bearer middleware -----
def test_bearer_middleware():
    from nexusserver import Application
    app = Application()
    app.add_middleware(BearerTokenMiddleware, token=["a" * 20, "b" * 20], exempt_paths=("/open",))
    app.get("/open")(lambda: "open")
    app.get("/secret")(lambda: "secret")

    def get(path, auth=None):
        headers = Headers([("Authorization", auth)]) if auth else Headers()
        return app.handle(Request("GET", path, headers=headers))

    assert get("/open").status_code == 200
    denied = get("/secret")
    assert denied.status_code == 401 and denied.headers["WWW-Authenticate"].startswith("Bearer")
    assert get("/secret", "Bearer wrong").status_code == 401
    assert get("/secret", "Basic " + "a" * 20).status_code == 401
    assert get("/secret", "Bearer " + "a" * 20).status_code == 200
    assert get("/secret", "Bearer " + "b" * 20).status_code == 200  # rotated token also valid
    with pytest.raises(ValueError):
        BearerTokenMiddleware(lambda r: None, token="short")


# ----- HTTP API -----
TOKEN = "t" * 24


@pytest.fixture
def api(tmp_path):
    manager = EnvManager(tmp_path / "apihome")
    app = create_api(manager, TOKEN)

    def call(method, path, body=None, token=TOKEN):
        headers = Headers([("Authorization", f"Bearer {token}")] if token else [])
        raw = json.dumps(body).encode() if body is not None else b""
        if raw:
            headers["Content-Length"] = str(len(raw))
            headers["Content-Type"] = "application/json"
        return app.handle(Request(method, path, headers=headers, body=raw))

    return call, manager


def test_api_requires_token(api):
    call, _ = api
    assert call("GET", "/envs", token=None).status_code == 401
    assert call("GET", "/envs", token="wrong-token-wrong-token").status_code == 401
    health = call("GET", "/health", token=None)
    assert health.status_code == 200 and b"nexuspy" in health.body


def test_api_environment_lifecycle(api):
    call, manager = api
    assert json.loads(call("GET", "/envs").body) == {"envs": []}
    assert json.loads(call("GET", "/pythons").body)["pythons"]

    created = call("POST", "/envs", {"name": "web"})
    assert created.status_code == 201 and json.loads(created.body)["name"] == "web"
    assert call("POST", "/envs", {"name": "web"}).status_code == 409
    assert call("GET", "/envs/web").status_code == 200
    assert call("GET", "/envs/ghost").status_code == 404
    assert [e["name"] for e in json.loads(call("GET", "/envs").body)["envs"]] == ["web"]

    doctor = json.loads(call("GET", "/envs/web/doctor").body)
    assert doctor["ok"] is True
    assert call("DELETE", "/envs/web").status_code == 204
    assert call("GET", "/envs/web").status_code == 404


def test_api_install_and_packages(api, tmp_path):
    call, manager = api
    wheel = build_wheel(tmp_path)
    call("POST", "/envs", {"name": "svc"})
    installed = call("POST", "/envs/svc/install", {"packages": [str(wheel)]})
    assert installed.status_code == 200
    names = {p["name"].lower() for p in json.loads(call("GET", "/envs/svc/packages").body)["packages"]}
    assert "nxdemo" in names
    assert any("nxdemo" in line.lower() for line in json.loads(call("GET", "/envs/svc/freeze").body)["requirements"])
    assert call("POST", "/envs/svc/uninstall", {"packages": ["nxdemo"]}).status_code == 200


def test_api_input_validation(api):
    call, _ = api
    assert call("POST", "/envs", {}).status_code == 400
    assert call("POST", "/envs", {"name": "../x"}).status_code == 400
    assert call("POST", "/envs", {"name": "ok", "python": "2.7"}).status_code == 400
    assert call("POST", "/envs", {"name": "ok", "packages": "notalist"}).status_code == 400
    call("POST", "/envs", {"name": "v"})
    assert call("POST", "/envs/v/install", {"packages": ["--index-url=http://evil.example"]}).status_code == 400
    assert call("POST", "/envs/v/install", {"packages": []}).status_code == 400
    bad_pkg = call("POST", "/envs/v/install", {"packages": ["/no/such/wheel-1.0-py3-none-any.whl"]})
    assert bad_pkg.status_code == 422 and b"output" in bad_pkg.body
