import re
import subprocess
import sys
from pathlib import Path

import nexusserver
from nexusserver import _version

ROOT = Path(__file__).resolve().parent.parent


def test_version_is_consistent():
    assert nexusserver.__version__ == _version.__version__
    assert ".".join(map(str, nexusserver.__version_info__)) == nexusserver.__version__
    assert re.fullmatch(r"\d{2}\.\d+\.\d+", nexusserver.__version__)


def test_release_channel():
    # 26.3.x is the LTS line; any other minor is a regular "stable" release.
    on_lts_line = f"{nexusserver.__version_info__[0]}.{nexusserver.__version_info__[1]}" == _version.LATEST_LTS
    assert nexusserver.LTS is on_lts_line
    assert nexusserver.RELEASE_CHANNEL == ("lts" if on_lts_line else "stable")


def test_changelog_and_policy_mention_current_version():
    assert f"## {nexusserver.__version__}" in (ROOT / "CHANGELOG.md").read_text()
    policy = (ROOT / "docs" / "release-policy.md").read_text()
    assert _version.LATEST_LTS in policy and "26.4" in policy


def test_cli_version_flag():
    out = subprocess.run([sys.executable, "-m", "nexusserver", "--version"], capture_output=True, text=True,
                         cwd=ROOT, env={"PYTHONPATH": str(ROOT / "src"), "PATH": ""}, timeout=30)
    suffix = " (LTS)" if nexusserver.LTS else ""
    assert out.stdout.strip() == f"nexusserver {nexusserver.__version__}{suffix}"
