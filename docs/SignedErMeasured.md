# Signed Efficiency Ratio — measured and reverted (`signed_er`)

**Status: REVERTED 2026-10-22, before Gate E, on the owner's call.** This file is the receipt.
The module, its export, its `Category` entry, its accessor and its tests were deleted.
Its successor for the same task is `pfe` (`docs/PfeMeasured.md`).

The task named Hans Hannula's Polarized Fractal Efficiency (TASC, January 1994), found by
the ResearchIntel RAG scan of 2026-10-22, round 2. Its pre-registered expectation was a
revert with high ρ against `er`. The first build was not PFE but a signed variant of
Kaufman's Efficiency Ratio (Kaufman, *Trading Systems and Methods*, 5th ed., 2013,
ch. 17): `er` with the sign of the net move kept, EMA(5)-smoothed, column `SER_10_5`.
Hannula's PFE was set aside because its raw-price form is not scale-free. That was argued
from the formula, and the port that followed confirmed it was needed (`pfe` uses log-returns).

## Why it was reverted

On bars where the path is non-zero, unsmoothed signed ER **is** the summed Chande Momentum
Oscillator. `sum(up) - sum(down)` is the net change and `sum(up) + sum(down)` is the path:

    er(close, n) * sign(close.diff(n)) == cmo(close, n, talib=False) / 100

Measured max |diff| 2.2e-16, Spearman 1.0, n = 2,990. Where the path is zero (a flat window),
the deleted module returned 0 while `er` and `cmo` return NaN, so the identity holds only
off flat windows. The default `cmo` (`talib=True`, RMA rather than sums) is not identical:
max |diff| 0.66, ρ 0.874. The shipped default added only a 5-bar EMA over the summed CMO.

## Measured before the revert

Environment: pandas 3.0.6, numpy 2.5.4, Python 3.12. The proxy and identity
numbers reproduce with `python docs/measure_pfe_proxy.py`, which rebuilds the raw form from
the identity above. The Gate B and D rows were measured by `tests/test_signed_er.py`, which
was deleted before it was committed, so they cannot be reproduced.

| Gate | Result |
|---|---|
| A | hand-computed 5-bar case; `raw == er * sign` exactly on non-flat windows; smoothing == `ewm(span=5, adjust=False)` |
| B | 31-offset future-perturbation sweep: real module 0 leaks; two one-bar look-ahead mutants caught 31 of 31 |
| C | synthetic only; never measured on real data |
| D | x8 / x64 bit-identical; x10 / x3.7 within 1e-12; `0 < fires < n` |
| E | not run |

Proxy overlap of `SER_10_5` (one synthetic GBM walk, σ = 0.02, seed 1, n = 2,990 — **not
Gate E**): summed `CMO_10` 0.9101, `ROC_10` 0.9017, `SLOPE_10` 0.8858, `CMO_14` 0.8235,
`RSI_14` 0.8235, `ER_10` −0.0089.

The pre-registered guess (high ρ against `er`) was **falsified**: ρ = −0.0089, because `er`
is unsigned. The redundancy was with the sign-carrying momentum columns instead.
