# Median Absolute Daily Log Return — measured (`tf_median_absdiff_20`)

**Status: BUILT 2026-10-30. Gates A, B and D cleared; C synthetic only; Gate E pending, run by
issue-solver after this session; F not yet confirmed by both repos (see below).**
If Gate E strikes it, revert and keep this file as the receipt.

Column `MEDABSDIFF_20`: the rolling 20-bar median of the absolute bar-to-bar log return — a
robust (outlier-resistant) realised-volatility measure, in the same spirit as `natr` but built
from the median instead of a mean/EMA. Category `volatility`.

## Source

TSFEL (BSD-3-Clause), `features.py median_abs_diff: median(|diff(x)|)` — the median absolute
first difference of a generic 1-D signal. Issue #118 picks the scale-free form: `x` = log(close),
so `diff(x)` is the bar-to-bar log return. TSFEL is not a dependency of this package, dev or
otherwise — its existence and licence are cited, per the issue ("Library code (TSFEL,
BSD-3-Clause): existence, not evidence"), but the library itself is neither vendored nor
installed nor run as an oracle here, so Gate A is checked against an independent loop written
from the formula text, not against TSFEL's own code — the same situation as `pfe` against
Hannula's published formula, and `tf_centroid_20` against TSFEL's `calc_centroid`.

Prototype: `docs/issues/screen/ind_screen_r2.py`, candidate `tf_median_absdiff_20`:

```python
np.log(c).diff().abs().rolling(20).median()
```

The port computes the log-return as `log(close / close.shift(1))` rather than
`log(close).diff()` — algebraically identical, but the ratio form is exact under a power-of-two
price rescale in floating point, where the two-log-and-subtract form is not (see Gate D below).
`length` replaces the hard-coded 20; everything else is the formula verbatim.

Measured on the prototype (2026-10-24, from the issue): Gate E max |ρ| 0.7422 vs `natr`
(compute_all, n = 397,069), top-5 per-frame max median 0.7337 → SHIP band. That run used
`ind_screen_r2.py`, not this module; **Gate E must be re-run on the port** per CLAUDE.md.

## Gates

Environment: Python 3.11.2, pandas 2.3.3, numpy 1.26.4 (`python docs/measure_tf_median_absdiff_20.py`).
Synthetic numbers are a 1,200-bar GBM walk, σ = 0.02, seed 11, 0.05 tick, the same walk
`tests/test_tf_median_absdiff_20.py` uses.

