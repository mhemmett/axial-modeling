"""Check inherited compute limits in a real child process."""

import json
import subprocess
import sys
from pathlib import Path


def test_child_inherits_affinity_address_limit_and_exit_code() -> None:
    guard = Path(__file__).resolve().parents[1] / "scripts" / "resource_guard.py"
    child = (
        "import json, os, resource; "
        "print(json.dumps([len(os.sched_getaffinity(0)), "
        "resource.getrlimit(resource.RLIMIT_AS)[0], os.environ['OMP_NUM_THREADS']])); "
        "raise SystemExit(7)"
    )
    result = subprocess.run(
        [sys.executable, str(guard), sys.executable, "-c", child],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 7, result.stderr
    cpus, address_limit, threads = json.loads(result.stdout)
    assert 1 <= cpus <= 8
    assert 0 < address_limit <= 16 * 1024**3
    assert threads == "1"
