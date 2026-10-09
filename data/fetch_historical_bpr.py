"""Fetch selected raw-depth files from independent Axial BPR archives."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import tarfile
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path

MGDS_FILELIST = "https://www.marine-geo.org/tools/search/filelist.php"
MGDS_DOWNLOAD_MODAL = "https://www.marine-geo.org/services/download/download_modal.php"
MGDS_DOWNLOAD_ACCEPT = "https://api.marine-geo.org/services/download/download_accept.php"
USER_AGENT = "axial-modeling independent raw BPR cross-check"


@dataclass(frozen=True)
class RawBPRFile:
    """Identify one original Axial BPR deployment file in an MGDS archive."""

    archive: str
    dataset_uid: str
    dataset_doi: str
    file_uid: str
    filename: str
    site: str
    event: str
    latitude_deg: float
    longitude_deg: float


ARCHIVES = {
    "fox_1998": {
        "dataset_uid": "22344",
        "doi": "10.1594/IEDA/322344",
        "title": "Axial 1997–1998 BPR deployments; original Fox data",
        "files": (
            RawBPRFile(
                "fox_1998", "22344", "10.1594/IEDA/322344", "941690",
                "nemo1997-1998-BPR-center-15sec-spotl-lpf.txt",
                "center", "1998", 45.956667, -130.0,
            ),
            RawBPRFile(
                "fox_1998", "22344", "10.1594/IEDA/322344", "941691",
                "nemo1997-1998-BPR-south-15sec-spotl-lpf.txt",
                "south", "1998", 45.930233, -129.983967,
            ),
        ),
    },
    "chadwick_nooner_2011": {
        "dataset_uid": "22282",
        "doi": "10.1594/IEDA/322282",
        "title": "Axial uncabled BPR deployment records; raw-depth columns only",
        "files": (
            RawBPRFile(
                "chadwick_nooner_2011", "22282", "10.1594/IEDA/322282", "896882",
                "nemo2010-2011-BPR-center-15sec-driftcorr-detided-lpf.txt",
                "center", "2011", 45.955467, -130.009567,
            ),
            RawBPRFile(
                "chadwick_nooner_2011", "22282", "10.1594/IEDA/322282", "896881",
                "nemo2009-2011-BPR-south-15sec-detided-lpf.txt",
                "south", "2011", 45.934117, -129.999883,
            ),
        ),
    },
}


def mgds_file_inventory(dataset_uid: str) -> dict[str, dict[str, str]]:
    """Return file metadata keyed by file ID without downloading data files."""
    from html.parser import HTMLParser

    class Parser(HTMLParser):
        def __init__(self) -> None:
            super().__init__()
            self.items: dict[str, dict[str, str]] = {}
            self.current: dict[str, str] | None = None
            self.depth = 0
            self.in_filename = False

        def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
            values = dict(attrs)
            if tag == "div" and "filerow" in (values.get("class") or "").split():
                self.current = {
                    "file_uid": values.get("data-uid") or "",
                    "size_bytes": values.get("data-size") or "",
                    "filename": "",
                }
                self.depth = 1
            elif self.current is not None and tag == "div":
                self.depth += 1
            if self.current is not None and tag == "span" and "file_name" in (
                values.get("class") or ""
            ).split():
                self.in_filename = True

        def handle_endtag(self, tag: str) -> None:
            if tag == "span":
                self.in_filename = False
            if self.current is not None and tag == "div":
                self.depth -= 1
                if self.depth == 0:
                    self.items[self.current["file_uid"]] = self.current
                    self.current = None

        def handle_data(self, data: str) -> None:
            if self.current is not None and self.in_filename:
                self.current["filename"] += data.strip()

    query = urllib.parse.urlencode(
        {"data_set_uid": dataset_uid, "offset": 0, "limit": 1000}
    )
    request = urllib.request.Request(
        f"{MGDS_FILELIST}?{query}", headers={"User-Agent": USER_AGENT}
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        html = response.read().decode("utf-8", errors="replace")
    parser = Parser()
    parser.feed(html)
    return parser.items


def selected_archive(file: RawBPRFile, output_dir: Path) -> dict[str, str | int]:
    """Download one dataset archive containing the selected file records."""
    dataset = ARCHIVES[file.archive]
    selected = dataset["files"]
    file_ids = ",".join(sorted(record.file_uid for record in selected))
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor())
    modal_request = urllib.request.Request(
        MGDS_DOWNLOAD_MODAL,
        data=urllib.parse.urlencode(
            {"FileDownload": file_ids, "data_set_uid": file.dataset_uid}
        ).encode(),
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": USER_AGENT,
        },
    )
    try:
        with opener.open(modal_request, timeout=60) as response:
            modal = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"MGDS download form returned HTTP {exc.code}") from exc
    data_uid_match = re.search(r'name="data_uids"\s+value="([^"]+)"', modal)
    if not data_uid_match or data_uid_match.group(1) != file_ids:
        raise RuntimeError("MGDS download form did not confirm the selected file IDs")

    payload = urllib.parse.urlencode(
        {
            "purpose": "Research",
            "doc_uids": "",
            "client": "DataLink",
            "force_download": "1",
            "data_uids": file_ids,
        }
    ).encode()
    download_request = urllib.request.Request(
        MGDS_DOWNLOAD_ACCEPT,
        data=payload,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": USER_AGENT,
            "Referer": MGDS_DOWNLOAD_MODAL,
        },
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / f"axial-bpr-{file.archive}.tar"
    digest = hashlib.sha256()
    try:
        with opener.open(download_request, timeout=120) as response:
            content_type = response.headers.get("Content-Type", "")
            if "tar" not in content_type.lower() and "octet-stream" not in content_type.lower():
                detail = response.read(1000).decode("utf-8", errors="replace")
                raise RuntimeError(
                    f"MGDS returned {content_type!r}, not an archive: {detail[:300]}"
                )
            with output.open("wb") as stream:
                while chunk := response.read(1024 * 1024):
                    digest.update(chunk)
                    stream.write(chunk)
    except Exception:
        output.unlink(missing_ok=True)
        raise

    expected = {record.filename for record in selected}
    try:
        with tarfile.open(output, "r:*") as archive:
            members = {Path(member.name).name.removesuffix(".gz") for member in archive}
            if not expected.issubset(members):
                raise RuntimeError(
                    f"archive is missing selected records: {sorted(expected - members)}"
                )
    except Exception:
        output.unlink(missing_ok=True)
        raise

    return {
        "archive": file.archive,
        "dataset_uid": file.dataset_uid,
        "dataset_doi": file.dataset_doi,
        "file_uids": file_ids,
        "filenames": sorted(expected),
        "archive_file": str(output),
        "archive_bytes": output.stat().st_size,
        "archive_sha256": digest.hexdigest(),
    }


def parse_args() -> argparse.Namespace:
    """Parse source selection and local output options."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--archives",
        nargs="+",
        choices=tuple(ARCHIVES),
        default=tuple(ARCHIVES),
        help="historical BPR archives (default: both eruption records)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parent / "raw" / "historical_bpr",
        help="directory for ignored local ZIP files and manifest",
    )
    parser.add_argument(
        "--download",
        action="store_true",
        help="retrieve the selected raw-depth files; otherwise print the plan",
    )
    return parser.parse_args()


