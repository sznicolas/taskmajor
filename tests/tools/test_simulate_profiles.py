from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_simulate_profiles_cli_runs():
    repo_root = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        [sys.executable, "tools/simulate_profiles.py", "--profiles", "standard"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=True,
    )

    assert "Chain:" in result.stdout
    assert "taskmajor://agenda/today" in result.stdout
    assert "Resources:" in result.stdout
