"""End-to-end: `nexusserver --reload` restarts on edits and cleans up on SIGTERM."""

import http.client
import os
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

SRC = str(Path(__file__).resolve().parent.parent / "src")


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def fetch(port, timeout=10):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            conn = http.client.HTTPConnection("127.0.0.1", port, timeout=2)
            conn.request("GET", "/")
            return conn.getresponse().read().decode()
        except OSError:
            time.sleep(0.2)
    raise AssertionError("server did not answer")


def wait_for(port, expected, timeout=15):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            if fetch(port, timeout=1) == expected:
                return
        except AssertionError:
            pass
        time.sleep(0.2)
    raise AssertionError(f"never saw {expected!r}")


@pytest.mark.skipif(sys.platform == "win32", reason="uses POSIX signals")
def test_reload_restarts_and_terminates_cleanly(tmp_path):
    app_file = tmp_path / "reload_demo.py"
    app_file.write_text(
        "from nexusserver import Application\napp = Application()\n"
        "@app.get('/')\ndef index():\n    return 'one'\n"
    )
    port = free_port()
    env = {**os.environ, "PYTHONPATH": SRC}
    proc = subprocess.Popen(
        [sys.executable, "-m", "nexusserver", "reload_demo:app", "--port", str(port), "--reload"],
        cwd=tmp_path, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    try:
        wait_for(port, "one")
        app_file.write_text(app_file.read_text().replace("'one'", "'two'"))
        os.utime(app_file, (time.time() + 5, time.time() + 5))
        wait_for(port, "two")
    finally:
        proc.send_signal(signal.SIGTERM)
        proc.wait(timeout=15)
    time.sleep(0.5)
    with pytest.raises(OSError):  # child was shut down too: port is closed
        socket.create_connection(("127.0.0.1", port), timeout=1).close()
