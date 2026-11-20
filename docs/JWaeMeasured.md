# J-WAE — measured

PandasTa issue **#123**: *Waddah Attar Explosion: MACD-change power over
Bollinger width*. Shipped as `pandas_ta/momentum/j_wae.py`, one column
**`J_WAE_150_20_40_20_2.0`**.

```
macd[T] = EMA(close, 20)[T] - EMA(close, 40)[T]      both SMA-seeded
t1[T]   = (macd[T] - macd[T-1]) * 150
e1[T]   = BBupper(close, 20, 2)[T] - BBlower(close, 20, 2)[T]
J_WAE[T] = t1[T] / e1[T]                             blank where e1 <= 0
```

Source: jesse indicators (MIT), `waddah_attar_explosion.py`, as issue #123
quotes it — `t1 = (MACD20/40 - MACD20/40[1])*150, e1 = BB20,2 upper -
lower`. The underlying rule is Waddah Attar's "Explosion" histogram, which
the TradingView community knows through LazyBear's transcription. The issue
says of the library: *existence, not evidence*.

**Every number below is printed by `python docs/measure_j_wae.py`** (section
names match the headings) and the figures that move between numpy CPU
dispatches are re-printed by `python docs/measure_j_wae_cpu.py <section>`.

⚠ **Six exceptions, named here rather than left for a reader to find.**
The script has no §F section and does not read the repo's documents, so:

1. §F's counts (`245 passed`, `2 warnings`, the collected totals and the
   full-suite line) are **pytest's**, from the runs named there;
