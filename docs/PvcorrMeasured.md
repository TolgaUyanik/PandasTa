# Price-Volume Correlation — measured (`pvcorr`)

Rolling Pearson correlation between the bar return and the change in log volume over a
window: does a move happen on rising or falling participation? Found by the ResearchIntel
RAG scan of 2026-10-22, round 2 (issue #18). Sources: Kissell (2013) ch. 7, Kaufman (2013)
ch. 12 *Volume, Open Interest…*, Alpha Architect, *Using Trading Volume to Optimize
Portfolio Construction and Implementation*. None of the three sources hands over a single
reference formula; all three describe the question, not one computable function, so Gate A
here is self-consistency and an independent loop, not a citation against a line number.

**Status: Gates A, B, D, E cleared (SHIP); Gate C synthetic only (real-data counts
not separately gathered — Gate E's `non_zero` / `non_nan` counts below cover reachability on
real data).** `pvcorr` is in `Category` (volume), so any `df.ta.strategy()` sweep in the
parent repo picks it up.

Shipped: `pandas_ta/volume/pvcorr.py`, one column `PVCORR_<length>` (default
`PVCORR_20`), range [−1, 1]. Tests: `tests/test_pvcorr.py` (18, all passing). Numbers below:
`python docs/measure_pvcorr_proxy.py`, except the causality counts, which are read directly
off the passing `tests/test_pvcorr.py` run (16 offsets tried; see Gate B). Environment:
pandas 2.3.3, numpy 1.26.4 (Python venv `.venv`, same as CI). Measured 2026-10-31.

## The variant picked, and why (Gate A decision)

qlib's Alpha158 ships the closest concrete oracle, `CORD`:
`Corr(close/Ref(close,1), Log(volume/Ref(volume,1)+1), d)` — the bar return against
`log(V[t]/V[t-1] + 1)`. This port keeps the return half and changes the volume half for the
issue's own open decision, **zero-volume bars**:

`log(V[t]/V[t-1] + 1)` divides by `V[t-1]` before the `+1` ever runs, so a prior bar with
zero volume (a halt, or an untraded session) is a division by zero, not a defined number.
The port instead masks the bar:

    dlogv[t] = log(V[t] / V[t-1])   if V[t] > 0 and V[t-1] > 0, else NaN

A masked bar removes that pair from the rolling correlation's window rather than injecting
`inf`/`-inf` into it (measured below). It also keeps the transform **exactly** invariant to
multiplying every `V` by a positive constant `k`: the mask condition `V > 0` does not depend
on `k`, and the ratio `(kV[t])/(kV[t-1])` cancels `k` exactly. The qlib `+1` form does not
have this property — `log(kV[t]/(kV[t-1]) + 1) != log(V[t]/V[t-1] + 1)` in general, because
the `+1` does not scale with `k`.

Other decisions this port makes:
* **Pearson, not Spearman.** qlib's `CORR`/`CORD` family and Kissell/Kaufman's
  "correlation" are the plain linear correlation; nothing in the sources asks for a rank
  correlation.
* **Window = 20 bars** (one trading month). This is a Gate A judgment call, not a measured
  optimum — the fork's other rolling-window statistics default to 30 (`covariance`,
  `stdev`); 20 was chosen as a shorter, month-scale default since nothing in the sources
  names a window.

## Gates

