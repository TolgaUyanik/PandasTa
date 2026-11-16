# J-CHANDELIER-DIST-22 — measured

PandasTa issue **#122**: *distance to the Chandelier Exit, long (22, 3)*.
Shipped as `pandas_ta/trend/j_chandelier_dist.py`, one column
**`J_CHANDELIER_DIST_22_3.0`**.

```
tr[T]   = max(high - low, |high - close[T-1]|, |low - close[T-1]|)   tr[0] undefined
atr[T]  = Wilder(tr, 22), seeded with mean(tr[1..22])
stop[T] = max(high[T-21..T]) - 3 * atr[T]
J_CHANDELIER_DIST[T] = (close[T] - stop[T]) / close[T]
```

Source: jesse indicators (MIT), `chande.py`, as issue #122 quotes it —
`chande.py: HH22 - 3*ATR22` — and Skender Stock.Indicators' `Chandelier`
for the same formula. The underlying rule is Chuck LeBeau's Chandelier
Exit. The issue says of the library: *existence, not evidence*.

**Every number below is printed by `python docs/measure_j_chandelier_dist.py`**
(section names match the headings) and the figures that move between numpy
CPU dispatches are re-printed by
`python docs/measure_j_chandelier_dist_cpu.py <section>`.

⚠ **Six exceptions, named here rather than left for a reader to find** —
six numbered items, and the count is the number of items. The script has no
§F section and does not read the repo's documents, so:

1. §F's counts (`255 passed`, `1,353 passed`, and
   `1 failed, 12,116 passed, 86 skipped`, plus the porting session's
   earlier `254` and `2 failed, 12,107 passed, 86 skipped`) are
   **pytest's**, from the runs named there;
2. §F's `701 → 702` tagged columns is **`docs/MLCompanionContract.md`'s**
   count, checked by
   `tests/test_ml_companions.py::test_the_contract_quotes_the_dictionarys_actual_ml_form_counts`;
3. §E's figures are the **launcher's**, not the measurement script's: the
   Gate E run `is122-j_chandelier_dist-976ee44b` of 2026-11-16, read by the
   receipt session out of that run's `overlap_max.csv`, `top25.csv`,
   `perframe.csv`, `degenerate.csv` and `meta.json` and out of
   `docs/gate_e_ledger.csv`. Neither the porting session nor the receipt
   session ran the harness;
4. §L's real-data figures (0.8606 / 0.8759 / 0.8603 / 0.8656 and the run id
   `screen_r2_20261024`) are **issue #122's**, quoted;
5. the "web access is unavailable" line below is a fact about the session,
   not a printed measurement. The two library-absence flags next to it
   **are** printed, by §0;
6. and the remaining non-cells: §A1's "moved MAMA by 1.1e-2" is
   **`CLAUDE.md`'s** (cited inline), and the **asserted bounds** quoted
   next to several measurements (1e-12 and 1e-9 at §A1, the bar-1,000
   convergence bound at §A3, 1e-9 at §D2, `> 300` bars and `> 1e-5` at
   §G2, `> 100` bars at §G1) are
   **`tests/test_j_chandelier_dist.py`'s own constants**,
   not run output — the measured value beside each one is. Round 2 found
   four more leaks of this kind (§A2's NaN-mask equality, §G4's frame
   length and exact 0.0, §A5's ATR magnitude) and round 3 a fifth (§G3's
   frame length); rather than being listed, all five are now **printed by
   the script** and quoted from it.

Everything else in this receipt is a cell from a run.

Run environment (§0): python 3.11.2 · numpy 1.26.4 · pandas 2.3.3 · talib
0.7.1 installed · **jesse NOT installed, stock_indicators NOT installed**;
web access is unavailable in this worktree.

⚠ **And nothing in this receipt is a statement about what jesse's or
Skender's code says.** Neither library is installed and neither can be
read, so which smoother each calls and which series each takes the highest
high over are **not claimed**. The reading of the issue's `ATR22` as
Wilder's SMA-seeded ATR rests on two checkable things: Wilder's 1978
specification, and TA-Lib's `ATR` — the conventional meaning of a bare
"ATR" — which this worktree can run, and does, in §A2.

---

## Verdict

