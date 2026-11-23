# MESA Lead Sine, fixed-period DFT form — measured (`msw_lead`)

John Ehlers' MESA Sine Wave lead line ("MESA Sine Wave Indicator", Stocks & Commodities, April
1996; reprinted as "The Sinewave Indicator", Rocket Science for Traders, Wiley 2001, ch. 11): the
phase of the period-`length` discrete Fourier term of `close`, read as a sine 45 degrees (pi/4
rad) ahead of the in-phase sine. Issue #145. Catalog candidate `tl_msw_lead_20` in
`docs/issues/screen/ind_screen_r4.py`, which cites Tulip Indicators `msw.c` (LGPL-3.0) as the
library the candidate was found in; per the issue, the port is written from Ehlers' published
formula, never from `msw.c`. Only the lead line is in scope here — the in-phase sine
(`tl_msw_sine_20`) is a separate candidate, not ported.

**Status: Gates A, B, C (synthetic), D cleared. Gate E pending** (run by issue-solver after
this session). **Do not merge to `main` before Gate E is recorded**: `msw_lead` is in
`Category`, so any `df.ta.strategy()` sweep in the parent repo picks it up.

Shipped: `pandas_ta/cycles/msw_lead.py`, one column `MSW_LEAD_<length>` (default `MSW_LEAD_20`),
range [-1, 1]. Tests: `tests/test_msw_lead.py` (12). Numbers:
`python docs/measure_msw_lead_proxy.py`. CPU-kernel check:
`python docs/measure_msw_lead_cpu.py disable pytest`. Environment: pandas 2.x, numpy, this
machine's own CPU features (measured 2026-11-23).

## What the published algorithm is

Ehlers' pseudocode (EasyLanguage, degrees; `Count` runs 0 = current bar to `Period - 1` = oldest
bar in the window):

```
RealPart = Sum(Cosine(360 * Count / Period) * Price[Count], Count = 0..Period-1)
ImagPart = Sum(Sine(360 * Count / Period) * Price[Count], Count = 0..Period-1)
If AbsValue(RealPart) > 0.001 Then DCPhase = Arctangent(ImagPart / RealPart)
Else DCPhase = 90 * Sign(ImagPart)
DCPhase = DCPhase + 90
If RealPart < 0 Then DCPhase = DCPhase + 180
If DCPhase < 0 Then DCPhase = DCPhase + 360
If DCPhase > 360 Then DCPhase = DCPhase - 360
MESASine = Sine(DCPhase)
MESALeadSine = Sine(DCPhase + 45)
```

This module ports that formula in radians, with one change: the guard `|RealPart| > 0.001` is a
raw-price-unit constant, not scale-free (a price rescale can flip which branch a bar takes once
`|RealPart|` crosses the unscaled 0.001 line — exactly what the issue's prototype pre-flight
measured). The port uses `|RealPart| > 0.001 * close`, the scale-free form the issue specifies.

## Gates

