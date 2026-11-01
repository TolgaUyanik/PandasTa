# -*- coding: utf-8 -*-
"""One-off: drop ewmac's five Gate E STRUCK rows from docs/gate_e_ledger.csv
(EWMAC_2_8_35, EWMAC_4_16_35, EWMAC_8_32_35, EWMAC_16_64_35, EWMAC_32_128_35
-- no waiver exists for them, so they cannot stay recorded once the columns
are removed from the module). The surviving EWMAC_64_256_35 row (DISCLOSE_GAP)
is left in place; it goes stale (owed) because editing ewmac.py changes the
module's sha1, same pattern as CRSI's docs/measure_crsi_ledger_fix.py. A later
Gate E re-run on the post-revert tree records a fresh row for it.
"""
import csv
from pathlib import Path

LEDGER = Path(__file__).resolve().parent / "gate_e_ledger.csv"
KEEP_COLUMN = "EWMAC_64_256_35"


def main():
    with LEDGER.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.reader(fh))
    header, body = rows[0], rows[1:]
    kept = [r for r in body if not (r[0] == "ewmac" and r[2] != KEEP_COLUMN)]
    print(f"{len(body)} -> {len(kept)} rows")
    with LEDGER.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh, lineterminator="\n")
        writer.writerow(header)
        writer.writerows(kept)


if __name__ == "__main__":
    main()
