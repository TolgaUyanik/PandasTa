# STIFFNESS-60 — measured

PandasTa issue **#259**: *Katsanos stiffness: share of the last 60 closes
above SMA(100) + 0.2 std*. Shipped as `pandas_ta/trend/stiffness.py`, one
column **`STIFF_60`**.

```
MA[T]    = mean(close[T-99..T])                               SMA 100
S[T]     = std(close[T-99..T], ddof=0)
above[T] = 1 if close[T] > MA[T] + 0.2 * S[T] else 0
STIFF[T] = 100 * (above[T-59] + ... + above[T]) / 60
```

Source: Markos Katsanos, *Stiffness*, Technical Analysis of Stocks &
Commodities, November 2018, as issue #259 states it from the ProRealCode
port (https://www.prorealcode.com/prorealtime-indicators/stiffness-indicator/)
and the thinkorswim Stiffness reference, both of which cite Katsanos. The
article itself was not readable when the issue was written and was not read
here. jesse (MIT) counts closes above `SMA - 0.2 * std` and adds an EMA(3);
the owner chose the upper-band, unsmoothed version. The issue says of the
source: *existence, not evidence*.

**Every number below is printed by `python docs/measure_stiffness.py`**
(section names match the headings), with these exceptions:

1. §F's counts are **pytest's**, from the targeted run quoted there;
2. §F's wiring counts (`CATEGORY_TOTAL` 384 → 385, README 384 → 385 /
   392 → 393 / `trend (66)`, MLCompanionContract 729 → 730 tagged /
   363 → 364 `SF`) are the **repo's**, checked by
   `tests/test_altport2_ports.py`, `tests/test_readme_counts.py` and
   `tests/test_ml_companions.py`;
3. the **asserted** bounds in `tests/test_stiffness.py` (1e-9 for the
   inexact rescale, 100/60 for a mutant's catch, `>= 900` / `>= 100` /
   `>= 40` floors under measured counts) are that file's constants, not run
   output.

Frames: nine synthetic 1,500-bar closes — `walk`, `trend`, `range-bound`,
`grid` (tick 0.01), `coarse` (tick 0.5 on a level of 100: 206 of 1,500
closes equal their predecessor), `heavy-tailed`, `jump`, `flat`, `rising`.
Six of them are **varying** for this column; `trend`, `flat` and `rising`
are constant (§C1). Warm-up: `MIN_BARS = 159`, first fired bar 158, 1,342
fired bars per frame.

## §A1 Gate A — the issue's formula, spelled independently

A bar-by-bar oracle over plain Python floats — its own 100-term mean, its
own two-pass population variance, its own 60-term count, sharing no code
with the module — against the module:

| frames | fired per frame | same NaN mask | bit-equal | bars differing | max \|abs\| |
|---|---|---|---|---|---|
| all 9 | 1,342 | 9 of 9 | 9 of 9 | 0 | 0.000e+00 |

## §A2 Gate A — TA-Lib as the third speller

`talib.SMA(close, 100) + 0.2 * talib.STDDEV(close, 100, nbdev=1)` (TA-Lib's
STDDEV is the population SD), then the 60-bar count. talib 0.7.1.

| frames | same NaN mask | bit-equal | bars differing | first fired bar |
|---|---|---|---|---|
| all 9 | 9 of 9 | 9 of 9 | 0 | 158 on every frame |

## §A3 Gate A — the other readings are other columns

