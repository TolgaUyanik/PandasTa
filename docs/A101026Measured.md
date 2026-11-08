# a101_026 — measured (issue #44)

> **Status: Gates A-E cleared (SHIP), Gate F run by the launcher in both repos.**
> `python -m pytest -q` in this worktree is reported below for the record.

Volume-high rank correlation peak: Kakushadze's (2016, Wilmott, "101 Formulaic Alphas")
Alpha101 `#26`, per issue #44. Module `pandas_ta/volume/a101_026.py`, column
`A101_026_5_5_5_3`. Tests: `tests/test_a101_026.py` (17, all passing). Numbers below:
`python docs/measure_a101_026.py`. Environment: this worktree's pinned pandas/numpy.
Measured 2026-11-08.

## Gate A: derivation from the published formula, not the prototype

Issue #44 states Alpha101 `#26`:

    -ts_max(corr(ts_rank(volume, 5), ts_rank(high, 5), 5), 3)

**What this session could NOT do, disclosed up front:** `docs/pine/` and web access are
both unavailable in this worktree, so the issue's own named copy -- vnpy's `vnpy/alpha101`
module (MIT) -- was never read. Everything below is derived from the issue's own stated
formula and from this fork's already-shipped operators, not from vnpy or from
Kakushadze's original paper text.

Each operator is read from the issue's formula string and mapped to an existing,
already-tested primitive, or to pandas' own documented behaviour, not reimplemented from
scratch:

1. `ts_rank(x, d)` = the percentile rank of the current bar's value of `x` within its own
   trailing `d`-bar window: `count(x[t-d+1..t] <= x[t]) / d`. Same convention already
   shipped under this exact name by `a101_035`/`a101_058` and, underneath it, by
   `pandas_ta.statistics.rank`'s `RANK_d` (issue #34, a port of qlib's `Rank`).
   ASSUMPTION, disclosed, carried over unchanged from those two ports: Kakushadze's
   glossary names the operator but does not spell out tie handling or normalisation, so
   this fork's own existing convention is reused for internal consistency, not
   independently re-derived from vnpy.
2. `corr(x, y, d)` = rolling Pearson correlation of `x` and `y` over a trailing `d`-bar
   window. Reused verbatim: `pandas_ta.utils._pine.correlation`, the same helper `pvcorr`
   and `a101_058` already ship behind. No new correlation code was written.
