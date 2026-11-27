# Task: rd-lh-run-182

**Status:** PASS (round 1)

## Implementation summary

Ported issue #182's `rd_lh_run` candidate — run length of consecutive lower highs,
`n_t = n_{t-1} + 1 if high_t < high_{t-1} else 0` — as `pandas_ta/trend/rd_lh_run.py`, built
on `pandas_ta.ml.companions.ml_bars_since` the same way the sibling `range_compress_run`
(volatility) is: flip the condition (`~lower_high`), since "bars since the flag last fired"
is exactly the issue's recursion. Bar 0 reads 0 (not NaN, unlike `range_compress_run`, since
this port's condition is a direct value comparison, not a subtraction) — matches the issue's
own screen prototype (`docs/issues/screen/ind_screen_r6.py`'s `run_length(h < h.shift(1))`).
Wired into `pandas_ta/trend/__init__.py`, the `Category` dict (`pandas_ta/__init__.py`), and
the `df.ta.rd_lh_run()` accessor (`pandas_ta/core.py`). Category: trend (nearest comparator
`HIGHER_HIGH` lives in `pandas_ta.trend.bos`; `short_run`/`long_run` are the same
run-length-of-a-condition shape already in trend).

Wrote `tests/test_rd_lh_run.py` (17 tests): correctness against an independent plain-Python
loop and a hand-computed sequence (Gate A), a future-splice sweep plus a `high.shift(-1)`
look-ahead mutant caught via paired extreme-future perturbations (Gate B — a single random
future only caught it at 16/31; pinning one future far above and one far below guarantees
31/31), bit-identical scale invariance under x8/x64/x10/x3.7 (Gate D — measured 0 exact
consecutive ties in `high` on the synthetic walk, so no tolerance band was needed, unlike
`range_compress_run`'s subtraction-based tie case), reachability/cap/edge-case/wiring tests.

Measured all numbers via `docs/measure_rd_lh_run.py` (Gates A/B/C/D) and
`docs/measure_rd_lh_run_cpu.py` (CPU-feature variant, `AVX512F AVX512_SKX AVX2 FMA3`
disabled — 17 passed) before writing `docs/RdLhRunMeasured.md`. Updated the counters this
port moves: `CATEGORY_TOTAL` 416→417 and `CATEGORY_BUCKETS["trend"]` 70→71
(`tests/test_altport2_ports.py`), README's three counts (417 registered / 425 callable /
trend (71)), `docs/IndicatorDictionary.md` (regenerated, `python docs/gen_indicator_dictionary.py`),
`docs/MLCompanionContract.md` (761→762 tagged, 59→60 `ORD`).

Gate E and the whole-suite runs are explicitly out of scope for this session (the launcher
runs them); `docs/RdLhRunMeasured.md`'s Gate E section says "pending, run by issue-solver
after this session". Verified with the issue-solver's required subset:

```
python -m pytest -q tests/test_rd_lh_run.py tests/test_readme_counts.py \
    tests/test_altport2_ports.py tests/test_wiring_accessors.py \
    tests/test_ml_companions.py tests/test_gate_e_ledger.py \
    tests/test_pine_coverage_csv.py tests/test_prose_counts_match_the_csvs.py
```

**1,731 passed, 7 skipped, 1 failed** — the one failure,
`test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`, is expected per the
issue-solver's own rules (no ledger row yet) and not a finding.

## Assumptions

- **Category = trend** (not stated by the issue): chosen because the issue's own Gate E
  comparator, `HIGHER_HIGH`, is a `pandas_ta.trend.bos` column, and this fork's other
  run-length-of-a-condition ports in the same SHAPE (`short_run`, `long_run`) are already in
  trend. Conservative reading: the issue left category unstated, so the category closest to
  the issue's own named comparator and the existing sibling pattern was used, not guessed
  arbitrarily. Logged here per the issue-solver's "most conservative reading" rule (no
  AskUserQuestion available in this session).
- **`cap` default 100** (not in the issue's own unbounded formula): matches the ML-feature
  contract's established convention for every other run-length port in this fork
  (`range_compress_run`'s own `cap`, `ml_bars_since`'s own default) — an uncapped counter on
  an unboundedly-growing condition would dominate every split it appears in.

## Review round 1

```
VERDICT: PASS
FINDINGS:
  (none)
SUMMARY: Gate A checks out by hand and by independent-loop test: lower_high = high <
high.shift(1) evaluates False at bar 0 (value < NaN is False, not NaN), so fired =
~lower_high is True at bar 0, groups[0] = 1 (never 0), meaning ml_bars_since's "since[groups
== 0] = nan" branch never fires here -- bar 0 is 0 by construction, exactly as the docstring
claims, and matches the screen prototype's own run_length(h<h.shift(1)) bar-0 value of 0.0
(verified by reading docs/issues/screen/ind_screen_r6.py directly). Gate B's paired-extreme-
futures trick is sound: pinning one future high far above and one far below the real value at
bar J guarantees one of the two disagrees with the base's actual (unknown) boolean at bar
J-1, so the mutant (high.shift(-1)) is caught at all 31 swept J -- rerunning
docs/measure_rd_lh_run.py reproduces "real module leaked at 0 of 31; mutant leaked at 31 of
31" to the digit, matching the test's hits==len(OFFSETS) assertion and the Measured.md prose
exactly. Gate D's "0 exact ties" claim is honestly scoped to the measured synthetic walk, not
oversold as universal, consistent with the sibling range_compress_run precedent that does
need a tie tolerance for its subtraction-based comparison. Wiring (Category, core.py
accessor, trend/__init__.py import) and every counter (CATEGORY_TOTAL 417, trend bucket 71,
README's 417/425/71, IndicatorDictionary's 419/71/ORD row, MLCompanionContract's 762
tagged/60 ORD, which sums correctly: 137+387+108+60+46+2+22=762) are internally consistent
and were confirmed, not just diffed. Running the exact required pytest invocation reproduces
1731 passed / 7 skipped / 1 failed (the one failure being the expected, pre-authorized
test_gate_e_ledger.py ledger-row gap), and both docs/measure_rd_lh_run.py and
docs/measure_rd_lh_run_cpu.py reproduce every number in RdLhRunMeasured.md bit-for-bit
including the module sha1. The diff touches only the files in the allowed scope with no stray
edits or deletions. Nothing here needs a fix.
```
