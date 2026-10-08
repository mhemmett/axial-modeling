"""Print BPR dataset citations without retrieving source data."""

DATASETS = {
    "chadwick-nooner": "https://doi.org/10.1594/IEDA/322282",
    "fox": "https://doi.org/10.1594/IEDA/322344",
}


def main() -> None:
    """List dataset references; downloads are intentionally unsupported."""
    for name, doi_url in DATASETS.items():
        print(f"{name}: {doi_url}")
    print(
        "Source-data retrieval is disabled by the project's provenance rules. "
        "Use only numerical input values given in allowed written sources."
    )


if __name__ == "__main__":
    main()
