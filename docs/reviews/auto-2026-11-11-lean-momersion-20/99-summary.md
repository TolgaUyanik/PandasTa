# Run summary — `/brutally-honest-review --auto`, 2026-11-11

| task | status | rounds | files touched | follow-ups |
|---|---|---|---|---|
| `lean-momersion-20` (issue #86) | **PASS** at round 4 | 4 (R1 REVISE, R2 REVISE, R3 REVISE, R4 PASS), plus the round-4 MINOR/NIT fixes applied after the PASS and verified by re-running the harness and both pytest commands | **new:** `pandas_ta/momentum/lean_momersion_20.py`, `tests/test_lean_momersion_20.py`, `docs/measure_lean_momersion_20.py`, `docs/LeanMomersion20Measured.md`, this run folder · **modified:** `pandas_ta/momentum/__init__.py`, `pandas_ta/__init__.py`, `pandas_ta/core.py`, `README.md`, `docs/MLCompanionContract.md`, `docs/IndicatorDictionary.md`, `tests/test_altport2_ports.py` | Gate E and Gate C's real-data counts are owed: the launcher runs Gate E, a receipt session records the `docs/gate_e_ledger.csv` row and writes the numbers into `docs/LeanMomersion20Measured.md` |

## What the rounds were about

Every REVISE round turned on the same thing, and none of them on the
indicator's mathematics:

* **R1 CRITICAL** — a `length=2.9` row in the receipt's parameter-guard table
  typed from expectation while the harness printed the opposite four lines
  away. Fixed and pinned.
* **R2 CRITICAL** — the round-1 fix for the ×10/×3.7 scale claim measured the
  right number and narrated the wrong cause (a binade bound stated as [1, 2)
  that is really (1/2, 2), and a "the ratio can round to exactly 1.0" that
  the same script's output disproves). Mechanism replaced with FUSION and the
  fused-pair counts measured.
* **R3 CRITICAL/MAJOR** — the refuted sentence survived in two more places
  (the harness's `ulp_walk` docstring, the test header). Both fixed; the
  k = 10 example narrowed to the binade where it actually holds.
* **R4 PASS** — three MINORs and four NITs, all applied: the "same walk"
  mislabelling of the seed-55 grid frames, the missing step in the `g = 2`
  fusion argument, a status header that over-claimed Gate C, and four
  smaller prose/dead-code items. The AR(1) persistence rows were
  re-measured with common random numbers, which moved the φ = +0.4 median
  from 60 to 65.

## State at the end of the run

* `python -m pytest tests/test_lean_momersion_20.py -q` → **104 passed**.
* `python -m pytest -q` → **3 failed, 5562 passed, 83 skipped**. The three:
  the two `CLAUDE.md` "Known breaks" (`test_altrepo_talib_csv`'s
  `../AlternativeRepos` dependency, `test_pine_coverage_csv`'s citation into
  the untracked `docs/pine/`) and
  `test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`,
  which reports `['lean_momersion_20', 'mtd_ret']` — the owed Gate E row and
  one owed before this branch. CI into `dev` skips the last under
  `GATE_E_PENDING_OK=1`.
* `docs/gate_e_ledger.csv` is untouched, as the session rules require.
* Verdict on the column itself: **not decided here.** Gates A–D are through
  on synthetic frames; whether `LEAN_MOMERSION_20` ships or is reverted is
  Gate E's call, on the launcher's run.
