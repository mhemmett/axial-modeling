"""Read processed independent OOI bottom-pressure observations."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.float64]
PROCESSED_DIR = Path(__file__).resolve().parents[2] / "data" / "processed"
PROCESSED_HEADER = [
    "time_utc",
    "signed_depth_m",
    "relative_uplift_m",
    "ooi_qc_aggregate",
]


@dataclass(frozen=True)
class BprSeries:
    """One processed daily OOI bottom-pressure series."""

    site: str
    times_utc: tuple[datetime, ...]
    uplift_m: FloatArray
    quality_codes: tuple[str, ...]


def latest_processed_bpr_path(site: str, directory: Path = PROCESSED_DIR) -> Path:
    """Return the most recently processed series for a named site."""
    matches = list(directory.glob(f"{site}_*.relative-uplift.csv"))
    if not matches:
        raise FileNotFoundError(
            f"no processed {site} BPR series found under {directory}; "
            "fetch and process the authorized OOI records first"
        )
    return max(matches, key=lambda path: (path.stat().st_mtime_ns, path.name))


def read_processed_bpr_series(site: str, path: Path) -> BprSeries:
    """Read a processed OOI series and validate UTC timestamps and row order."""
    times: list[datetime] = []
    uplift: list[float] = []
    quality_codes: list[str] = []
    with path.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != PROCESSED_HEADER:
            raise ValueError(f"unexpected processed BPR header in {path}")
        for row_number, row in enumerate(reader, start=2):
            try:
                time = datetime.fromisoformat(row["time_utc"].replace("Z", "+00:00"))
                value = float(row["relative_uplift_m"])
            except (TypeError, ValueError) as exc:
                raise ValueError(f"invalid BPR row {row_number} in {path}") from exc
            if time.tzinfo is None or time.utcoffset() != timedelta(0):
                raise ValueError(f"BPR timestamps must be UTC in {path}")
            if np.isinf(value):
                raise ValueError(f"BPR uplift must not be infinite in {path}")
            times.append(time.astimezone(UTC))
            uplift.append(value)
            quality_codes.append(row["ooi_qc_aggregate"])

    if not times:
        raise ValueError(f"processed BPR series has no rows: {path}")
    if any(later <= earlier for earlier, later in zip(times, times[1:], strict=False)):
        raise ValueError(f"BPR timestamps must be strictly increasing in {path}")
    return BprSeries(site, tuple(times), np.asarray(uplift), tuple(quality_codes))
