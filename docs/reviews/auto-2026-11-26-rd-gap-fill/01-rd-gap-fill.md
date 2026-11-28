# RD-GAP-FILL — same-day gap fill, signed

Task text (verbatim, see `00-manifest.md`): port the indicator of issue #174 through
Gates A-D, the wiring, the tests and `docs/RdGapFillMeasured.md`, per the issue and the
issue-solver's own system-prompt rules (Gate E and whole suites deferred to the launcher).

## Execution log

- Read `docs/issues/screen/ind_screen_r6.py`'s `rd_gap_fill` candidate (lines 102-107) to
  cross-check the issue's own restated formula, without treating the prototype as Gate A's
  source (the issue's own instruction).
- Read the already-shipped twin `rd_gap_fill_rate_60` (issue #165, statistics) and sibling
  signed/binary candle ports (`rd_horseshoe`, `rd_outside_bar`) as structural templates.
- ASSUMPTION: placed `rd_gap_fill` in `candles`, matching the sibling signed flags, not
  `statistics` where the rolling-share twin lives — logged in `00-manifest.md` since
  AskUserQuestion is unavailable in this headless session.
- ASSUMPTION: kept `min_gap` as a parameter (default 0.003), matching the twin's own
  convention, rather than hard-coding the issue's 0.3%.
- Wrote `pandas_ta/candles/rd_gap_fill.py` (Gate A/B/D arguments in the docstring),
  wired all 5 touch points (module, `pandas_ta/candles/__init__.py`,
  `pandas_ta/__init__.py` Category, `pandas_ta/core.py` accessor, `tests/test_rd_gap_fill.py`).
- Wrote `tests/test_rd_gap_fill.py` (18 tests initially): hand-derived 5-bar fixture
  (filled up-gap, unfilled down-gap, sub-threshold, filled down-gap), no-gap-ever case,
  warm-up, column-name defaults/custom, offset, fillna, short-input, causality
  future-splice sweep (28 J) + live mutant, Gate D x8/x64 bit-identical + x10/x3.7
  tolerance, both-signs reachability, wiring.
- Ran the new test module standalone: 18 passed. Hit the `test_lookahead_mutant_is_caught`
  assertion with the real measured number (9 of 28, not an assumed "majority") and
  corrected both the test and the module's own Gate B docstring paragraph to match.
- Updated `docs/gen_indicator_dictionary.py`'s output, `README.md` (400→401 registered,
  408→409 callable, candles (9)→(10)), `tests/test_altport2_ports.py`
  (`CATEGORY_TOTAL` 400→401), `docs/MLCompanionContract.md` (745→746 tagged, 106→107
  `BIN`).
- Wrote `docs/measure_rd_gap_fill.py` and ran it to get the real Gate A/B/C/D numbers
  (not asserted from memory) and `docs/measure_rd_gap_fill_cpu.py` for the
  AVX512F/AVX512_SKX/AVX2/FMA3-disabled variant.
- Wrote `docs/RdGapFillMeasured.md` with those measured numbers; Gate E section reads
  "pending, run by issue-solver after this session" per the system-prompt override.
- Ran the required Gate F subset: 1,604 passed, 7 skipped, 1 expected failure
  (`test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`, owed until the
  launcher's Gate E run).

## Review round 1

VERDICT: PASS
FINDINGS:
  - severity: MINOR
    location: tests/test_rd_gap_fill.py:57-76 (`_hand_rows`) and the Gate A section it backs
    problem:  No test exercises the `>=`/`<=` boundary itself (`gap_pct` exactly equal to `+min_gap` or `-min_gap`). The hand fixture only covers a gap safely above threshold (bar1, +0.5%), safely below (bar3, +0.1%), and comfortably past threshold on the down side (bar2, bar4, -1.59%/-1.30%). The spec's inclusive `|gap| >= 0.3%` is read correctly in the code (`gap_pct >= min_gap` / `gap_pct <= -min_gap`), but nothing pins that the boundary itself is included rather than excluded.
    fix:      Add a bar to `_hand_rows()` (or a new small fixture) where `open / prev_close - 1` is exactly `0.003` (e.g. `prev_close=100.0`, `open=100.3`) with `low` set to reach `prev_close`, and assert the output is `+1.0` (not `0.0`), proving the comparison is inclusive as coded.
  - severity: MINOR
    location: tests/test_rd_gap_fill.py:112-115 (`test_custom_min_gap_in_name`)
    problem:  The only test touching a non-default `min_gap` checks the column-name string, not that the parameter actually changes which bars fire. A regression that ignored `min_gap` in the comparisons (while still formatting it into the name) would pass every test in this file.
    fix:      Add a test that runs `rd_gap_fill` on a frame with a gap sized between two thresholds (e.g. a 0.5% gap that fills) at `min_gap=0.003` (fires) and `min_gap=0.01` (must read `0.0`, not `1.0`/`-1.0`), asserting the two outputs differ at that bar.
SUMMARY: This port is clean. I hand-recomputed bar1/bar2/bar4 of the fixture against the raw OHLC numbers and the module's actual `.shift(1)`-only arithmetic, and it matches the asserted `[1.0, 0.0, 0.0, -1.0]` exactly; I re-ran `docs/measure_rd_gap_fill.py`, the full Gate-F test subset, and the CPU-feature variant myself, and every number quoted in `docs/RdGapFillMeasured.md` (Gate A values, 648/1599 with 318 up/330 down, the 215-272 range and the seed-103/106 split across ten seeds, 0 mismatches at x8/x64/x10/x3.7, 0/28 real leaks vs 9/28 mutant leaks, the module sha1, 1,604 passed/7 skipped/1 failed, 18 passed standalone and under the CPU variant) reproduced bit-for-bit. Wiring across the five touch points is alphabetically consistent and the core.py accessor forwards `min_gap` correctly. All five counter bumps (`CATEGORY_TOTAL`, README's three numbers, `MLCompanionContract`'s 745→746/106→107) add up by exactly one, and the `IndicatorDictionary.md` diff is scoped to precisely what the receipt claims. Gate E is correctly left pending per the session's actual job, the expected ledger-test failure is the only failure, and there's no sign of a whole-suite run, pip/gh/docker use, or any file outside the stated 12. The only real gaps are two missing test cases (exact-threshold boundary, behavioral proof that `min_gap` isn't just cosmetic) — both MINOR, neither blocks.

### Fixes applied (polish, not required for the PASS gate)

- Added `test_gap_exactly_at_threshold_counts_as_a_gap` — proves the inclusive `>=`
  boundary with binary-exact values (`min_gap=0.25`, `open/prev_close = 1.25`), avoiding a
  false sense of precision from a decimal threshold that cannot be hit exactly in binary
  float.
- Added `test_min_gap_parameter_actually_changes_firing` — proves `min_gap` gates the
  comparisons, not merely the column name.
- Re-measured and updated `docs/RdGapFillMeasured.md`'s Gate A section and Gate F counts
  (18 → 20 tests, 1,604 → 1,606 passed) to the new real numbers.

## Outcome

PASS (round 1). Two MINOR findings addressed as polish; no REVISE round needed per the
gate rule (CRITICAL/MAJOR → REVISE; MINOR/NIT → PASS).