def main() -> None:
    """Print a dry-run plan or download selected BPR archives and manifest."""
    args = parse_args()
    results = []
    for archive_name in args.archives:
        archive = ARCHIVES[archive_name]
        inventory = mgds_file_inventory(archive["dataset_uid"])
        for record in archive["files"]:
            item = inventory.get(record.file_uid)
            if item is None or item["filename"] != record.filename:
                raise SystemExit(
                    f"source file inventory changed for {record.file_uid}: {item}"
                )
            print(
                f"{record.event} {record.site}: {record.filename} "
                f"({item['size_bytes']} bytes), DOI {record.dataset_doi}"
            )
        if args.download:
            result = selected_archive(archive["files"][0], args.output_dir)
            result["source_inventory"] = [
                inventory[record.file_uid] for record in archive["files"]
            ]
            results.append(result)

    if args.download:
        manifest = {
            "source": "Marine Geoscience Data System (MGDS), Axial uncabled BPR archives",
            "purpose": "Independent checks using raw-depth channels only",
            "retrieved_utc": dt.datetime.now(dt.UTC).isoformat(),
            "excluded_columns": [
                "Spotl-detided depth",
                "low-pass-filtered depth",
                "drift-corrected depth",
            ],
            "archives": results,
        }
        path = args.output_dir / "manifest.json"
        path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        print(f"provenance manifest: {path}")


if __name__ == "__main__":
    main()
