"""Read processed Center observations from the two BPR archives cited by Cabaniss."""

from __future__ import annotations

import csv
import gzip
import hashlib
import math
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from axialstress.historical_bpr import DEPLOYMENTS, FOX_1997_1998_DEPLOYMENTS, Deployment


@dataclass(frozen=True)
class PaperBPRSource:
    """Identify a processed observation field and its archive DOI."""

    deployment: Deployment
    channel: str
    doi: str
    zero_is_missing: bool = False


_DEPLOYMENTS = {item.slug: item for item in (*DEPLOYMENTS, *FOX_1997_1998_DEPLOYMENTS)}
CANDIDATE_PROCESSED_CENTER_SOURCES = (
    PaperBPRSource(
        _DEPLOYMENTS["fox_wc81_1997_center"], "LPFDetidedDepth", "10.1594/IEDA/322344", True
    ),
    *(
        PaperBPRSource(_DEPLOYMENTS[slug], channel, "10.1594/IEDA/322282")
        for slug, channel in (
            ("nemo_2002_2004_center", "DriftCorrLPFDep"),
            ("nemo_2003_2005_center", "LPFDetidedDepth"),
            ("nemo_2004_2007_center", "DriftCorrLPFDep"),
            ("nemo_2007_2010_center", "DriftCorrLPFDep"),
            ("nemo_2010_2011_center", "DriftCorrLPFDep"),
            ("nemo_2011_2013_center", "DriftCorrLPFDep"),
            ("nemo_2013_2015_center", "DriftCorrLPFDep"),
        )
    ),
)


def file_sha256(path: Path) -> str:
    """Return the SHA-256 digest of a source file without loading it into memory."""
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def export_hourly_observations(source: PaperBPRSource, output: Path) -> dict:
    """Copy on-hour source observations, retaining depth in meters and UTC time.

    Parameters
    ----------
    source : PaperBPRSource
        Archive file, exact field name, DOI, and missing-value convention.
    output : pathlib.Path
        Destination CSV containing observed depth and original source row.

    Returns
    -------
    dict
        Source digest, field, date range, sample count, and gaps over one hour.

    Notes
    -----
    Hourly selection is a project export cadence. It does not assert the
    paper's time discretization. No interpolation, datum adjustment, or
    additional filtering is applied. The Fox format notes identify zero LPF
    entries as absent values. Other archives must supply finite depths.
    """
    path = source.deployment.path
    digest = file_sha256(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    previous = None
    first = None
    count = 0
    missing = 0
    gaps = []
    try:
        with gzip.open(path, "rt", newline="", encoding="utf-8") as stream, temporary.open(
            "w", newline="", encoding="utf-8"
        ) as destination:
            reader = csv.reader(stream)
            header = [item.strip() for item in next(reader)]
            if not header or header[0] not in {"Date", "DateTime"}:
                raise ValueError(f"missing archive date header in {path}")
            if source.channel not in header:
                raise ValueError(f"missing source channel {source.channel!r} in {path}")
            index = header.index(source.channel)
            writer = csv.writer(destination)
            writer.writerow(["time_utc", "observed_depth_m", "source_row"])
            for row_number, row in enumerate(reader, start=2):
                if len(row) != len(header):
                    raise ValueError(f"malformed source row {row_number} in {path}")
                stamp = row[0].strip()
                if len(stamp) != 19:
                    raise ValueError(f"malformed timestamp at row {row_number} in {path}")
                if stamp[14:] != "00:00":
                    continue
                when = datetime.strptime(stamp, "%m/%d/%Y %H:%M:%S").replace(tzinfo=UTC)
                depth = float(row[index])
                if source.zero_is_missing and depth == 0.0:
                    missing += 1
                    continue
                if not math.isfinite(depth) or depth <= 0:
                    raise ValueError(f"invalid observed depth at row {row_number} in {path}")
                if previous is not None:
                    difference_s = (when - previous).total_seconds()
                    if difference_s <= 0:
                        raise ValueError(f"source timestamps are not increasing in {path}")
                    if difference_s > 3600:
                        gaps.append({
                            "after_utc": previous.isoformat(),
                            "before_utc": when.isoformat(),
                            "missing_hourly_samples": int(difference_s / 3600) - 1,
                        })
                writer.writerow([when.isoformat(), row[index].strip(), row_number])
                first = when if first is None else first
                previous = when
                count += 1
        if count == 0:
            raise ValueError(f"no valid hourly observations in {path}")
        temporary.replace(output)
    finally:
        temporary.unlink(missing_ok=True)
    return {
        "deployment": source.deployment.slug,
        "source_file": str(path),
        "source_sha256": digest,
        "source_doi": source.doi,
        "source_channel": source.channel,
        "source_coordinates_lat_lon_deg": [
            source.deployment.latitude, source.deployment.longitude,
        ],
        "observed_depth_units": "m",
        "samples": count,
        "missing_zero_values_on_hour": missing,
        "first_time_utc": first.isoformat(),
        "last_time_utc": previous.isoformat(),
        "gaps": gaps,
        "output_file": str(output),
        "output_sha256": file_sha256(output),
        "common_datum_verified": False,
    }
