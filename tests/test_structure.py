"""Guards the rule: the core engine never names a business or assumes an industry.
Business data lives in examples/ (or the database); industry rules live in verticals/*.toml."""

import re
from pathlib import Path

SRC = Path(__file__).parents[1] / "src"
FORBIDDEN = re.compile(r"raam|hector|gloster|comet|windsor|ex-showroom|dealership|showroom|test drive|dental",
                       re.IGNORECASE)


def test_core_is_business_agnostic():
    offenders = []
    for path in SRC.rglob("*"):
        if path.suffix in {".py", ".txt"}:
            for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if FORBIDDEN.search(line):
                    offenders.append(f"{path.relative_to(SRC)}:{n}: {line.strip()}")
    assert not offenders, "Business/industry-specific text in core code:\n" + "\n".join(offenders)
