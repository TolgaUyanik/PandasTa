# Three bars of 3% expanding highs / lows — measured (`expand3_3pct`)

Issue #201 (B3-EXPAND3-3PCT). Catalog candidate `b3_expand3_3pct` in
`docs/issues/screen/ind_screen_r9.py` (owner's machine only; not read for this port).
Source: Reddit r/TradingView post 1jlvqer (2025-03-28),
https://www.reddit.com/r/TradingView/comments/1jlvqer/ — crowd talk (tier 4); the poster's
claim (a 4th bar then stays inside a range) is untested here and by the poster.

**Status: Gates A–D measured on synthetic frames; Gate E OWED** (no ledger row; under
`GATE_E_PENDING_OK=1` `tests/test_gate_e_ledger.py` reports it as a "Gate E owed" skip).
`expand3_3pct` is in `Category["trend"]`, so `df.ta.strategy()` picks it up.

Shipped: `pandas_ta/trend/expand3_3pct.py`, one column `EXPAND3_<pct>` (default
`EXPAND3_3.0`). Tests: `tests/test_expand3_3pct.py` (128). Numbers:
`python docs/measure_expand3_3pct.py` (sections A1 A2 A3 B B1 C CT D E0 W W2 Z; B1 takes ~7
minutes). Environment: pandas 2.3.3, numpy 1.26.4, Python 3.11 (measured 2026-11-25).

## What the published algorithm is

The poster's Pine line, quoted in the issue:

    highSignal = high[2]*1.03 <= high[1] and high[1]*1.03 <= high
    lowSignal  = "same for the lows the other way around"

Port:

    up[T] = high[T-2] * 1.03 <= high[T-1] and high[T-1] * 1.03 <= high[T]
    dn[T] = low[T-2]  * 0.97 >= low[T-1]  and low[T-1]  * 0.97 >= low[T]
    EXPAND3_3.0[T] = up[T] - dn[T]        # in {-1, 0, +1}; both legs firing -> 0

Choices, each measured:

1. **The low leg reads `low[1] <= 0.97 * low[2]`** (lows 3% lower), not the reciprocal
   `low[1] * 1.03 <= low[2]` (a 2.913% step). They differ on 0 .. 2 bars per 1,500-bar
   frame (§A2: walk 1, range-bound 2, jump 1, coarse 2, the other five 0).
2. **Ties fire**, as in the source: both comparisons are non-strict. At the default the
   multipliers are exactly the float literals (`1 + 3/100 == 1.03`, `1 - 3/100 == 0.97`),
   and 100 → 103 → 106.09 is an exact float chain that gives +1 (§A3); the mirrored lows give
   -1, both together give 0. One ulp under 106.09 gives 0 (pinned in the tests).
3. **NaN** on the first 2 bars and on any bar whose 3-bar window holds a NaN high or low —
   the Pine comparison with `na` is false, but a 0 there would claim "no expansion" on bars
   with no data.
4. **`pct` parameter** (default 3) so the column name encodes it; `pct=2` is pinned to change
   the output and the name (`EXPAND3_2.0`).

## Gates

Nine synthetic OHLC frames (`walk`, `trend`, `range-bound`, `grid` tick 0.01, `heavy-tailed`,
`jump`, `calm` 0.5% bars, `coarse` tick 1.0 at level 100, `flat`), 1,500 bars unless stated.

| Gate | Result | Evidence |
|---|---|---|
| A Correctness | pass | scalar-loop oracle with the float literals 1.03 / 0.97, no pandas: **bit-equal, NaN masks included, on all nine frames** at 1,500 bars (§A1) and at the tests' 400 bars (§CT). Exact-boundary bars (a comparison that is an exact float equality): 2 on `coarse`, 0 elsewhere (§A3) |
| B Causality | pass | blind sweep, 1,499 offsets per frame, two futures per offset (each later bar ×(1+3u) vs ÷(1+3u)): **0 caught on all nine frames** (§B). Five look-ahead mutants read off the shipped source and `exec`'d in memory (`h2-lead`, `l2-lead`, `up-early`, `dn-early`, `output-early`): live on every frame where the leg they touch fires (`up-early` 0 on `calm`/`flat`, `dn-early` 0 on `trend`/`calm`/`flat`), caught on 80 / 83 / 84 / 85 / 169 of 1,499 offsets on `walk` and 51 / 44 / 51 / 44 / 96 of 399 on the tests' 400-bar `range-bound` (§B1); 0 on `calm` and `flat`, which never fire. ⚠ A sparse ±1 column is only caught near a signal, so the tests pin `> 0`, not "every offset". Two further mutants, `h1-lead` / `l1-lead`, are live (1 .. 45 bars) but caught on only 0 .. 3 of 1,499 offsets per frame — the mutated comparison needs bar T+1 inside a window as narrow as `[high[T-2]*1.03, high[T]/1.03]` — so they are disclosed here and NOT pinned |
| C Reachability | synthetic only | warm-up a constant 2 bars on every frame. Nonzero bars per 1,500: walk 12 (6 +1 / 6 -1), trend 43 (43 / 0), range-bound 50 (30 / 20), grid 10 (7 / 3), heavy-tailed 9 (7 / 2), jump 12 (6 / 6), coarse 10 (6 / 4), calm 0, flat 0. Both legs on one bar: 0 on every frame (only the planted §A3 case) (§C). No real-data count: the BIST cache is not on this machine |
| D Scale-free | pass | ×8 / ×64 / ×2^-20 / ×2^300 bit-identical on all nine frames; ×10 / ×3.7 / ×0.1 differ on **0 bars** of every frame with identical NaN masks (the tests allow 1, room for a comparison within one ulp of the step to flip). `0 < fires < n` on the seven firing frames. A +1 level shift is NOT invariant (0 .. 6 bars move) — a percent step is a ratio (§D) |
| E Attribution | **owed** | not run on the port. The issue's prototype measured max \|ρ\| 0.2935 vs `Dist_to_FWMA_pct` (n = 397,692), top-5 per-frame max median 0.2957 → SHIP; a prototype is not a port. Pre-port equivalence screen (§E0, NOT Gate E: 12 synthetic frames x 1,500 bars at 1/3/5% per-bar vol, tick 0.01/0.05, 6 .. 118 exact high ties per frame; the 4 frames at 1% vol never fire, the other 8 fire on 49 .. 196 bars): per-frame Spearman ρ vs `ROC_2` median 0.3885 over 8 frames (range 0.2971 .. 0.5193), vs `INC_2` 0.2559 (0.1814 .. 0.3558), vs `bos` `HIGHER_HIGH − LOWER_LOW` 0.1822 (0.1376 .. 0.2333) |
| F Suites | targeted only | `python -m pytest -q -p no:cacheprovider -W ignore tests/test_expand3_3pct.py tests/test_altport2_ports.py tests/test_gate_e_ledger.py tests/test_indicator_list_tables.py tests/test_readme_counts.py tests/test_wiring_accessors.py`: 1,623 passed, 8 skipped (one of them the "Gate E owed" skip for `expand3_3pct`). Full suites: run by the orchestrator |

## Dictionary tag

`docs/IndicatorDictionary.md` tags `EXPAND3_3.0` **`CONST`**: its probe frame is quiet and
never takes a 3% step, so the column reads 0 on every probed bar. Not a constant column —
§C above. `docs/MLCompanionContract.md`'s count line moves 741 → 742 tagged / 45 → 46 `CONST`
(§W2).

## Cost

§Z: 100,000 bars 4.5 ms, peak 5.9 MB; 400,000 bars 13.2 ms, peak 23.6 MB.

## Wiring

`pandas_ta/trend/expand3_3pct.py`, `pandas_ta/trend/__init__.py`, `Category["trend"]`
(66 → 67; total 396 → 397, after #167's `rd_outside_bar` landed on dev), `AnalysisIndicators.expand3_3pct` in `pandas_ta/core.py`,
`tests/test_expand3_3pct.py`. README counts (397 registered / 405 callable / trend 67) and
`tests/test_altport2_ports.py` (`CATEGORY_TOTAL` 397, trend bucket 67) updated (§W).
