"""The nexuspy environment manager."""

from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from collections.abc import Iterable, Sequence
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from .._version import __version__
from .errors import CommandFailed, EnvExists, EnvNotFound, InvalidName, NexusPyError
from .pythons import PythonInfo, find_python, probe

NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
META_FILE = "nexuspy.json"
PROJECT_FILE = ".nexuspy-env"
_IS_WINDOWS = os.name == "nt"


@dataclass
class EnvInfo:
    name: str
    path: str
    python_version: str
    base_python: str
    created: str
    healthy: bool = True

    def to_dict(self) -> dict:
        return asdict(self)


def _tail(text: str, limit: int = 2000) -> str:
    return text if len(text) <= limit else "..." + text[-limit:]


def validate_name(name: str) -> str:
    if not isinstance(name, str) or not NAME_RE.match(name):
        raise InvalidName(
            f"Invalid environment name {name!r}: use 1-64 letters, digits, '.', '_' or '-', starting with a letter or digit"
        )
    return name


def validate_specs(specs: Iterable[str], allow_options: bool = False) -> list[str]:
    """Reject anything that pip would treat as an option (``--index-url ...``) unless allowed."""
    out = []
    for spec in specs:
        if not isinstance(spec, str) or not spec.strip():
            raise InvalidName("Package specs must be non-empty strings")
        if "\n" in spec or "\r" in spec or "\x00" in spec:
            raise InvalidName(f"Invalid package spec {spec!r}")
        if spec.startswith("-") and not allow_options:
            raise InvalidName(f"Package spec {spec!r} looks like a pip option; options are not allowed here")
        out.append(spec)
    return out


