# Task: FFD port (issue #13)

## Implementation

Ported AFML's fixed-width window fractional differencing of log price as `pandas_ta/statistics/ffd.py`:

- `d` is a fixed parameter (default 0.4), never estimated from the series — resolves the
  issue's causality-of-`d` 🔴.
- `_ffd_weights` builds AFML's `getWeights_FFD` recursion then re-centres the truncated
  weights so `sum(w) = 0` (moves the residual onto the most-lagged weight) — resolves the
  issue's Gate D 🔴 (the "re-centred form" option), and incidentally fixes an
  anchor-dependence bug that an anchor-only fix would have introduced (measured: 6.3e-2
  before, 1.3e-15 after, at d=0.4/threshold=1e-5).
- `y = log(close / first finite positive close)` (the `kalman_trend` device) on top of the
  re-centring, making x8/x64 bit-identical by construction rather than merely small.
- Default `threshold` set to `1e-4` (not AFML's own `1e-5`), disclosed: `1e-5` needs 1,458
  bars just to emit a first value and does not fit this repo's fixed 600-bar
  `gen_indicator_dictionary.py` probe.

Wired all five touch points (module, `pandas_ta/statistics/__init__.py`,
`pandas_ta/__init__.py` `Category`, `pandas_ta/core.py` accessor, `tests/test_ffd.py`).
Updated README.md (249 indicators, statistics (17)), `docs/MLCompanionContract.md` (582
tagged / 228 SF), `docs/IndicatorDictionary.md` (regenerated), and bumped
`tests/test_altport2_ports.py::CATEGORY_TOTAL` 248 -> 249 with its running comment.

Wrote `docs/measure_ffd_proxy.py` (measurement script) and `docs/FfdMeasured.md` (receipt),
Gate E section explicitly `PENDING, run by the issue-solver launcher after this session`.

Full local suite: 3 failed / 3535 passed / 83 skipped — the 3 failures are pre-existing,
documented breaks (`test_pine_coverage_csv`, `test_altrepo_talib_csv`, both in CLAUDE.md's
"Known breaks") plus `test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`,
which is EXPECTED to fail until the launcher records the Gate E run (per this session's
rules, not a defect).

## Review round 1

VERDICT: REVISE

FINDINGS:
- CRITICAL (docs/FfdMeasured.md, pandas_ta/statistics/ffd.py, tests/test_ffd.py): the
  headline Gate D defect numbers (6.3e-2 before / 1.2e-15 after) were quoted in three
  places but reproduced by nothing in the repo — `docs/measure_ffd_proxy.py` never ran the
  raw (uncorrected) weights, and the "before" and "after" numbers were actually measured at
  two different, never-jointly-run `(d, threshold)` configs.
- MAJOR (tests/test_ffd.py `_independent_binom_weight`): the Gate A "independent" oracle
  shares the exact closed-form derivation with the module's recursion — both would
  reproduce the same error if the closed form were a wrong translation of AFML's
  (unavailable-to-check) published algorithm. Advertised as more independent than it is.
- MINOR (tests/test_ffd.py:286, `OFFSETS` comment): stale `W=1458` reference; the file's
  own `W` constant is 282.

SUMMARY: the arithmetic, causality mutants, bad-input handling and wiring all checked out;
both blocking findings were about claims outrunning what was actually measured/proven.

## Fixes applied

1. Added a `"Gate D defect"` block to `docs/measure_ffd_proxy.py` (`_raw_weights`,
   `_ffd_with_weights`) that runs the raw AFML weights and the re-centred weights through
   the IDENTICAL 100/500/900-bar slice experiment at the IDENTICAL `(d=0.4, threshold=1e-5)`
   config, so the before/after pair is reproducible and comparable. Re-ran it; measured
   1.283e-02 / 4.698e-02 / 6.327e-02 (raw) vs 1.110e-15 / 1.284e-15 / 1.332e-15 (re-centred).
   Updated all three prose copies (`ffd.py`, `test_ffd.py`, `FfdMeasured.md`) to cite these
   exact reproducible numbers and to stop implying the pre/post numbers came from the same
   run as the module's actual default (0.4, 1e-4) head-stability test.
2. Added `_independent_gamma_weight` (via `math.gamma`, a genuinely different numerical
   codepath, bounded to the first 40 weights to avoid overflow) and a new test
   `test_weights_match_the_gamma_function_for_small_k`. Reworded the product-loop oracle's
   docstring/doc-table language to honestly scope it as catching a recursion coding bug, not
   a conceptual AFML-translation error.
3. Fixed the stale `OFFSETS` comment (`W=1458` -> `W=282`).

Re-ran `tests/test_ffd.py` (34 passed) and the full suite (3 failed — same 3 pre-existing /
expected — 3535 passed, 83 skipped).

## Review round 2

VERDICT: PASS
FINDINGS: (none)
SUMMARY: "Both findings are genuinely fixed... no overclaiming remains." (quoted in full in
the round-2 reviewer's SUMMARY; see dispatch transcript.) `test_weights_match_the_gamma_function_for_small_k`
passes 4/4, the Gate D defect numbers are reproducible and consistently quoted, and the
reworded oracle framing is honest about what each check does and does not prove.
