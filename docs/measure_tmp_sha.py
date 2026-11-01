# -*- coding: utf-8 -*-
"""One-off: recompute pandas_ta/momentum/ewmac.py's lf_sha1 (docs/gate_e_ledger.py's
CRLF-folded sha1) after docs/measure_ewmac_ledger_fix.py's revert edited the file post-record.
The EWMAC_64_256_35 row's measured numbers stay valid -- that pair's computation is
byte-identical before and after the revert, only comments and the other five PAIRS
entries changed -- so docs/gate_e_ledger.csv's module_sha1 for that row is updated to
this value (22c33233e0d95e267e06a462cd56a7a82988617a) rather than treating the
measurement as owed. Refs #29.
"""
import hashlib
from pathlib import Path

MODULE = Path(__file__).resolve().parent.parent / "pandas_ta" / "momentum" / "ewmac.py"


def main():
    print(hashlib.sha1(MODULE.read_bytes().replace(b"\r\n", b"\n")).hexdigest())


if __name__ == "__main__":
    main()