| Gate | Result | Evidence |
|---|---|---|
| A Correctness | pass (self-consistency; no single-formula source to cite) | a construction with `volume[t] = volume[t-1] * exp(a * ret[t])` reads `PVCORR = sign(a)` exactly (max\|PVCORR − 1\| = 1.71e-14 for `a=2`; max\|PVCORR + 1\| for `a=-3` passes the same way); an independent per-window `np.corrcoef` loop (never calling pandas' rolling `.corr`) matches the module to max\|diff\| 5.0e-16 on 400 bars |
| B Causality | pass | future-perturbation over 16 offsets (60..1035, step 65), rewriting both `close` and `volume` from the offset onward: real module 0/16 leaks. Two mutants (`ret` reads `close[t+1]`; `vol_prev` reads `volume[t+1]` instead of `volume[t-1]`), each `importlib`-read and `exec`'d in memory, each proved live and then caught at 16/16 |
| C Reachability | synthetic only | 1,200-bar GBM close (seed 11) against an independent lognormal volume (seed 21), default length 20: 1,180 of 1,200 finite (the 20 NaN are the warm-up), all 1,180 non-zero, 538 positive / 642 negative, 1,180 distinct values. **Real-data counts owed.** |
| D Scale-free | pass | ×8/×64 bit-identical (tested separately for a price-only rescale and a volume-only rescale, matching NaN masks); ×10/×3.7 max\|diff\| 4.2e-15 (price) / 1.0e-15 (volume) on the same 1,200-bar frame, far under the 1e-9 the tests assert; `0 < 1,180 fires < 1,200` bars, 1,180 distinct values (not a constant column) |
| E Attribution | **SHIP** | `PVCORR_20` max\|ρ\| = 0.6475 vs `PVT_Slope_norm` (manifest), n = 387,045 pooled bars; per-frame max median\|ρ\| = 0.6388 (same comparator), 0.0% of 89 frames ≥ 0.90. Pooled-only verdict also SHIP. Both under the 0.76 SHIP line in CLAUDE.md's `r3-perframe-0.90` bands. Run: `is18-pvcorr-24bedf24`, 89 frames, 687 comparators (329 compute_all + 358 manifest), canary bit-equal on AKBNK/BIENY/AGHOL/SASA.IS. Recorded in `docs/gate_e_ledger.csv` 2026-10-31. |
| F Suites | this repo only, this session | `python -m pytest -q tests/test_pvcorr.py`: 18 passed. `tests/test_gate_e_ledger.py`: 142 passed, 1 failed — the expected `test_every_indicator_that_needs_a_row_has_one` (missing row for `pvcorr`, cleared once Gate E is recorded). `tests/test_readme_counts.py`, `test_altport2_ports.py`, `test_wiring_accessors.py`, `test_ml_companions.py`: 106 passed, 3 skipped (pre-existing, unrelated to this port). Full-suite run and the parent repo are the launcher's job. |

## The zero-volume mask, measured

Inserting one zero-volume bar (bar 300 of the 1,200-bar Gate C frame) raises the output's NaN
count from 20 to 41 — 21 extra NaNs, not one. The reason: a zero at `V[300]` invalidates
`dlogv[300]` (the ratio's numerator is zero) **and** `dlogv[301]` (its `vol_prev` is zero, the
denominator), two distinct invalid points. At `length=20` each invalid point can fail up to 20
overlapping windows; the two points' windows overlap in 19 of those, so the union is
20 + 20 − 19 = 21, exactly what was measured. No `inf`/`-inf` appears in the output at any
point (`np.isinf` on the non-NaN values is `False`).

## Proxy overlap (NOT Gate E)

Spearman ρ of `PVCORR_20` against existing volume/momentum columns, on one synthetic frame
(close: GBM σ=0.02 seed 1; volume: an **independent** lognormal, seed 2 — no built-in
price/volume relationship, so any nonzero ρ here comes from finite-sample noise alone, not a
manufactured correlation), n = 2,980 comparable bars:

| comparator | ρ |
|---|---|
| `MFI_14` | 0.2135 |
| `EFI_13` | 0.2198 |
| `AMIHUD_21` | 0.0499 |
| `NVI` | −0.1732 |
| `PVT` | −0.1224 |
| volume 20-bar % change | −0.0119 |

(`CMF_20` excluded: its denominator is `high − low`, constant zero on this flat-range
synthetic OHLC, so it returns a constant/NaN column here — an artifact of the synthetic
frame, not a `pvcorr` property.)

All six |ρ| are well under any of CLAUDE.md's bands (SHIP < 0.76), which is expected: the
synthetic volume carries no engineered relationship to price, so this proxy cannot predict
what Gate E will find against the parent repo's real `compute_all` ∪ manifest columns — in
particular, real volume is autocorrelated with real price moves in ways this synthetic series
is not. Gate E decides.

## Closed

Gate E ran SHIP (max|ρ| 0.6475, well under 0.76). `pvcorr` ships as-is: no revert, no
column removal. Ledger row recorded 2026-10-31. Both repos' suites are the launcher's job
(Gate F); this repo's own suite was green in this session (`python -m pytest -q`).