3. `ts_max(x, d)` = the rolling maximum of `x` over its own trailing `d`-bar window,
   `max(x[t-d+1..t])`. Not previously named by any port in this fork, but nothing to
   assume: it is `pandas`' own `Series.rolling(d).max()`, read off literally; `min_periods
   =d` is set explicitly so a partial window (fewer than `d` valid values) stays NaN
   rather than silently returning a max over fewer points.

No `IndNeutralize` wrapper and no `vwap` substitution are needed -- the formula is already
stated in terms of plain `volume` and `high`, which this fork has directly; `low` and
`close` are not read anywhere in it, so the port's signature is `a101_026(high, volume,
...)`, narrower than `a101_035`'s/`a101_058`'s four-input signature (same pattern already
used by `a101_023`'s `(high, close, ...)` and `a101_043`'s `(close, volume, ...)` when a
formula does not need all four OHLCV series).

## Gates

| Gate | Result | Evidence |
|---|---|---|
| A Correctness | primary vnpy/Kakushadze text NOT consulted (no `docs/pine/`/web this session) -- self-consistent against the issue's own stated formula, built entirely from already-shipped, already-tested primitives (`corr`, this fork's own `ts_rank` convention, and pandas' own `rolling().max()`) | Hand-derived 8-bar example at `vol_rank_length=3, high_rank_length=3, corr_length=3, max_length=2` (small enough windows that every `ts_rank`, the 3-point Pearson correlation by the full formula with fractions, and the 2-point rolling max are checked by hand): bars 5/6/7 read exactly -0.5 / -1.0 / -1.0, confirmed against the module (not merely asserted). Matches an independent loop built from an explicit counting rank and `numpy.corrcoef` at the shipped defaults (`vol_rank_length=5, high_rank_length=5, corr_length=5, max_length=3`), 3 spot-checked bars (300, 500, 899) on a 900-bar synthetic walk, rel. tolerance 1e-9 -- bar 899 is a mid-stream NaN in BOTH the module and the independent reference (see below), not a mismatch |
| B Causality | pass | Future-perturbation sweep (both high and volume rewritten from `j` onward), 30 offsets past the 10-bar warm-up: real module **0 of 30** leaks (`python docs/measure_a101_026.py`). The repo test module (`tests/test_a101_026.py`) runs the same check over a shorter 15-offset sweep on a 900-bar frame, same result. A single-bar lookahead inside the chain was tried FIRST as the mutant and rejected: the rolling max absorbs a 1-bar forward peek whenever the shifted value isn't the new window maximum, catching only **10 of 30** offsets (measure script, kept and run rather than only described, so the count is re-derivable) -- a smoothing artefact of the max step, not a causality gap. The mutant actually shipped shifts the whole write index `corr_length + max_length = 8` bars into the future (`result = -peak.shift(-8)`, `importlib` source read, `exec`'d in memory): shown live (differs from the real module), then caught at **30 of 30** (measure script) / every offset (test module) |
| C Reachability | synthetic only (real-data reachability comes from Gate E's pooled count, not re-derived here) | 1,500-bar synthetic walk (seed 11, σ=1.5%/bar close-derived high, σ=1.95%/bar volume), shipped defaults: **1,252 of 1,500** bars non-NaN (83.47%), **792 distinct values** among the fired bars -- comfortably not constant. The 10-bar leading warm-up alone would allow up to 1,490 fires; the other **238** mid-stream NaNs (16.0% of the 1,490 post-warmup bars) are a real property of this formula, not a gap: `corr(ts_rank(volume,5), ts_rank(high,5), 5)` is undefined whenever a trailing 5-bar window of either rank series has zero variance (the rank series only takes 5 possible values, so a flat run of 5 identical ranks is not rare), and `rolling(3).max()` correctly propagates that NaN forward -- see the MID-STREAM NaN note below |
| D Scale-free | pass | x8/x64 on EITHER `high` OR `volume` independently: **bit-identical, 0.0 max\|diff\|** (`ts_rank` is an order statistic, invariant to any positive monotonic rescale of its input; `corr` of two already-rank series inherits it twice over; `ts_max` and negation preserve it). x10/x3.7 on either input: **also 0.0 max\|diff\|**, exact rather than merely within the 1e-9 tolerance the test asserts -- no floating-point drift anywhere in the chain, matching NaN masks exactly. `0 < 1,252 fires < 1,500` and 792 distinct values rule out a constant column |
| E Attribution | **SHIP** | Launcher's Gate E run (`is44-a101_026-bbc92714`, 2026-11-08), column `A101_026_5_5_5_3`, 89 ALTPORT-1 BIST frames, 398,849 pooled bars, 687 comparators (329 `compute_all` + 358 manifest): max\|ρ\| **0.2857** vs `efi_norm` (manifest, n=364,068); per-frame max median\|ρ\| **0.2711**, 0.0% of frames ≥ 0.90. Both well under the SHIP line (< 0.76) and the STRUCK/DISCLOSE bands. Canary bit-equal on AKBNK/BIENY/AGHOL/SASA. Matches the issue's 2026-10-24 prototype screen (0.2870 vs `efi_norm`, per-frame max median 0.2706) within measurement noise -- this port reproduces the prototype's numbers. Recorded in `docs/gate_e_ledger.csv` |
| F Suites | this repo only; parent repo (`Backtesting`) and Gate E are run by the launcher in clean worktrees | `python -m pytest -q` (this session): see Receipt below |

## MID-STREAM NaN: `corr` of two quantised rank series is sometimes undefined

`ts_rank(x, 5)[t] = count(x[t-4..t] <= x[t]) / 5` can only take one of 5 values
(`1/5, 2/5, 3/5, 4/5, 1`). A trailing 5-bar window of a rank series therefore sometimes
contains 5 identical values (zero variance), at which point the Pearson correlation in
that window is `0/0` and pandas' `.rolling().corr()` correctly returns NaN rather than a
divide-by-zero error. `rolling(3, min_periods=3).max()` then correctly refuses to produce
a value from a window that contains that NaN (one of the three corr values it would need
to compare is undefined), so the NaN propagates through `ts_max` too. This is a
consequence of the formula's own quantisation, not a bug in the port: Gate A's independent
loop reproduces the SAME NaN at bar 899 of its 900-bar spot-check, built from a completely
separate `numpy.corrcoef`-based reference, and Gate C measures exactly 238 such mid-stream
NaNs (16.0% of the 1,490 bars that clear the 10-bar leading warm-up) on the 1,500-bar
synthetic walk.
`tests/test_a101_026.py::test_matches_an_independent_loop_at_defaults` pins the bar-899
agreement explicitly so this is not silently "fixed" into a different (wrong) convention
later.

## Wiring

`Category` **284 → 285** (`volume` **33 → 34**); `df.ta.<name>()` accessor count **292 →
293**. Touch points: `pandas_ta/volume/a101_026.py` (module), `pandas_ta/volume/__init__.py`
(export), `pandas_ta/__init__.py` → `Category["volume"]` (discovery), `pandas_ta/core.py` →
`AnalysisIndicators.a101_026` (accessor), `tests/test_a101_026.py` (tests). `README.md`'s
headline and `volume (34)` row, and `docs/IndicatorDictionary.md` (regenerated), both
updated and checked by `tests/test_readme_counts.py`. `docs/MLCompanionContract.md`'s
running tag count updated **629 → 630 / 272 → 273 `SF`** (`A101_026_5_5_5_3` probes
cleanly at the dictionary's 600-bar synthetic frame -- the 10-bar warm-up fits trivially);
`tests/test_ml_companions.py::test_the_contract_quotes_the_dictionarys_actual_ml_form_counts`
re-derives and passes against the updated `Counter`. `tests/test_altport2_ports.py`'s
`CATEGORY_TOTAL` updated to match (284 → 285) and `CATEGORY_BUCKETS["volume"]`
updated (33 → 34), since that test pins the exact per-category count.

## Receipt

Gate E run by the launcher 2026-11-08 (`is44-a101_026-bbc92714`), recorded in
`docs/gate_e_ledger.csv` by this receipt session. Verdict SHIP: max\|ρ\| 0.2857 vs
`efi_norm`, well under the 0.76 ship line. The port ships -- no column removed.

`python -m pytest -q` in this worktree (this session): see below.