| Gate | Result | Evidence |
|---|---|---|
| A Correctness | pass | matches an independent Python-loop re-derivation of the published pseudocode (not the module's vectorized rolling/dot form): NaN masks match, max\|diff\| 3.28e-14 on 1,200 bars (measured) |
| B Causality | pass | 31-offset future-perturbation sweep: real module 0 leaks; two look-ahead mutants (`real_lookahead`, `write_shift`) proven live, then caught 31 of 31. A third candidate mutant (shifting the imaginary part's rolling input) was tried and rejected as degenerate: Ehlers' sine weight at the window's newest position is `sin(0) = 0`, so the one bar a 1-bar shift newly reads into that window is always multiplied by zero — live overall (1,178/1,200 bars differ) but invisible to this exact boundary test at any offset. See `tests/test_msw_lead.py` docstring. |
| C Reachability | synthetic only | 1,200-bar GBM walk (seed 11, sigma 0.02): 1,181 of 1,200 finite, 1,181 distinct values, 576 positive / 605 negative. **Real-data counts owed** (Gate E run). |
| D Scale-free | pass | x8/x64 bit-identical with matching NaN masks (the guard and both dot products are linear in `close`, so a power-of-two rescale is exact); x10/x3.7 within 1e-9 (measured 1.52e-14 / 2.30e-14); `0 < fires < n` and > 100 distinct values, pinned in `test_column_fires_and_is_not_constant` |
| E Attribution | **PENDING** — run by issue-solver after this session | `../Backtesting/Backtesting/scripts/analysis/gate_e_overlap.py run --module pandas_ta.cycles.msw_lead --name msw_lead` |
| F Suites | this repo, targeted only | `python -m pytest -q tests/test_msw_lead.py tests/test_readme_counts.py tests/test_altport2_ports.py tests/test_wiring_accessors.py tests/test_ml_companions.py tests/test_gate_e_ledger.py tests/test_pine_coverage_csv.py tests/test_prose_counts_match_the_csvs.py`: 1,414 passed, 7 skipped, 1 failed (`test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`, expected: no ledger row yet). Same command under `python docs/measure_msw_lead_cpu.py disable pytest` (CPU kernels without AVX-512/AVX2/FMA3): 12 of 12 `test_msw_lead.py` tests pass. Whole suites: run by issue-solver in clean worktrees (see the PR body). |

## CPU-kernel check (NPY_DISABLE_CPU_FEATURES)

`python docs/measure_msw_lead_cpu.py disable pytest` (this machine's own features: all 12 tests
of `tests/test_msw_lead.py` pass under `NPY_DISABLE_CPU_FEATURES="AVX512F AVX512_SKX AVX2 FMA3"`
as well as under the native kernel set. The indicator's only CPU-sensitive point is the
`|real| > eps` branch condition, a float comparison that a kernel-dependent last-bit move could
in principle flip near the boundary; no such flip was observed on the test module's own frames.

## Proxy overlap (NOT Gate E)

Spearman rho of `MSW_LEAD_20` on one synthetic GBM walk (sigma = 0.02, seed 1), n = 1,200:

| comparator | rho |
|---|---|
| `HT_LEADSINE` | 0.7781 |
| `HT_SINE` | 0.5082 |
| `CC_ANGLE_20` | 0.3490 |
| `ROC_10` | 0.0653 |
| `STOCHk_14_3_3` | 0.0396 |
| `RSI_14` | -0.2248 |

The issue's own stage-2 fork-overlap screen (scale-free `Category` outputs at defaults, 12
frames, real data) measured max |rho| 0.7625 vs `ht_sine:HT_LEADSINE`, per-frame max median
0.7624 — the same comparator this synthetic proxy also ranks highest, at a comparable magnitude.
That screen is not Gate E (different frame count, not the 687-comparator manifest); Gate E
decides.

The issue's measured Gate E on the prototype (`screen_r4_20261024`, 89 ALTPORT-1 frames,
398,849 bars): max |rho| 0.6911 vs `apo_pct`, top-5 per-frame max median 0.6939 -> SHIP. That
number is on the prototype candidate, not this module; this port changes nothing about the
arithmetic (same formula, same scale-free guard), so no divergence from the prototype's figure is
expected, but the port's own run is what gets recorded.

## To close

1. Run Gate E on this module: `python scripts/analysis/gate_e_overlap.py run --module
   pandas_ta.cycles.msw_lead --name msw_lead` from `../Backtesting/Backtesting` (rebuild the
   cache first if a prior run is stale).
2. Record the ledger row: `python docs/gate_e_ledger.py record <run dir> --measured YYYY-MM-DD`.
3. Apply CLAUDE.md's `r3-perframe-0.90` bands. On SHIP, fill in the real Gate E numbers above and
   the Gate C real-data counts. On STRUCK (unlikely given the issue's own 0.6911 prototype
   measurement, well under 0.90), delete the module, its wiring, and its tests, and keep this
   file as the receipt — a measured revert closes the issue exactly as well as a ship.
4. Run both repos' suites.
