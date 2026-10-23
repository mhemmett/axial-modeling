"""Fetch the cited processed 2000–2002 Center BPR archive from MGDS."""

from __future__ import annotations

import argparse
import json
import urllib.parse
from datetime import UTC, datetime
from pathlib import Path

from fetch_historical_bpr import download, extract_mgds_archive

ROOT = Path(__file__).resolve().parents[1]
DATA_UID = "896872"
DATASET_UID = "22282"
DOI = "10.1594/IEDA/322282"
SOURCE_LIST_URL = (
    "https://www.marine-geo.org/tools/search/filelist.php"
    f"?offset=0&limit=100&data_set_uid={DATASET_UID}&internal=false"
)
TERMS_URL = (
    "https://www.marine-geo.org/services/download/download.php"
    f"?data_uids={DATA_UID}&data_set_uid={DATASET_UID}"
)
ACCEPT_URL = "https://api.marine-geo.org/services/download/download_accept.php"
ARCHIVE = ROOT / "data/raw/axial_bpr/mgds/ieda_322282_2000_2002_bpr_records.tar"
EXTRACTED = ROOT / "data/raw/axial_bpr/mgds/source_archive_2000_2002"
FILENAME = "nemo2000-2002-BPR-center-15sec-driftcorr-detided-lpf.txt.gz"


def main() -> None:
    """Download one documented MGDS observation file after terms acceptance."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--accept-mgds-terms", action="store_true")
    args = parser.parse_args()
    print(f"Dataset DOI: {DOI}")
    print(f"Source inventory: {SOURCE_LIST_URL}")
    print(f"File UID: {DATA_UID}; filename: {FILENAME}")
    print(f"MGDS terms: {TERMS_URL}")
    if not args.download:
        print("Dry run only. Add --download --accept-mgds-terms to retrieve the file.")
        return
    if not args.accept_mgds_terms:
        parser.error("--download requires --accept-mgds-terms")

    payload = urllib.parse.urlencode({
        "purpose": "Research",
        "client": "DataLink",
        "force_download": "1",
        "data_uids": DATA_UID,
    }).encode()
    result = download(ACCEPT_URL, ARCHIVE, payload)
    members = extract_mgds_archive(ARCHIVE, EXTRACTED)
    matches = [name for name in members if Path(name).name == FILENAME]
    if len(matches) != 1:
        raise RuntimeError(f"archive did not contain exactly one {FILENAME}")
    record = {
        **result,
        "source_dataset_doi": DOI,
        "source_data_uid": DATA_UID,
        "source_inventory": SOURCE_LIST_URL,
        "license": "CC BY-NC-SA 3.0",
        "retrieved_utc": datetime.now(UTC).isoformat(),
        "extracted_file": str(EXTRACTED / matches[0]),
        "processed_observations_allowed_as_inputs": True,
        "paper_channel_selection_verified": False,
    }
    manifest = EXTRACTED / "source_manifest.json"
    manifest.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(f"Retrieved {result['bytes']} bytes; source record: {manifest}")


if __name__ == "__main__":
    main()
