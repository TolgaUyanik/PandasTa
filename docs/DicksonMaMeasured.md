# Dickson Moving Average distance — measured (`dickson_ma`)

The close's percent distance from Nathan Dickson's moving average (DMA), the mean of
Ehlers & Way's error-correcting EMA (EC) and Alan Hull's moving average (HMA):
`DMA = (EC(30) + HMA(7)) / 2`. Issue #147 (BT-DMA-DIST), found by the 2026-10-24 library
catalog screen, round 4 (backtrader `DicksonMovingAverage`, GPL-3.0). backtrader shows only
that the indicator exists; the module is written from the published definitions below, and
no backtrader code was read.

**Status: Gates A, B, D cleared; Gate C synthetic only (real-data counts come with the Gate E
run); Gate E: pending, run by issue-solver after this session.** `dickson_ma` is in
`Category`, under the `pfe` / `kalman_trend` precedent, so a revert must undo every touch
point listed under *To close*.

Shipped: `pandas_ta/overlap/dickson_ma.py`, one column `DICKSON_DIST_<length>_<hull_length>`
(default `DICKSON_DIST_30_7`), in percent. Tests: `tests/test_dickson_ma.py` (32).
**Every number below is printed by `python docs/measure_dickson_ma.py`**, except the suite
counts in Gate F and the prototype figures quoted from the issue, which are marked.
Environment: numpy 1.26.4, pandas 2.3.3, Python 3.11.9. Measured 2026-10-25.

## Sources, and how far each was checked

| source | used for | how it is known |
|---|---|---|
| backtrader `dma.py` (GPL-3.0) | that the indicator exists; the formula line `(EC(30) + HMA(7)) / 2` and the defaults 30 / 7, both as quoted in the issue | the issue text; the file was not opened |
| J. F. Ehlers and R. Way, "Zero Lag (Well, Almost)", *Technical Analysis of Stocks & Commodities*, Nov 2010 | EC, from its EasyLanguage listing | **recalled, not fetched**: this session had no web access and no copy of the paper. The listing below is the transcription the test oracle implements |
| N. Dickson, "Dickson Moving Average", r/algotrading (2016) | the combination `(EC + HMA) / 2` | recalled as the post backtrader's docstring links (that docstring was not opened either); not fetched |
| A. Hull, alanhull.com | HMA | the fork's own upstream `hma`, checked against an independent loop written from Hull's formula |

