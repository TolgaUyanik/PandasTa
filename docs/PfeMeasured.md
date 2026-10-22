# Polarized Fractal Efficiency — measured (`pfe`)

Hans Hannula's PFE (Technical Analysis of Stocks & Commodities, January 1994), in
log-percent form. It is the straight-line distance between the first and last bar of a
window over the bar-to-bar path length, on a chart where one bar is one unit across. The
result is signed by the net move and EMA(5)-smoothed. Found by the ResearchIntel RAG scan of
2026-10-22, round 2. It replaces `signed_er`, which was built and reverted
(`docs/SignedErMeasured.md`).

**Status: Gates A, B, D cleared; Gate C synthetic only (real-data counts owed); Gate E
OWED; verdict pending. Do not merge to `main` before Gate E**: `pfe` is in `Category`, so
any `df.ta.strategy()` sweep in the parent repo picks it up.

Shipped: `pandas_ta/momentum/pfe.py`, one column `PFE_<length>_<smooth>` (default
`PFE_10_5`), range [−100, 100]. Tests: `tests/test_pfe.py` (17). Numbers:
`python docs/measure_pfe_proxy.py`. Environment: pandas 3.0.6, numpy 2.5.4, Python 3.12.
Measured 2026-10-22.

## What differs from Hannula

| | Hannula (1994) | `pfe` |
|---|---|---|
| vertical leg | raw price change | 100 × log-return, about 1 unit per 1% move |
| scale-free | no: it adds price units to bar counts | yes: a price ratio |
| window | 10 bars, 9 segments, horizontal leg 10 | `length` segments, horizontal leg `length`, so a straight line reads exactly 100 |
| net leg | close − close[9] | 100 × ln(close / close[length]) |

No published source defines the log-percent form. Gate A is checked against an
independent loop written from the formula, not against a textbook implementation.

**Known flaw, by design: volatility dependence.** "One bar across = one 1% move up" is an
arbitrary exchange rate. On calm bars both legs approach `length`, so |PFE| saturates
near 100 and only the sign carries information. Measured on 3,000-bar walks (seed 1):

| σ per bar | median \|raw PFE\| | ρ vs summed `CMO_10` | ρ vs `ROC_10` |
|---|---|---|---|
| 0.1% | 99.60 | 0.8191 | 0.8177 |
| 0.5% | 91.86 | 0.8319 | 0.8206 |
| 1% | 78.26 | 0.8495 | 0.8325 |
| 2% | 58.43 | 0.8743 | 0.8559 |
| 5% | 36.71 | 0.9001 | 0.8864 |

Intraday frames, which move far less than 1% per bar, sit at the saturated end. The same
chart shape scores differently on a calm and a wild asset; the ×8 test cannot see this,
because it rescales price, not volatility.

## A bug Gate D caught during the port

The first version summed the per-bar log-returns for the net leg. On tick-rounded prices,
a window that returns to its starting tick summed to ±1e-16 instead of 0, and `sign()`
turned that into a jump of about ±100. The ×10 tolerance test failed by 47.8. The net leg
is now `ln(close / close[length])`, which is exactly 0 when the two closes are equal.
`test_round_trip_window_reads_exactly_zero` pins this on 6 such bars of a 3,000-bar
tick-rounded walk.

An inherent PFE property remains: when the net move is tiny but non-zero, the sign can
flip between bars and the raw value jumps across zero by up to 2 × 100 × length / path.
The EMA damps this; it does not remove it.

## Gates

| Gate | Result | Evidence |
|---|---|---|
| A Correctness | pass (self-consistency; no source oracle — Hannula's raw-price form is never computed, and no page of TASC 1994 or Kaufman 2013 ch. 20 is cited) | straight line reads 100; steps (+1, +1, −1) read 100·√10 / (3·√2); matches an independent loop to 1e-9 on 400 bars; smoothing == `ewm(span=5, adjust=False)` exactly; \|raw\| ≤ 100 + 1e-9 at σ 0.1%, 2%, 10% |
| B Causality | pass | 31-offset future-perturbation sweep: real module 0 leaks; mutants `net` and `path` (each reads bar t+1) proven live, then caught 31 of 31 |
| C Reachability | synthetic only | 1,200-bar tick-rounded walk (seed 11, tick 0.05): 1,190 finite, 1,190 non-zero, 612 positive / 578 negative. **Real-data counts owed.** |
| D Scale-free | pass | ×8 / ×64 bit-identical with matching NaN masks; ×10 / ×3.7 within 1e-12 (measured 1.7e-13 / 2.7e-13); 0 < 1,190 fires < 1,200 bars (vacuous on its own: the warm-up NaNs guarantee `< n`), so the test also pins > 100 distinct values and 612 positive / 578 negative |
| E Attribution | **OWED** | `../Backtesting/scripts/analysis/measure_pfe_overlap_full.py` against the engine's full production column set |
| F Suites | this repo only | 42 failed / 3,087 passed / 85 skipped / 1 error (2026-10-22, after fixing the `MLCompanionContract` `SF` count the port had broken). No failure names `pfe`; the strategy-sweep ones are pandas 3 dtype errors (`KeyError: 0`, int64 setitem). Pre-port baseline 42 / 3,070 is **inferred** (3,087 − 17 new `pfe` tests), not re-measured, so "same 42 failures" is unverified. The failures come from the pandas 3.0.6 environment; CLAUDE.md records 1 failure on its own environment. Rerun on pandas 2.x. Parent repo not run. |

## Proxy overlap (NOT Gate E)

Spearman ρ of `PFE_10_5` on one synthetic GBM walk (σ = 0.02, seed 1), n = 2,990:

| comparator | ρ |
|---|---|
| `CMO_10` (`talib=False`) | 0.8743 |
| `ROC_10` | 0.8559 |
| `SLOPE_10` | 0.8487 |
| `CMO_14` (default) | 0.8011 |
| `RSI_14` | 0.8011 |
| `ER_10` | −0.0027 |

CLAUDE.md's thresholds are "ρ ≈ 0.9 → revert; 0.76–0.80 → ship with disclosure; below
0.76 → ship". The 0.874 maximum is above the disclosure band, in the range between 0.80
and ≈ 0.9 that CLAUDE.md does not define, and below `signed_er`'s 0.910. It rises with
volatility and reaches 0.90 at σ = 5%. On the proxy alone this leans toward revert, which
was also the pre-registered expectation; Gate E decides. Whether summed CMO or ROC at
length 10 is in the production set is unknown here.

The pre-registered guess (high ρ against `er`) was **falsified**: ρ = −0.0027, because
`er` is unsigned. The redundancy is with the sign-carrying momentum columns instead.

## To close

1. In the parent repo, write `measure_pfe_overlap_full.py` from an existing
   `measure_*_overlap_full.py`, run it, and enter the maximum |ρ|, its comparator and its
   sample size above.
2. Fill Gate C from the same real frames. Report the saturation (median |raw PFE|) on
   those frames too.
3. Apply CLAUDE.md's thresholds. On a revert, delete the module, export, `Category` entry,
   accessor, tests and README count, and keep this file.
4. Regenerate `docs/indicators/pfe.md` with `docs/gen_indicator_pages.py`, which reads
   the parent repo. `docs/IndicatorDictionary.md` needs only this package, but
   regenerating on this machine's pandas 3.0.6 writes 8 environment breaks into it, so the
   `pfe` row and the counts were patched in by hand on 2026-10-22. Regenerate on pandas 2.x,
   including after a revert.
5. Run both suites.
