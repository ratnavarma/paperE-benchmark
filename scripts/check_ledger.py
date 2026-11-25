"""Check that every data-file key cited in docs/EVIDENCE_LEDGER.md exists in results/paper_numbers.json.

Usage: uv run python scripts/check_ledger.py
Backticked tokens that look like data-file keys are checked; `*`, `{a,b}` and `<name>` are
expanded as patterns. Exits 1 and lists the misses if any cited key has no match.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "docs" / "EVIDENCE_LEDGER.md"
DATA = ROOT / "results" / "paper_numbers.json"
PREFIXES = ("e1/", "e2/", "e3/", "cell/", "scale/", "secondary/", "g2_full/", "layers/")


def to_regex(token: str) -> re.Pattern:
    token = token.strip().rstrip("/").replace("...", "*")
    out, i = "", 0
    while i < len(token):
        ch = token[i]
        if ch == "*":
            out += ".*"
        elif ch == "{":
            j = token.index("}", i)
            out += "(" + "|".join(re.escape(x) for x in token[i + 1:j].split(",")) + ")"
            i = j
        elif ch == "<":
            j = token.index(">", i)
            out += "[^/]+"
            i = j
        else:
            out += re.escape(ch)
        i += 1
    return re.compile("^" + out + "(/.*)?$")


def main() -> int:
    numbers = json.loads(DATA.read_text(encoding="utf-8"))["numbers"]
    tokens = [t for t in re.findall(r"`([^`]+)`", LEDGER.read_text(encoding="utf-8"))
              if t.startswith(PREFIXES)]
    missing = []
    for tok in tokens:
        for part in re.split(r",\s+(?=[a-z0-9_]+/)", tok):
            rx = to_regex(part)
            if not any(rx.match(k) for k in numbers):
                missing.append(part)
    sha = hashlib.sha256(DATA.read_bytes()).hexdigest()
    print(f"checked {len(tokens)} cited keys against {len(numbers)} numbers; data sha256 {sha}")
    if missing:
        print("missing:", *missing, sep="\n  ")
        return 1
    print("all cited keys present")
    return 0


if __name__ == "__main__":
    sys.exit(main())
