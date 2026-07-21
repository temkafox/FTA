"""Update the application's version during a release."""

from __future__ import annotations

import re
import sys
from pathlib import Path


VERSION_PATTERN = re.compile(r'^__version__\s*=\s*["\'][^"\']+["\']\s*$', re.MULTILINE)


def main() -> int:
    if len(sys.argv) != 2 or not re.fullmatch(r"\d+\.\d+\.\d+", sys.argv[1]):
        print("ERROR: version must look like 1.2.3")
        return 2

    path = Path(__file__).with_name("version.py")
    source = path.read_text(encoding="utf-8")
    updated, replacements = VERSION_PATTERN.subn(
        f'__version__ = "{sys.argv[1]}"', source, count=1
    )
    if replacements != 1:
        print("ERROR: __version__ was not found in version.py")
        return 1

    path.write_text(updated, encoding="utf-8")
    print(f"Version set to {sys.argv[1]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
