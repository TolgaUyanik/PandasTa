# Task — c22_whiten_timescale (issue #139)

## Implementation log

Ported catch22's `FC_LocalSimple_mean1_taurat` as `c22_whiten_timescale`
(`pandas_ta/statistics/c22_whiten_timescale.py`): over a rolling window of
`length` (default 100) one-bar simple returns, take the first difference
(the residual of a trivial "forecast = previous point" predictor, hctsa
train length 1), then report `tau(residual) / tau(raw window)`, where
`tau` is hctsa's `CO_FirstZero` — the first lag the sample ACF crosses
zero or below, read off one FFT per window (same "biased" estimator and
divisor this fork's `c22_acf_first_min`/`firstzero_ac` already use on the
same returns window).

An initial build scanned only the bare INTEGER crossing lag and read
exactly 1.0 on every sampled window of a synthetic walk frame, while
`pycatch22.catch22_all(...)["FC_LocalSimple_mean1_taurat"]` (the GPL-3.0
reference, used only for black-box measurement, never imported by shipped
code) read a tight band around 0.70–0.73 on the same windows — a value no
integer scan can produce. Re-derived `_first_zero_lag` to report the
LINEARLY INTERPOLATED fractional crossing point instead
(`tau = (k-1) + acf(k-1)/(acf(k-1)-acf(k))`), which closed the gap: 0 of
8,400 sampled windows across six synthetic frames disagree with the
reference beyond 1e-9 (worst 1.6e-12).

Measured Gates A–D and G via `docs/measure_c22_whiten_timescale.py`
(sections A, B, C, D, G, opt-in P, plus diagnostics Y and Z that found and
then confirmed the interpolation fix), both at default numpy CPU dispatch
and under `NPY_DISABLE_CPU_FEATURES="AVX512F AVX512_SKX AVX2 FMA3"`
(`docs/measure_c22_whiten_timescale_cpu.py`). Wrote 38 tests
(`tests/test_c22_whiten_timescale.py`): an independent double-loop oracle,
closed forms (alternating returns, a ramp that differences to a constant
and blanks), four look-ahead mutants, the shared floor rule on both
series, scale-free checks (bit-identical x8/x64; tolerance-bound x10/x3.7/
x0.1/x1.0000001 and chunk-boundary float noise, since this column's output
is a continuous interpolated ratio rather than a discrete lag like its
siblings), and edge cases.

Wired all five touch points: `pandas_ta/statistics/__init__.py` export,
`pandas_ta/__init__.py` `Category["statistics"]`, `pandas_ta/core.py`
accessor, the test file, and the module itself. Bumped README's three
counts (420→421 Category, 428→429 accessor, statistics 85→86) and its
category list, `tests/test_altport2_ports.py`'s `CATEGORY_TOTAL`
(420→421), regenerated `docs/IndicatorDictionary.md` via its own generator,
and bumped `docs/MLCompanionContract.md`'s tagged-column counts (765→766 /
390→391 `SF`) with a new log entry. Wrote `docs/C22WhitenTimescaleMeasured.md`
with the Gate E section as the required "Gate E: pending, run by
issue-solver after this session" and did not touch
`docs/gate_e_ledger.csv` (the launcher's job).

Ran the required test subset:
`python -m pytest -q tests/test_c22_whiten_timescale.py
tests/test_readme_counts.py tests/test_altport2_ports.py
tests/test_wiring_accessors.py tests/test_ml_companions.py
tests/test_gate_e_ledger.py tests/test_pine_coverage_csv.py
tests/test_prose_counts_match_the_csvs.py` → 1,784 passed, 7 skipped, 1
failed (`test_every_indicator_that_needs_a_row_has_one`, expected and
documented, not a finding).

Committed as `4127c5c` on `issue-139-c22-whiten-timescale`.

## Review round 1 — Fletcher (full persona, `Explore` subagent, read-only, independently re-ran the harness and pytest subset, verified the interpolation math by hand, and checked wiring/scope/receipt honesty against the files directly)

```
VERDICT: PASS
FINDINGS:
  - (none)
SUMMARY: The interpolation math checks out -- `j`/`k-1`/`k` indexing in
`_first_zero_lag` (c22_whiten_timescale.py:91-98) is exactly right, `denom`
is provably positive whenever `found` is true, and the floor logic catches
both the flat-raw-window and flat-residual-ramp failure modes. Every
number in the receipt reproduced bit-for-bit when I re-ran
`measure_c22_whiten_timescale.py A/B/C/D/G/P` and the mandated pytest
subset (1,784 passed / 7 skipped / 1 expected ledger failure) myself
against the actual GPL-3.0 `pycatch22` as a black box, not a
self-comparison. Wiring (export, Category, core.py accessor,
README/IndicatorDictionary/MLCompanionContract counts, CATEGORY_TOTAL) is
complete and mechanically consistent, scope stayed inside the allowed
files, and the ledger was correctly left untouched. This is what the
other 17 of 18 candidates should have looked like before review.
```

No fixes needed. Round 1, PASS.