| Gate | Result |
|---|---|
| A Correctness | Checked against an independent loop written from the TSFEL formula text (`test_matches_an_independent_loop`, 400 bars, sorted-window median, max\|diff\| < 1e-9) and a constant-log-return hand check (every window's median equals that one constant, `test_constant_log_return_reads_that_value`). No published TSFEL source line is cited (library not installed; see Source). |
| B Causality | 31-offset future-perturbation sweep (`test_real_module_never_reads_the_future`): the real module leaks at 0 of 31 offsets. The catching mutant shifts the log-return series 10 bars into the future (`importlib`-read source, `exec`'d in memory) and is caught at 31 of 31 (`test_mutant_is_caught`). ⚠ A naive 1-bar-ahead shift is a genuine look-ahead (proved live — differs from the real module) but is caught at only 17 of the same 31 offsets, documented and pinned by `test_one_bar_future_read_is_only_partially_caught`: median is a robust statistic, so replacing exactly one of the 20 window values changes the median's rank only part of the time. A test that checked a single offset with the naive mutant would have better-than-even odds of reading a real leak as "causal" — the CANDLE-1 / `smc_sweep` escape, reproduced here by construction rather than found by accident, which is why the 10-bar mutant is the one `test_mutant_is_caught` requires at 31/31. |
| C Reachability | Synthetic only: on the seed-11 walk, 1,180 of 1,200 bars finite (20-bar warm-up), all 1,180 non-zero, range [0.004214, 0.025018], mean 0.013706. **Real-data counts owed** — the BIST frames are in the Backtesting repo, out of scope for this session. |
| D Scale-free | ×8 and ×64 bit-identical with matching NaN masks — achieved by computing `log(close / close.shift(1))` as a single log of a ratio (exact under a power-of-two rescale in IEEE float) rather than `log(close).diff()`, whose two separate logs cancel the `log(k)` term only to within a few ulp, not bit-exactly. The rejected `log(close).diff()` form is kept as a non-shipped comparison block in `docs/measure_tf_median_absdiff_20.py` (run it to reproduce): max|diff| 8.882e-16 at ×8, 1.776e-15 at ×64 — small, but not the exact 0 the shipped ratio form achieves, which is what CLAUDE.md's Gate D asks for. ×10 and ×3.7 within 2.2e-16 (tighter than CLAUDE.md's 1e-12 bar, because the ratio form has no subtraction to lose precision in). `0 < fires < n` (1,180 of 1,200) plus > 100 distinct values and a non-constant column (`test_column_is_not_constant`), so a degenerate pass cannot sneak through. A flat price run (all-zero log-return window) is pinned to read exactly 0, not NaN or an error (`test_flat_price_run_reads_zero_not_nan`) — unlike `tf_centroid_20`, there is no division here, so no NaN guard is needed for this case. |
| E Attribution | **Pending, run by issue-solver after this session.** From `../Backtesting/Backtesting`: `python scripts/analysis/gate_e_overlap.py run --module pandas_ta.volatility.tf_median_absdiff_20 --name tf_median_absdiff_20`, then record with `python docs/gate_e_ledger.py record`. |
| F Suites | See below. |

### Gate F, this repo (measured 2026-10-30, branch `issue-118-tf-median-absdiff-20`)

`python -m pytest -q`: **3 failed, 3272 passed, 83 skipped.** The 3 failures, all pre-existing and
unrelated to this port:

* `tests/test_pine_coverage_csv.py::test_audited_rows_carry_their_evidence` — the known break
  recorded in `CLAUDE.md` (the untracked `docs/pine/` corpus).
* `tests/test_altrepo_talib_csv.py::test_regenerating_reproduces_the_committed_rows` — needs the
  sibling `../AlternativeRepos` checkout, not present here; CI deselects it by name.
* `tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one` — **expected for
  this port**: `tf_median_absdiff_20` is new, not in `docs/gate_e_grandfathered.json`, and has no
  ledger row yet because Gate E is pending. The same test would have failed on `pfe`,
  `kalman_trend`, `range_compress_run` and `tf_centroid_20` before their rows were recorded; this
  one clears once the Gate E receipt session runs `docs/gate_e_ledger.py record`.

`tests/test_tf_median_absdiff_20.py` itself: 14 passed. The Backtesting repo's suite was not run
here — Gate E and both suites are run by the issue-solver launcher after this session.

**Disclosed, pre-existing issue found while running tests, not introduced by this port:**
`pandas_ta.core.AnalysisIndicators.strategy()` (`pandas_ta/core.py`, `_indicators_by_category`)
returns the LIVE list object `Category[name]`, and `strategy(category, ...)` then does
`[ta.remove(x) for x in excluded if x in ta]` directly on it — a category sweep permanently
removes any of its own members that also sit in the hard-coded `excluded` list (e.g. `trend`
loses `long_run`/`short_run`, `momentum` loses `td_seq`) for the rest of the process. Measured:
running `tests/test_wiring_accessors.py`'s `test_each_previously_broken_category_runs` before
`tests/test_altport2_ports.py`'s `test_the_category_count_moved_by_exactly_three` in the same
session drops the live `Category` total from 238 to 235 and makes the pinned-count test fail —
purely an artifact of invoking those two files in that explicit order; the default alphabetical
full-suite run (`test_altport2_ports.py` before `test_wiring_accessors.py`) does not hit it, which
is why the whole-suite number above is clean. Out of scope for this port (unrelated file,
pre-existing on `dev`, not something this session introduced or was asked to fix) — recorded here
for whoever next touches `strategy()` or `Category`-pinned tests.

## To close

1. Run Gate E on the port (not the prototype) and record it with `docs/gate_e_ledger.py record`,
   which also clears the `test_gate_e_ledger.py` failure above.
2. Apply CLAUDE.md's thresholds (SHIP < 0.76, DISCLOSE 0.76–0.80, DISCLOSE_GAP 0.80–0.90, STRUCK
   ≥ 0.90 pooled or per-frame median). The prototype's screen-level measurement (0.7422 vs `natr`)
   sits just inside SHIP; the port must be re-measured on its own, since the prototype and the
   module compute the log-return differently in floating point (see Gate D). On a revert, delete
   the module, its exports, `Category` entry, accessor, tests, and the README/`IndicatorDictionary`/
   `MLCompanionContract` counts added here, and keep this file.
3. Fill Gate C from the same real frames the Gate E run touches.
4. Run both repos' suites.
