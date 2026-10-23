"""Fetch observed OOI Central Caldera daily seafloor depth without model output."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
from datetime import UTC, date, datetime
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
BASE_URL = (
    "https://erddap.dataexplorer.oceanobservatories.org/erddap/tabledap/"
    "ooi-rs03ccal-mj03f-05-botpta301.csv"
)
OUT = ROOT / "data" / "raw" / "ooi_center_daily"
COLUMNS = ("time", "botsflu_daydepth", "botsflu_daydepth_qc_agg")


def _validate_response(body: bytes, start: date, stop: date) -> int:
    """Check OOI column units, dates, and unique daily values before saving."""
    stream = io.StringIO(body.decode("utf-8"))
    reader = csv.reader(stream)
    if tuple(next(reader, ())) != COLUMNS or tuple(next(reader, ())) != ("UTC", "m", ""):
        raise ValueError("OOI daily-depth columns or units changed")
    count = 0
    last_day = None
    for row in reader:
        if len(row) != 3:
            raise ValueError("OOI daily-depth row has unexpected width")
        timestamp = datetime.fromisoformat(row[0].replace("Z", "+00:00"))
        day = timestamp.date()
        if not start <= day < stop or timestamp.hour or timestamp.minute:
            raise ValueError("OOI daily-depth time is outside the requested UTC day")
        if last_day is not None and day <= last_day:
            raise ValueError("OOI daily-depth timestamps are duplicated or unordered")
        depth = float(row[1])
        if not -2000.0 < depth < -1000.0:
            raise ValueError("OOI central-caldera depth is outside the station range")
        if row[2] not in {"1", "2", "3", "4", "9"}:
            raise ValueError("OOI quality flag is not a QARTOD value")
        last_day = day
        count += 1
    return count


def main() -> None:
    """Print public OOI requests or download and validate yearly CSV files."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--stop", type=date.fromisoformat, default=date.today())
    parser.add_argument("--output-dir", type=Path, default=OUT)
    args = parser.parse_args()
    args.output_dir = args.output_dir.resolve()
    first = date(2015, 4, 25)
    stop = args.stop
    if stop <= first:
        raise ValueError("stop must follow the 2015 eruption")
    manifest = {
        "source": "OOI Central Caldera MJ03F BOTPTA301 via OOI ERDDAP",
        "product": "BOTSFLU-DAYDEPTH: daily mean seafloor depth in m",
        "product_url": "https://oceanobservatories.org/data-product/botsflu/",
        "data_url": BASE_URL,
        "paper_model_output_used": False,
        "retrieved_utc": datetime.now(UTC).isoformat() if args.download else None,
        "files": [],
    }
    for year in range(first.year, stop.year + 1):
        start = max(first, date(year, 1, 1))
        end = min(stop, date(year + 1, 1, 1))
        if start >= end:
            continue
        query = (
            ",".join(COLUMNS)
            + f"&time>={start.isoformat()}T00:00:00Z"
            + f"&time<{end.isoformat()}T00:00:00Z"
            + "&botsflu_daydepth>=-1600"
        )
        url = f"{BASE_URL}?{query}"
        print(url)
        if not args.download:
            continue
        response = requests.get(url, timeout=90)
        response.raise_for_status()
        count = _validate_response(response.content, start, end)
        path = args.output_dir / f"center_daily_depth_{year}.csv"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(response.content)
        manifest["files"].append(
            {
                "path": path.name,
                "request_url": url,
                "sha256": hashlib.sha256(response.content).hexdigest(),
                "record_count": count,
            }
        )
    if args.download:
        (args.output_dir / "manifest.json").write_text(
            json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
        )
        print(f"saved {sum(item['record_count'] for item in manifest['files'])} daily depths")


if __name__ == "__main__":
    main()