The EC listing as transcribed (line numbers are this document's, used by Gate A):

```
L1   Inputs: Length(20), GainLimit(50);
L2   Vars: alpha(0), Gain(0), BestGain(0), EC(0), Error(0), LeastError(0), EMA(0);
L3   alpha = 2 / (Length + 1);
L4   EMA = alpha*Close + (1 - alpha)*EMA[1];
L5   LeastError = 1000000;
L6   For Value1 = -GainLimit to GainLimit Begin
L7       Gain = Value1 / 10;
L8       EC = alpha*(EMA + Gain*(Close - EC[1])) + (1 - alpha)*EC[1];
L9       Error = Close - EC;
L10      If AbsValue(Error) < LeastError Then Begin
L11          LeastError = AbsValue(Error);
L12          BestGain = Gain;
L13      End;
L14  End;
L15  EC = alpha*(EMA + BestGain*(Close - EC[1])) + (1 - alpha)*EC[1];
```

## Gate A — line by line

| listing | `pandas_ta/overlap/dickson_ma.py` | note |
|---|---|---|
| L1 `GainLimit(50)` | :7 `GAIN_LIMIT = 50` | fixed, not a parameter |
| L1 `Length(20)` | :38 `length ... else 30` | default 30 is backtrader's, per the issue; the paper's 20 is not used |
| L3 | :14 | |
| L4 | :23 | |
| L5 `LeastError = 1000000` | :25 `argmin` over all candidates | **departure**: the search starts from +inf. 1000000 is a price-unit constant; once \|Close − EC\| ≥ 1e6 for every gain the listing keeps the previous bar's BestGain, so the output would depend on price scale |
| L6–L7 | :15 `arange(-GAIN_LIMIT, GAIN_LIMIT + 1) / 10` | the same doubles as `Value1 / 10`: both are a correctly rounded integer / 10 |
| L8 | :24 | the same expression in the same operation order, vectorised over the 101 gains |
| L9–L13 | :25 `argmin(npabs(x[t] - cand))` | `argmin` returns the first minimum, i.e. the lowest gain on a tie, which is what the strict `<` scanning upward from −GainLimit keeps |
| L15 | :25 `cand[...]` | L15 recomputes L8 at BestGain, the same double as the stored candidate |
| `EMA[1]`, `EC[1]` start at 0 (L2) | :20–22 | **departure**: both are seeded on the first valid close. From 0 the EMA would start at alpha × Close, about 6% of price at length 30; the head is masked instead (see *Warm-up*) |
| HMA (Hull) | :50 `hma(x, length=hull_length)` | `WMA(2 × WMA(int(n/2)) − WMA(n), int(sqrt n))`: at n = 7 that is WMA(2 × WMA(3) − WMA(7), 2) |
| DMA | :50 | `(EC + HMA) / 2` |
| distance | :51 | `100 × (close / DMA − 1)`; a non-positive DMA emits NaN |

Measured against the oracle (`tests/test_dickson_ma.py::literal_ec`, a scalar loop that
follows L3–L15, and `literal_hma`, two nested WMA loops from Hull's formula):

| check | measured |
|---|---|
| EC, bit-identical bars, lengths 10 / 30 / 50 (3 walks × 899 valid bars, one NaN bar each) | 2,697 / 2,697 at each length |
| distance vs oracle at (30, 7) / (10, 4) / (50, 16), 1,200-bar walk with one NaN bar | max \|diff\| 0 / 0 / 4.4e-14; NaN masks equal; n 915 / 1,103 / 720 |
| hand check, closes (10, 11), length 30: the best gain wants 1/alpha − alpha = 15.4 > 5, so it clamps at +5 and EC[1] = 10 + alpha² + 5·alpha | module 10.326742976066598, formula 10.326742976066598 |
| constant close 37.5, 600 bars | max \|distance\| 2.2e-14 |
| the round-4 prototype `bt_dma_dist` × 100, past the warm-up (σ 0.005 / 0.02 / 0.05) | max \|diff\| 4.4e-14 over 2,723 bars each |

The last row is a cross-check, not Gate A: the prototype lives in the gitignored
`docs/issues/screen/`, so the script runs that block only where the folder exists. It shows
the port computes what the screen measured, apart from the head mask.

The oracle comparison is not vacuous: the test also asserts that its walks land the gain
search both on the clamp and strictly inside it.

### What the gain search actually does

Oracle BestGain over 3,000-bar walks (seed 1, length 30, 2,999 searched bars each):

| σ per bar | +5.0 | −5.0 | interior |
|---|---|---|---|
| 0.005 | 97.4% | 1.4% | 1.2% |
| 0.02 | 97.3% | 1.2% | 1.4% |
| 0.05 | 97.1% | 1.3% | 1.5% |

On a clamped bar, EC = alpha·EMA + 5·alpha·Close + (1 − 6·alpha)·EC[1] (algebra from L8 at
g = 5), a fixed fast smoother with pole 1 − 12/31 = 0.613 at length 30. So the
"error-correcting" part mostly reduces to a constant gain, and the distance behaves like a
short-horizon return: on the proxy below its closest comparator is `ROC_1`.

## Warm-up (the head, not only the tail)

The EMA's seed error decays as (1 − alpha) per valid close. The warm-up is
`ceil(ln 1e-8 / ln(1 − alpha))` **valid closes** (finite and > 0; a missing bar does not
shrink the seed error), computed from `length` alone, so the mask cannot leak the future.
It is 277 at length 30, 92 at 10 and 461 at 50. HMA(7) needs 8 bars and is covered by it.

Head check: started at bar s ∈ {100, 500, 900} vs bar 0, worst |diff| from the FIRST
emitted bar on, 10 seeds × σ ∈ {0.005, 0.02, 0.05} (90 runs per row), test bound 1e-6:

| length | warm-up | head worst |
|---|---|---|
| 30 (default) | 277 | 5.5e-8 |
| 10 | 92 | 5.1e-8 |
| 50 | 461 | 4.1e-7 |

At length 30, on the same 90 runs with the mask removed (compared from bar 7, the first bar
where HMA(7) exists):

| check | measured |
|---|---|
| worst \|diff\| at bar 7 | 1.980 |
| first bar from which it stays under 1e-3, vs `ceil(ln(1e-3 / 1.980) / ln(29/31))` | bar 7 + 135, vs 7 + 114 predicted |
| first bar from which it stays under 1e-6, vs the same prediction at 1e-6 | bar 7 + 226 = 233, vs 7 + 218 predicted |
| emitting from W // 2 = 138 instead (seed 3, s = 500), \|diff\| at the first emitted bar | 4.7e-5 |

Decay runs a little slower than (1 − alpha) predicts, as it did for `kalman_trend`. The
277-bar mask leaves 44 bars of margin over the measured 233. The last row is the Hilbert
lesson in CLAUDE.md: half the warm-up passes any tail check and still emits a
start-dependent value 47 times the head test's bound.

## Gates

| gate | status |
|---|---|
| A Correctness | pass, against a transcription of the listing (recalled, see *Sources*); numbers in *Gate A* above |
| B Causality | future-perturbation over 32 offsets (290 to 1,189, step 29), all past the warm-up: real module 0 leaks. Five mutants (`importlib` source read, `exec`'d in memory), each proved live: EC write back-dated, distance back-dated (`shift(-1)`), HMA fed tomorrow's close, EMA fed tomorrow's close — each caught at 32 of 32; the gain search scored against tomorrow's close — caught at 19 of 32, because it changes EC only where tomorrow's close moves the gain off its +5 clamp. Both counts are pinned |
| C Reachability | **synthetic only**: 1,200-bar walk, seed 11, tick 0.05: 923 finite, 923 non-zero, 484 positive / 439 negative, 923 distinct values. Real-data counts: the Gate E run's sample size over the 89 frames, to be entered by the receipt session |
| D Scale-free | ×8 and ×64: max \|diff\| 0, `Series.equals` true, NaN masks equal. ×10 and ×3.7: max \|diff\| 6.7e-14 / 4.4e-14 (test bound 1e-9), NaN masks equal. 0 < 484 positive < 923 finite, with 923 distinct values |
| E Attribution | Gate E: pending, run by issue-solver after this session |
| F Suites | this repo, run in three chunks (`tests/test_[a-h]*.py`, `[i-r]`, `[s-z]`): 2 failed / 3,194 passed / 83 skipped. Neither failure touches this port: `test_pine_coverage_csv::test_audited_rows_carry_their_evidence` is the CLAUDE.md known break, and `test_altrepo_talib_csv::test_regenerating_reproduces_the_committed_rows` stops with `pandas-ta-classic not found at D:\AwakenAnalytics\PandasTaWork\AlternativeRepos\pandas-ta-classic`, a directory outside this repo. Neither was re-run with the port removed. Parent repo: run by the launcher |

## The prior from the prototype (quoted from issue #147, NOT measured here)

The 2026-10-24 screen ran Gate E on the prototype: max |ρ| **0.8889** vs `Dist_to_PP_pct`
(n = 398,226), top-5 per-frame max median 0.8979 → DISCLOSE_GAP; next comparators
`log_return` 0.8599 and `Ret_1d_pct` 0.8599. Fork overlap (stage 2): 0.8844 vs
`priorday_fib:PDFIB_MID`.

The port matches the prototype to 4.4e-14 past the warm-up (Gate A cross-check), so the
only difference Gate E can see is the head mask: 270 bars per frame (277 − the 7 the
prototype also lost to HMA) that the prototype emitted and the port does not. The per-frame median sat 0.0021 under the 0.90
STRUCK line, so the verdict could land on either side. That is a guess; Gate E decides.

## Proxy overlap (NOT Gate E)

Spearman ρ of `DICKSON_DIST_30_7` on one synthetic walk (σ = 0.02, seed 1), n = 2,723:

| comparator | ρ |
|---|---|
| `ROC_1` | **0.8956** |
| 100·(close / EMA₅ − 1) | 0.8543 |
| 100·(close / EC₃₀ − 1), EC alone | 0.8457 |
| 100·(close / HMA₁₀ − 1) | 0.7846 |
| 100·(close / EMA₁₀ − 1) | 0.7542 |
| 100·(close / EMA₂₀ − 1) | 0.6709 |
| `CMO_14` / `RSI_14` | 0.6321 |
| 100·(close / HMA₂₀ − 1) | 0.6216 |
| 100·(close / EMA₃₀ − 1) | 0.6210 |
| 100·(close / HMA₇ − 1) | 0.6120 |
| `KFT_DIST_0.01_0.0001` | 0.6014 |
| `BIAS_SMA_26` | 0.5940 |
| `ROC_5` | 0.5539 |
| `ROC_10` | 0.5116 |
| `PFE_10_5` | 0.3404 |
| `PPO_12_26_9` | 0.2816 |

The maximum does not move with volatility: `ROC_1` at 0.8956 / 0.8957 / 0.8956 / 0.8943
for σ = 0.005 / 0.01 / 0.02 / 0.05. This agrees in direction with the screen, whose next
comparators on real data were the one-day returns (0.8599).

Runtime: 0.28 s for 5,000 bars (one Python-level loop over bars, 101 gains vectorised per bar).

## Docs touched by the wiring

`docs/IndicatorDictionary.md` was regenerated in full on this machine (pandas 2.3.3), not
patched by hand. Its diff against the committed file is the probe date, the counts, the
`overlap (51)` header, the `dickson_ma` row (`DICKSON_DIST_30_7` SF, warm-up 277), its entry
in the feed-ready list, and the removal of the two hand-patch notes for `pfe` and
`kalman_trend`, whose rows came out identical. `docs/MLCompanionContract.md`'s counts moved
568 → 569 tagged columns and 215 → 216 `SF`.

## To close

1. Receipt session: enter Gate E's max |ρ|, its comparator, its sample size and the top-5
   per-frame median above, and apply the bands. Enter the same run's sample size as Gate
   C's real-data count.
2. STRUCK → delete the module, the export in `pandas_ta/overlap/__init__.py`, the
   `Category` entry, the accessor in `pandas_ta/core.py`, `tests/test_dickson_ma.py`,
   `docs/measure_dickson_ma.py`, and revert the README counts, the dictionary row and
   counts, the `MLCompanionContract` counts and `CATEGORY_TOTAL` in
   `tests/test_altport2_ports.py`. Keep this file. A revert closes #147 as well as a ship.
3. DISCLOSE_GAP or DISCLOSE → ship, and state the measured ρ and comparator in the
   module docstring and here.