| reading | where it differs from the module |
|---|---|
| SD with `ddof=1` (`stdev`'s default) | 60 bars of `coarse` and 60 of `jump` (max 1.667, Spearman 0.9999); **0** bars of `walk`, `range-bound`, `grid`, `heavy-tailed` |
| `close >= band` | **0** bars of all six varying frames; on `flat` the module reads 0.0 and `>=` reads 100.0 |
| jesse's lower band `SMA - 0.2*std` | 943 .. 1,342 bars of each of the six (max 26.667 .. 58.333, Spearman 0.9275 .. 0.9866) |
| jesse's lower band + EMA(3) | 1,169 .. 1,342 bars of each of the six (Spearman 0.9265 .. 0.9825) |

## §A4 Gate A — nothing reads before T−158

Truncating each 1,500-bar frame at bar 500: all **842** bars from 658 on are
bit-equal, on all nine frames.

## §B1 Gate B — future sweep and look-ahead mutants

Sweep: rescale every bar `>= j` by **x10**, for each of the 36 offsets
`j = 1464 .. 1499`; a catch is any bar `< j` moving. ⚠ Not the x1.03 of
`j_kaufmanstop_dist`: this column is a count, so a look-ahead shows only
when the perturbation flips a comparison.

The module: **0 of 36** on each of the six varying frames.

| mutant (edit to the shipped source) | caught of 36 (walk / range-bound / heavy-tailed) | bars live (same) | first-catch gap |
|---|---|---|---|
| `ma-lead-10` — `sma(cl.shift(-10))` | 27 / 11 / 5 | 761 / 1,094 / 835 | 1.6667 / 1.6667 / 8.3333 |
| `sd-lead-10` — `stdev(cl.shift(-10))` | 27 / 11 / 5 | 250 / 214 / 92 | 1.6667 / 1.6667 / 8.3333 |
| `close-lead` — `cl.shift(-1) > band` | 29 / 24 / 36 | 500 / 750 / 490 | 1.6667 |
| `above-lead` — `above.shift(-1)` | 29 / 24 / 36 | 492 / 699 / 388 | 1.6667 |
| `output-early` — output `.shift(-1)` | 29 / 24 / 36 | 492 / 699 / 388 | 1.6667 |
| *not gated:* `ma-lead` (1 bar) | 7 / 10 / 0 | 240 / 94 / 24 | — |
| *not gated:* `sd-lead` (1 bar) | 7 / 11 / 0 | 60 / 0 / 0 | — |

⚠ The one-bar leads of the band's legs are printed and NOT used as the
gate's mutants: one close in 100 moves the mean and SD so little that
`sd-lead` is identical to the module on two of the three swept frames before
any perturbation, and neither is caught on `heavy-tailed`.

## §B2 Gate B — the sweep's blind spot, covered by the oracle

| mutant | caught of 36 | bars off the oracle (walk / range-bound / heavy-tailed) | max \|abs\| |
|---|---|---|---|
| `close-lag` — `cl.shift(1) > band` | 0 / 0 / 0 | 433 / 748 / 404 | 3.3333 / 3.3333 / 1.6667 |
| `band-lag` — `cl > band.shift(1)` | 0 / 0 / 0 | 120 / 118 / 320 | 1.6667 / 5.0000 / 5.0000 |

## §C1 Gate C — reachability (synthetic)

| frame | fired | distinct | == 0 | == 100 | min | max |
|---|---|---|---|---|---|---|
| walk | 1,342 | 61 | 366 | 84 | 0 | 100 |
| trend | 1,342 | 1 | 0 | 1,342 | 100 | 100 |
| range-bound | 1,342 | 52 | 11 | 0 | 0 | 85 |
| grid | 1,342 | 61 | 111 | 284 | 0 | 100 |
| coarse | 1,342 | 61 | 133 | 135 | 0 | 100 |
| heavy-tailed | 1,342 | 61 | 371 | 29 | 0 | 100 |
| jump | 1,342 | 61 | 252 | 73 | 0 | 100 |
| flat | 1,342 | 1 | 1,342 | 0 | 0 | 0 |
| rising | 1,342 | 1 | 0 | 1,342 | 100 | 100 |

Every value on every frame is a multiple of 100/60. Pooled over the six
varying frames: **8,052** fired bars, **1,244** at 0, **605** at 100,
**6,203** strictly between.

Gate C on real data (from the Gate E run, §E): 384,787 non-NaN and 340,451 non-zero bars, pooled
over the 89 BIST frames.

## §C2 Gate C — the tie: a close exactly ON its band

On `flat` the band equals the close on 1,401 of 1,401 bars, SD exactly 0 on
all 1,401. The module (strict `>`) reads **0.0**; the `>=` reading reads
**100.0**.

## §D1 Gate D — x8 / x64 bit-identity

All nine frames at price levels 100, 1e-6, 1e6 and 1e100: **36 of 36**
(frame × level) cells bit-equal under both x8 and x64, 1,342 fired bars in
each.

## §D2 Gate D — inexact factors

x10, x3.7, x0.1 and x1.0000001 on all nine frames: NaN masks identical in
all **36** cells, **0** bars differing in all 36, worst cell 0.000e+00.

## §D3 Gate D — what moves the column

| frame | moved by +10 | moved by `close**2` | moved by `log(close)` |
|---|---|---|---|
| walk | 0 | 180 | 181 |
| range-bound | 0 | 298 | 489 |
| grid | 0 | 322 | 163 |
| coarse | 0 | 372 | 310 |
| heavy-tailed | 0 | 266 | 210 |
| jump | 0 | 239 | 43 |
| trend / flat / rising | 0 | 0 | 0 |

⚠ The column is **translation-invariant** as well as scale-invariant
(`close`, `MA` and `0.2*S` all move together under `a*close + b`, `a > 0`),
so a level shift cannot show the bit-identity is non-vacuous; a non-affine
transform does.

## §G1 Guards — one bad close

NaN, +inf and -inf planted at bars 5, 100, 700 and 1,495 of `walk`
(12 cells):

| bar | blanked | moved | inf in output |
|---|---|---|---|
| 5 | 6 | 0 | 0 |
| 100 | 101 | 0 | 0 |
| 700 | 159 | 0 | 0 |
| 1,495 | 5 | 0 | 0 |

Same for all three values. With the module's finite guard removed, the
column is bit-equal in all 12 cells: the guard is a **measured no-op**
(pandas' rolling window reads an infinite close as NaN), kept as defence in
depth and documented as such in the module.

## §L In-fork overlap — synthetic, a disclosure, NOT Gate E

Spearman ρ per frame over the six varying frames:

| comparator | median \|ρ\| | min | max |
|---|---|---|---|
| `ma_disparity` → `MADISP_200_SMA` | **0.8099** | +0.3375 | +0.8447 |
| `zscore(close, 100)` (non-default length) | 0.5401 | +0.2141 | +0.6843 |
| `zscore` → `Z_30` | 0.1180 | −0.1161 | +0.2803 |
| `psl` → `PSL_12` | 0.0415 | −0.1652 | +0.1868 |
| 60-bar mean of `zscore(close, 100)` (not shipped) | 0.9525 | +0.9410 | +0.9653 |

⚠ `MADISP_200_SMA` at 0.8099 sits inside the 0.80 .. 0.90 DISCLOSE_GAP
band *if* real data agreed; synthetic overlap has read both high and low
against Gate E on earlier ports, so this predicts nothing in either
direction.

## §E Gate E

**Gate E: DISCLOSE_GAP** (measured 2026-11-26 at merge time, run `pr395-stiffness`, recorded in
`docs/gate_e_ledger.csv`; not printed by `docs/measure_stiffness.py`). 89 BIST frames, 687
comparators.

| column | max \|ρ\| | against | n | per-frame max median \|ρ\| | verdict |
|---|---:|---|---:|---:|---|
| `STIFF_60` | 0.8728 | `SMA_50_200_Spread_pct` (manifest) | 381,138 | 0.8699 | DISCLOSE_GAP |

Next comparators: `Ret_126d_pct` 0.8192, `Dist_to_SMA_200_pct` 0.8009 (both manifest); highest in
`compute_all`: `support_touches_60` 0.7467. Not STRUCK, so no waiver is needed; the overlap with
the long-trend manifest columns is disclosed here.

## §F Suites

Targeted run (`tests/test_stiffness.py tests/test_altport2_ports.py
tests/test_gate_e_ledger.py tests/test_indicator_list_tables.py
tests/test_readme_counts.py tests/test_ml_companions.py
tests/test_wiring_accessors.py`), 2026-11-24: `1690 passed, 8 skipped`;
one of the skips is `Gate E owed ... ['stiffness']`. The full suite is run
once by the orchestrator and is not quoted here. Backtesting's suite is not
touched by this change.

## §Z Cost — this machine, this run

`stiffness` ~1.7 ms per call on 1,500 bars (python 3.11.18, numpy 1.26.4,
pandas 2.3.3).
