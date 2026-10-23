"""Report the source requirements remaining before the paper can be reproduced."""

from __future__ import annotations

import argparse
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    """Print method requirements and reject a premature reproduction claim."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require-complete", action="store_true")
    args = parser.parse_args()
    with (ROOT / "docs/reproduction_requirements.yaml").open(encoding="utf-8") as stream:
        specification = yaml.safe_load(stream)
    print("Cabaniss reproduction: 1998–2011 and 2011–2015 Center BPR cycles.")
    for item in specification["requirements"]:
        print(f"{item['id']} [{item['status']}]: {item['detail']}")
    print(f"Source audit: {ROOT / specification['source_audit']}")
    if args.require_complete:
        raise SystemExit(
            "The complete paper experiment is not implemented. "
            "Use make paper-bpr to prepare the available cited observations."
        )


if __name__ == "__main__":
    main()
