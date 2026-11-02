# -*- coding: utf-8 -*-
"""One-off: apply issue #34's Gate E revert to docs/gate_e_ledger.csv.

Gate E STRUCK `rank`'s RANK_20, RANK_30 and RANK_60 (pooled |rho| 0.9767 /
0.9788 / 0.9403 vs BB_%B / zscore / Range_Pos_60) -- no waiver exists for
them, so they cannot stay recorded once the columns are removed from the
module (same pattern as EWMAC's `docs/measure_ewmac_ledger_fix.py`, #29).

The surviving RANK_5 / RANK_10 rows (DISCLOSE_GAP) are kept, with their
`module_sha1` resynced to the post-revert `pandas_ta/statistics/rank.py`:
removing the other three lengths does not change either surviving column's
computed values (each length is independent in the module's `lengths`-keyed
dict comprehension), only the file's other bytes, so the measured numbers
stay valid -- they just need the row's module_sha1 updated to match the
edited file (same pattern as EWMAC's `docs/measure_tmp_sha.py`), rather than
being treated as owed pending a fresh harness run.
"""
import csv
import hashlib
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
LEDGER = REPO / "docs" / "gate_e_ledger.csv"
MODULE = REPO / "pandas_ta" / "statistics" / "rank.py"
KEEP_COLUMNS = {"RANK_5", "RANK_10"}


def lf_sha1(path: Path) -> str:
    return hashlib.sha1(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def main():
    with LEDGER.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.reader(fh))
    header, body = rows[0], rows[1:]
    sha1_idx = header.index("module_sha1")
    new_sha1 = lf_sha1(MODULE)

    kept = []
    for row in body:
        if row[0] == "rank" and row[2] not in KEEP_COLUMNS:
            continue  # drop the STRUCK, unwaived RANK_20/30/60 rows
        if row[0] == "rank":
            row[sha1_idx] = new_sha1
        kept.append(row)

    print(f"{len(body)} -> {len(kept)} rows; rank module_sha1 -> {new_sha1}")
    with LEDGER.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh, lineterminator="\n")
        writer.writerow(header)
        writer.writerows(kept)


if __name__ == "__main__":
    main()
