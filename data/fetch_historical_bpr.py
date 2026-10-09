"""Fetch raw Axial BPR records spanning the 1998 and 2011 eruptions."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import tarfile
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RAW_DIR = ROOT / "raw" / "axial_bpr"
NCEI_BASE = (
    "https://www.ngdc.noaa.gov/thredds/fileServer/"
    "dart_bpr/rawdata/axial_seamount"
)
NCEI_FILES = (
    "wc09_19870923to19880710.csv.gz",
    "wc15_19880905to19890804.csv.gz",
    "wc20_19890907to19900730.csv.gz",
    "wc25_19900819to19910522.csv.gz",
    "wc32_19910624to19920604.csv.gz",
    "wc51_19930721to19940917.csv.gz",
    "wc61_19940806to19950615.csv.gz",
    "wc67_19950721to19960622.csv.gz",
    "wc68_19950721to19960622.csv.gz",
    "wc69_19950617to19960622.csv.gz",
    "wc81_19971003to19980807.csv.gz",
    "wc82a_19971003to19981003.csv.gz",
    "wc82b_19980924to19990505.csv.gz",
    "nemo_20000706to20010801.csv.gz",
    "nemo_20010701to20020719.csv.gz",
)
MGDS_DATA_SET_UID = "22282"
MGDS_DATA_UIDS = (
    "896874",
    "896875",
    "896876",
    "896877",
    "896878",
    "896879",
    "896880",
    "896881",
    "896882",
    "896883",
    "896884",
)
MGDS_ACCEPT_URL = "https://api.marine-geo.org/services/download/download_accept.php"
MGDS_TERMS_URL = (
    "https://www.marine-geo.org/services/download/download.php?data_uids="
    f"{urllib.parse.quote(','.join(MGDS_DATA_UIDS), safe='')}&"
    f"data_set_uid={MGDS_DATA_SET_UID}"
)
MGDS_ARCHIVE = RAW_DIR / "mgds" / "ieda_322282_2003_2013_bpr_records.tar"
MGDS_FOX_DATA_SET_UID = "22344"
MGDS_FOX_DATA_UIDS = ("941690", "941691")
MGDS_FOX_TERMS_URL = (
    "https://www.marine-geo.org/services/download/download.php?data_uids="
    f"{urllib.parse.quote(','.join(MGDS_FOX_DATA_UIDS), safe='')}&"
    f"data_set_uid={MGDS_FOX_DATA_SET_UID}"
)
MGDS_FOX_ARCHIVE = RAW_DIR / "mgds" / "ieda_322344_1997_1998_bpr_records.tar"


def sha256_file(path: Path) -> str:
    """Return the SHA-256 checksum of a local file."""
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def download(url: str, destination: Path, data: bytes | None = None) -> dict[str, object]:
    """Stream one public source file to disk and return its provenance."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_suffix(destination.suffix + ".part")
    request = urllib.request.Request(
        url,
        data=data,
        headers={
            "User-Agent": "axial-modeling historical raw BPR fetcher",
            **({"Content-Type": "application/x-www-form-urlencoded"} if data else {}),
        },
    )
    digest = hashlib.sha256()
    size = 0
    try:
        with urllib.request.urlopen(request, timeout=180) as response, partial.open("wb") as output:
            while chunk := response.read(1024 * 1024):
                output.write(chunk)
                digest.update(chunk)
                size += len(chunk)
    except urllib.error.HTTPError as exc:
        partial.unlink(missing_ok=True)
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        raise RuntimeError(f"download returned HTTP {exc.code}: {detail}") from exc
    except Exception:
        partial.unlink(missing_ok=True)
        raise
    partial.replace(destination)
    return {
        "url": url,
        "file": str(destination),
        "bytes": size,
        "sha256": digest.hexdigest(),
    }


def extract_mgds_archive(
    archive: Path, destination: Path | None = None
) -> list[str]:
    """Extract selected MGDS files after rejecting paths outside the target."""
    if destination is None:
        destination = RAW_DIR / "mgds" / "source_archive"
    destination.mkdir(parents=True, exist_ok=True)
    extracted = []
    with tarfile.open(archive, "r:") as tar:
        for member in tar.getmembers():
            target = (destination / member.name).resolve()
            if destination.resolve() not in target.parents:
                raise ValueError(f"unsafe MGDS archive member: {member.name}")
        tar.extractall(destination, filter="data")
        extracted = [member.name for member in tar.getmembers() if member.isfile()]
    return extracted


