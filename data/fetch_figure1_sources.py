"""Fetch independent Axial source records for the project Figure 1 map."""

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

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw" / "figure1"
MGDS_ACCEPT_URL = "https://api.marine-geo.org/services/download/download_accept.php"
GMRT_URL = "https://www.gmrt.org/services/GridServer"

SOURCES = (
    {
        "name": "1998 flow outlines",
        "dataset_uid": "23601",
        "data_uids": ("1029462", "1029463"),
        "doi": "10.1594/IEDA/323601",
        "archive": RAW_DIR / "mgds" / "clague-1998-outlines.tar",
        "extract_dir": RAW_DIR / "mgds" / "clague-1998",
    },
    {
        "name": "2011 flow outlines",
        "dataset_uid": "24416",
        "data_uids": ("1127422", "1127423"),
        "doi": "10.1594/IEDA/324416",
        "archive": RAW_DIR / "mgds" / "clague-2011-outlines.tar",
        "extract_dir": RAW_DIR / "mgds" / "clague-2011",
    },
    {
        "name": "2015 flow outlines",
        "dataset_uid": "24418",
        "data_uids": ("1127427", "1127428"),
        "doi": "10.1594/IEDA/324418",
        "archive": RAW_DIR / "mgds" / "clague-2015-outlines.tar",
        "extract_dir": RAW_DIR / "mgds" / "clague-2015",
    },
    {
        "name": "2015 earthquake catalog",
        "dataset_uid": "24421",
        "data_uids": ("1127449",),
        "doi": "10.1594/IEDA/324421",
        "archive": RAW_DIR / "mgds" / "arnulf-2015-earthquakes.tar",
        "extract_dir": RAW_DIR / "mgds" / "arnulf-earthquakes",
    },
    {
        "name": "3-D P-wave velocity grid",
        "dataset_uid": "24420",
        "data_uids": ("1127447",),
        "doi": "10.1594/IEDA/324420",
        "archive": RAW_DIR / "mgds" / "arnulf-vp-model.tar",
        "extract_dir": RAW_DIR / "mgds" / "arnulf-vp-model",
    },
)


def sha256_file(path: Path) -> str:
    """Return the SHA-256 checksum of a local file."""
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def download(url: str, destination: Path, data: bytes | None = None) -> dict[str, object]:
    """Stream one public source file and return checksum-bearing provenance."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_suffix(destination.suffix + ".part")
    request = urllib.request.Request(
        url,
        data=data,
        headers={
            "User-Agent": "axial-modeling independent Figure 1 source fetcher",
            **({"Content-Type": "application/x-www-form-urlencoded"} if data else {}),
        },
    )
    digest = hashlib.sha256()
    size = 0
    try:
        with urllib.request.urlopen(request, timeout=240) as response, partial.open("wb") as output:
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
    return {"url": url, "file": str(destination.relative_to(ROOT)), "bytes": size,
            "sha256": digest.hexdigest()}


def extract_archive(archive: Path, destination: Path) -> list[str]:
    """Extract MGDS members after rejecting paths outside the destination."""
    destination.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive, "r:*") as tar:
        members = tar.getmembers()
        for member in members:
            target = (destination / member.name).resolve()
            if destination.resolve() not in target.parents:
                raise ValueError(f"unsafe MGDS archive member: {member.name}")
        tar.extractall(destination, filter="data")
    return [member.name for member in members if member.isfile()]


def mgds_request(source: dict[str, object]) -> tuple[str, bytes]:
    """Build the terms page and accepted download request for a source record."""
    data_uids = source["data_uids"]
    query = urllib.parse.urlencode(
        {"data_uids": ",".join(data_uids), "data_set_uid": source["dataset_uid"]}
    )
    payload = urllib.parse.urlencode(
        {"purpose": "Research", "client": "DataLink", "force_download": "1",
         "data_uids": ",".join(data_uids)}
    ).encode()
    return f"https://www.marine-geo.org/services/download/download.php?{query}", payload


def main() -> None:
    """Print source URLs or retrieve authorized raw map inputs."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--download", action="store_true", help="retrieve raw source data")
    parser.add_argument(
        "--accept-mgds-terms", action="store_true",
        help="submit MGDS research-use acceptance for each selected archive",
    )
    parser.add_argument(
        "--skip-mgds", action="store_true", help="fetch GMRT bathymetry only",
    )
    args = parser.parse_args()

    manifest_path = RAW_DIR / "manifest.json"
    sources = []
    if not args.skip_mgds:
        for source in SOURCES:
            terms_url, _ = mgds_request(source)
            print(f"{source['name']}: {terms_url}")
            sources.append(source)
    north, south, east, west = 46.15, 45.68, -129.65, -130.35
    gmrt_params = urllib.parse.urlencode(
        {"north": north, "south": south, "east": east, "west": west,
         "layer": "topo", "format": "geotiff", "resolution": "high"}
    )
    gmrt_url = f"{GMRT_URL}?{gmrt_params}"
    print(f"GMRT Axial bathymetry: {gmrt_url}")
    if not args.download:
        print("Dry run only. Add --download --accept-mgds-terms to fetch all sources.")
        return
    if not args.skip_mgds and not args.accept_mgds_terms:
        raise SystemExit("MGDS downloads also require --accept-mgds-terms")

    records: list[dict[str, object]] = []
    if manifest_path.exists():
        previous = json.loads(manifest_path.read_text(encoding="utf-8"))
        records = [r for r in previous.get("records", []) if r.get("source") == "GMRT"]
    for source in sources:
        terms_url, payload = mgds_request(source)
        downloaded = download(MGDS_ACCEPT_URL, source["archive"], payload)
        files = extract_archive(source["archive"], source["extract_dir"])
        records.append({
            "source": "MGDS", "name": source["name"], "dataset_uid": source["dataset_uid"],
            "data_uids": list(source["data_uids"]), "doi": source["doi"],
            "license": "CC BY-NC-SA 3.0", "terms_url": terms_url,
            "archive": downloaded, "extracted_files": files,
        })
        print(f"Fetched {source['name']}: {downloaded['bytes']} bytes, {len(files)} files")

    bathymetry = RAW_DIR / "gmrt" / "axial_gmrt_high_50km.tif"
    if bathymetry.exists():
        records = [r for r in records if r.get("name") != "Axial regional bathymetry"]
        records.append({
            "source": "GMRT", "name": "Axial regional bathymetry",
            "dataset": "Global Multi-Resolution Topography GridServer",
            "bounds_degrees": {"north": north, "south": south, "east": east, "west": west},
            "record": {"file": str(bathymetry.relative_to(ROOT)),
                       "bytes": bathymetry.stat().st_size, "sha256": sha256_file(bathymetry)},
            "url": gmrt_url,
        })
        print(f"Using existing bathymetry: {bathymetry}")
    else:
        downloaded = download(gmrt_url, bathymetry)
        records.append({
            "source": "GMRT", "name": "Axial regional bathymetry",
            "dataset": "Global Multi-Resolution Topography GridServer",
            "bounds_degrees": {"north": north, "south": south, "east": east, "west": west},
            "record": downloaded,
        })
        print(f"Fetched GMRT bathymetry: {downloaded['bytes']} bytes")

    manifest = {
        "retrieved_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "purpose": "Independent raw geology, seismicity, tomography, and bathymetry for Figure 1.",
        "excluded_inputs": ["Cabaniss et al. model outputs and figure data"],
        "records": records,
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote local checksummed manifest: {manifest_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
