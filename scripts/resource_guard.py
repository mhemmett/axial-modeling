"""Run a command on at most 16 CPUs and stop at 60% memory use."""

from __future__ import annotations

import json
import os
import resource
import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAX_CPUS = 16
MAX_MEMORY_FRACTION = 0.60
ADDRESS_SPACE_BYTES = 16 * 1024**3


def memory_state() -> tuple[int, int]:
    """Return total and available host memory in bytes from Linux procfs."""
    values = {}
    for line in Path("/proc/meminfo").read_text().splitlines():
        name, value, *_ = line.split()
        if name in {"MemTotal:", "MemAvailable:"}:
            values[name] = int(value) * 1024
    return values["MemTotal:"], values["MemAvailable:"]


def process_tree(root_pid: int) -> dict[int, int]:
    """Return descendant process IDs and resident memory in bytes."""
    processes = {}
    page_bytes = os.sysconf("SC_PAGE_SIZE")
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        try:
            fields = (entry / "stat").read_text().rsplit(")", 1)[1].split()
            processes[int(entry.name)] = (int(fields[1]), int(fields[21]) * page_bytes)
        except (OSError, ValueError, IndexError):
            continue  # Processes may exit while procfs is being read.
    descendants = {root_pid: processes.get(root_pid, (0, 0))[1]}
    while True:
        added = {
            pid: rss for pid, (parent, rss) in processes.items()
            if parent in descendants and pid not in descendants
        }
        if not added:
            return descendants
        descendants.update(added)


def pin_mpi_ranks(
    descendants: dict[int, int], cpus: list[int], assigned: dict[int, int]
) -> bool:
    """Bind one PyLith MPI rank to each allowed CPU when all ranks exist.

    Parameters
    ----------
    descendants : dict[int, int]
        Process IDs and resident bytes below this resource guard.
    cpus : list[int]
        Allowed CPU IDs for the bounded run.
    assigned : dict[int, int]
        Existing process-to-CPU assignments, updated in place.

    Returns
    -------
    bool
        Whether a complete new MPI group was bound.
    """
    workers = []
    for pid in descendants:
        try:
            if Path(f"/proc/{pid}/comm").read_text().strip() == "mpinemesis":
                workers.append(pid)
        except OSError:
            continue
    if len(workers) != len(cpus):
        return False
    workers.sort()
    try:
        if all(
            assigned.get(pid) == cpu and os.sched_getaffinity(pid) == {cpu}
            for pid, cpu in zip(workers, cpus, strict=True)
        ):
            return False
    except OSError:
        return False
    for pid, cpu in zip(workers, cpus, strict=True):
        try:
            tasks = Path(f"/proc/{pid}/task")
            thread_ids = sorted(int(entry.name) for entry in tasks.iterdir())
            for thread_id in thread_ids:
                os.sched_setaffinity(thread_id, {cpu})
        except OSError:
            return False
    assigned.clear()
    assigned.update(zip(workers, cpus, strict=True))
    return True


def stop_command(command: subprocess.Popen, descendants: dict[int, int]) -> None:
    """Terminate the command group and descendants that created new sessions."""
    targets = set(descendants) - {os.getpid()}
    for sig in (signal.SIGTERM, signal.SIGKILL):
        try:
            os.killpg(command.pid, sig)
        except ProcessLookupError:
            pass
        for pid in targets:
            try:
                os.kill(pid, sig)
            except ProcessLookupError:
                pass
        if sig == signal.SIGTERM:
            time.sleep(0.2)
    command.wait()


def main(argv: list[str] | None = None) -> int:
    """Launch a bounded command and record measured memory and exit status."""
    arguments = sys.argv[1:] if argv is None else argv
    if not arguments:
        raise SystemExit("usage: resource_guard.py COMMAND [ARG ...]")
    cpus = sorted(os.sched_getaffinity(0))[:MAX_CPUS]
    os.sched_setaffinity(0, cpus)
    _, hard_limit = resource.getrlimit(resource.RLIMIT_AS)
    address_limit = ADDRESS_SPACE_BYTES
    if hard_limit != resource.RLIM_INFINITY:
        address_limit = min(address_limit, hard_limit)
    resource.setrlimit(resource.RLIMIT_AS, (address_limit, address_limit))
    for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
                 "NUMEXPR_NUM_THREADS", "RAYON_NUM_THREADS"):
        os.environ[name] = "1"
    os.environ["PYLITH_NODES"] = str(len(cpus))
    total, available = memory_state()
    if total - available >= MAX_MEMORY_FRACTION * total:
        print("Stopped: host memory use has reached 60%.", file=sys.stderr)
        return 125
    start = time.monotonic()
    peak_tree_rss = 0
    peak_host_fraction = (total - available) / total
    mpi_binding_events = 0
    assigned_mpi_ranks: dict[int, int] = {}
    reason = "completed"
    command = subprocess.Popen(arguments, start_new_session=True)
    def interrupted(signum, _frame):
        raise SystemExit(128 + signum)

    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    try:
        while True:
            descendants = process_tree(os.getpid())
            mpi_binding_events += pin_mpi_ranks(descendants, cpus, assigned_mpi_ranks)
            tree_rss = sum(descendants.values())
            total, available = memory_state()
            peak_tree_rss = max(peak_tree_rss, tree_rss)
            peak_host_fraction = max(peak_host_fraction, (total - available) / total)
            if max(tree_rss, total - available) >= MAX_MEMORY_FRACTION * total:
                reason = "memory limit reached"
                print("Stopped: memory use has reached 60%.", file=sys.stderr)
                stop_command(command, descendants)
                status = 125
                break
            status = command.poll()
            if status is not None:
                break
            time.sleep(0.2)
    except BaseException:
        stop_command(command, process_tree(os.getpid()))
        raise
    record = {
        "command": Path(arguments[0]).name,
        "cpus": cpus,
        "address_space_limit_bytes_per_process": address_limit,
        "memory_limit_fraction": MAX_MEMORY_FRACTION,
        "peak_process_tree_rss_bytes": peak_tree_rss,
        "peak_host_memory_fraction": peak_host_fraction,
        "sampling_interval_s": 0.2,
        "mpi_binding_events": mpi_binding_events,
        "elapsed_s": time.monotonic() - start,
        "exit_status": status,
        "reason": reason,
    }
    log_path = ROOT / "data" / "processed" / "resource_usage.jsonl"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record) + "\n")
    return status if status >= 0 else 128 - status


if __name__ == "__main__":
    raise SystemExit(main())
