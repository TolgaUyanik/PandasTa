# Run summary — /brutally-honest-review --auto (G191-003, issue #79)

**Date:** 2026-11-11 · **Mode:** C · **Tasks:** 1 · **Review rounds:** 4
(PASS / REVISE / PASS / PASS) · **Findings:** 19 total (4 + 5 + 5 + 5) —
0 CRITICAL, 1 MAJOR, 4 MINOR, 14 NIT. All 19 fixed.

| task | status | rounds | files touched | follow-ups |
|---|---|---|---|---|
| G191-003 — port GTJA191 alpha `#3` as `g191_003` | **PASS** | 4 | `pandas_ta/momentum/g191_003.py` · `pandas_ta/momentum/__init__.py` · `pandas_ta/__init__.py` · `pandas_ta/core.py` · `tests/test_g191_003.py` · `tests/test_altport2_ports.py` · `docs/measure_g191_003.py` · `docs/G191003Measured.md` · `README.md` · `docs/IndicatorDictionary.md` · `docs/MLCompanionContract.md` | Gate E (launcher) · ledger row (receipt session) · Backtesting suite (launcher) |

## What shipped

`G191_003_6` in `momentum`: `SUM(C=C1 ? 0 : C-(C>C1 ? MIN(L,C1) :
MAX(H,C1)), 6) / C`, scale-free and causal, the windowed form of Williams'
Accumulation/Distribution. Gates A–D cleared on synthetic frames, Gate F
green in this repo bar the two known breaks and the owed ledger row.
`Category` 313 → 314, `momentum` 79 → 80.

## The one MAJOR, and what it says about the run

Round 2's MAJOR was not a mathematics error — it was round 1's own fix
overreaching: "one flat bar moves `length` outputs" where the fixture
moves 2 of 3 windows (the third sits in the warm-up). That is this repo's
dominant defect class, and it appeared in a sentence written to repair an
earlier instance of the same thing. 14 of the 19 findings are prose
claiming more than the run behind it; the other 5 added or strengthened a
test or a line of the measure script. None touched the arithmetic, which
every round re-derived and found correct.

## Numbers the reviewer independently reproduced

1,494 fires of 1,500 · first fire bar 6 · nunique 1,494 ·
767 positive / 727 negative / 0 zeros · census 762 up / 737 down / 0 flat ·
0 sign violations either side · ×8/×64 max|diff| 0.0 · ×10/×3.7
3.99e-16 / 4.06e-16 · 0 bars changing branch at any multiplier ·
0 of 37 real-module leaks vs 37 of 37 for both mutants ·
port vs retyped vs REAL screen candidate all max|diff| 0.0 ·
Spearman 0.906078 vs `kdj:J_9_3` (n=888) ·
suite 3 failed / 5221 passed / 83 skipped.

## Open, by design

* **Gate E is pending** — the launcher runs it. The synthetic
  Spearman 0.906078 against `kdj:J_9_3` sits ABOVE the 0.90 strike line,
  while the owner's own real-data fork-overlap screen measured 0.8394
  against that same column. `docs/G191003Measured.md` carries both, labels
  the gap's explanation a read rather than a measurement, and commits to
  reverting if the launcher's run strikes the column.
* **No ledger row** — nothing to record until Gate E runs.
* **A pre-existing `Category`-mutation bug** found while running test
  subsets (`pandas_ta/core.py:692` removes from the live list returned by
  `core.py:453`) is disclosed at the end of the receipt and deliberately
  not fixed: it changes `strategy()` behaviour and is outside issue #79.
* **Five round-4 MINOR/NIT fixes landed after its PASS** with no fifth
  review, the skill's 4-round cap being spent; see the disclosure in
  `01-g191-003.md`.
