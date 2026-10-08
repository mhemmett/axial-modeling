"""Fetch OOI-derived daily BPR depths and retain the original quality flags."""

from __future__ import annotations

import argparse
import datetime as dt
import gzip
import hashlib
import json
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import quote

ERDDAP_TABLEDAP = "https://erddap.dataexplorer.oceanobservatories.org/erddap/tabledap"
FIELDS = ("time", "botsflu_daydepth", "botsflu_daydepth_qc_agg")
SITES = {
    "central": {
        "dataset_id": "ooi-rs03ccal-mj03f-05-botpta301",
        "instrument": "RS03CCAL-MJ03F-05-BOTPTA301",
    },
    "east": {
        "dataset_id": "ooi-rs03ecal-mj03e-06-botpta302",
        "instrument": "RS03ECAL-MJ03E-06-BOTPTA302",
    },
}
PRODUCT = "BOTSFLU-DAYDEPTH"
PRODUCT_VARIABLE = "botsflu_daydepth"


def erddap_url(dataset_id: str, start: dt.date, end: dt.date) -> str:
    """Build a URL for daily OOI depth rows within an inclusive date range."""
    if end < start:
        raise ValueError("end date must be on or after start date")
    columns = quote(",".join(FIELDS), safe=",")
    start_time = f"{start.isoformat()}T00:00:00Z"
    end_time = f"{end.isoformat()}T23:59:59Z"
    constraints = (
        f"time%3E%3D{quote(start_time, safe=':-TZ')}"
        f"&time%3C%3D{quote(end_time, safe=':-TZ')}"
        f"&{PRODUCT_VARIABLE}%21%3DNaN"
    )
    return f"{ERDDAP_TABLEDAP}/{dataset_id}.csvp?{columns}&{constraints}"


def download_site(
    site: str,
    start: dt.date,
    end: dt.date,
    output_dir: Path,
) -> dict[str, str | int]:
    """Stream one OOI site CSV into a compressed local archive."""
    if site not in SITES:
        raise ValueError(f"unknown OOI BPR site: {site}")
    metadata = SITES[site]
    url = erddap_url(metadata["dataset_id"], start, end)
    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / f"{site}_{PRODUCT.lower()}_{start}_{end}.csv.gz"
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "axial-modeling OOI BPR fetcher"},
    )
    digest = hashlib.sha256()
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            with gzip.open(output, "wb") as compressed:
                while chunk := response.read(1024 * 1024):
                    digest.update(chunk)
                    compressed.write(chunk)
    except urllib.error.HTTPError as exc:
        output.unlink(missing_ok=True)
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        raise RuntimeError(f"OOI ERDDAP returned HTTP {exc.code}: {detail}") from exc
    except Exception:
        output.unlink(missing_ok=True)
        raise

    with gzip.open(output, "rt", encoding="utf-8", newline="") as stream:
        header = stream.readline().strip()
        row_count = sum(1 for _ in stream)
    expected = "time (UTC),botsflu_daydepth (m),botsflu_daydepth_qc_agg"
    if header != expected or row_count == 0:
        output.unlink(missing_ok=True)
        raise RuntimeError(f"unexpected or empty OOI response for {site}: {header!r}")

    return {
        "site": site,
        "instrument": metadata["instrument"],
        "dataset_id": metadata["dataset_id"],
        "product": PRODUCT,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "rows": row_count,
        "url": url,
        "file": str(output),
        "sha256_uncompressed": digest.hexdigest(),
    }


def parse_args() -> argparse.Namespace:
    """Parse command-line options."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--start",
        type=dt.date.fromisoformat,
        default=dt.date(2014, 1, 1),
        help="first date to request (inclusive; default: 2014-01-01)",
    )
    default_end = dt.datetime.now(dt.UTC).date()
    parser.add_argument(
        "--end",
        type=dt.date.fromisoformat,
        default=default_end,
        help=f"last date to request (inclusive; default: {default_end})",
    )
    parser.add_argument(
        "--sites",
        nargs="+",
        choices=tuple(SITES),
        default=tuple(SITES),
        help="OOI BOTPT instruments to request (default: central east)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parent / "raw" / "ooi_bpr",
        help="directory for ignored local CSV archives",
    )
    parser.add_argument(
        "--download",
        action="store_true",
        help="retrieve records; without this flag, print request URLs only",
    )
    return parser.parse_args()


def main() -> None:
    """Print OOI requests or retrieve records and write a provenance manifest."""
    args = parse_args()
    if args.end < args.start:
        raise SystemExit("--end must be on or after --start")

    results = []
    for site in args.sites:
        url = erddap_url(SITES[site]["dataset_id"], args.start, args.end)
        if not args.download:
            print(f"{site}: {url}")
            continue
        result = download_site(site, args.start, args.end, args.output_dir)
        results.append(result)
        print(f"{site}: saved {result['rows']} daily records to {result['file']}")

    if args.download:
        manifest = {
            "source": "Ocean Observatories Initiative public ERDDAP",
            "product": PRODUCT,
            "retrieved_utc": dt.datetime.now(dt.UTC).isoformat(),
            "records": results,
        }
        manifest_path = args.output_dir / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        print(f"provenance manifest: {manifest_path}")


if __name__ == "__main__":
    main()
