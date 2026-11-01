# Checks a local copy of changelog.json before it is pushed to the "changelog"
# branch, because a broken file would make every environment keep showing its
# old list. Usage: python -m app.cli.changelog_check <path to changelog.json>

import sys
from pathlib import Path

from app.landing.changelog import parse_changelog


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python -m app.cli.changelog_check <path to changelog.json>")
        return 2

    try:
        entries = parse_changelog(Path(sys.argv[1]).read_bytes())
    except (OSError, ValueError) as error:
        print(f"INVALID: {error}")
        return 1

    print(f"OK: {len(entries)} lines")
    return 0


if __name__ == "__main__":
    sys.exit(main())
