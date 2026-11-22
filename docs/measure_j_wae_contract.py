"""Print the `J_WAE_150_20_40_20_2.0` entries of the documents that name it.

`docs/MLCompanionContract.md` keeps its column inventory on a single very
long line, which neither an editor's grep nor this repo's reading tools will
show in context, so the receipt session needs a way to read the one entry it
has to keep true. This script prints, for every document that mentions the
column, each mention with surrounding context, and then the ledger row the
mentions have to agree with.

Usage: `python docs/measure_j_wae_contract.py [width]` (default 400 chars of
context on each side of a mention).
"""

import csv
import sys
from pathlib import Path

COLUMN = "J_WAE_150_20_40_20_2.0"
ROOT = Path(__file__).resolve().parent.parent
DOCS = (
    "docs/MLCompanionContract.md",
    "docs/IndicatorDictionary.md",
    "README.md",
)


def _mentions(text: str, needle: str, width: int):
    start = 0
    while True:
        hit = text.find(needle, start)
        if hit < 0:
            return
        yield text[max(0, hit - width):hit + len(needle) + width]
        start = hit + len(needle)


def main() -> int:
    width = int(sys.argv[1]) if len(sys.argv) > 1 else 400
    for name in DOCS:
        path = ROOT / name
        if not path.exists():
            print(f"== {name}: ABSENT")
            continue
        text = path.read_text(encoding="utf-8")
        chunks = list(_mentions(text, COLUMN, width))
        print(f"== {name}: {len(chunks)} mention(s) of {COLUMN}")
        for i, chunk in enumerate(chunks, 1):
            print(f"-- mention {i} --")
            print(chunk.replace("|", "|\n  "))
        print()

    path = ROOT / "docs" / "gate_e_ledger.csv"
    with path.open(newline="", encoding="utf-8") as handle:
        rows = [r for r in csv.DictReader(handle) if r["indicator"] == "j_wae"]
    print(f"== docs/gate_e_ledger.csv: {len(rows)} row(s) for j_wae")
    for row in rows:
        for key, value in row.items():
            print(f"  {key}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