| Gate | Result |
|---|---|
| A Correctness | **PASS** — matches an independent bar-by-bar oracle to 2.5e-16 absolute on 1,478 of 1,478 bars of each of six frames, and `talib.MAX - 3*talib.ATR` (the issue's two operators as TA-Lib spells them) to 2.4e-16 at Spearman 1.0000 |
| B Causality | **PASS** — 0 of 36 sweep catches on six frames; six look-ahead mutants live and caught 11–36 of 36; three blind-spot edits caught 0 by the sweep and all three by the oracle |
| C Reachability | **PASS** — synthetic: 1,478 of 1,500 bars on each of six frames, 1,478 distinct values, 3,759 of 8,868 pooled bars negative, 0 exactly zero. Real data (the Gate E run): **396,891 non-NaN of 398,849** pooled BIST bars, **396,891 of them non-zero** |
| D Scale-free | **PASS** — ×8/×64 bit-identical on six frames and at price levels 1e-6, 1e+6, 1e+100; ×10/×3.7/×0.1/×1.0000001 within 2.467e-11; a +10 level shift moves all 1,478 fired bars of every frame |
| E Attribution | **DISCLOSE_GAP — ship with a note** — run `is122-j_chandelier_dist-976ee44b`, 2026-11-16: max \|ρ\| **0.8609** vs the manifest's `Range_Pos_20` over n = 396,891, top-five per-frame max median **0.8760** over 89 frames, 687 comparators, no waiver (only STRUCK needs one) |
| F Suites | this repo's suite run below; both repos' suites are the launcher's |

**The one thing to read first.** This port does **not** reproduce the screen
prototype bit for bit, and that is deliberate: the issue says *Gate A starts
from the source formula, not the prototype*. `ATR22` is read as Wilder's
ATR **seeded with the mean of the first 22 true ranges** — Wilder 1978, and
what TA-Lib's `ATR` computes; the prototype's recurses from bar 0 with no
seed. §A3 measures
the gap — 655 … 722 of 1,478 bars disagree, by up to 2.0e-02, converging to
bit-equality by bar 732 … 808. So the screen's Gate E figures are evidence
about a neighbouring column, and the port's own Gate E run is what decided
its band. **That run landed in the same band, DISCLOSE_GAP** (§E): max
\|ρ\| 0.8609 against `Range_Pos_20`, the prototype's 0.8606 against the
same comparator — agreement to three digits on a column whose warm-up is
provably different, which §E3 reads as the warm-up washing out of 396,891
bars rather than as the two columns being the same arithmetic.

---

## §A1 Gate A — against a bar-by-bar oracle

The oracle is TA-Lib's rule written out in plain Python: its own true-range
loop, its own SMA seed over a slice, its own Wilder recursion over Python
floats, its own 22-bar running maximum. It shares no code with the module.

| frame | fired | NaN mask equal | bit-equal | max \|abs\| | max \|rel\| |
|---|---|---|---|---|---|
| walk | 1478 | True | False | 2.359e-16 | 1.583e-12 |
| trend | 1478 | True | False | 2.151e-16 | 8.556e-13 |
| range-bound | 1478 | True | False | 1.665e-16 | 1.246e-12 |
| grid | 1478 | True | False | 2.220e-16 | 3.875e-13 |
| heavy-tailed | 1478 | True | False | 2.498e-16 | 4.325e-12 |
| jump | 1478 | True | False | 2.290e-16 | 1.696e-12 |

⚠ **Not bit-equal, and the reason is measured rather than waved at.**
Writing Wilder's step as `alpha*tr + (1-alpha)*atr[-1]` instead of
`atr[-1] + (tr - atr[-1])/22` moves the ORACLE by exactly the same amounts
(2.359e-16 / 2.151e-16 / 1.665e-16 / 2.220e-16 / 2.498e-16 / 2.290e-16, cell
for cell). pandas' `ewm(adjust=False)` uses one spelling and the oracle the
other; that re-association is the whole of the disagreement. `CLAUDE.md`
records a TALIB-1 case where this kind of re-association moved MAMA by
1.1e-2, so it is printed rather than assumed small.

Assertions: **1e-12 absolute** and **1e-9 relative**. Under
`NPY_DISABLE_CPU_FEATURES="AVX512F AVX512_SKX AVX2 FMA3"` all six absolute
figures stay inside 1.5e-16 … 2.4e-16 and the worst relative rises to
**1.407e-11** (range-bound), still two orders inside the bound.
⚠ Four of the six absolute cells move in their SECOND digit between
dispatches — trend 2.151e-16 → 2.198e-16, range-bound 1.665e-16 →
1.596e-16, heavy-tailed 2.498e-16 → 2.229e-16, jump 2.290e-16 → 2.359e-16;
only `walk` and `grid` hold. The band is the claim, not the digits.

## §A2 Gate A — against talib's `MAX` and `ATR`

`talib.MAX(high, 22) - 3 * talib.ATR(high, low, close, 22)` is the issue's
two operators as TA-Lib spells them, and TA-Lib's Wilder ATR is the
conventional meaning of a bare "ATR". ⚠ Not a stand-in for jesse's code,
which this session cannot read. talib **0.7.1**:

| frame | shared | NaN mask equal | max \|abs\| | max \|rel\| | Spearman |
|---|---|---|---|---|---|
| walk | 1478 | True | 2.359e-16 | 1.583e-12 | 1.0000 |
| trend | 1478 | True | 2.212e-16 | 8.556e-13 | 1.0000 |
| range-bound | 1478 | True | 1.665e-16 | 1.246e-12 | 1.0000 |
| grid | 1478 | True | 2.220e-16 | 4.263e-13 | 1.0000 |
| heavy-tailed | 1478 | True | 2.255e-16 | 4.325e-12 | 1.0000 |
| jump | 1478 | True | 2.290e-16 | 1.696e-12 | 1.0000 |

The test **skips** where talib is absent rather than passing silently;
`talib` is a dev-only dependency and no shipped module imports it.

## §A3 the screen prototype is a different column on the warm-up

| frame | shared | differ | last differing bar | max \|abs\| | Spearman |
|---|---|---|---|---|---|
| walk | 1478 | 710 | 808 | 4.923e-03 | 1.0000 |
| trend | 1478 | 655 | 803 | 5.591e-03 | 0.9990 |
| range-bound | 1478 | 722 | 775 | 1.988e-02 | 0.9989 |
| grid | 1478 | 708 | 755 | 1.034e-02 | 0.9995 |
| heavy-tailed | 1478 | 696 | 761 | 6.931e-03 | 0.9998 |
| jump | 1478 | 684 | 732 | 4.525e-03 | 0.9999 |

The difference decays geometrically — the recursion forgets its seed at
`(21/22)^k`. On `walk`: 4.92e-03 at bar 22, 1.42e-04 at 100, 1.49e-06 at
200, 1.57e-10 at 400, 2.13e-14 at 600, and **exactly 0 at the sampled bars
800, 1,000 and 1,499**. ⚠ Those are nine sampled bars, not a scan: the last
bar that actually differs on `walk` is **808** (**758** under reduced
dispatch — the 873 below is `heavy-tailed`'s, the worst of the six), which
is why the test takes its convergence bound at bar 1,000.

The prototype also fires on **one bar more** (bar 21), because its ATR needs
no seed window.

Under reduced CPU dispatch the differing counts move to 656 … 714 and the
last differing bar to **717 … 873**, which is why the test asserts
convergence at bar 1,000 rather than at the measured last bar.

## §A4 the other readings, priced

Over the six varying frames plus `tied` (a walk with a doji every seventh
bar):

| reading | differing bars | max \|abs\| | Spearman |
|---|---|---|---|
| (a) prototype `ewm(alpha, adjust=False)` from bar 0 | 655 … 722 | 4.5e-03 … 2.0e-02 | 0.9989 … 1.0000 |
| (b) this fork's `rma` (`adjust=True`) | 779 … 961 | 3.8e-04 … 5.9e-03 | 0.9998 … 1.0000 |
| (c) `SMA(tr, 22)` instead of Wilder | 1477 of 1478 | 6.0e-03 … 2.8e-02 | 0.9662 … 0.9974 |
| (d) `HH22` over the CLOSE, not the high | 1294 … 1478 | 4.0e-03 … 4.5e-03 | 0.9729 … 0.9994 |
| (e) the fork's `true_range` (`non_zero_range` epsilon) | **0** on all six varying frames | 0.0 | 1.0000 |

(a) is the screen's; (b) is what `ta.atr(mamode="rma")` would give and is
not Wilder's by `rma`'s own docstring; (c) is the `cksp` book reading;
(d) is the one spelling of "HH22" the quote leaves open — `HH` names the
highest HIGH in every statement of the rule this session can read (the
issue's `HH22`, the prototype's `tsmax(h, 22)`), and what the libraries
themselves pass is not checkable here.

### (e) where `non_zero_range`'s epsilon bites — and where it does not

`non_zero_range` adds `sys.float_info.epsilon` (2.220e-16) to EVERY bar of
the `high - low` leg as soon as ONE bar has `high == low`. It is an
**absolute** quantity, so what it costs depends on the price level, and
Gate D runs at 1e-6 as well as at 100:

| frame | level | `high==low` bars | differ | max \|abs\| | module ×8 | variant ×8 | variant ×64 |
|---|---|---|---|---|---|---|---|
| walk | 1e+02 | 0 | 0 | 0.0 | True | True | True |
| walk | 1e-06 | 0 | 0 | 0.0 | True | True | True |
| grid | 1e+02 | 0 | 0 | 0.0 | True | True | True |
| grid | 1e-06 | 0 | 0 | 0.0 | True | True | True |
| flat | 1e+02 | 1500 | 0 | 0.0 | True | True | True |
| flat | 1e-06 | 1500 | 1478 | 6.661e-10 | True | **False** | **False** |
| tied | 1e+02 | 215 | 14 | 1.908e-16 | True | **False** | **False** |
| tied | 1e-06 | 215 | 1478 | 2.032e-10 | True | **False** | **False** |

So the inline true range is load-bearing **only on the frames that can show
it**, and the receipt says both halves: on the six varying frames the
`true_range`-based variant is bit-equal to this module and the copy buys
nothing; on a tie-bearing frame it loses Gate D at a price level of 100, and
at 1e-6 it loses both factors. The module holds in all eight cells. (⚠ the
`grid` frame is tick-rounded and still has **0** tied bars at this tick and
seed — it is not the frame that exercises this, which is why `tied` exists.)

## §A5 the warm-up is the chain, not the number 22

| series | first non-NaN |
|---|---|
| true range | 1 |
| `high.rolling(22).max()` | 21 |
| Wilder ATR | 22 |
| the column | 22 |

`MIN_BARS = 23`; a 22-bar frame returns `None` and a 23-bar frame fires on
exactly 1 bar. Restoring bar 0's true range (the prototype's reading) moves
the first firing bar to 21 and moves 660 later bars, by up to 7.168e-04.

Both legs are checked against TA-Lib directly rather than against
recollection, on the `walk` frame:

* `talib.TRANGE` first fires at index **1** and is **BIT-EQUAL** to this
  module's `_true_range`;
* `talib.ATR(22)` first fires at index **22** and agrees with
  `wilder_rma(tr, 22)` to **1.110e-15** absolute, on an ATR whose median
  magnitude the same line prints as **0.4833**.

So "bar 0's true range is undefined" and "the Wilder seed is
`mean(tr[1..22])`" are run, not remembered.

---

## §B1 Gate B — the blind future sweep

36 offsets (1464 … 1499), each rescaling every bar ≥ j by 1.03 on all three
legs and asking whether any bar < j moved.

**The module is caught 0 of 36 on walk, trend, range-bound, grid,
heavy-tailed and jump.**

Six mutants are read off the shipped source, edited and `exec`'d in memory.
Every one is LIVE (it changes the column) before it is swept:

| mutant | walk | trend | heavy-tailed | first catch \|abs\| |
|---|---|---|---|---|
| tr-high-lead | 35/36 | 36/36 | 36/36 | 1.4e-03 … 4.1e-03 |
| tr-prev-lead | 36/36 | 36/36 | 36/36 | 2.1e-03 … 4.1e-03 |
| atr-lead | 36/36 | 36/36 | 36/36 | 2.2e-03 … 4.1e-03 |
| hh-lead | 17/36 | 36/36 | 11/36 | 6.3e-04 … 3.0e-02 |
| close-lead | 36/36 | 36/36 | 36/36 | 2.8e-02 … 3.1e-02 |
| output-early | 36/36 | 36/36 | 36/36 | 3.2e-03 … 3.3e-02 |

⚠ A count below 36 is the FORMULA's, not a gap in the mutant: `hh` is a
22-bar MAXIMUM, so leading it by a bar changes nothing at an offset where
the perturbed bar is not the one the maximum selects. The test therefore
asserts "at least one offset" and this table carries the counts.

## §B2 the sweep's blind spot, and the oracle covering it

Three edits make the true range read the WRONG close, or lag the highest
high, **without reading any later bar**. The sweep is right not to catch
them and Gate A's oracle rejects all three:

| mutant | caught by the sweep | bit-equal to the oracle | max \|abs\| vs the oracle |
|---|---|---|---|
| tr-today-close (`prev = close`) | 0/36 on both frames | False | 2.918e-02 / 6.046e-02 |
| tr-two-days-ago (`prev = close.shift(2)`) | 0/36 on both frames | False | 1.999e-02 / 5.035e-02 |
| hh-lag (`hi.shift(1).rolling(22).max()`) | 0/36 on both frames | False | 2.685e-02 / 3.079e-01 |

Pinned in BOTH directions: a sweep that started catching these would mean
the module's shift structure had changed.

---

## §C Gate C — reachability

### C1 the six varying frames (SYNTHETIC)

| frame | fired | of | distinct | min | max | < 0 | == 0 |
|---|---|---|---|---|---|---|---|
| walk | 1478 | 1500 | 1478 | -0.133111 | 0.039391 | 817 | 0 |
| trend | 1478 | 1500 | 1478 | -0.026934 | 0.030675 | 78 | 0 |
| range-bound | 1478 | 1500 | 1478 | -0.144646 | 0.063879 | 690 | 0 |
| grid | 1478 | 1500 | 1478 | -0.134723 | 0.036384 | 632 | 0 |
| heavy-tailed | 1478 | 1500 | 1478 | -0.316265 | 0.041263 | 767 | 0 |
| jump | 1478 | 1500 | 1478 | -0.110474 | 0.063479 | 775 | 0 |
| **pooled** | **8868** | | **8868** | **-0.316265** | **0.063879** | **3759** | **0** |

On well-formed OHLC the close is at most the 22-bar high, so the column is
bounded above by `3*atr/close` and is unbounded below; it goes negative
exactly when the close has fallen more than three ATRs below that high,
which is what the Chandelier Exit is for.

### C2 the degenerate frames

* **flat** (`high == low == close`): fires on 1,478 of 1,500 and reads
  **exactly 0.0** on every one — every true range is 0, so the ATR is 0 and
  the stop IS the highest high. ⚠ This is the exception to "not a constant
  column", and it is why that limb is asserted on the varying frames only.
* **rising** (a one-way market): fires on 1,478, 1,477 distinct values,
  0.009754 … 0.009879, every reading positive — no drawdown ever puts the
  close three ATRs below its high.

### C3 the real-data limb, from the Gate E run

Everything above is synthetic. The launcher's Gate E run
(`is122-j_chandelier_dist-976ee44b`, 2026-11-16) is where the real bars
come from, and `overlap_max.csv` carries the two counts:

| | over the 89 frozen ALTPORT-1 BIST frames |
|---|---|
| pooled bars | 398,849 |
| non-NaN readings | **396,891** (99.509 %) |
| of those, non-zero | **396,891** — every one |

The 1,958 blank bars are the warm-up: 22 bars per frame × 89 frames =
1,958, so **every** frame loses exactly its first 22 bars and nothing else
goes missing on real data. (That identity is arithmetic on the two printed
counts, not a per-frame scan — the run does not print per-frame NaN counts.)

⚠ The `== 0` limb reads differently on real data than §C2's flat frame
warns it might: `non_zero` equals `non_nan`, so **no** real bar reads
exactly 0.0, even though 86,415 of 408,253 BIST daily bars close exactly at
an extreme (`CLAUDE.md`'s FVGDEAD figure). A zero here needs the close to
sit exactly at the 22-bar high AND the ATR to be exactly 0 — a whole flat
window, not one tied bar.

---

## §D Gate D — scale-freeness

### D1 ×8 / ×64 are bit-identical

True on all six varying frames, both factors, 1,478 of 1,478 bars each.

### D2 inexact factors, max relative move

| frame | ×10 | ×3.7 | ×0.1 | ×1.0000001 |
|---|---|---|---|---|
| walk | 2.575e-12 | 2.204e-12 | 3.219e-12 | 1.561e-12 |
| trend | 1.540e-12 | 3.665e-12 | 8.071e-13 | 4.778e-12 |
| range-bound | 2.251e-11 | 1.064e-11 | 2.110e-11 | 1.422e-12 |
| grid | 3.319e-12 | **2.467e-11** | 1.088e-12 | 1.761e-11 |
| heavy-tailed | 5.190e-12 | 4.442e-12 | 6.778e-12 | 3.314e-12 |
| jump | 1.696e-12 | 7.794e-13 | 6.496e-13 | 2.334e-12 |

Worst of the 24 cells **2.467228e-11**, NaN masks identical in all 24. Under
reduced CPU dispatch the worst cell is the same 2.467228e-11 (grid × 3.7)
while individual cells move by up to an order. The test asserts **1e-9**.

### D3 extreme price levels, with the headroom printed

| level | fired | ×8 | ×64 | largest intermediate | DBL_MAX / it |
|---|---|---|---|---|---|
| 1e-06 | 1478 | True | True | 6.438e-05 | `inf` (the ratio itself overflows) |
| 1e+06 | 1478 | True | True | 6.438e+07 | 2.792e+300 |
| 1e+100 | 1478 | True | True | 6.438e+101 | 2.792e+206 |

The largest intermediate is taken over `high`, `low`, `close`, `tr`, `atr`,
`hh` and `stop`, at ×1, ×8 and ×64 of each level — walked, not reasoned
about.

### D4 a level SHIFT moves every fired bar

`+10` on all three legs moves **1,478 of 1,478** bars on every one of the
six frames. Without this the ×8 bit-identity would be consistent with a
column that reads nothing at all.

---

## §E Gate E — **DISCLOSE_GAP**, measured 2026-11-16

**Gate E: measured 2026-11-16 by issue-solver — DISCLOSE_GAP, the column
ships with a note.** The earlier "pending, run by issue-solver after this
session" line is replaced by the numbers below. The launcher ran
`gate_e_overlap.py run --module pandas_ta.trend.j_chandelier_dist` on the
code at commit `b47887e`; outputs `is122-j_chandelier_dist-976ee44b`,
recorded into `docs/gate_e_ledger.csv` by
`python docs/gate_e_ledger.py record <run dir> --measured 2026-11-16`,
which printed
`j_chandelier_dist:J_CHANDELIER_DIST_22_3.0 DISCLOSE_GAP 0.8609 vs Range_Pos_20`.
Every figure in §E1–§E3 is read off that run's `overlap_max.csv`,
`top25.csv`, `perframe.csv`, `degenerate.csv` and `meta.json`. Neither this
session nor the porting session ran the harness.

### §E1 the verdict

| column | max \|ρ\| | against | set | n | top-5 per-frame max median | verdict |
|---|---|---|---|---|---|---|
| `J_CHANDELIER_DIST_22_3.0` | **0.8609** | `Range_Pos_20` | manifest | **396,891** | **0.8760** (vs the same `Range_Pos_20`) | **DISCLOSE_GAP** |

```
column            J_CHANDELIER_DIST_22_3.0
verdict           DISCLOSE_GAP           (0.80 <= rho < 0.90, r3-perframe-0.90)
pooled max |rho|  0.860867110309758   vs Range_Pos_20         (manifest)  n = 396,891
per-frame         0.87595405414863    vs Range_Pos_20          median over 89 frames
                  5.617977528089887 % of the 89 frames at |rho| >= 0.90
best in compute_all  0.8487899894432914 vs ICHI_PRICE_VS_KIJUN n = 396,624
best in manifest     0.860867110309758  vs Range_Pos_20        n = 396,891
comparators       687 (329 compute_all + 358 manifest), 1 dropped as degenerate
kwargs            {} -- defaults, period 22 / mult 3.0 (module constants)
canary            AKBNK.IS, BIENY.IS, AGHOL.IS, SASA.IS bit-equal
universe          89 ALTPORT-1 frames, 398,849 pooled bars
```

`verdict_pooled_only` is **also** `DISCLOSE_GAP`, so neither limb of the
band carried the other. The one dropped comparator is `squeeze_SQZ_NO`
(manifest), dropped as `constant` — a comparator fault, not this column's,
and the same one `j_acosc` and `j_safezone_dist` dropped.

**DISCLOSE_GAP is a ship with a note, not a strike**, so nothing is
removed: the column stays in `Category`, in `core.py`, in the dictionary and
in `README.md`, and the ledger row needs no waiver (only STRUCK does).
Both limbs are under 0.90: pooled 0.8609 and the top comparator's per-frame
median 0.8760.

**Run facts** (from `meta.json`): module
`pandas_ta.trend.j_chandelier_dist`, `fn` `j_chandelier_dist`, `kwargs`
`{}`, no `end`, nothing excluded, pandas 2.3.3 / numpy 1.26.4, data stamp
`1be6495ef7095ff67ad8f59a2fc0311d74f02652`, universe stamp
`fa3060e68acef410cbc04573ac39450bd210d81d`, candidate source sha1
`a3dbad7f12da70d4a4681196bd45301902cec018`, `pandas_ta_src_sha1`
`7ffe3dfee7a1308b13ae101536ef6e24b6bc0127`. `record` re-derives the verdict
from the run's own CSV and refuses a tree whose `pandas_ta_src_sha1`
differs from the one measured, so the ledger row is not a transcription of
this paragraph.

### §E2 the five per-frame rows, and where the 0.90 line is actually touched

`perframe.csv`, the top five comparators, 89 frames each:

```
against                n_frames  median    mean      max       min      >=0.90   >=0.80
Range_Pos_20                 89  0.87595   0.86946   0.92178   0.46196   5.62 %  97.75 %
ICHI_PRICE_VS_KIJUN          89  0.86793   0.85809   0.92390   0.35265   5.62 %  97.75 %
bias                         89  0.85707   0.85030   0.91430   0.62340   3.37 %  95.51 %
bias_ta                      89  0.85181   0.84304   0.91132   0.61819   2.25 %  92.13 %
ATR_POSITION                 89  0.83882   0.83904   0.91186   0.67211   2.25 %  93.26 %
```

⚠ **Single frames DO cross 0.90 here, and the band is read on the MEDIAN.**
All five comparators have a maximum above 0.90 (0.9119 … 0.9239) and
5.617977528089887 % of 89 frames — **5 frames** — sit at or above 0.90 on
each of the top two. The `r3-perframe-0.90` band strikes on a top-5
comparator's per-frame **median** ≥ 0.90, and the worst median is 0.8760;
so this column is DISCLOSE_GAP and not STRUCK by the rule as written. That
is a different shape from `j_acosc`, where no single frame reached 0.90 at
all, and closer to `j_damiani`'s, where runners-up touched 0.90 on one
frame — except that here the medians are high (0.84 … 0.88) rather than
0.74, and **97.75 %** of frames are above 0.80 on the top comparator. The
agreement is broad, not driven by a handful of frames.

Minimum per-frame \|ρ\| **0.46196** (`Range_Pos_20`) and 0.35265
(`ICHI_PRICE_VS_KIJUN`): at least one frame disagrees substantially, so the
pooled figure is not uniform across the universe either.

### §E3 what the run adds that §E0 could not

**It reproduced the screen's PROTOTYPE band and its top-three comparators,
in order** — `Range_Pos_20` 0.8606 → **0.8609**, `ICHI_PRICE_VS_KIJUN`
0.8485 → **0.8488**, `bias` 0.8438 → **0.8441**, with the per-frame max
median 0.8759 → **0.8760** and n 396,980 → **396,891**.

⚠ **That agreement was not a foregone conclusion and is not evidence that
the two columns are the same arithmetic** — §A3 measures them disagreeing
on 655 … 722 of 1,478 bars by up to 2.0e-02. What it shows is that the
difference is a warm-up transient decaying at `(21/22)^k`: on the six
synthetic frames the last bar that differs at all falls at 732 … 808 (717 …
873 under reduced dispatch, §A3), so on a real frame of ~4,480 bars the
transient covers a small head of it — and Spearman is a rank statistic. ⚠
That per-frame share is an inference from the synthetic decay, not a
measurement on the BIST frames: the run compares this column against the
687 comparators and never against the prototype. The n differs by 89 bars — exactly one bar per
frame — which is §A5's measured fact that the prototype fires one bar
earlier (bar 21, no ATR seed window).

Because an expected agreement is the easiest kind of row to copy over by
mistake, `tests/test_j_chandelier_dist.py::test_the_gate_e_row_is_recorded_and_says_disclose_gap`
pins the row's own run id `is122-j_chandelier_dist-976ee44b`, not only its
arithmetic.

### §E4 the §L prediction, priced against the run

§L measured eight in-fork neighbours on six SYNTHETIC frames and said two
things that the run can now check:

| | §L, synthetic | the run, 89 real frames |
|---|---|---|
| retyped `Range_Pos_20` | 0.9181 (per-frame median) | **0.8760** (per-frame median), 0.8609 pooled |
| `ichimoku_ml:ICHI_PRICE_VS_KIJUN` | 0.9115 | **0.8679** (per-frame median), 0.8488 pooled |
| `bias:BIAS_SMA_26` | 0.9150 | `bias` **0.8571** (per-frame median), 0.8441 pooled |

So §L's "six synthetic frames read HIGH" holds on all three comparators it
could be checked on: +0.0421, +0.0436 and +0.0579 on the per-frame median.
⚠ And §L's other warning is now a measured one rather than a conditional:
the run DID land in DISCLOSE_GAP, so `cksp`'s family is where the redundancy
would live, and **a `cksp` distance column must not be added without
measuring it against this one**. The run cannot price that pair — `cksp`
ships the price LEVEL `CKSPl_10_3_20`, which is not in the 687 comparators
as a distance.

### §E0 what the screen measured, on the PROTOTYPE

⚠ **A prototype is not a port.** These are issue #122's numbers, from run
`screen_r2_20261024` (`gate_e_overlap.py run --module ind_screen_r2 --fn
screen`, Backtesting `main` b2d94243, 89 ALTPORT-1 frames, 398,849 bars,
329 + 358 = 687 comparators, canary bit-equal):

| | |
|---|---|
| max \|ρ\| | **0.8606** vs `Range_Pos_20` (manifest), n = 396,980 |
| top-5 per-frame max median | **0.8759** → **DISCLOSE_GAP** |
| next comparators | `ICHI_PRICE_VS_KIJUN` 0.8485, `bias` 0.8438 |
| fork overlap (stage 2, not Gate E) | max \|ρ\| 0.8603 vs `ichimoku_ml:ICHI_PRICE_VS_KIJUN`, per-frame max median 0.8656, 12 frames |

⚠ The shipped docstring of `pandas_ta/trend/j_chandelier_dist.py` still
reads "the port's own Gate E run … is PENDING" and points here. That file is
outside this receipt session's writable set, so the correction lives in this
receipt and in `docs/gate_e_ledger.csv`, which are the record; the
docstring's own prototype figures (0.8606 / 0.8759) are unaffected by the
run and remain correct as the screen's.

---

## §G guards, bad data and the three overflow routes

### G1 one bad price, and exactly which bars it empties

Planted at bars 100, 700 and 1100, as NaN, +inf and −inf — nine cells per
leg, and the three values behave identically in every cell.

| leg | bars emptied | which | prefix bit-identical |
|---|---|---|---|
| high | **22** | T … T+21 | True |
| low | **0** | — | True |
| close | **1** | T only | True |

A bad **high** is in exactly the 22 windows of `high.rolling(22).max()` that
end at T … T+21.

⚠ **A bad LOW empties nothing and is still not harmless**, and this is the
row where the NaN mask and the values part company: `low` reaches the output
only through the true range, and `wilder_rma` SKIPS a NaN observation rather
than blanking it, so the ATR carries and later bars read different numbers
with no NaN to flag them — 658, 608 and 400 bars moved at the three plant
points.

⚠ **And a bad HIGH moves nothing at bars 100 and 700 while moving every
remaining bar at 1100**, which looks inconsistent until it is measured.
Dropping the high blanks the two true-range legs that use it and leaves
`|low - prev close|`; `max(axis=1)` skips NaN rather than propagating it, so
the true range only changes when a high leg was the winning one — which is
what an UP bar has:

| bar | direction | true range | winning leg | without the high legs |
|---|---|---|---|---|
| 100 | down | 0.442605 | `\|low - prev close\|` | 0.442605 (unchanged) |
| 700 | down | 0.128342 | `\|low - prev close\|` | 0.128342 (unchanged) |
| 1100 | up | 0.145597 | `high - low` | 0.012615 |

⚠ **The helper's NaN rule is a deliberate divergence from TA-Lib's**, stated
rather than assumed. TA-Lib poisons everything after a NaN; `wilder_rma`
carries its state across one. On a frame with a NaN high at bar 700 the
module still fires on 740 of the bars after 760 and the oracle on 0. That is
why Gate A's oracle is run on clean frames and this section exists.

### G2 the five guards, each priced on its own

On all nine frames, every one of the five guards is a **no-op** (bit-equal
with it removed). On probes built to reach them — and a row appears below
only *because* removing that guard changed the column; the loop skips a
guard that is bit-equal:

| probe | guard removed | fired (shipped) | infinite (shipped) | bars differing | max \|abs\| |
|---|---|---|---|---|---|
| high = +inf at bar 700 | high is finite | 1456 (1456) | 0 (0) | **636** (634) | 3.463e-04 |
| low = −inf at bar 700 | low is finite | 1478 (1478) | 0 (0) | **664** (662) | 1.112e-03 |
| close = +inf at bar 700 | close is finite | 1477 (1477) | 0 (0) | **663** (664) | 1.118e-03 |
| close = −50 at bar 700 | close is positive+normal | **1478 (1477)** | 0 (0) | 0 | — |
| 1e300 stop over a 1e-300 close | output is finite | **98 (0)** | **98 (0)** | 0 (no shared bar) | — |

⚠ The second figure in the `bars differing` column is the same cell under
`NPY_DISABLE_CPU_FEATURES="AVX512F AVX512_SKX AVX2 FMA3"`: those three
counts are **dispatch-dependent** (634, 662, 664 against 636, 664, 663),
with the same `max |abs|`. The assertions that rest on them are shapes
(`> 300` bars, `> 1e-5`), not these counts.

⚠ **All five guards are load-bearing, and the first three are load-bearing
in the VALUES rather than in the NaN mask** — which is the correction this
section exists to carry. `fired` and `inf` are identical with and without
each of the first three guards, and the columns still differ on 634 … 664
bars (both dispatches). An earlier draft of this receipt, of the shipped
docstring and of the test header read those equal cells as "the three input
guards move nothing"; the `differ` and `max |abs|` columns are printed so
that reading is no longer available.

The mechanism, and it is **not** "pandas blanks it anyway": with the guard
the bad leg is NaN and `max(axis=1)` SKIPS it, so the true range is the
largest SURVIVING leg and the ATR takes it; without the guard the leg is
infinite, so the true range is infinite and a pandas window DROPS that
observation entirely (§G3). Two different ATRs from bar T onward, with the
same fired-bar count either way. A planted **NaN** is unaffected by these
three guards, because the guard only maps a non-finite value to the NaN it
already is — the guards earn their lines on ±inf.

The close-positivity guard is the one that moves the NaN mask: without it a
close of −50 FIRES, at a large positive reading — the sign flip shipping as
a feature. ⚠ And it blanks that bar only: a zero or negative close is
FINITE, so it still feeds the true range and moves the same bounded run of
later bars §G1 measures for a NaN close — 669 bars at a plant of 100 and
629 at 700, not every later bar.

### G3 three routes to an infinity on FINITE inputs

| route | bars | infinite, guarded | infinite, unguarded | fired, guarded |
|---|---|---|---|---|
| 1. true range (+DBL_MAX high, −DBL_MAX close) | 120 | 0 | **0** | 0 |
| 2. stop (`hh - 3*atr` with an ATR near DBL_MAX/3) | 120 | 0 | **97** | 0 |
| 3. division (a 1e300 stop over a 1e-300 close) | 120 | 0 | **98** | 0 |

⚠ TWO of the three reach the output without the final mask — unlike
`j_safezone_dist`, where pandas' compensated `rolling.sum` absorbed two of
its three. There is no rolling sum in this chain at all, and route 1 is
absorbed by a different pandas behaviour, probed directly:

| probe (81 bars, bad value at bar 40) | `ewm(alpha=1/22, adjust=False)` | through `wilder_rma` |
|---|---|---|
| one `+inf` | 0 infinite, 0 NaN, **bar 40 reads 1.000** | 0 infinite, 21 NaN (the warm-up), bar 40 reads 1.000 |
| one `DBL_MAX` | 0 infinite, 0 NaN, bar 40 reads **8.171e+306** | same, 21 NaN |

A pandas window operation treats an infinity as a **missing observation** —
it leaves no trace at all — while a merely huge finite value flows straight
through. That behaviour is pinned on its own in the test file, so an upgrade
that moves it fails there rather than shipping an infinite feature.

### G4 degenerate and hostile frames raise nothing

| constant frame (60 bars) | fired | infinite | distinct | min … max |
|---|---|---|---|---|
| 0.0 | 0 of 60 | 0 | 0 | — |
| −100.0 | 0 of 60 | 0 | 0 | — |
| 5e-310 (subnormal) | 0 of 60 | 0 | 0 | — |
| 1e308 | 38 of 60 | 0 | 1 | 0.0 … 0.0 |
| all-NaN | 0 of 60 | 0 | 0 | — |

Frames of 0, 1, 5 and 22 bars return `None`; a 23-bar frame fires on 1 bar.
An all-NaN frame returns an empty column rather than the `None`
`wilder_rma` would hand back.

---

## §L in-fork overlap — a DISCLOSURE, not Gate E

Spearman \|ρ\| against eight chosen in-fork neighbours over the six varying
frames:

| neighbour | walk | trend | range-bound | grid | heavy-tailed | jump | median |
|---|---|---|---|---|---|---|---|
| `cksp`: (close − `CKSPl_10_3_20`)/close | 0.9309 | 0.9658 | 0.9310 | 0.9452 | 0.9007 | 0.9330 | **0.9320** |
| (retyped analogue) `Range_Pos_20` | 0.9205 | 0.9111 | 0.9252 | 0.9441 | 0.9040 | 0.9158 | 0.9181 |
| `bias`: `BIAS_SMA_26` | 0.9443 | 0.6345 | 0.9055 | 0.9084 | 0.9216 | 0.9353 | 0.9150 |
| `ichimoku_ml`: `ICHI_PRICE_VS_KIJUN` | 0.9355 | 0.5811 | 0.9155 | 0.9074 | 0.9072 | 0.9326 | 0.9115 |
| `vstop`: `VSTOP_DIST_PCT_20_1.0` | 0.4760 | 0.8174 | 0.4204 | 0.5447 | 0.4840 | 0.4634 | 0.4800 |
| `j_safezone_dist`: `J_SAFEZONE_DIST_22_2.5_3` | 0.3259 | 0.7060 | 0.3391 | 0.3847 | 0.0787 | 0.2950 | 0.3325 |
| `chop`: `CHOP_14_1_100` | 0.2662 | 0.3205 | 0.1104 | 0.0891 | 0.2200 | 0.1672 | 0.1936 |
| `natr`: `NATR_14` | 0.0843 | 0.2854 | 0.1317 | 0.0399 | 0.2087 | 0.1549 | 0.1433 |

Three things this table is not, each measured rather than hedged:

1. **It is not Gate E** — but it is not necessarily invisible to it either,
   and the honest statement is agnostic. The 687 comparators are the
   engine's `compute_all` ∪ the `ml_features` manifest `1d`, and neither is
   readable from this worktree (`../Backtesting` is out of bounds for this
   session). ⚠ **Three of the eight rows below carry names from §E's
   comparator list** — `ICHI_PRICE_VS_KIJUN` (0.8485 on the screen's
   prototype run), `bias` (0.8438), and `Range_Pos_20` (**0.8606**, the
   figure that decided the prototype's band; the row here is that rule
   retyped, not the manifest's column, which this worktree cannot read) —
   and `CLAUDE.md` records that the engine's `indicator_engine.py` calls
   this fork. Whether the engine computes any of the three *through*
   `pandas_ta` is **still not checked in this repo**. ⚠ But the port's own
   run settles the other half: those three names are the run's own **top
   three comparators** — `Range_Pos_20`, then `ICHI_PRICE_VS_KIJUN`, then
   `bias`, which is this table's order with the last two swapped — so §L
   previewed the gate rather than being blind to it (§E4). The other five are pandas_ta ports
   or derived columns with no counterpart in the run's `top25.csv`.
2. **Six synthetic frames read HIGH**, and after the port's own run this
   can be checked on three rows rather than one. Per-frame median, synthetic
   here against 89 real BIST frames: retyped `Range_Pos_20` **0.9181 vs
   0.8760** (+0.0421), `ICHI_PRICE_VS_KIJUN` **0.9115 vs 0.8679** (+0.0436),
   `bias` **0.9150 vs 0.8571** (+0.0579). Against the screen's pooled
   prototype figure the first row read +0.0575. A figure in this table is an
   upper-ish reading, on every row where both figures exist.
3. **The nearest neighbour is a column the fork does not ship.** `cksp`'s
   long leg is `HH(10) − 3·ATR(10)` run through a second 20-bar maximum —
   the same family as the Chandelier Exit — but what `cksp` SHIPS is the
   price LEVEL `CKSPl_10_3_20`, which the ML contract does not treat as a
   feature. The row above is that level turned into a distance by
   `docs/measure_j_chandelier_dist.py`. It belongs in the receipt anyway,
   because a consumer could build it in one line.

⚠ What this flags for the owner, and the condition is now **met**: the
port's own Gate E run landed in DISCLOSE_GAP, as the screen's prototype did
(§E). So the `cksp` family is where the redundancy would live, and a `cksp`
distance column must not be added without measuring it against this one.
§E4 prices the three rows of this table that the run could check — all
three read 0.042 … 0.058 HIGHER here than on 89 real frames.

---

## §Z cost — this machine, this run

Order of magnitude and shape only, because the digits do not survive a
second run on the same machine: **~0.2 … 0.35 µs per bar** at 400,000 bars
and **~2.5 … 3.5 ms per 1,500-bar call**, over several runs of three under
different machine load. The §Z triples observed so far at 400,000 bars —
two from this session, one from the round-3 review and one from the
round-4 review — read 89.0 / 77.4 / 81.2 ms, 91.8 / 78.8 / 81.8 ms,
133.8 / 107.8 / 108.8 ms and 91.8 / 80.1 / 92.0 ms. What is
claimed is **linearity in bars**, which the formula gives: one `concat` of
three legs, one rolling maximum, one Wilder EWMA, two shifts and one
division. ⚠ One machine; nothing else in this receipt is meant to depend
on it.

---

## §F suites

The figures of the porting session (2026-11-16) were **254 passed** for the
module and **2 failed, 12,107 passed, 86 skipped** for the repo, the second
failure being the owed Gate E row. The receipt session re-ran both after
recording the row and swapping the two pending-Gate-E tests for three that
pin it (`+1` test):

* `python -m pytest tests/test_j_chandelier_dist.py -q` — **255 passed**.
* The same 255 under
  `NPY_DISABLE_CPU_FEATURES="AVX512F AVX512_SKX AVX2 FMA3"` via
  `python docs/measure_j_chandelier_dist_cpu.py`, which prints the
  dispatchable features still enabled (`SSSE3 SSE41 POPCNT SSE42 AVX F16C
  AVX512CD AVX512_CLX AVX512_CNL AVX512_ICL`) and refuses to run if any of
  the four survived.
* `python -m pytest tests/test_j_chandelier_dist.py tests/test_gate_e_ledger.py -q`
  — **1,353 passed**, so the ledger module is green now that the row
  exists.
* Full repo suite: **1 failed, 12,116 passed, 86 skipped**. The one failure
  is `tests/test_altrepo_talib_csv.py::test_regenerating_reproduces_the_
  committed_rows`, which needs the sibling `../AlternativeRepos` checkout
  (`pandas-ta-classic not found at …`) and which CI deselects by name.
  `tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_
  one` passed: §E's row is recorded. The parent repo's suite is the
  launcher's.
  ⚠ Two other tests failed on intermediate runs and are green now, and
  both are worth knowing about because neither is obvious:
  `tests/test_ml_companions.py::test_the_contract_quotes_the_dictionarys_
  actual_ml_form_counts` (the tagged-column total in
  `docs/MLCompanionContract.md` had to move from 701 to 702 — which is also
  the independent check that this port adds exactly one `SF` column), and
  `tests/test_pine_coverage_csv.py::test_no_other_document_retypes_the_split`,
  which fires on any document in the fork containing five or more
  slash-joined numbers. The round-1 review quoted a list of nine sampled
  bar indices that way inside
  `docs/reviews/auto-2026-11-16-j-chandelier-dist/01-j-chandelier-dist.md`;
  the quote now uses commas and says so.

## Wiring

| # | File | What |
|---|---|---|
| 1 | `pandas_ta/trend/j_chandelier_dist.py` | the indicator |
| 2 | `pandas_ta/trend/__init__.py` | package export |
| 3 | `pandas_ta/__init__.py` → `Category["trend"]` | discovery / `df.ta.strategy` |
| 4 | `pandas_ta/core.py` | `df.ta.j_chandelier_dist()` |
| 5 | `tests/test_j_chandelier_dist.py` | the test suite |

Plus the counted surfaces: `README.md`, `docs/IndicatorDictionary.md`,
`docs/MLCompanionContract.md` and `tests/test_altport2_ports.py`.
