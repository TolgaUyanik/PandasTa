# Run summary — TS-PEAKS-20 (`/brutally-honest-review --auto`, Mode C)

| task | status | rounds | files touched | follow-ups |
|---|---|---|---|---|
| ts-peaks-20 | **PASS** | 5 (PASS → REVISE → REVISE → PASS → PASS) | 11 (4 new, 7 modified) | Gate E owed (launcher); the `core.py` `Category` mutation below is the owner's call |

## What shipped

New:

* `pandas_ta/statistics/ts_peaks_20.py` — the indicator, column
  `TS_PEAKS_20_2`, warm-up 19
* `tests/test_ts_peaks_20.py` — **192 tests**
* `docs/measure_ts_peaks_20.py` — the measurement script, 8 sections
* `docs/TsPeaks20Measured.md` — the receipt

Modified (five wiring touch points plus the four count surfaces):
`pandas_ta/statistics/__init__.py`, `pandas_ta/__init__.py`
(`Category["statistics"]`), `pandas_ta/core.py` (accessor), `README.md`
(324 → 325, 332 → 333, statistics 33 → 34), `docs/IndicatorDictionary.md`
(regenerated: `TS_PEAKS_20_2 ORD`, warm-up 19), `docs/MLCompanionContract.md`
(669 → 670 tagged, `ORD` 51 → 52), `tests/test_altport2_ports.py`
(`CATEGORY_TOTAL` 325).

`docs/gate_e_ledger.csv` is **untouched**: the row is owed.

## The gates, in one line each

* **A** — bit-equal to an independent `np.roll` spelling of `number_peaks`
  (581/581 on four frames), to a plain-Python scalar loop (581/581 on three),
  to the screen prototype and the owner's own registry entry on clean frames
  (1481/1481 on four), and to eight hand-derived windows. Five open readings
  decided and priced; the ceiling 6 proved by exhaustive enumeration over all
  65,536 subsets with one attaining subset, and attained by a pinned witness.
* **B** — the real module leaks 0 of 37 offsets in six configurations. The
  blind sweep is weak against the two one-bar leaks (2–5 and 1–4 of 37,
  because the peak flag fires on 13.8–14.9% of candidates); that is measured,
  explained as an exact set equality, and the gate instead rests on a designed
  probe where the real module leaks 0 and the mutants are caught 50/50 and
  41/50 with the 9 misses accounted for.
* **C** — synthetic only: fires 1,481 of 1,500 on each of seven frames, 5–6
  distinct values, full histograms. Real-data counts owed with Gate E.
* **D** — bit-identical on 1,481/1,481 bars for all 42 frame × scale
  combinations, at four non-default lengths, and under `log`/`sqrt`/`x**3`/
  `+1000`; the strict-`>` float-collapse limit stated as a measurement; drift
  (0.4066) and coarser rounding (0.5667) shown to move it.
* **E** — *pending, run by issue-solver after this session.*
* **F** — `python -m pytest -q` → **3 failed, 6,285 passed, 83 skipped**
  (133.15 s). The three: the two `CLAUDE.md` *Known breaks* plus the owed Gate
  E row, which names exactly `['mtd_ret', 'ts_peaks_20']`. The parent repo's
  suite is the launcher's.

## Review loop

Five rounds, each a fresh read-only `Explore` subagent with the Fletcher
persona, the ask verbatim and the file list; every verdict is quoted in full in
`01-ts-peaks-20.md`.

* Round 1 **PASS** (5 MINOR) — all prose: a self-contradicting value count, a
  knob whose docstring described behaviour its code did not have, an
  unmeasured "uniquely", a 16-digit float nobody printed, a digit-exact pin in
  a file that bands such counts.
* Round 2 **REVISE** (1 MAJOR) — the Cost prose claimed O(n) memory while
  `bad = (windows < 0).any(axis=1)` allocated a `(rows, 16)` bool temporary.
  The module was changed to `windows.min(axis=1) < 0` and the memory
  re-measured.
* Round 3 **REVISE** (1 MAJOR) — the replacement measurement ran on an
  all-zero flag array, so the equivalence check could not have failed. `cost()`
  now builds the module's own three-valued flags (census printed) and asserts
  the retyped copy reproduces the shipped column.
* Round 4 **PASS** (3 MINOR, 3 NIT) — absolutes one bar wider than the
  measurement: "empties exactly 20 bars" (interior only) and "bit-for-bit vs
  the prototype" (clean data only). Both scoped, both now measured at the
  edges; a missing `mutant == "forward_leg"` guard restored.
* Round 5 **PASS** (4 NIT) — lint only. Applied.

⚠ **Round 5's four NIT fixes landed after the last gate and are unreviewed.**
They are prose-only (a banded wall-time cell, two re-wraps, a deleted
duplicate sentence, an §A2 qualifier); the suite was re-run afterwards with
the numbers above.

## Follow-ups

1. **Gate E** on `pandas_ta.statistics.ts_peaks_20`, then the ledger row and
   the real-data Gate C counts — the launcher's, then a receipt session's. The
   screen's 0.2453 vs `BB_Lower` is indicative only: it was taken on the
   prototype by a different harness run.
2. **Owner's call, out of scope here:** `pandas_ta/core.py:691-692` mutates the
   global `Category` (it `.remove()`s excluded names from the list
   `_indicators_by_category` returns by reference), so a category-mode
   `strategy()` run deletes three names from `Category` for the rest of the
   process. Measured in this session by running
   `tests/test_wiring_accessors.py` before `tests/test_altport2_ports.py`:
   "Category total 322, expected 325". The suite's own ordering hides it.
