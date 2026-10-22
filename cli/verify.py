"""Offline evidence verification. Supply trust pins independently of the archive."""

import argparse
import json
import sys
from pathlib import Path

from services.exporter import verify_pack


def main() -> int:
    """Return nonzero for invalid evidence or absent independent trust."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument(
        "--trust", required=True, type=Path, help="Out-of-band role → SHA256 fingerprint JSON"
    )
    args = parser.parse_args()
    try:
        result = verify_pack(args.archive.read_bytes(), json.loads(args.trust.read_text()))
        print(json.dumps(result))
        return 0
    except (ValueError, OSError) as error:
        print(json.dumps({"valid": False, "reason": str(error)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
