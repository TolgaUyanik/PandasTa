# MESA Sine Wave, fixed-period DFT form — measured (`msw_sine`)

John Ehlers' MESA Sine Wave, in-phase line ("MESA Sine Wave Indicator", Stocks & Commodities, April
1996; reprinted as "The Sinewave Indicator", Rocket Science for Traders, Wiley 2001, ch. 11). Issue
#146. Catalog candidate `tl_msw_sine_20` in `docs/issues/screen/ind_screen_r4.py`, which cites
Tulip Indicators `msw.c` (LGPL-3.0) as the library the candidate was found in; per the issue, the
port is written from Ehlers' published formula, never from `msw.c`. This is the sister port of
issue #145's `msw_lead` (the lead line, `sin(phase + pi/4)`); this module ships the in-phase line,
`sin(phase)`.

**Status: Gates A-E cleared, SHIP. Run `is146-msw_sine-00e99a5b`, recorded in the Gate E ledger
2026-11-23.** `msw_sine` is in `Category`, so any `df.ta.strategy()` sweep in the parent repo picks
it up.

Shipped: `pandas_ta/cycles/msw_sine.py`, one column `MSW_SINE_<length>` (default `MSW_SINE_20`),
range [-1, 1]. Tests: `tests/test_msw_sine.py` (12). Numbers:
`python docs/measure_msw_sine_proxy.py`. CPU-kernel check:
`python docs/measure_msw_sine_cpu.py disable pytest`. Environment: pandas 2.x, numpy, this
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

This module ports the `MESASine` line in radians, with one change: the guard `|RealPart| > 0.001`
is a raw-price-unit constant, not scale-free (a price rescale can flip which branch a bar takes
once `|RealPart|` crosses the unscaled 0.001 line — exactly what the issue's prototype pre-flight
measured). The port uses `|RealPart| > 0.001 * close`, the scale-free form the issue specifies.
`MESALeadSine` is out of scope here; it is `msw_lead` (issue #145, already shipped).

## Gates

| Gate | Result | Evidence |
|---|---|---|
| A Correctness | pass | matches an independent Python-loop re-derivation of the published pseudocode (not the module's vectorized rolling/dot form): NaN masks match, max\|diff\| 2.36e-14 on 1,200 bars (measured, `python docs/measure_msw_sine_proxy.py`) |
| B Causality | pass | 31-offset future-perturbation sweep: real module 0 leaks; two look-ahead mutants (`real_lookahead`, `write_shift`) proven live, then caught 31 of 31. A third candidate mutant (shifting the imaginary part's rolling input) was tried and rejected as degenerate: Ehlers' sine weight at the window's newest position is `sin(0) = 0`, so the one bar a 1-bar shift newly reads into that window is always multiplied by zero — live overall (measured: differs on 1,178 of 1,181 non-NaN bars) but invisible to this exact boundary test at any offset, same as `msw_lead`'s rejected mutant (identical phase arithmetic). See `tests/test_msw_sine.py` docstring. |
| C Reachability | synthetic + real | 1,200-bar GBM walk (seed 11, sigma 0.02): 1,181 of 1,200 finite, 1,181 distinct values, 608 positive / 572 negative (measured). Real data (Gate E run `is146-msw_sine-00e99a5b`, 89 ALTPORT-1 frames, 398,849 pooled bars): 397,158 non-NaN, 396,399 non-zero. |
| D Scale-free | pass | x8/x64 bit-identical with matching NaN masks (the guard and both dot products are linear in `close`, so a power-of-two rescale is exact); x10/x3.7 within 1e-9 (measured 2.21e-14 / 1.75e-14); `0 < fires < n` and > 100 distinct values, pinned in `test_column_fires_and_is_not_constant` |
| E Attribution | SHIP | Gate E run `is146-msw_sine-00e99a5b` (89 ALTPORT-1 frames, n = 396,090, 687 comparators, canary bit-equal): `MSW_SINE_20` max \|rho\| 0.7460 vs `StochRSI_D`; per-frame max median \|rho\| 0.7463 (same comparator). Both under the 0.76 SHIP line and the 0.90 STRUCK line. Recorded in `docs/gate_e_ledger.csv` 2026-11-23. |
| F Suites | this repo, targeted only | `python -m pytest -q tests/test_msw_sine.py tests/test_readme_counts.py tests/test_altport2_ports.py tests/test_wiring_accessors.py tests/test_ml_companions.py tests/test_gate_e_ledger.py tests/test_pine_coverage_csv.py tests/test_prose_counts_match_the_csvs.py`: all pass (measured on the receipt run, 2026-11-23, after the ledger row was recorded). Same command's `test_msw_sine.py` subset under `python docs/measure_msw_sine_cpu.py disable pytest` (CPU kernels without AVX-512/AVX2/FMA3): 12 of 12 pass. Whole suites: run by issue-solver in clean worktrees (see the PR body). |

## CPU-kernel check (NPY_DISABLE_CPU_FEATURES)

`python docs/measure_msw_sine_cpu.py disable pytest` (this machine's own features: all 12 tests
of `tests/test_msw_sine.py` pass under `NPY_DISABLE_CPU_FEATURES="AVX512F AVX512_SKX AVX2 FMA3"`
as well as under the native kernel set, measured 2026-11-23). The indicator's only CPU-sensitive
point is the `|real| > eps` branch condition, a float comparison that a kernel-dependent last-bit
move could in principle flip near the boundary; no such flip was observed on the test module's own
frames.

## Proxy overlap (NOT Gate E)

Spearman rho of `MSW_SINE_20` on one synthetic GBM walk (sigma = 0.02, seed 1), n = 1,200:

| comparator | rho |
|---|---|
| `HT_SINE` | 0.7165 |
| `ROC_10` | 0.6728 |
| `STOCHk_14_3_3` | 0.6444 |
| `MSW_LEAD_20` | 0.5904 |
| `HT_LEADSINE` | 0.3828 |
| `RSI_14` | 0.3546 |
| `CC_ANGLE_20` | -0.3842 |

The issue's own measurements on the prototype: Gate E (89 ALTPORT-1 frames, 396,090 bars, run
`screen_r4_20261024`) max |rho| 0.7416 vs `StochRSI_D`, top-5 per-frame max median 0.7417 -> SHIP;
the stage-2 fork-overlap screen (scale-free `Category` outputs at defaults, 12 frames) max |rho|
0.7444 vs `stochrsi:STOCHRSId_14_14_3_3`, per-frame max median 0.7432. Neither of those comparators
appears in this synthetic single-frame proxy (`STOCHRSI` needs an `rsi`-of-`rsi`, not probed here);
`HT_SINE` ranking highest in both this proxy and `msw_lead`'s equivalent proxy, at a comparable
magnitude to `msw_lead`'s own top synthetic comparator, is consistent with the two lines sharing
their phase arithmetic. The port's own run (`is146-msw_sine-00e99a5b`, above) measured 0.7460 vs
`StochRSI_D` against the prototype's 0.7416, same top comparator -- confirms the port changed
nothing about the arithmetic.

## Open

None. Gates A-F cleared; Gate E SHIP (run `is146-msw_sine-00e99a5b`, recorded 2026-11-23). Both
repos' whole suites are run by issue-solver in clean worktrees per the PR body.