2. the before/after counts quoted from other documents — §F's `704 → 705`
   tagged columns and `341 → 342` `SF` (**`docs/MLCompanionContract.md`'s**,
   checked by
   `tests/test_ml_companions.py::test_the_contract_quotes_the_dictionarys_actual_ml_form_counts`)
   and the Wiring table's `359 → 360` / `367 → 368` / `87 → 88`
   (**`README.md`'s**, checked by `tests/test_readme_counts.py`) — are read
   off those files' diffs;
3. §E0's screen figures are **issue #123's**, quoted: run
   `screen_r2_20261024`, 89 ALTPORT-1 frames, 398,849 bars, 329 + 358
   comparators, canary bit-equal, 0.8698 / `BB_PctB_Pctl` / n = 391,907 /
   0.8715 / 0.8565 / 0.8536, and the fork-overlap stage's 0.8562 / 0.8606
   on 12 frames (§L's script prints 0.8562 as a quoted line, not as a
   measurement). **§E1, §E2 and §C3's real-data block are the launcher's
   Gate E run** of 2026-11-20 (`is123-j_wae-39655747`), read out of its
   output folder — also not this script's, and not readable from this
   worktree;
4. the "web access is unavailable" line below is a fact about the session,
   not a printed measurement. The jesse-absence flag next to it **is**
   printed, by §ENV;
5. the **asserted bounds** quoted next to several measurements — 1e-7 and
   Spearman > 0.9999 at §A1, 1e-7 at §D2, `> 1000` differing bars and
   "still differing after bar 1,450" at §A4, `0.9 < ratio < 1.0` at §A4(c),
   `> 150` zero-width bars at §G2 — are **`tests/test_j_wae.py`'s own
   constants**, not run output; the measured value beside each one is;
6. the reduced-dispatch figures (§A1b's last paragraph, §A4's ⚠ line) are
   printed by `python docs/measure_j_wae_cpu.py A1B A4`, not by
   `measure_j_wae.py`.

Everything else in this receipt is a cell from a run.

Run environment (§ENV): python 3.11.2 · numpy 1.26.4 · pandas 2.3.3 · talib
0.7.1 installed · **jesse NOT installed** · `pandas_ta` imported from
this checkout (`pandas_ta/__init__.py`); web access is unavailable in
this worktree.

⚠ **And nothing in this receipt is a statement about what jesse's code
says.** jesse is not installed and cannot be read, so which EMA seeding it
uses, which standard deviation its bands take, and whether it ships this
ratio at all — its own output is the pair `t1`/`e1` with a dead zone, not
their quotient — are **not claimed**. The reading of `EMA` as the
SMA-seeded one rests on two checkable things: this fork's own `ema`, and
TA-Lib's `EMA`, which this worktree can run, and does, in §A5. The RATIO is
issue #123's scale-free conversion, "t1 / e1 (both price units)", and it is
what the 2026-10-24 screen measured.

---

## Verdict

| Gate | Result |
|---|---|
| A Correctness | **PASS** — matches an independent bar-by-bar oracle on 1,460 of 1,460 bars of each of six frames, identical NaN masks, to 1.692e-10 absolute / 4.302e-11 relative at Spearman 1.0000; the MACD leg is BIT-EQUAL to this fork's `macd` and the width leg BIT-EQUAL to its `bbands`; `talib.EMA(20) - talib.EMA(40)` is the same leg to 1.273e-11, firing at the same bar |
| B Causality | **PASS** — 0 of 36 sweep catches on six frames; six look-ahead mutants live and caught 36 of 36 on three frames; three blind-spot edits caught 0 by the sweep and all three by the oracle |
| C Reachability | **PASS** — synthetic: 1,460 of 1,500 bars on each of six frames, 1,460 distinct values each, 4,297 of 8,760 pooled bars negative, **0 exactly zero**; real (the Gate E run): **395,289 of 398,849** BIST bars fire and the same **395,289** are non-zero, so **0** real fired bar reads exactly 0.0 (§C3) |
| D Scale-free | **PASS** — ×8/×64 bit-identical on six frames and at price levels 1e-6, 1e+6, 1e+100; ×10/×3.7/×0.1/×1.0000001 within 5.267e-10 absolute with every NaN mask matching; `0 < fires < n`. ⚠ The usual "a level shift moves it" non-vacuity limb FAILS here, because the column is affine-invariant; §D5 substitutes a one-bar nudge |
| E Attribution | **DISCLOSE_GAP — ships with the disclosure** — max \|ρ\| **0.8698142454259801** vs the manifest's `BB_PctB_Pctl` over n = **391,907**, top-five per-frame max median **0.8715545505700394** over **89** frames, 687 comparators; measured 2026-11-20 by issue-solver, run `is123-j_wae-39655747` (§E1). No column is removed and no waiver is needed |
| F Suites | this repo's suite run below; both repos' suites are the launcher's |

**The one thing to read first.** This port does **not** reproduce the screen
prototype, and that is deliberate: the issue says *Gate A starts from the
source formula, not the prototype*. `EMA` is read as the **SMA-seeded** one
— this fork's `ema`, and TA-Lib's — while the prototype recurses from bar 0
with no seed and uses the algebraic width `4σ`. §A4 measures the gap:
**1,399 … 1,435 of the 1,460 shared bars disagree**, by up to **2.664e+00**,
and unlike `j_chandelier_dist`'s warm-up transient it **does not wash out** —
the last disagreement falls at bar 1,499 of 1,500 on all six. The prototype
also fires 21 bars earlier. So the screen's DISCLOSE_GAP figures were
evidence about a **neighbouring column**, and the port's own Gate E run of
2026-11-20 is what decided this one's band.

**And it landed on the same band and the same comparator.** Max \|ρ\|
**0.8698142454259801** vs `BB_PctB_Pctl` over n = 391,907, per-frame max
median 0.8715545505700394 — the leading figure, the comparator and n to
every digit issue #123 prints, while the 2nd and 3rd comparators moved in
the fourth decimal (`MACD_Hist_ATR` 0.8568 against 0.8565,
`MACD_Hist_ATR_Pctl` 0.8535 against 0.8536). Two columns 2.664e+00 apart at
Spearman 0.9983 … 1.0000 is exactly the shape that moves a **rank**
correlation by ~1e-4 and leaves the band where it was. §E2 reads it out.

**The second thing.** This column is **affine-invariant**, not merely
scale-free: every EMA of `close + k` is that EMA plus `k`, so the MACD
cancels the shift and the standard deviation ignores it. A +10 level shift
moves the column by at most **3.564e-11** (§D4). That is worth knowing
twice over — it makes the usual Gate D non-vacuity check useless here (§D5
replaces it), and it means the column carries **no** information about the
price level at all, only about its shape.

---

## §A1 Gate A — against a bar-by-bar oracle

The oracle shares no code with the module: its own `math.fsum` SMA seed,
its own EMA recursion over plain Python floats, its own windowed mean and
population variance, and the LITERAL band subtraction the issue quotes.

| frame | fired | masks | bit-equal | max \|abs\| | max rel | Spearman |
|---|---|---|---|---|---|---|
| walk | 1460 | True | False | 1.104e-10 | 2.034e-11 | 1.0000 |
| trend | 1460 | True | False | 1.669e-11 | 5.396e-12 | 1.0000 |
| range-bound | 1460 | True | False | 3.045e-12 | 9.166e-13 | 1.0000 |
| grid | 1460 | True | False | 1.692e-10 | 3.283e-11 | 1.0000 |
| heavy-tailed | 1460 | True | False | 1.081e-10 | 3.409e-11 | 1.0000 |
| jump | 1460 | True | False | 1.604e-10 | 4.302e-11 | 1.0000 |

First firing bar: **40** on all six. Asserted: 1e-7 absolute, 1e-7
relative, masks identical, Spearman > 0.9999.

## §A1b WHICH leg carries that gap

⚠ Attributed, not excused — and the first draft of the matching test
attributed it to the wrong leg and FAILED, which is why this section
exists.

| frame | ema20 | ema40 | macd | t1 | e1 (max rel) |
|---|---|---|---|---|---|
| walk | 2.842e-14 | bit-equal | bit-equal | bit-equal | 2.034e-11 |
| trend | 2.842e-14 | bit-equal | bit-equal | bit-equal | 5.396e-12 |
| range-bound | 2.842e-14 | bit-equal | bit-equal | bit-equal | 9.167e-13 |
| grid | bit-equal | bit-equal | bit-equal | bit-equal | 3.283e-11 |
| heavy-tailed | bit-equal | bit-equal | bit-equal | bit-equal | 3.409e-11 |
| jump | bit-equal | 1.421e-14 | 1.421e-14 | 2.132e-12 | 4.302e-11 |

The column's relative gap matches `e1`'s to three significant digits on
every frame (§A1's max rel against this table's last column), which is
what the ratio does with it. `e1` differs because pandas' `rolling.var`
is an online update and the oracle's is a two-pass `fsum`.

Both EMA legs are bit-equal on **two** of the six frames (`grid`,
`heavy-tailed`); on the other **four** one leg differs, by at most
2.842e-14. Where it differs, the SEED differs too — §A1b's second table,
run on all six frames:

| frame | seed20 equal | ema20 bit-equal | seed40 equal | ema40 bit-equal |
|---|---|---|---|---|
| walk | False (1.421e-14) | False (2.842e-14) | True | True |
| trend | False (1.421e-14) | False (2.842e-14) | True | True |
| range-bound | False (2.842e-14) | False (2.842e-14) | True | True |
| grid | True | True | True | True |
| heavy-tailed | True | True | True | True |
| jump | True | True | **False (1.421e-14)** | **False (1.421e-14)** |

So on these frames a leg is bit-equal exactly when its `Series.mean()`
seed equals the oracle's `math.fsum` seed, `jump`'s 40-bar leg included:
the residue enters at the seed, and the recursion forms agree on every
frame where the seeds do. Under numpy's reduced CPU dispatch
(`python docs/measure_j_wae_cpu.py A1B`) all twelve seeds are equal and
every EMA, MACD and `t1` leg is bit-equal on all six frames; only `e1`
differs.

## §A2 the EMA the module imports, and where it seeds

The module takes `ema` from its own module — `from pandas_ta.overlap.ema
import ema`, as `CLAUDE.md` prescribes and as ten other momentum modules
already do — and calls it at its defaults. What that does, printed:

| frames | length | first fire | seed == mean of first `length` closes | bars differing from a bar-0 `ewm` |
|---|---|---|---|---|
| walk / trend / range-bound / grid / heavy-tailed / jump | 20 | 19 | True | 325 / 314 / 298 / 287 / 300 / 306 |
| same six | 40 | 39 | True | 699 / 538 / 589 / 646 / 598 / 582 |
| flat / rising | 20 | 19 | True | 0 / 336 |
| flat / rising | 40 | 39 | True | 0 / 599 |

So `ema` is SMA-seeded on all 16 cells, which is the reading §A4 shows is
load-bearing. `test_the_forks_ema_is_still_sma_seeded` pins the first fire
and the seed on the same 16 cells, so a change to `ema`'s defaults fails in
`tests/test_j_wae.py` rather than only moving the column.

## §A3 the MACD leg is this fork's `macd`

`macd(close, fast=20, slow=40)["MACD_20_40_9"]` is **bit-equal** to
`ema(close, 20) - ema(close, 40)` on all six frames (1,461 fired bars).
The module does not call `macd` itself because `macd` would also compute a
9-bar signal line and histogram this column does not use.

## §A4 the readings NOT taken, priced

### (a) the screen prototype — no SMA seed, algebraic width

| frame | shared | differ | max \|abs\| | last differing bar | Spearman | its first fire |
|---|---|---|---|---|---|---|
| walk | 1460 | 1414 | 2.664e+00 | 1499 | 0.9983 | 19 |
| trend | 1460 | 1413 | 2.085e-01 | 1499 | 1.0000 | 19 |
| range-bound | 1460 | 1399 | 1.543e-02 | 1499 | 1.0000 | 19 |
| grid | 1460 | 1435 | 4.702e-02 | 1499 | 1.0000 | 19 |
| heavy-tailed | 1460 | 1403 | 4.188e-01 | 1499 | 1.0000 | 19 |
| jump | 1460 | 1416 | 9.544e-02 | 1499 | 1.0000 | 19 |

⚠ Under numpy's reduced CPU dispatch the differing counts move
(1,390 … 1,435) and `range-bound`'s last differing bar is **1,496**, so the
test asserts "> 1000 bars differ" and "still differing after bar 1,450",
not the cells.

### (b) pandas' `adjust=True`

1,065 … 1,113 of 1,460 bars differ, by up to **4.495e+00**, Spearman
0.9950 … 0.9999, first fire 19, last differing bar 1,496 … 1,499.

### (c) a SAMPLE standard deviation in the width (`ddof=1`)

**All 1,460** bars differ, by up to **3.105e-01**, Spearman 1.0000, same
first fire. A `ddof=1` width is WIDER, so that reading is a column SMALLER
in magnitude: the median |alt| / |module| is **0.9747** on every frame
(the test asserts `0.9 < ratio < 1.0`).

## §A5 TA-Lib as the third speller

`talib.EMA(close, 20) - talib.EMA(close, 40)` (talib 0.7.1), against the
module's MACD leg:

| frame | bit-equal | max \|abs\| | max rel | talib first fire | ours |
|---|---|---|---|---|---|
| walk | False | 1.279e-13 | 1.087e-10 | 39 | 39 |
| trend | False | 1.273e-11 | 1.771e-13 | 39 | 39 |
| range-bound | False | 1.705e-13 | 6.747e-11 | 39 | 39 |
| grid | False | 2.558e-13 | 1.339e-10 | 39 | 39 |
| heavy-tailed | False | 1.421e-13 | 2.033e-11 | 39 | 39 |
| jump | False | 2.274e-13 | 2.823e-09 | 39 | 39 |

The **first-fire agreement is the load-bearing cell**, not the magnitude:
it is what makes "EMA means the SMA-seeded one" a run rather than a
memory. ⚠ It is NOT a stand-in for jesse's code.

## §A6 the width is the LITERAL band subtraction

`bbands(close, 20, 2.0)`'s `BBU - BBL` is **bit-equal** to the module's
`e1` on all six frames. The algebraic `2 * MULT * sd` is not: the WIDTH
differs by up to **1.819e-12** (7.220e-15 relative), and the COLUMN differs
on **1,357 … 1,410 of 1,460** bars by up to **5.329e-14** at Spearman
1.0000.

| frame | vs `bbands` | vs `2·MULT·sd` (width) | column differs | column max \|abs\| |
|---|---|---|---|---|
| walk | bit-equal | 1.421e-14 | 1388 | 4.619e-14 |
| trend | bit-equal | 1.819e-12 | 1392 | 3.819e-14 |
| range-bound | bit-equal | 1.421e-14 | 1357 | 1.066e-14 |
| grid | bit-equal | 2.842e-14 | 1410 | 3.375e-14 |
| heavy-tailed | bit-equal | 1.421e-14 | 1370 | 5.329e-14 |
| jump | bit-equal | 2.842e-14 | 1389 | 3.730e-14 |

The issue quotes "BB20,2 upper - lower", so the literal route is what
ships. Where the variance overflows, §G3 finds the two readings agree
(both inf on the overflowing bar, both NaN after it), so the choice rests
on the last-bits difference above and nothing else.

---

## §B1 Gate B — the blind future sweep

Perturb every bar from J onward by ×1.03 and assert nothing before J moves.
36 J values (1,464 … 1,499).

| frame | the module |
|---|---|
| walk / trend / range-bound / grid / heavy-tailed / jump | **0 of 36** each |

Six look-ahead mutants, read off the shipped source, edited and `exec`'d in
memory, over `walk`, `trend` and `heavy-tailed`:

| mutant | walk | trend | heavy | smallest first catch |
|---|---|---|---|---|
| close-lead | 36 | 36 | 36 | 1.668e+00 |
| macd-lead | 36 | 36 | 36 | 1.937e+00 |
| t1-lead | 36 | 36 | 36 | 1.937e+00 |
| window-lead | 36 | 36 | 36 | 2.539e-02 |
| sd-lead | 36 | 36 | 36 | 2.539e-02 |
| output-early | 36 | 36 | 36 | 1.668e+00 |

Every one is caught at every offset. The quietest first catch, 2.539e-02,
stands against a loudest inexact-rescale move of 5.267e-10 (§D2), so no
catch is a rounding artefact.

## §B2 the sweep's blind spot, and the oracle covering it

Three edits that are WRONG without reading any later bar:

| mutant | sweep (walk) | live? | vs the oracle, max \|abs\| | differing bars |
|---|---|---|---|---|
| t1-two-bar-change | **0 of 36** | yes | 1.220e+01 | 1459 |
| e1-lagged | **0 of 36** | yes | 2.956e+00 | 1460 |
| sample-stdev | **0 of 36** | yes | 2.929e-01 | 1460 |

That is the limit of a causality sweep, stated rather than left to be
found: it sees only reads of the FUTURE. Gate A's oracle rejects all three.

---

## §C Gate C — reachability

### C1 the six varying frames (SYNTHETIC)

| frame | fired | of | distinct | min | max | < 0 | == 0 | \|v\| ≤ 10 |
|---|---|---|---|---|---|---|---|---|
| walk | 1460 | 1500 | 1460 | -8.1833e+00 | 1.1568e+01 | 722 | 0 | 1457 |
| trend | 1460 | 1500 | 1460 | -7.5626e+00 | 3.7905e+00 | 665 | 0 | 1460 |
| range-bound | 1460 | 1500 | 1460 | -5.8524e+00 | 5.6958e+00 | 737 | 0 | 1460 |
| grid | 1460 | 1500 | 1460 | -6.8906e+00 | 6.8436e+00 | 740 | 0 | 1460 |
| heavy-tailed | 1460 | 1500 | 1460 | -8.0599e+00 | 1.2263e+01 | 691 | 0 | 1454 |
| jump | 1460 | 1500 | 1460 | -8.7671e+00 | 8.0532e+00 | 742 | 0 | 1460 |
| **POOLED** | **8760** | 9000 | 8760 | **-8.7671e+00** | **1.2263e+01** | **4297** | **0** | **8751** |

The 40 missing bars of each frame are the leading warm-up, a prefix with no
holes (pinned by `test_reachability_on_the_varying_frames`).

### C2 the two degenerate frames

| frame | fired | distinct | min | max |
|---|---|---|---|---|
| flat (constant close) | **0 of 1500** | — | — | — |
| rising (arithmetic ramp) | 1460 of 1500 | 193 | -1.844667e-12 | 1.844667e-12 |

* **flat**: `e1` is exactly 0.0 on all 1,481 full windows and `t1` is
  exactly 0.0, so the `e1 > 0` guard blanks every bar. This column has
  nothing to say about a price that does not move.
* **rising**: the MACD of an arithmetic ramp is constant, so `t1` is zero
  up to the last bits (±4.263e-12) over a constant width of 2.311126e+00.
  It fires everywhere and says nothing — the second shape to know about.

Both are why "not a constant column" is asserted on the VARYING frames
only.

### C3 the real-data limb — **MEASURED** (the Gate E run, 2026-11-20)

From `overlap_max.csv` of run `is123-j_wae-39655747`, over the 89 frozen
ALTPORT-1 BIST frames:

| figure | value |
|---|---|
| pooled bars | **398,849** |
| non-NaN (fired) | **395,289** |
| non-zero | **395,289** |

So the column fires on **395,289 of 398,849** real bars, and the **same
395,289** are non-zero: **0** real fired bar reads exactly 0.0, which is the
real-data limb of the `== 0` column §C1 measures on synthetic frames (0 on
each of the six, 0 pooled).

`398,849 − 395,289 = 3,560 = 89 × 40` — the 40-bar warm-up §C1 measures,
recounted here as an identity between two of the run's own numbers. ⚠ It is
**not** a per-frame measurement: the run prints no per-frame fired count, so
"every frame loses exactly its leading 40 bars" is consistent with these two
totals and is **not** measured. Nor is any infinity count printed, so "no
real bar is infinite" is **not** measured either — §G2 and §G3's routes are
synthetic.

The comparator the band reads, `BB_PctB_Pctl`, overlaps on n = **391,907**
of those 395,289 bars, 3,382 fewer: the comparator's own missing bars, not
this column's.

---

## §D Gate D — scale-freeness

### D1 ×8 / ×64 are bit-identical

Bit-identical on **1,460 of 1,460** bars of each of the six varying frames,
for both factors. Both legs are homogeneous of degree 1 in the price and a
power of two scales every intermediate exactly, so this is an equality and
not a tolerance.

### D2 inexact factors — masks, absolute and relative

24 cells (6 frames × ×10, ×3.7, ×0.1, ×1.0000001). **Every NaN mask
matches.** Worst of the 24: **max \|abs\| 5.267e-10**, max relative
**1.535e-07**, max relative over the bars reading \|value\| ≥ 1e-3
**4.964e-10**.

⚠ The relative figure is printed twice on purpose. This column crosses
zero — §C1 shows 4,297 of 8,760 bars negative — so a relative gap measured
at a bar reading 1e-13 is a division by the cancellation, not a scaling
failure. The 1.535e-07 is `trend`'s, and the same frame's largest ABSOLUTE
move across all four factors is 5.376e-11. The test therefore asserts the
absolute gap (1e-7) plus the relative gap restricted to \|value\| ≥ 1e-3
(1e-7).

### D3 extreme price levels, with the headroom printed

| frame | level | fired | ×8 | ×64 | largest \|t1\| | largest e1 |
|---|---|---|---|---|---|---|
| walk | 1e-06 | 1460 | bit-equal | bit-equal | 3.241e-07 | 1.638e-07 |
| walk | 1e+06 | 1460 | bit-equal | bit-equal | 3.241e+05 | 1.638e+05 |
| walk | 1e+100 | 1460 | bit-equal | bit-equal | 3.241e+99 | 1.638e+99 |
| trend | 1e-06 | 1460 | bit-equal | bit-equal | 2.506e-05 | 1.318e-05 |
| trend | 1e+06 | 1460 | bit-equal | bit-equal | 2.506e+07 | 1.318e+07 |
| trend | 1e+100 | 1460 | bit-equal | bit-equal | 2.506e+101 | 1.318e+101 |
| range-bound | 1e-06 | 1460 | bit-equal | bit-equal | 8.099e-07 | 2.537e-07 |
| range-bound | 1e+06 | 1460 | bit-equal | bit-equal | 8.099e+05 | 2.537e+05 |
| range-bound | 1e+100 | 1460 | bit-equal | bit-equal | 8.099e+99 | 2.537e+99 |

Largest intermediate at 1e100: **2.506e+101** (`trend`'s `t1`), against
DBL_MAX **1.798e+308**.

### D4 ⚠ a level SHIFT moves it by nothing either — it is AFFINE-invariant

| frame | fired | bars moved by +10 | max \|abs\| | max rel over \|v\| ≥ 1e-3 |
|---|---|---|---|---|
| walk | 1460 | 1260 | 3.564e-11 | 2.884e-10 |
| trend | 1460 | 1442 | 3.043e-11 | 1.089e-10 |
| range-bound | 1460 | 760 | 8.784e-13 | 5.697e-11 |
| grid | 1460 | 925 | 1.665e-11 | 8.076e-11 |
| heavy-tailed | 1460 | 870 | 1.629e-11 | 4.160e-11 |
| jump | 1460 | 1152 | 2.526e-11 | 2.971e-11 |

Every EMA of `close + k` is that EMA plus `k` (the seed is a mean), so the
MACD cancels `k` exactly, and a standard deviation ignores it. The residue
above is the last bits. **So the "a +10 shift moves every fired bar" limb
that `j_chandelier_dist` and `j_safezone_dist` use to show their ×8
bit-identity is not vacuous does not transfer**, and §D5 is what does the
job here.

### D5 the non-vacuity check that does work: one bar

A +1 % bump at bar 700 — which no rescale and no shift can imitate:

| frame | bars moved | of | max \|abs\| | first moved bar |
|---|---|---|---|---|
| walk | 800 | 1460 | 9.126e-01 | 700 |
| trend | 594 | 1460 | 4.940e-01 | 700 |
| range-bound | 800 | 1460 | 6.984e-01 | 700 |
| grid | 800 | 1460 | 9.513e-01 | 700 |
| heavy-tailed | 800 | 1460 | 1.040e+00 | 700 |
| jump | 800 | 1460 | 9.235e-02 | 700 |

`800` is the structural number: bars 700 … 1499 are every bar at or after
the nudge. Why `trend` moves only 594 of them is **not measured here**.

### D6 `0 < fires < n`

| frame | fired | of | 0 < fires < n | distinct | > 1 distinct |
|---|---|---|---|---|---|
| walk / trend / range-bound / grid / heavy-tailed / jump | 1460 | 1500 | True | 1460 | True |

So no constant column passes Gate D by being invariant for the wrong
reason.

---

## §E Gate E

**Gate E: measured 2026-11-20 by issue-solver.** Run
`is123-j_wae-39655747`,
`gate_e_overlap.py run --module pandas_ta.momentum.j_wae` at default
parameters, recorded into `docs/gate_e_ledger.csv` by
`python docs/gate_e_ledger.py record … --measured 2026-11-20`, which printed
`j_wae:J_WAE_150_20_40_20_2.0 DISCLOSE_GAP 0.8698 vs BB_PctB_Pctl`.

⚠ Every figure in §E1 and §E2 is the **launcher's** run output, read out of
that folder's `overlap_max.csv`, `top25.csv`, `perframe.csv`,
`degenerate.csv` and `meta.json`. `docs/measure_j_wae.py` prints none of
them, and this worktree can neither read the 89 frames nor run the harness;
`python docs/measure_j_wae_contract.py` prints the ledger row the documents
have to agree with.

### §E1 the verdict

| figure | value |
|---|---|
| column | `J_WAE_150_20_40_20_2.0` |
| pooled max \|ρ\| | **0.8698142454259801** (positive; `rho` = `abs_rho`) |
| against | **`BB_PctB_Pctl`**, from the `ml_features` manifest |
| n | **391,907** |
| per-frame max median \|ρ\| | **0.8715545505700394**, against `BB_PctB_Pctl`, over **89** frames |
| verdict | **DISCLOSE_GAP** (`r3-perframe-0.90`), pooled-only verdict the same |
| waiver | **none** — only STRUCK needs one |

`0.80 ≤ 0.8698142454259801 < 0.90`, and the largest per-frame median among
the top five is the same comparator's **0.8715545505700394**, **0.0284**
under the 0.90 line. Both limbs of the band therefore give DISCLOSE_GAP and
the column **ships with this disclosure**: nothing is removed and no waiver
is needed. Issue #123's *Done when* is met by a ship; a measured revert
would have closed it equally well and is not what the numbers say.

**Run facts** (`meta.json`): 89 frames, **398,849** pooled bars, **687**
comparators (**329** `compute_all` + **358** `ml_features` `1d`), `kwargs`
empty, nothing excluded, canary *AKBNK.IS, BIENY.IS, AGHOL.IS, SASA.IS
bit-equal*, pandas 2.3.3 / numpy 1.26.4, data stamp
`1be6495ef7095ff67ad8f59a2fc0311d74f02652`, engine code
`d4b78314a2ef494d6e36f77afc13a3178536f249`, module sha1
`159e58f3809dd1b0b58458d021f0b12e513e525e`, tree sha1
`3ca1107edd5d7125b33631bab4176cb4e2713b2d`. **One** comparator was
degenerate and dropped — `squeeze_SQZ_NO` (manifest), reason `constant`
(`degenerate.csv`) — so **686** carried a correlation.

**The five nearest comparators** (`top25.csv`, pooled; `perframe.csv` for
the same five). Every one of the five is a manifest column:

| against | pooled \|ρ\| | n | per-frame median | per-frame max | per-frame min | frames ≥ 0.90 | frames ≥ 0.80 |
|---|---|---|---|---|---|---|---|
| `BB_PctB_Pctl` | **0.8698142454259801** | 391,907 | **0.8715545505700394** | 0.9092969602639043 | 0.7743634318430944 | **5 of 89** | 88 of 89 |
| `MACD_Hist_ATR` | 0.8568217256216852 | 395,289 | 0.8579333539156462 | 0.8773466790492896 | 0.8349883108456296 | 0 of 89 | **89 of 89** |
| `MACD_Hist_ATR_Pctl` | 0.8535455693627491 | 390,661 | 0.8541426746054753 | 0.8720899829235261 | 0.8342468606676526 | 0 of 89 | **89 of 89** |
| `pgo` | 0.8457405769244867 | 395,289 | 0.8470283057074977 | 0.8945869848848321 | 0.7459982362665182 | 0 of 89 | 85 of 89 |
| `CCI_Pctl` | 0.8454301122353177 | 391,907 | 0.8498918947335661 | 0.8853546079062564 | 0.7484827699980081 | 0 of 89 | 85 of 89 |

The frame counts are recounted from `perframe.csv`'s percentages against
its own `n_frames` 89: 5.617977528089887 % is **5** frames,
98.87640449438202 % is **88**, 95.50561797752809 % is **85**, 100.0 % is
**89**.

**What the disclosure actually is**, read off that table rather than
asserted:

1. **two families, not one.** `BB_PctB_Pctl` is where the Bollinger
   denominator shows up and `MACD_Hist_ATR` / `MACD_Hist_ATR_Pctl` are where
   the MACD numerator does, and they sit 0.0130 apart (0.8698 against
   0.8568). A miner fed this column together with a percentile-ranked %B
   **or** with a MACD histogram over an ATR double-weights one of the two
   halves, which is the note the ML companion contract now carries.
2. **the MACD family is the steadier of the two.** `MACD_Hist_ATR` reaches
   0.80 on **all 89** frames (min 0.8350, max 0.8773) while `BB_PctB_Pctl`
   spreads 0.7744 … 0.9093 — so the lower pooled figure comes with the
   tighter spread, and 0.8568 is the more reliable of the two overlaps even
   though 0.8698 is the number the band reads.
3. **5 of 89 frames cross 0.90 against `BB_PctB_Pctl` individually**, up to
   0.9093. The band reads the per-frame **median**, not the tail, so they do
   not strike the column — but they are the honest reading of "0.8698
   pooled", and 88 of 89 frames sit at 0.80 or above.
4. **the pooled and per-frame limbs do not agree on the order.** `CCI_Pctl`
   is 5th pooled (0.8454) and 4th per-frame (median 0.8499), overtaking
   `pgo` (0.8457 pooled, 0.8470 per-frame). Both stay far under the line, so
   the swap changes no verdict; it is recorded because the two limbs are
   different measurements and reading one as a proxy for the other is how a
   band gets misquoted.

**`compute_all`'s own nearest is lower**: `ZSCORE_20` at
**0.8305331047713075** over n = 395,289, **0.0393** below the manifest's
best. `BB_%B` (compute_all) and `BB_PctB` (manifest) both read
**0.8305331037748611** — the same figure to 9 digits as `ZSCORE_20`,
differing by 1.0e-9, which is what a Spearman does to three monotone
transforms of one quantity.

⚠ **The percentile-ranked %B overlaps MORE than %B itself** — 0.8698 against
0.8305, a 0.0393 gap on what the engine presumably computes from the same
band. A rolling percentile is not a monotone transform of the whole series,
so it is free to move a rank correlation in either direction; **why it moves
it UP here is not measured** — this worktree cannot read either column's
code.

### §E2 against the screen's prototype figure

| figure | the PORT's run (2026-11-20) | the SCREEN's prototype (2026-10-24) |
|---|---|---|
| max \|ρ\| | **0.8698142454259801** | **0.8698** (4 decimals, as issue #123 prints it) |
| against | `BB_PctB_Pctl` (manifest) | `BB_PctB_Pctl` (manifest) |
| n | **391,907** | **391,907** |
| per-frame max median | **0.8715545505700394** | **0.8715** |
| verdict | **DISCLOSE_GAP** | **DISCLOSE_GAP** |
| 2nd comparator | `MACD_Hist_ATR` **0.8568** | `MACD_Hist_ATR` **0.8565** |
| 3rd comparator | `MACD_Hist_ATR_Pctl` **0.8535** | `MACD_Hist_ATR_Pctl` **0.8536** |
| comparator set | 687 (329 + 358) | 329 + 358 |

The leading figure, its comparator, its n and the per-frame figure agree to
**every digit issue #123 prints**. The 2nd and 3rd comparators **moved**:
0.8568 against 0.8565 (+0.0003) and 0.8535 against 0.8536 (−0.0001). So the
run is not the screen's run restated — it is a **different column** measured
through the same harness, and the two columns' Spearman ranks differ by
roughly 1e-4 where their values differ by up to 2.664e+00.

That is the reading §A4 predicts and §E0's warning did not: §A4 measures the
prototype **1,399 … 1,435 of 1,460 shared bars apart** from this module,
without converging, yet at Spearman **0.9983 … 1.0000** — and Spearman is
what Gate E measures. The pre-run draft of this receipt said the screen's
figures "describe a neighbouring column", which stays literally true; what
the run adds is that **the neighbour's band is this column's band too**, to
four decimals on the top comparator and to the fourth decimal on the next
two.

**The three things the screen's figure did not settle, settled:**

1. the harness imported **this module** — `meta.json`'s `candidate_source`
   is `pandas_ta/momentum/j_wae.py` with sha1
   `159e58f3809dd1b0b58458d021f0b12e513e525e`, which `record` re-derived
   from this tree — and the engine's frames left **395,289 of 398,849** real
   bars firing, **0** of them exactly zero (§C3);
2. the **687**-comparator set found nothing closer than the screen's own
   `BB_PctB_Pctl`, and `compute_all`'s nearest (`ZSCORE_20`, 0.8305) is
   0.0393 below it;
3. the **per-frame** limb reads 0.8716 as the maximum of the top five's
   medians, 0.0017 ABOVE the pooled figure and 0.0284 below the 0.90 line,
   with 5 of 89 frames above 0.90 individually.

⚠ **What is still not read here**: what the engine computes under the names
`BB_PctB_Pctl`, `MACD_Hist_ATR`, `MACD_Hist_ATR_Pctl` or `pgo`. §L's
`MACD_Hist_ATR` was this session's **invented retyping**, and it came within
**0.0037** of the engine's real figure (0.8531 synthetic median against
0.8568) — the closest §L got on any row, and still a guess rather than a
reading of the engine's code.

⚠ **`pandas_ta/momentum/j_wae.py` was deliberately NOT edited in this
session**, so its docstring still reads "The port's own Gate E run is what
decides its band, and it is PENDING". The ledger pins `module_sha1`
`159e58f3809dd1b0b58458d021f0b12e513e525e` to the bytes the harness
imported, and `tests/test_gate_e_ledger.py::test_row_still_describes_its_module`
re-derives it — so a docstring fix would invalidate the measurement it
describes. The measured numbers live here, in `docs/gate_e_ledger.csv`, in
`docs/MLCompanionContract.md` and in `tests/test_j_wae.py`. A later session
that edits that module for any other reason should fix the paragraph then.

### §E0 what the screen measured, on the PROTOTYPE

Issue #123, run `screen_r2_20261024` (2026-10-24), 89 ALTPORT-1 frames,
398,849 bars, 329 + 358 comparators, canary bit-equal:

| comparator | max \|ρ\| | n | band |
|---|---|---|---|
| `BB_PctB_Pctl` (manifest) | **0.8698** | 391,907 | **DISCLOSE_GAP** |
| `MACD_Hist_ATR` | 0.8565 | — | — |
| `MACD_Hist_ATR_Pctl` | 0.8536 | — | — |

Top-five per-frame max median **0.8715**. Fork-overlap stage 2 (12 frames,
not Gate E): max \|ρ\| **0.8562** vs `pgo:PGO_14`, per-frame max median
0.8606.

⚠ **Those figures describe a different column.** §A4 measures the
prototype disagreeing with the shipped one on 1,399 … 1,435 of 1,460 bars
by up to 2.664e+00, without converging. They are quoted as the prior, not
as this port's result — and §E2 is where the port's own run is read against
them. It agrees with the leading figure to every digit the issue prints and
moves the next two comparators in the fourth decimal.

---

## §G guards, bad data and the overflow route

### G1 the close-is-finite guard — it bites in the SEED and nowhere else

One bad close planted at one bar of `walk`, with the guard and without:

| plant | at bar | fired on | fired off | masks equal | differing bars | max \|abs\| |
|---|---|---|---|---|---|---|
| nan | 10 / 19 / 39 / 700 | 1460 / 1460 / 1441 / 1440 | same | True | 0 | 0.0 |
| +inf | 10 | 1460 | **1459** | **False** | 649 | 1.120e+01 |
| +inf | 19 | 1460 | **1459** | **False** | 649 | 1.134e+01 |
| +inf | 39 | 1441 | 1441 | True | 631 | 4.569e+00 |
| +inf | 700 | 1440 | 1440 | True | **0** | **0.0** |
| −inf | 10 / 19 / 39 / 700 | as +inf | as +inf | as +inf | 649 / 649 / 631 / 0 | 1.120e+01 / 1.134e+01 / 4.569e+00 / 0.0 |

And the mechanism, probed directly rather than reasoned about:

* with the guard off and a +inf at bar 10, `seed20` is **inf**, so `ema20`
  is NaN at bar 19 where the guarded one reads 98.15837 — the EMA starts a
  bar later, from a raw close, and the MACD loses one bar (1,460 against
  1,461);
* with the guard off and a +inf at bar **700**, every printed leg is
  identical to the guarded one, because

```
pandas 2.3.3, [1, 2, inf, 4, 5, 6, 7]:
  ewm(span=3, adjust=False).mean(): [1.0, 1.5, 1.5, 3.1667, 4.0833, 5.0417, 6.0208]
      -> the inf observation is SKIPPED, exactly like a NaN
  rolling(3).mean():                [nan, nan, nan, nan, nan, 5.0, 6.0]
      -> only the windows CONTAINING it are lost, and it recovers
```

Both behaviours are pinned by
`test_pandas_skips_an_infinite_ewm_observation_and_a_window_recovers`, so a
pandas upgrade that moves either fails here instead of silently changing
the column.

⚠ **So this guard is not what keeps an infinity out of the output** — §G2
is. What it buys is a correct EMA seed. On all eight ordinary frames it is
**bit-equal** with the guard off.

A single NaN close, with the guard on: at bar 700 it costs 20 fired bars
(1,440 fired, `CHANNEL` = 20), the first bar that differs in mask or value
is **700** itself, so every earlier bar is unchanged, and 780 later bars
move through the EMA; at bar 1,400 the first differing bar is **1,400**
and 80 bars move. At bar 10, inside the warm-up, no fired bar is lost, the
first differing bar is 40 (the first that fires) and all 1,460 move.

### G2 the two output guards are ONE guard in two halves

⚠ Each alone is a **measured no-op**, so they are priced together.

| frame | fired | = without `e1 > 0` | = without the finite mask | fired without BOTH | infinite without BOTH | zero-width bars |
|---|---|---|---|---|---|---|
| walk / trend / range-bound / grid / heavy-tailed / jump | 1460 | True | True | 1460 | 0 | 0 |
| flat | 0 | True | True | 0 | 0 | 1481 |
| rising | 1460 | True | True | 1460 | 0 | 0 |
| **flat-stretch** | **1278** | True | True | **1460** | **182** | **182** |

`flat-stretch` is a `walk` held exactly constant over bars 400 … 600, which
is what an illiquid or halted name prints. The width is exactly 0.0 on 182
bars while the 20/40 EMAs are still converging, so `t1` is non-zero on
**all 182** of them (largest 2.4887e+00): a real division by zero, not a
0/0. With both guards off the column ships 182 infinite values; with either
one it blanks those bars and fires on 1,278.

### G3 the overflow route — **not reached**, stated as the negative it is

Three frames built to overflow the division on FINITE inputs (a higher price
regime feeding `t1` through the 40-bar EMA while the width is computed over
a tiny one), run with BOTH output guards off:

| frame | bars | fired with guards | without | **infinite without** | max \|t1\| | min positive e1 |
|---|---|---|---|---|---|---|
| tiny-to-subnormal | 120 | 39 | 39 | **0** | 7.009e-10 | 1.033e-12 |
| huge-to-tiny | 120 | 0 | 0 | **0** | 7.009e+200 | inf |
| max-to-subnormal | 120 | 0 | 0 | **0** | 7.009e+300 | inf |

and on all eight ordinary frames, removing both guards is **bit-equal**.

So the finite mask's own load-bearing case is **UNPROVEN in this repo**:
no frame reached here produces an infinite quotient that `e1 > 0` had not
already blanked. The line is kept as defence in depth and the module says
so in those words rather than implying a measurement.

Where the variance overflows, both readings of the width, counted bar by
bar over bars 19 … 119 (101 bars):

| frame | literal NaN & algebraic inf | both inf | both NaN | mid inf | var inf | var NaN | var < 0 | last NaN-variance bar |
|---|---|---|---|---|---|---|---|---|
| tiny-to-subnormal | **0** | 0 | 41 | 0 | 0 | 0 | 41 | — |
| huge-to-tiny | **0** | 1 | 100 | 0 | 1 | 100 | 0 | 119 |
| max-to-subnormal | **0** | 1 | 100 | 0 | 1 | 100 | 0 | 119 |

So the two readings of the width **agree** on these frames: there is no
bar where the literal one is NaN and the algebraic one inf. On
`huge-to-tiny` and `max-to-subnormal` the variance overflows on exactly
one bar, bar 19, where both widths are inf (the mean stays finite); on
every later bar pandas' rolling variance is NaN, so both widths are NaN.
⚠ Unlike §G1's NaN close, whose windows recover, one overflowing bar
leaves the rolling variance NaN for the rest of the frame — 100 of the 100
bars after bar 19 — which is why those two frames fire on 0 bars. On
`tiny-to-subnormal` the variance never overflows; it is negative on 41
bars, and `sqrt` of those is the NaN both readings share.

### G4 degenerate and hostile frames raise nothing

| whole frame of | bars | returned | fired | infinite | name |
|---|---|---|---|---|---|
| nan / +inf / −inf / 0.0 / −1.0 | 200 | True | 0 | **0** | `J_WAE_150_20_40_20_2.0` |

At the length boundary a 40-bar frame returns `None`, a 41-bar frame
(`MIN_BARS`) fires on 1 bar and a 42-bar frame on 2.

⚠ RuntimeWarnings, counted. §G3 records the warnings `j_wae` itself raises:
**1** over the three overflow frames (`invalid value encountered in
sqrt`, from pandas' rolling variance going marginally negative on a
subnormal window; the NaN it produces is blanked by the guards) and **0**
over the eight ordinary frames. pytest reports **2 warnings** on
`tests/test_j_wae.py`, both from
`test_the_overflow_route_is_not_reached[tiny-to-subnormal]`, which calls
the function twice on that frame (shipped, and with both output guards
off).

---

## §L in-fork overlap — a DISCLOSURE, not Gate E

Spearman \|ρ\| against shipped fork columns over the six varying SYNTHETIC
frames:

| comparator | median \|ρ\| | max | min |
|---|---|---|---|
| `pgo:PGO_14` | **0.8580** | 0.9519 | 0.8311 |
| `MACD_Hist_ATR` (retyped, invented) | 0.8531 | 0.8686 | 0.8053 |
| `MACDh_12_26_9 / close` | 0.8522 | 0.8648 | 0.8017 |
| `bbands` %B (20, 2) | 0.8473 | 0.9401 | 0.8033 |
| `roc:ROC_10` | 0.7555 | 0.7969 | 0.7300 |
| `squeeze:SQZ_20_2.0_20_1.5` | 0.3885 | 0.4876 | 0.2593 |
| 1-bar change of %B | 0.3040 | 0.3973 | 0.1705 |

Three things keep this from being a verdict:

1. six synthetic frames are not 89 real ones. ⚠ **Re-read against the port's
   own Gate E run (2026-11-20), this table reads HIGH on two of its three
   measurable rows and low on the third:**

   | this table's comparator | synthetic median | the Gate E run's pooled \|ρ\| | gap |
   |---|---|---|---|
   | `pgo:PGO_14` | 0.8580 | `pgo` **0.8457405769244867** | synthetic **high by 0.0123** |
   | `bbands` %B (20, 2) | 0.8473 | `BB_%B` / `BB_PctB` **0.8305331037748611** | synthetic **high by 0.0168** |
   | `MACD_Hist_ATR` (retyped) | 0.8531 | `MACD_Hist_ATR` **0.8568217256216852** | synthetic **low by 0.0037** |

   The pre-run draft of this point compared the 0.8580 with the screen's
   stage-2 figure 0.8562 and called the synthetic frames "high by 0.0018";
   against the port's own 89-frame Gate E figure for `pgo` the gap is
   **0.0123**, which is the number to use. Worst of the three is 0.0168, so
   this table was within 0.017 of the run on every row it could be checked
   against — and `MACDh_12_26_9 / close` and the two rows below `roc` have
   no counterpart in the run's output and remain **unchecked**;

   ⚠ The synthetic TAIL was worse than the real one, not better: this
   table's `pgo:PGO_14` maximum over six frames is **0.9519**, while the Gate
   E run's per-frame maximum against `pgo` over 89 real frames is
   **0.8945869848848321** — no real frame reached 0.90 on that comparator;

2. `MACD_Hist_ATR` is **retyped and invented**: the engine's column of that
   name is not readable from this repo, so what is measured is
   `macd(close)["MACDh_12_26_9"] / atr(high, low, close, 14)`, this
   session's guess at it. It is labelled as such in the script's own
   output. The engine's `MACD_Hist_ATR` is also one of the screen's top
   three comparators (0.8565), which is why the guess is worth printing —
   and the Gate E run measured the engine's own column at **0.8568**, so the
   guess was out by 0.0037 and is **still not a reading of the engine's
   code**;
3. a single frame crosses 0.90 on `pgo:PGO_14` (0.9519) and on %B (0.9401).
   The band rule reads a MEDIAN, and both medians sit in DISCLOSE_GAP.

⚠ The family is the point: `PGO_14` is `(close − SMA) / EMA(TR)` — a price
displacement over a volatility — and this column is a MACD displacement
over a volatility. They answer a neighbouring question, and the port's own
Gate E run priced it: the manifest's `pgo` — its column of that name, not
this fork's `PGO_14`, which is **not** what the harness compared against —
is the **4th** nearest of the 686 comparators that carried a correlation, at
0.8457 pooled and 0.8470 per-frame median, under the 0.90 line and under
`BB_PctB_Pctl` (0.8698) and `MACD_Hist_ATR` (0.8568). So the family §L
points at is real and is **not** where this column's largest overlap sits.

---

## §Z cost — this machine, this run

| call | ms per call, 1,500 bars |
|---|---|
| `j_wae` | 1.446 |
| the §A1 oracle | 4.112 |

Nothing else in this repo cites these two numbers.

---

## §F suites

⚠ Re-run by the **receipt session** of 2026-11-20, after the Gate E row was
recorded. The porting session's figures are given beside each one.

* `python -m pytest tests/test_j_wae.py -q` — **245 passed, 2 warnings**
  (244 before: the two pending-Gate-E tests were replaced by the three
  §E1 names).
* `python docs/measure_j_wae_cpu.py` — the same **245 passed, 2 warnings**
  under `NPY_DISABLE_CPU_FEATURES="AVX512F AVX512_SKX AVX2 FMA3"`, which the
  script refuses to run unless all four are actually disabled. It prints
  the dispatchable features still enabled: `SSSE3`, `SSE41`, `POPCNT`,
  `SSE42`, `AVX`, `F16C`, `AVX512CD`, `AVX512_CLX`, `AVX512_CNL`,
  `AVX512_ICL`.
* `python -m pytest -q tests/test_j_wae.py tests/test_gate_e_ledger.py
  tests/test_ml_companions.py` — **1,381 passed**, so the owed-row failure
  is gone and the contract's new Gate E paragraph does not break
  `tests/test_ml_companions.py`.
* Count and wiring tests, porting session: `python -m pytest -q
  tests/test_altport2_ports.py tests/test_readme_counts.py
  tests/test_ml_companions.py tests/test_indicator_list_tables.py` — **40
  passed, 7 skipped, 2 warnings** (the seven need `../AlternativeRepos`, the
  sibling repo's `IndicatorList.md` or the parent repo's parquet cache). Not
  re-run by the receipt session, which touched none of the counts.
* Full suite: `python -m pytest -q` — **1 failed, 12962 passed, 86 skipped**
  in 419 s. The one is
  `tests/test_altrepo_talib_csv.py::test_regenerating_reproduces_the_committed_rows`,
  the `AlternativeRepos`-dependent test CI deselects by name, and nothing
  else. The porting session read **2 failed, 12953 passed, 86 skipped**
  (and 2 failed, 12360 passed, 86 skipped before its rebase onto `dev`); the
  second failure was
  `tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
  reporting `['j_wae']`, the **owed Gate E row**, which this session's
  `record` closed. The code under test did not change between the two runs,
  and the **9 further passes** are accounted for: the collected total moved
  **13,041 → 13,049** (+8), of which **+1** is this session's net test swap
  and **+7** are `tests/test_gate_e_ledger.py` tests the new row
  parametrises — it matches **8** of them
  (`python -m pytest tests/test_gate_e_ledger.py --collect-only -k j_wae`),
  one of which, `test_every_new_indicator_has_gate_b_and_d_tests[j_wae]`,
  was already collected from `Category` before the row existed. The ninth
  pass is the owed test itself, moving from failed to passed.
* `docs/MLCompanionContract.md`: 704 → 705 tagged columns, 341 → 342 `SF`.
* The parent repo's suite is the launcher's.

---

## Wiring

| # | File | Change |
|---|---|---|
| 1 | `pandas_ta/momentum/j_wae.py` | the indicator (new) |
| 2 | `pandas_ta/momentum/__init__.py` | `from .j_wae import j_wae` |
| 3 | `pandas_ta/__init__.py` | `"j_wae"` in `Category["momentum"]` |
| 4 | `pandas_ta/core.py` | `df.ta.j_wae()` |
| 5 | `tests/test_j_wae.py` | the suite (new) |

and the documents that count it: `README.md` (359 → 360 registered, 367 →
368 callable, momentum 87 → 88), `docs/IndicatorDictionary.md`
(regenerated), `docs/MLCompanionContract.md`, and
`tests/test_altport2_ports.py`'s `CATEGORY_TOTAL`.

The receipt session of 2026-11-20 added `docs/gate_e_ledger.csv`'s row and
`docs/measure_j_wae_contract.py`, which prints every mention of
`J_WAE_150_20_40_20_2.0` in the documents that name it next to the ledger
row they have to agree with. It exists because
`docs/MLCompanionContract.md` keeps its column inventory on one line long
enough that this repo's reading tools refuse to print it in context, so the
one sentence that had to stop saying "pending" could not be read any other
way. It changed **no** shipped code: `pandas_ta/momentum/j_wae.py` is
byte-for-byte the file the harness imported (§E2).