class EnvManager:
    """Create and manage virtual environments under one home directory.

    Layout::

        <home>/envs/<name>/        a normal venv, plus nexuspy.json metadata
    """

    def __init__(self, home: str | os.PathLike | None = None) -> None:
        chosen = home or os.environ.get("NEXUSPY_HOME") or (Path.home() / ".nexuspy")
        self.home = Path(chosen).expanduser().resolve()
        self.envs_dir = self.home / "envs"

    # ----- paths -----
    def env_path(self, name: str) -> Path:
        return self.envs_dir / validate_name(name)

    def bin_dir(self, name: str) -> Path:
        return self.env_path(name) / ("Scripts" if _IS_WINDOWS else "bin")

    def python_path(self, name: str) -> Path:
        return self.bin_dir(name) / ("python.exe" if _IS_WINDOWS else "python")

    def exists(self, name: str) -> bool:
        return (self.env_path(name) / "pyvenv.cfg").is_file()

    def _require(self, name: str) -> Path:
        if not self.exists(name):
            raise EnvNotFound(f"No environment named {name!r}")
        return self.env_path(name)

    # ----- creating / inspecting / removing -----
    def create(
        self,
        name: str,
        python: str | None = None,
        packages: Sequence[str] = (),
        requirements: str | os.PathLike | None = None,
        system_site_packages: bool = False,
        with_pip: bool = True,
    ) -> EnvInfo:
        """Create environment ``name`` with the interpreter matching ``python`` (default: the running one)."""
        path = self.env_path(name)
        if path.exists():
            raise EnvExists(f"Environment {name!r} already exists")
        specs = validate_specs(packages)
        interpreter = find_python(python)

        self.envs_dir.mkdir(parents=True, exist_ok=True)
        cmd = [interpreter.path, "-m", "venv", str(path)]
        if system_site_packages:
            cmd.append("--system-site-packages")
        if not with_pip:
            cmd.append("--without-pip")
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            shutil.rmtree(path, ignore_errors=True)
            raise CommandFailed(
                f"Could not create environment {name!r} with {interpreter.path}",
                result.returncode, _tail(result.stdout + result.stderr),
            )

        meta = {
            "name": name,
            "python_version": interpreter.version,
            "base_python": interpreter.path,
            "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "nexuspy": __version__,
        }
        (path / META_FILE).write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")

        if specs or requirements:
            if not with_pip:
                raise InvalidName("Cannot install packages into an environment created with with_pip=False")
            self.install(name, specs, requirements=requirements)
        return self.info(name)

    def info(self, name: str) -> EnvInfo:
        path = self._require(name)
        meta: dict = {}
        meta_file = path / META_FILE
        if meta_file.is_file():
            try:
                meta = json.loads(meta_file.read_text(encoding="utf-8"))
            except ValueError:
                meta = {}
        python = self.python_path(name)
        probed = probe(python) if python.exists() else None
        return EnvInfo(
            name=name,
            path=str(path),
            python_version=probed.version if probed else meta.get("python_version", "unknown"),
            base_python=meta.get("base_python", ""),
            created=meta.get("created", ""),
            healthy=probed is not None,
        )

    def list(self) -> list[EnvInfo]:
        if not self.envs_dir.is_dir():
            return []
        names = sorted(p.name for p in self.envs_dir.iterdir() if (p / "pyvenv.cfg").is_file() and NAME_RE.match(p.name))
        return [self.info(n) for n in names]

    def remove(self, name: str) -> None:
        """Delete an environment. Refuses anything that is not a venv directly inside ``envs/``."""
        path = self._require(name)
        if path.is_symlink() or path.resolve().parent != self.envs_dir.resolve():
            raise NexusPyError(f"Refusing to delete {path}: it is not a regular directory inside {self.envs_dir}")
        shutil.rmtree(path)

    # ----- pip -----
    def _env_vars(self, name: str) -> dict[str, str]:
        env = dict(os.environ)
        env["VIRTUAL_ENV"] = str(self.env_path(name))
        env["PATH"] = str(self.bin_dir(name)) + os.pathsep + env.get("PATH", "")
        env["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
        env.pop("PYTHONHOME", None)
        return env

    def pip(self, name: str, *args: str, check: bool = True) -> subprocess.CompletedProcess:
        self._require(name)
        result = subprocess.run(
            [str(self.python_path(name)), "-m", "pip", *args],
            capture_output=True, text=True, env=self._env_vars(name),
        )
        if check and result.returncode != 0:
            raise CommandFailed(
                f"pip {' '.join(args[:1])} failed in {name!r}",
                result.returncode, _tail(result.stdout + result.stderr),
            )
        return result

    def install(
        self,
        name: str,
        packages: Sequence[str] = (),
        requirements: str | os.PathLike | None = None,
        upgrade: bool = False,
        allow_options: bool = False,
    ) -> str:
        """Install ``packages`` and/or a requirements file. Returns pip's output."""
        specs = validate_specs(packages, allow_options=allow_options)
        args = ["install"]
        if upgrade:
            args.append("--upgrade")
        if requirements:
            req = Path(requirements)
            if not req.is_file():
                raise InvalidName(f"Requirements file not found: {req}")
            args += ["-r", str(req)]
        if not specs and not requirements:
            raise InvalidName("Nothing to install: give packages or a requirements file")
        return self.pip(name, *args, *specs).stdout

    def uninstall(self, name: str, packages: Sequence[str]) -> str:
        specs = validate_specs(packages)
        if not specs:
            raise InvalidName("Nothing to uninstall")
        return self.pip(name, "uninstall", "-y", *specs).stdout

    def packages(self, name: str) -> list[dict[str, str]]:
        out = self.pip(name, "list", "--format=json").stdout
        try:
            return json.loads(out)
        except ValueError:
            raise CommandFailed("Could not read pip's package list", 1, _tail(out)) from None

    def freeze(self, name: str) -> list[str]:
        return [line for line in self.pip(name, "freeze").stdout.splitlines() if line.strip()]

    def lock(self, name: str, path: str | os.PathLike | None = None) -> Path:
        """Write ``pip freeze`` output to ``path`` (default ``./nexuspy.lock``)."""
        target = Path(path or "nexuspy.lock")
        header = f"# nexuspy lock for {name} (python {self.info(name).python_version}), nexuspy {__version__}\n"
        target.write_text(header + "\n".join(self.freeze(name)) + "\n", encoding="utf-8")
        return target

    def sync(self, name: str, lockfile: str | os.PathLike = "nexuspy.lock") -> str:
        """Install exactly what a lock file lists."""
        return self.install(name, requirements=lockfile)

    def clone(self, source: str, target: str) -> EnvInfo:
        """Create ``target`` with the same interpreter and packages as ``source``."""
        info = self.info(source)
        frozen = self.freeze(source)
        python = info.base_python if info.base_python and Path(info.base_python).exists() else None
        self.create(target, python=python)
        if frozen:
            lock = self.env_path(target) / "clone-requirements.txt"
            lock.write_text("\n".join(frozen) + "\n", encoding="utf-8")
            try:
                self.install(target, requirements=lock)
            finally:
                lock.unlink(missing_ok=True)
        return self.info(target)

    # ----- running things -----
    def run(
        self,
        name: str,
        command: Sequence[str],
        cwd: str | os.PathLike | None = None,
        capture: bool = False,
    ) -> subprocess.CompletedProcess:
        """Run ``command`` (a list, never a shell string) with the environment active."""
        self._require(name)
        if not command:
            raise InvalidName("No command given")
        env = self._env_vars(name)
        exe = shutil.which(command[0], path=env["PATH"]) or command[0]
        try:
            return subprocess.run([exe, *command[1:]], env=env, cwd=cwd, capture_output=capture, text=capture)
        except FileNotFoundError:
            raise CommandFailed(f"Command not found: {command[0]}", 127) from None

    def shell(self, name: str) -> int:
        """Start an interactive subshell with the environment active."""
        self._require(name)
        shell = os.environ.get("COMSPEC", "cmd.exe") if _IS_WINDOWS else os.environ.get("SHELL", "/bin/sh")
        return subprocess.call([shell], env=self._env_vars(name))

    def activate_snippet(self, name: str, shell: str | None = None) -> str:
        """Text to paste or ``eval`` into a shell to activate the environment there."""
        self._require(name)
        base = self.env_path(name)
        shell = (shell or ("powershell" if _IS_WINDOWS else "bash")).lower()
        if shell in ("powershell", "pwsh"):
            return f'& "{base / "Scripts" / "Activate.ps1"}"'
        if shell == "cmd":
            return f'"{base / "Scripts" / "activate.bat"}"'
        if shell == "fish":
            return f"source {shlex.quote(str(base / 'bin' / 'activate.fish'))}"
        return f"source {shlex.quote(str(base / 'bin' / 'activate'))}"

    # ----- project binding -----
    def use(self, name: str, directory: str | os.PathLike = ".") -> Path:
        """Bind a project directory to an environment (writes ``.nexuspy-env``)."""
        self._require(name)
        target = Path(directory) / PROJECT_FILE
        target.write_text(name + "\n", encoding="utf-8")
        return target

    def current(self, directory: str | os.PathLike = ".") -> str | None:
        """The environment bound to ``directory`` (searching parents), else the active ``VIRTUAL_ENV`` name."""
        start = Path(directory).resolve()
        for folder in [start, *start.parents]:
            marker = folder / PROJECT_FILE
            if marker.is_file():
                name = marker.read_text(encoding="utf-8").strip()
                if NAME_RE.match(name):
                    return name
        active = os.environ.get("VIRTUAL_ENV")
        if active and Path(active).resolve().parent == self.envs_dir.resolve():
            return Path(active).name
        return None

    # ----- diagnostics -----
    def doctor(self, name: str) -> list[dict]:
        """Run health checks; each result is ``{"check", "ok", "detail"}``."""
        checks: list[dict] = []

        def add(check: str, ok: bool, detail: str = "") -> None:
            checks.append({"check": check, "ok": bool(ok), "detail": detail})

        path = self.env_path(name)
        add("directory exists", path.is_dir(), str(path))
        add("pyvenv.cfg present", (path / "pyvenv.cfg").is_file())
        python = self.python_path(name)
        add("python executable present", python.exists(), str(python))
        probed = probe(python) if python.exists() else None
        add("python runs", probed is not None, probed.version if probed else "failed to run")
        if probed:
            pip = subprocess.run([str(python), "-m", "pip", "--version"], capture_output=True, text=True,
                                 env=self._env_vars(name))
            add("pip works", pip.returncode == 0, pip.stdout.strip() or "pip is not installed")
        meta = path / META_FILE
        add("nexuspy metadata", meta.is_file(), "" if meta.is_file() else "created outside nexuspy")
        base = None
        if meta.is_file():
            try:
                base = json.loads(meta.read_text(encoding="utf-8")).get("base_python")
            except ValueError:
                pass
        if base:
            add("base interpreter still exists", Path(base).exists(), base)
        return checks