def parse_args() -> argparse.Namespace:
    """Parse dry-run and download options."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--download",
        action="store_true",
        help="retrieve NCEI raw files and selected MGDS deployment archives",
    )
    parser.add_argument(
        "--accept-mgds-terms",
        action="store_true",
        help=(
            "submit MGDS research-use acceptance and cite each archive's "
            "investigators and DOI when redistributing derived products"
        ),
    )
    parser.add_argument(
        "--ncei-only",
        action="store_true",
        help="download only NCEI raw records without requesting the MGDS archive",
    )
    return parser.parse_args()


def main() -> None:
    """Print source URLs or download the authorized raw observation archives."""
    args = parse_args()
    print("NCEI raw BPR files:")
    for filename in NCEI_FILES:
        print(f"  {NCEI_BASE}/{filename}")
    if not args.ncei_only:
        print(
            "MGDS 2003–2013 center and south BPR deployment archive (terms page):\n"
            f"  {MGDS_TERMS_URL}\n"
            "  data UIDs: " + ", ".join(MGDS_DATA_UIDS)
        )
        print(
            "MGDS Fox 1997–1998 center and south raw-depth archive (terms page):\n"
            f"  {MGDS_FOX_TERMS_URL}\n"
            "  data UIDs: " + ", ".join(MGDS_FOX_DATA_UIDS)
        )
    if not args.download:
        print(
            "Dry run only. Add --download --ncei-only for NCEI files, or "
            "--download --accept-mgds-terms for all archives."
        )
        return
    if not args.ncei_only and not args.accept_mgds_terms:
        raise SystemExit("--download also requires --accept-mgds-terms for MGDS")

    records = []
    for filename in NCEI_FILES:
        url = f"{NCEI_BASE}/{filename}"
        destination = RAW_DIR / "ncei" / filename
        result = download(url, destination)
        result.update({"archive": "NCEI DART BPR raw data", "deployment": filename})
        records.append(result)

    if args.ncei_only and (RAW_DIR / "manifest.json").exists():
        existing_manifest = json.loads(
            (RAW_DIR / "manifest.json").read_text(encoding="utf-8")
        )
        records.extend(
            record
            for record in existing_manifest.get("records", [])
            if record.get("archive") in {"MGDS IEDA/322282", "MGDS IEDA/322344"}
        )
    elif not args.ncei_only:
        payload = urllib.parse.urlencode(
            {
                "purpose": "Research",
                "client": "DataLink",
                "force_download": "1",
                "data_uids": ",".join(MGDS_DATA_UIDS),
            }
        ).encode()
        result = download(MGDS_ACCEPT_URL, MGDS_ARCHIVE, payload)
        result.update(
            {
                "archive": "MGDS IEDA/322282",
                "data_uids": list(MGDS_DATA_UIDS),
                "dataset_uid": MGDS_DATA_SET_UID,
                "license": "CC BY-NC-SA 3.0",
                "extracted_files": extract_mgds_archive(MGDS_ARCHIVE),
            }
        )
        records.append(result)
        fox_payload = urllib.parse.urlencode(
            {
                "purpose": "Research",
                "client": "DataLink",
                "force_download": "1",
                "data_uids": ",".join(MGDS_FOX_DATA_UIDS),
            }
        ).encode()
        fox_result = download(MGDS_ACCEPT_URL, MGDS_FOX_ARCHIVE, fox_payload)
        fox_result.update(
            {
                "archive": "MGDS IEDA/322344",
                "data_uids": list(MGDS_FOX_DATA_UIDS),
                "dataset_uid": MGDS_FOX_DATA_SET_UID,
                "doi": "10.1594/IEDA/322344",
                "license": "CC BY-NC-SA 3.0",
                "extracted_files": extract_mgds_archive(
                    MGDS_FOX_ARCHIVE,
                    RAW_DIR / "mgds" / "source_archive_322344",
                ),
                "processed_channels": ["Depth"],
                "excluded_channels": ["SpotlDetidedDepth", "LPFDetidedDepth"],
            }
        )
        records.append(fox_result)
    manifest = {
        "source_boundary": (
            "Only NCEI raw pressure and original MGDS Depth or RawDep channels "
            "are processed. MGDS detided, filtered, and drift-corrected columns "
            "are excluded."
        ),
        "retrieved_utc": dt.datetime.now(dt.UTC).isoformat(),
        "records": records,
    }
    manifest_path = RAW_DIR / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"wrote local provenance manifest to {manifest_path}")
    for record in records:
        if args.ncei_only and record.get("archive") == "MGDS IEDA/322282":
            print(f"retained existing MGDS manifest entry: {record['file']}")
        else:
            print(f"downloaded {record['bytes']} bytes: {record['file']}")


if __name__ == "__main__":
    main()
