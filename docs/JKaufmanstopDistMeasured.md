# J-KAUFMANSTOP-DIST — measured

PandasTa issue **#124**: *distance to Kaufman's stop, long (22, mult 2)*.
Shipped as `pandas_ta/trend/j_kaufmanstop_dist.py`, one column
**`J_KAUFMANSTOP_DIST_22_2.0`**.

```
rng[T]  = high[T] - low[T]
avg[T]  = mean(rng[T-21..T])                                      SMA 22
stop[T] = low[T] - 2 * avg[T]
J_KAUFMANSTOP_DIST[T] = (close[T] - stop[T]) / close[T]
```

Source: jesse indicators (MIT), `kaufmanstop.py`, as issue #124 quotes it —
`kaufmanstop.py: L - 2*SMA22(H - L)`. Issue #124 names the rule Kaufman's
stop; that attribution is the issue's and is not checked here. The issue
says of the library: *existence, not evidence*.

**Every number below is printed by `python docs/measure_j_kaufmanstop_dist.py`**
(section names match the headings). **Every section that measures the
column was re-printed** by
`python docs/measure_j_kaufmanstop_dist_cpu.py <section>` under
`NPY_DISABLE_CPU_FEATURES="AVX512F AVX512_SKX AVX2 FMA3"` — §A1, §A2, §A3,
§A4, §A5, §B1, §B2, §C1, §C2, §D1, §D2, §D3, §D4, §G1, §G2, §G3, §G4, §G5
and §L, which is all 22 of the script's sections except §ENV (versions),
§E (the screen's quoted figures, named exception 3 below) and §Z
(wall-clock, one machine's by construction). **Eight of §D2's 24 cells
moved**, listed there; every other cell of every other section reproduced
exactly, and §D2's worst cell is the same 5.160e-14 under both dispatches.

⚠ Round 1 of the review caught this paragraph claiming **one** cell moved
over a §D2 table that lists eight, and claiming a complete enumeration that
left out five sections; round 2 caught the repaired enumeration calling 19
sections "all of them except two" when the script has 22 and §E is the
third. All three are corrected above, and the five sections round 1 named
were then run.

⚠ **Seven exceptions, named here rather than left for a reader to find** —
seven numbered items, and the count is the number of items. The script has
no §F section and does not read the repo's documents, so:

1. §F's counts (`380 passed`, `1,486 passed, 1 failed` and
   `2 failed, 12,700 passed, 86 skipped`) are **pytest's**, from the runs
   named there;
2. §F's `703 → 704` tagged columns is **`docs/MLCompanionContract.md`'s**
   count, checked by
   `tests/test_ml_companions.py::test_the_contract_quotes_the_dictionarys_actual_ml_form_counts`,
   and §F's wiring counts (`CATEGORY_TOTAL` 358 → 359, README 358 → 359 /
   366 → 367 / `trend (65)`) are the **repo's**, checked by
   `tests/test_altport2_ports.py` and `tests/test_readme_counts.py`. This
   script prints none of the five;
3. §E's real-data figures are **issue #124's and the screen's**, quoted out
   of `docs/issues/screen/candidates_r2.csv`, `fork_overlap_r2.csv`,
   `cand_pairs_r2.csv`, `sanity_r2.csv` and the issue text itself (the
   `Stop_2ATR_pct` / `Swing_Range_pct` row, which no CSV here carries) —
   the tracker being a gitignored read-only copy of the owner's.
   **Gate E on the port itself is PENDING**: the launcher runs the harness
   after this session and a later session records the row;
4. the "web access is unavailable" line below is a fact about the session,
   not a printed measurement. The jesse-absence flag next to it **is**
   printed, by §ENV;
5. the **asserted bounds** quoted next to a measurement — 1e-12 and 1e-9 at
   §A1, 1e-6 at §B1, 1e-9 at §D2, and those three places are the whole of
   it — are **`tests/test_j_kaufmanstop_dist.py`'s own constants**, not run
   output; the measured value beside each one is. ⚠ Round 3 of the review
   found this item also naming §A2, §B2, §G3 and §G5, which quote no bound
   anywhere in this receipt;
6. "**Eight** of §D2's 24 cells moved" is a hand diff of the section's two
   runs. No section prints it: the script prints each run's 24 cells and
   the two tables are above and inside §D2, so the count is recounted from
   printed cells rather than measured by code;
7. and **every** "identical cell for cell under the reduced CPU dispatch"
   statement is the same kind of comparison — two printed tables read
   against each other, not a diff the script computes. There are **twelve**:
   eleven in that wording, at §A1, §A3, §B1, §B2, §C1, §D3, §G2, §G3, §G4,
   §G5 and §L, and one shorter at §D1. ⚠ Counted with a multiline match,
   because a single-line one misses §G4's, where the sentence wraps — the
   first count written here said eleven for exactly that reason.

Everything else in this receipt is a cell from a run.

⚠ Items 2 (in part), 6 and 7 are round 2 of the review's: the list said
five and licensed figures it did not cover.

Run environment (§ENV): python 3.11.2 · Linux 6.6.147 x86-64 · numpy
1.26.4 · pandas 2.3.3 · talib 0.7.1 installed · **jesse NOT installed**;
web access is unavailable in this worktree.

⚠ **And nothing in this receipt is a statement about what jesse's code
says.** The library is not installed and cannot be read, so whether its
`SMA22` runs over `H - L` bar by bar and whether its `L` carries a lag are
**not claimed**. What is checked is the formula issue #124 quotes, read
literally, spelled three independent ways (§A1, §A2) — and the screen
prototype, which spells the same reading and which §A3 measures **bit-equal**
to this module.

---

## Verdict

| Gate | Result |
|---|---|
| A Correctness | **PASS** — bit-equal to an independent bar-by-bar oracle on 1,479 of 1,479 bars of each of six frames with identical NaN masks, and to `(close - (low - 2*talib.SMA(high - low, 22)))/close` on all six at Spearman 1.0000; all three first fire at bar 21 |
| B Causality | **PASS** — 0 of 36 sweep catches on six frames; six look-ahead mutants live and caught 36 of 36 on each of three frames; three blind-spot (lagging) edits caught 0 by the sweep and all three by the oracle; a prefix truncation leaves 979 of 979 later bars bit-equal |
| C Reachability | **PASS (synthetic)** — 1,479 of 1,500 bars on each of nine frames, 1,479 distinct values on each of the six varying ones, 8,874 of 8,874 pooled bars non-zero. ⚠ **Real data is OWED**: it comes from the Gate E run, which is pending |
| D Scale-free | **PASS** — ×8/×64 bit-identical on all nine frames at a level of 100 and on all nine at each of 1e-6, 1e+6 and 1e+100 (54 cells; worst intermediate 9.776e+101, 1.839e+206 of DBL_MAX headroom); ×10/×3.7/×0.1/×1.0000001 within 5.160e-14; `0 < fires < n` on all nine; a +10 level shift moves all 1,479 fired bars of each of the six varying frames |
| E Attribution | **Gate E: pending, run by issue-solver after this session.** The 2026-10-24 screen measured the PROTOTYPE — which §A3 measures bit-equal to this module — at max \|ρ\| **0.8776182137043917** vs the engine's `natr`, n = 396,980, per-frame max median 0.8600682984579084 → **DISCLOSE_GAP** |
| F Suites | this repo's suite run in §F; both repos' suites are the launcher's |

**The one thing to read first.** Unlike `j_chandelier_dist` (#122), this
port **does** reproduce the screen prototype bit for bit — §A3, on all nine
frames — and that is measured rather than inferred from the two quotes
reading alike. The consequence is specific and limited: the screen's
DISCLOSE_GAP figures describe **this arithmetic**, not a neighbour's, so
the band this column is likely to land in is already visible. It is not a
substitute for the port's own run, because those figures were taken on 89
real BIST frames and through an engine neither readable nor runnable from
this worktree, and because `gate_e_overlap.py` imports the shipped module
rather than the prototype. Gate E stays **PENDING**.

**The second thing.** This column **does not change sign**, which is where
it parts from both sibling stop distances. The stop sits twice the average
range below bar T's **own** low, so

```
(close - stop)/close = (close - low)/close + 2*avg/close
```

— two non-negative terms whenever `close >= low`. §C1 measures
0.005961 … 0.014415 over the 8,874 fired bars of six frames, **0** of them
negative and **0** exactly zero. So the signal is the SIZE and there is no
sign to read; `docs/MLCompanionContract.md` says so beside the `SF` tag.

**The third thing.** The three input finite guards are **measured no-ops**
(§G2), and this receipt says so rather than claiming a load they do not
carry. That is the opposite finding from #122, where the same three guards
moved 634 … 664 bars. The mechanism is measured too: pandas' rolling mean
turns an infinite observation into a NaN (§G3) where `ewm` skipped it.

---

## §ENV — environment

```
python 3.11.2 on Linux-6.6.147-09648-g97ef00d8a343-x86_64-with-glibc2.36
numpy 1.26.4, pandas 2.3.3
talib 0.7.1
jesse installed: False
PERIOD=22 MULT=2.0 MIN_BARS=22 WARMUP=21 FIRED=1479 N=1500
```

Nine synthetic frames, 1,500 bars each, the same builders and seeds as
`docs/measure_j_chandelier_dist.py` so the two ports can be compared:
`walk`, `trend`, `range-bound`, `grid` (tick-rounded), `heavy-tailed`
(Student-t), `jump` (×1.5 at bar 700) — the six **varying** frames — plus
`flat` (`high == low == close`), `rising` (one-way, constant relative
range) and `tied` (a doji every seventh bar).

---

## §A1 — Gate A: the issue's formula, spelled independently

The oracle is a bar-by-bar reimplementation over plain Python floats — its
own range loop, its own **naive** 22-term window sum — sharing no code with
the module.

| frame | fired | same NaN mask | bit-equal | max \|abs\| | max \|rel\| | Spearman |
|---|---|---|---|---|---|---|
| walk | 1479 | True | **True** | 0.000e+00 | 0.000e+00 | 1.000000 |
| trend | 1479 | True | **True** | 0.000e+00 | 0.000e+00 | 1.000000 |
| range-bound | 1479 | True | **True** | 0.000e+00 | 0.000e+00 | 1.000000 |
| grid | 1479 | True | **True** | 0.000e+00 | 0.000e+00 | 1.000000 |
| heavy-tailed | 1479 | True | **True** | 0.000e+00 | 0.000e+00 | 1.000000 |
| jump | 1479 | True | **True** | 0.000e+00 | 0.000e+00 | 1.000000 |

Identical cell for cell under the reduced CPU dispatch.

⚠ **Bit-equality was not assumed and is not asserted.** pandas'
`rolling.mean()` is a *compensated* running sum, not 22 additions, so the
two could have differed in the last bits. Measured on the `walk` frame:

```
SMA bit-equal to a naive window sum: True
max |abs| between the two means:     0.000e+00
bars of 1479 that differ:            0
```

The test asserts **1e-12** absolute and **1e-9** relative instead, because
the frames are built with `np.exp`/`np.cumsum` and a reduced numpy kernel
can move a price in its last bits. Both dispatches measure 0.0.

---

## §A2 — Gate A: TA-Lib as the third speller

`(close - (low - 2 * talib.SMA(high - low, 22))) / close` — the issue's
operators as TA-Lib spells them (talib 0.7.1; the test SKIPS where talib is
absent rather than passing silently).

| frame | fired | talib fired | same NaN mask | bit-equal | max \|abs\| | Spearman |
|---|---|---|---|---|---|---|
| walk | 1479 | 1479 | True | **True** | 0.000e+00 | 1.000000 |
| trend | 1479 | 1479 | True | **True** | 0.000e+00 | 1.000000 |
| range-bound | 1479 | 1479 | True | **True** | 0.000e+00 | 1.000000 |
| grid | 1479 | 1479 | True | **True** | 0.000e+00 | 1.000000 |
| heavy-tailed | 1479 | 1479 | True | **True** | 0.000e+00 | 1.000000 |
| jump | 1479 | 1479 | True | **True** | 0.000e+00 | 1.000000 |

The warm-up is run rather than recalled:
`talib.SMA(high - low, 22)` first fires at index **21**, this module's `sma`
at **21**, the column at **21**.

---

## §A3 — Gate A: the screen prototype IS this arithmetic

`docs/issues/screen/ind_screen_r2.py`, candidate `j_kaufmanstop_dist`:
`(c - (l - 2 * mean(h - l, 22))) / c`, with `ind_screen.py`'s
`mean(x, n) = x.rolling(n).mean()` — the same call `sma` makes.

| frame | fired | prototype fired | bit-equal | max \|abs\| | Spearman |
|---|---|---|---|---|---|
| walk | 1479 | 1479 | **True** | 0.000e+00 | 1.000000 |
| trend | 1479 | 1479 | **True** | 0.000e+00 | 1.000000 |
| range-bound | 1479 | 1479 | **True** | 0.000e+00 | 1.000000 |
| grid | 1479 | 1479 | **True** | 0.000e+00 | 1.000000 |
| heavy-tailed | 1479 | 1479 | **True** | 0.000e+00 | 1.000000 |
| jump | 1479 | 1479 | **True** | 0.000e+00 | 1.000000 |
| flat | 1479 | 1479 | **True** | 0.000e+00 | n/a (constant) |
| rising | 1479 | 1479 | **True** | 0.000e+00 | 1.000000 |
| tied | 1479 | 1479 | **True** | 0.000e+00 | 1.000000 |

Identical cell for cell under the reduced CPU dispatch.

⚠ The issue says *Gate A starts from the source formula, not the
prototype*, and it does: §A1 and §A2 are the formula, independently. That
the prototype coincides is a **result**, measured here, not the route taken
— and it is the reason §E's screen figures can be read as this column's.

---

## §A4 — Gate A: the other readings are other columns

**(a) the `sma` import against the `rolling` call it makes.** `sma` is
imported from its own module rather than retyped (CLAUDE.md, *Known
breaks*). Bit-equal to an inline `rolling(22, min_periods=22).mean()` on
all nine frames, so the import costs nothing.

**(b) the smoother, and the series it smooths.** Six varying frames:

| reading | differ (of 1,479) | last differing bar | max \|abs\| | Spearman |
|---|---|---|---|---|
| `SMA22` over the TRUE range | 1,478 on all six (alt fires 1,478) | 1,499 | 1.667e-02 … 5.606e-02 | 0.278975 … 0.533358 |
| `EMA22` over `high - low` | 1,479 on all six | 1,499 | 1.057e-03 … 1.326e-03 | 0.970456 … 0.977756 |
| stop off YESTERDAY's low | 1,473 … 1,479 | 1,499 | 3.098e-02 … 3.224e-01 | −0.075348 … 0.019946 |

The true-range reading also loses a bar: a true range needs a previous
close, so it fires 1,478 times against this column's 1,479 — the structural
difference `MIN_BARS == PERIOD` records.

**(c) `high - low` through `non_zero_range`.** The helper adds
`sys.float_info.epsilon` to **every** bar of the leg as soon as one bar has
`high == low`, and that epsilon is **absolute**.

| frame | `high == low` bars | variant bit-equal to the module |
|---|---|---|
| walk / trend / range-bound / grid / heavy-tailed / jump / rising | 0 | True |
| tied | 215 | **True** |
| flat | 1500 | **True** |

So at a price level of 100 the plain subtraction buys **nothing** — the
epsilon falls below the last bit of the result even with 1,500 tied bars.
What it buys is Gate D at a small level:

| frame | × | module bit-identical | `non_zero_range` variant bit-identical |
|---|---|---|---|
| tied @ 100 | 8 | True | True |
| tied @ 100 | 64 | True | True |
| tied @ 1e-06 | 8 | **True** | **False** |
| tied @ 1e-06 | 64 | **True** | **False** |

Both halves are in the module's comment, and both are pinned by tests.

---

## §A5 — Gate A: the warm-up, and the backward reach

```
first fired index: 21 (WARMUP = 21 = PERIOD - 1)
MIN_BARS = 22 = PERIOD
```

⚠ `MIN_BARS` is `PERIOD`, **not** `PERIOD + 1`, and that is the one
structural number that differs from `j_chandelier_dist`: nothing in this
chain reads a previous close, so the SMA's input is defined at bar 0.

| bars | fired | first fired index |
|---|---|---|
| 21 | None (refused) | — |
| 22 | 1 | 21 |
| 23 | 2 | 21 |
| 60 | 39 | 21 |

The backward limb, which the forward sweep of §B1 cannot see: nothing reads
before `T - 21`, so truncating a 1,500-bar `walk` at bar 500 leaves every
bar from 521 on untouched — **979 bars compared, bit-equal**. The test runs
it on all nine frames.

---

## §B1 — Gate B: the blind future sweep and its mutants

The sweep rescales every bar `>= j` by 1.03 and asks whether any bar `< j`
moved, at the 36 offsets 1,464 … 1,499. ⚠ A suffix rescale is not a global
one — the column is invariant under a global rescale, which is Gate D.

| frame | module caught at | offsets |
|---|---|---|
| walk / trend / range-bound / grid / heavy-tailed / jump | **0** | 36 |

Six look-ahead mutants, read off the shipped source, edited and `exec`'d in
memory, on each of `walk`, `trend` and `heavy-tailed`:

| mutant | live | caught at | first catch moves a bar by |
|---|---|---|---|
| `rng-high-lead` | True | **36 of 36** | 2.717e-03 … 2.765e-03 |
| `rng-low-lead` | True | **36 of 36** | 2.700e-03 … 2.748e-03 |
| `avg-lead` | True | **36 of 36** | 1.379e-05 … 1.706e-05 |
| `stop-low-lead` | True | **36 of 36** | 2.970e-02 … 3.023e-02 |
| `close-lead` | True | **36 of 36** | 2.854e-02 … 2.909e-02 |
| `output-early` | True | **36 of 36** | 2.061e-04 … 2.386e-04 |

Identical cell for cell under the reduced CPU dispatch. 36 of 36 on every
mutant and every frame — unlike #122, where a 22-bar MAXIMUM made some
leads invisible at some offsets; there is no maximum in this chain. The
loudness bound the test asserts is **1e-6**, which is **1.9e+07×** the
5.160e-14 an inexact rescale costs (§D2) — seven orders, not the "eight"
three files said until round 4 of the review divided it out — and an order
below the smallest measured catch.

---

## §B2 — Gate B: the sweep's blind spot, and the oracle on it

Three edits that **lag** a leg. None reads a later bar, so a suffix sweep
is structurally blind to all three.

| mutant | caught by sweep | bit-equal to oracle | oracle rejects by |
|---|---|---|---|
| `rng-high-lag` (walk / heavy-tailed) | **0 of 36** | False | 1.442e-02 / 3.266e-02 |
| `avg-lag` (walk / heavy-tailed) | **0 of 36** | False | 6.152e-04 / 6.590e-04 |
| `stop-low-lag` (walk / heavy-tailed) | **0 of 36** | False | 3.591e-02 / 3.224e-01 |

Identical cell for cell under the reduced CPU dispatch. Pinned in **both**
directions: a sweep that started catching them would mean the module's
shift structure had changed. This is why Gate B here is the sweep **and**
the oracle.

---

## §C1 — Gate C: reachability on the varying frames

| frame | fired | bars | distinct | min | max | < 0 | == 0 |
|---|---|---|---|---|---|---|---|
| walk | 1479 | 1500 | 1479 | 0.006020 | 0.014415 | 0 | 0 |
| trend | 1479 | 1500 | 1479 | 0.006343 | 0.014194 | 0 | 0 |
| range-bound | 1479 | 1500 | 1479 | 0.006044 | 0.013720 | 0 | 0 |
| grid | 1479 | 1500 | 1479 | 0.005961 | 0.013775 | 0 | 0 |
| heavy-tailed | 1479 | 1500 | 1479 | 0.006383 | 0.013782 | 0 | 0 |
| jump | 1479 | 1500 | 1479 | 0.005972 | 0.013908 | 0 | 0 |

Pooled: **8,874 bars, 0.005961 … 0.014415, 0 negative, 0 exactly zero,
8,874 positive.** Identical cell for cell under the reduced CPU dispatch.

⚠ **Gate C's real-data limb is OWED.** Every frame here is synthetic; the
real counts come from the Gate E run, which is pending. The receipt session
fills them in, as it did for #121 and #122.

---

## §C2 — Gate C: the frames that are not ordinary

| frame | fired | distinct | min | max | == 0 |
|---|---|---|---|---|---|
| flat | 1479 | **1** | 0.000000 | 0.000000 | **1479** |
| rising | 1479 | 1479 | 0.009898 | 0.009946 | 0 |
| tied | 1479 | 1479 | 0.004920 | 0.012727 | 0 |

`flat` is the exception to "not a constant column", and the reason that
limb is asserted on the varying frames: with `high == low == close` every
range is 0, so the average is 0, the stop **is** the low and the low **is**
the close. `rising` has a constant relative range and sits in a band
0.009898 … 0.009946 wide.

---

## §D1 — Gate D: ×8 / ×64 bit-identical

Bit-identical on **all nine** frames at both factors, 1,479 of 1,479 bars
each. Identical under the reduced CPU dispatch.

---

## §D2 — Gate D: inexact factors, a tolerance

Max relative difference, 24 cells:

| frame | ×10 | ×3.7 | ×0.1 | ×1.0000001 |
|---|---|---|---|---|
| walk | 3.669e-14 | 3.605e-14 | 4.178e-14 | 3.721e-14 |
| trend | 4.474e-14 | 4.109e-14 | 3.978e-14 | 4.305e-14 |
| range-bound | 4.400e-14 | 3.307e-14 | 3.456e-14 | 3.122e-14 |
| grid | 3.785e-14 | **5.160e-14** | 3.875e-14 | 3.662e-14 |
| heavy-tailed | 3.829e-14 | 3.436e-14 | 3.862e-14 | 2.985e-14 |
| jump | 3.851e-14 | 3.456e-14 | 4.140e-14 | 4.953e-14 |

NaN masks matched in all 24. Worst cell **5.160e-14**; the test asserts
**1e-9**, more than four orders above it.

⚠ **This is the one section whose cells move between numpy dispatches**, as
expected. With `AVX512F AVX512_SKX AVX2 FMA3` off: walk ×10 3.338e-14,
trend ×3.7 4.145e-14, range-bound ×10 3.592e-14 and ×3.7 3.328e-14 and ×0.1
3.782e-14 and ×1.0000001 3.111e-14, trend ×0.1 3.330e-14, jump ×3.7
3.775e-14 — and the **worst cell is the same 5.160e-14**. The test asserts
the bound rather than the digits for exactly this reason.

---

## §D3 — Gate D: extreme price levels, and the headroom

⚠ **All nine frames at each of three levels — 54 cells with both factors.**
Round 1 of the review found this table holding one frame (`walk`) under
prose that said nine, so the section and
`test_gate_d_scale_at_extreme_price_levels` were both widened.

| frame | level | fired | ×8 | ×64 | largest value the chain computes |
|---|---|---|---|---|---|
| walk | 1e-06 / 1e+06 / 1e+100 | 1479 | True | True | 1.442e-02 / 1.006e+06 / 1.006e+100 |
| trend | 1e-06 / 1e+06 / 1e+100 | 1479 | True | True | 1.419e-02 / 9.776e+07 / **9.776e+101** |
| range-bound | 1e-06 / 1e+06 / 1e+100 | 1479 | True | True | 1.372e-02 / 1.148e+06 / 1.148e+100 |
| grid | 1e-06 / 1e+06 / 1e+100 | 1479 | True | True | 1.378e-02 / 1.549e+06 / 1.549e+100 |
| heavy-tailed | 1e-06 / 1e+06 / 1e+100 | 1479 | True | True | 1.378e-02 / 1.161e+06 / 1.161e+100 |
| jump | 1e-06 / 1e+06 / 1e+100 | 1479 | True | True | 1.391e-02 / 1.593e+06 / 1.593e+100 |
| flat | 1e-06 / 1e+06 / 1e+100 | 1479 | True | True | 1.000e-06 / 1.000e+06 / 1.000e+100 |
| rising | 1e-06 / 1e+06 / 1e+100 | 1479 | True | True | 9.946e-03 / 2.509e+06 / 2.509e+100 |
| tied | 1e-06 / 1e+06 / 1e+100 | 1479 | True | True | 1.273e-02 / 1.237e+06 / 1.237e+100 |

Identical cell for cell under the reduced CPU dispatch.

⚠ The maximum is taken over **every value the chain computes** — the three
inputs, `rng`, `avg`, `2*avg`, `stop`, `px`, `px - stop` and `dist`, ten
series — and closing that set took two rounds: round 3 of the review found
`2*avg` and `dist` missing, round 4 the division's numerator `px - stop`
and the guarded divisor `px`. Neither addition moved the 1e+06 or 1e+100
column; the first moved the 1e-06 one: at that
level the largest number in the chain is the **dimensionless output**,
~1.4e-02, because `dist` is a ratio and does not shrink with the price.
That is Gate D's own point arriving in the headroom table, and the `flat`
frame is the exception because its output is exactly 0.0.

`trend` carries the largest price-side value because its drift takes the
price two orders above the starting level over 1,500 bars.
`DBL_MAX = 1.798e+308`; against the worst of the nine at 1e100 the headroom
is **1.839e+206×**. Printed rather than reasoned about:
`j_safezone_dist`'s margin was once a typed "four orders" and was wrong by
202 of them.

---

## §D4 — Gate D: `0 < fires < n`, and the level shift

`0 < fires < n` on all nine frames (1,479 of 1,500 each). A +10 level
shift, which the column is **not** invariant under:

| frame | shared bars | moved by +10 |
|---|---|---|
| walk / trend / range-bound / grid / heavy-tailed / jump | 1479 | **1479** |
| rising | 1479 | 1479 |
| tied | 1479 | 1479 |
| **flat** | 1479 | **0** |

So the ×8 bit-identity of §D1 is a real check rather than a vacuous one —
and the flat frame is the exception, pinned on its own, because a zero-range
frame reads exactly 0.0 at any level.

---

## §E — Gate E

**Gate E: pending, run by issue-solver after this session.**

`tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
fails on a local run until the row exists. That is the owed-measurement
state CLAUDE.md describes, not a defect in this port:
`tests/test_j_kaufmanstop_dist.py::test_no_gate_e_row_is_recorded_yet` and
`::test_the_receipt_says_gate_e_is_pending` are the receipt session's cue
and are expected to be **replaced** then, not to keep passing.

What the 2026-10-24 library catalog screen, round 2, measured — on the
**prototype**, which §A3 measures **bit-equal** to this module, so these
are this arithmetic's figures on data this worktree cannot read, through an
engine it cannot run. Quoted from the gitignored read-only tracker copy:

| figure | value | file |
|---|---|---|
| Gate E max \|ρ\| | **0.8776182137043917** vs `natr` (`compute_all`) | `candidates_r2.csv` |
| Gate E n | 396,980 | `candidates_r2.csv` |
| Gate E per-frame max median | 0.8600682984579084 | `candidates_r2.csv` |
| Gate E verdict | **DISCLOSE_GAP** | `candidates_r2.csv` |
| next comparators | `Stop_2ATR_pct` 0.8776, `Swing_Range_pct` 0.7305 | issue #124 |
| fork overlap (stage 2) | 0.8611 vs `natr:NATR_14`, per-frame max median 0.8547, 12 frames | `fork_overlap_r2.csv` |
| nearest other candidate | `lean_avgrange_14` 0.8646 — itself **STRUCK** at 0.9489 vs `natr` and dropped | `cand_pairs_r2.csv`, `candidates_r2.csv` |
| pre-flight | finite_min 0.9750593824228029, nunique_min 821, causal 0.0, px×8 0.0, vol×8 0.0 | `sanity_r2.csv` |

⚠ **And the screen struck the nearest member of this column's own family.**
`lean_avgrange_14`, `SMA(H - L, 14)/close`, is two thirds of this column
without the wick term and without the multiplier; it paired at 0.8646 with
this candidate (`cand_pairs_r2.csv`) and it measured **0.9489** vs `natr`
over n = 397,692, per-frame max median 0.9458 — **STRUCK**, status
`dropped: Gate E STRUCK` (`candidates_r2.csv`). The screen kept this
candidate and dropped that one, at 0.8776 against 0.9489 on the same
comparator, so the margin between shipping and striking here is the wick
term plus the `×2` — which is a reason to read the port's own run
carefully, not a reason to expect either verdict.

⚠ Four things the screen's figure does **not** settle, and the port's own
run is what settles them:

1. the harness imports `pandas_ta.trend.j_kaufmanstop_dist`, not the
   prototype, and the engine's guards are not this module's — §G2 and §G4
   measure what those guards do to the column, and a real frame with a bad
   bar is not a synthetic one;
2. the comparator set has grown to 687 (329 `compute_all` + 358
   `ml_features` `1d`), and the screen's own figure came from `compute_all`
   alone;
3. the band reads a **top-five per-frame median** as well as the pooled
   figure (`r3-perframe-0.90`), and the screen's per-frame figure, 0.8601,
   is the maximum of its top five — 0.0175 below the pooled 0.8776 and
   0.04 below the 0.90 line;
4. and what the engine computes under the name `natr` was **not checked
   here** — whether `compute_all`'s `natr` is this fork's
   `pandas_ta.volatility.natr` at the same length, or another spelling of a
   normalised ATR, is not readable from this worktree. §L's `natr` row is
   this fork's column on synthetic frames, which is a different
   measurement.

If the port's run lands in DISCLOSE_GAP, the column ships with the note and
no waiver (only STRUCK needs one). If it lands STRUCK, the column is
reverted or waived before a release, and **this receipt is the deliverable
either way** — issue #124: *a measured revert closes this exactly as well
as a ship*.

---

## §G1 — the guards are no-ops on an ordinary frame

All five guards, each removed on its own, on all nine frames: **bit-equal in
all 45 cells.**

| guard removed | walk | trend | range-bound | grid | heavy-tailed | jump | flat | rising | tied |
|---|---|---|---|---|---|---|---|---|---|
| high is finite | True | True | True | True | True | True | True | True | True |
| low is finite | True | True | True | True | True | True | True | True | True |
| close is finite | True | True | True | True | True | True | True | True | True |
| close is positive+normal | True | True | True | True | True | True | True | True | True |
| output is finite | True | True | True | True | True | True | True | True | True |

---

## §G2 — each guard priced on a frame built to reach it

⚠ **The three input finite guards are measured NO-OPS, and this section is
why the module's comment says so rather than claiming otherwise.** One bad
value planted at bar 700 of a `walk` (1,500 bars, 1,479 fired clean):

| guard removed | planted | fired | fired w/o | inf | inf w/o | bit-equal | differ | max \|abs\| |
|---|---|---|---|---|---|---|---|---|
| high is finite | +inf | 1457 | 1457 | 0 | 0 | **True** | 0 | 0.000e+00 |
| high is finite | −inf | 1457 | 1457 | 0 | 0 | **True** | 0 | 0.000e+00 |
| high is finite | NaN | 1457 | 1457 | 0 | 0 | **True** | 0 | 0.000e+00 |
| low is finite | +inf | 1457 | 1457 | 0 | 0 | **True** | 0 | 0.000e+00 |
| low is finite | −inf | 1457 | 1457 | 0 | 0 | **True** | 0 | 0.000e+00 |
| low is finite | NaN | 1457 | 1457 | 0 | 0 | **True** | 0 | 0.000e+00 |
| close is finite | +inf | 1478 | 1478 | 0 | 0 | **True** | 0 | 0.000e+00 |
| close is finite | −inf | 1478 | 1478 | 0 | 0 | **True** | 0 | 0.000e+00 |
| close is finite | NaN | 1478 | 1478 | 0 | 0 | **True** | 0 | 0.000e+00 |

Identical cell for cell under the reduced CPU dispatch. `1479 − 22 = 1457`
and `1479 − 1 = 1478` are the §G4 blanking patterns.

**Why they are kept rather than deleted, stated as a trade-off rather than
as a load.** What absorbs a bad high or low is pandas' rolling window — an
infinite observation makes the window NaN rather than propagating — and
what absorbs a bad close is the final finite mask. Both are *pandas*
behaviours rather than this module's arithmetic, and §G3 pins the first one
on its own, so an upgrade that stopped doing it fails **there**. §G3's
route 1 also shows this chain producing an infinity from two **finite**
legs, which no input guard would catch either way.

⚠ **An earlier draft of this section claimed more than that and round 1 of
the review refuted it.** It said the bit-equality above pins the absorption
"in both directions, so the same upgrade fails here too". It does not —
§G5 measures why — so what keeps these three lines is defence in depth and
the shape the two sibling ports already have, not a measured load. The
honest reading, scoped to what ran: **removing these three lines would not
change any of the 42 guard-off cells measured here** — §G1's 27 (three
guards × nine clean frames), §G2's 9 (bar 700, three values) and §G5's 6.
⚠ §G4's other four plant points (bars 5, 100, 1,100 and 1,495) were **not**
re-run with a guard removed, so this is 42 cells rather than every cell in
the receipt; round 4 of the review found the wider quantifier.

**The close-is-positive-and-normal guard is the one that bites**, planted
at bar 700:

| close | bars blanked | fired | fired w/o | value w/o the guard at bar 700 | inf w/o |
|---|---|---|---|---|---|
| 0 | [700] | 1478 | 1478 | NaN | 0 |
| **−50** | [700] | 1478 | **1479** | **1.924e+00** | 0 |
| 5e-310 | [700] | 1478 | 1478 | NaN | 0 |

Without it the −50 bar **fires** and reads 1.924 — a sign-flipped number in
a column whose every other bar is 0.006 … 0.014 (§C1). That is the guard
earning its line.

---

## §G3 — three routes to an infinity on FINITE inputs

Three 120-bar frames, numbered in the order the routes occur in the chain:

| route | bars | fired | inf | fired w/o the mask | inf w/o the mask |
|---|---|---|---|---|---|
| 1. range (+DBL_MAX high, −DBL_MAX low) | 120 | 0 | 0 | 0 | **0** |
| 2. stop (2 × an average range near DBL_MAX/2) | 120 | 0 | 0 | 99 | **99** |
| 3. division (1e300 stop over a 1e-300 close) | 120 | 0 | 0 | 99 | **99** |

Identical cell for cell under the reduced CPU dispatch. **Two of the three
reach the output without the final mask**, so the mask is not decoration;
route 1 ships nothing, and the reason is the pandas behaviour below rather
than anything this module does — ⚠ which is also why that row is the one
figure in this section that is *contingent*: §G5 measures route 1 shipping
99 of 120 the moment the absorption goes, making it three of three.

81 bars of 1.0 with one bad value at bar 40, through `sma(·, 22)`:

```
+inf:    fired 38, inf 0, bar 40 = nan, bar 61 = nan
DBL_MAX: fired 60, inf 0, bar 40 = 8.171e+306
```

So an **infinite** observation blanks the 22 windows that hold it (60 − 22 =
38 fire) while a merely **huge** one flows straight through. ⚠ That is
`rolling.mean()`, not `ewm`: #122 measured the EWM *skipping* an infinite
observation and carrying on, which is why a bad low there moved values
instead of blanking bars. Pinned on its own by
`test_a_pandas_rolling_mean_turns_an_infinite_observation_into_nan`.

---

## §G4 — which bars a bad price empties, leg by leg

A `walk`, one bad value planted at bar **5**, 100, 700, 1,100 or **1,495**,
each of NaN, +inf and −inf — **45 cells**, 15 per leg:

| leg | plant | blanked | range | prefix bit-equal | later bars | later bars **moved** |
|---|---|---|---|---|---|---|
| high | **5** | **6** | 21 … 26 | True | 1,494 | **0** |
| high | 100 / 700 / 1,100 | **22** | T … T+21 | True | 1,399 / 799 / 399 | **0** |
| high | **1,495** | **5** | 1,495 … 1,499 | True | 4 | **0** |
| low | **5** | **6** | 21 … 26 | True | 1,494 | **0** |
| low | 100 / 700 / 1,100 | **22** | T … T+21 | True | 1,399 / 799 / 399 | **0** |
| low | **1,495** | **5** | 1,495 … 1,499 | True | 4 | **0** |
| close | **5** | **0** | — | True | 1,494 | **0** |
| close | 100 / 700 / 1,100 / 1,495 | **1** | T … T | True | 1,399 / 799 / 399 / 4 | **0** |

(Each row is three cells, one per planted value; all three agree.) Identical
cell for cell under the reduced CPU dispatch.

The range at T is in exactly the windows of `sma(high - low, 22)` that hold
it, of which only the ones past the warm-up were ever firing — so the rule
is `max(T, 21) … min(T+21, n-1)`: 22 bars in the middle of a frame, **5** at
bar 1,495 of 1,500, and **6** at bar 5, where bars 5 … 20 had never fired.
The close reaches the output only as the divisor, so it costs its own bar,
or **nothing** inside the warm-up.

⚠ **Both plant points came from the review, one per round**: round 1 asked
for the right edge after finding "blanks exactly bars T … T+21" stated
without one, and round 2 found the left edge still missing after that fix.
Both boundaries are now measured rather than reasoned, and the tests compute
the expectation from `max`/`min` instead of typing it.

⚠ **Nothing after the window moves, in any of the 45 cells.** That is the
opposite of #122, where a bad low blanked nothing and moved a bounded run
of 400 … 658 later bars, and the reason is structural: Wilder's recursion
remembers and a rolling window does not.

---

## §G5 — would the input guards bite if pandas STOPPED absorbing?

This section exists because round 1 of the review refuted an **inference**,
and the fix was to run the question rather than to re-word it. The claim was
that §G2's bit-equality pins pandas' absorption in both directions — that an
upgrade propagating an infinite observation instead of NaN-ing the window
would fail there as well as at §G3.

`sma` is rebound, by editing the import line of the shipped source, to a
mean that **propagates** an infinity, and each input guard is then removed
on top of that.

⚠ **Round 2 of the review proposed `rolling(...).apply(np.mean, raw=True)`
as that mean, and the measurement below refutes it**: all three `rolling`
aggregations measured read NaN at the planted bar while a numpy window mean
reads `inf`, which places the conversion *before* the window function
rather than in the mean, so the aggregation is irrelevant. On the `walk`
with a `+inf` high at bar 700 and the high guard removed:

| mean over `high - low` | value at bar 700 | inf bars | fired |
|---|---|---|---|
| the shipped `sma` (rolling) | NaN | 0 | 1457 |
| `rolling(...).apply(np.mean, raw=True)` | NaN | 0 | 1457 |
| `rolling(...).max()` | NaN | 0 | 1457 |
| **a numpy window mean, no `rolling`** | **inf** | **22** | 1479 |

So §G5 is built on the last one. That also sharpens what §G3's absorption
*is*: not a property of the mean, but of whatever pandas does to a window's
values **before** the aggregation sees them.
`test_no_rolling_aggregation_can_propagate_an_infinity` pins the three
cells.

⚠ **Three aggregations is a sample, not a proof, and pandas' source is not
readable from this worktree** — so "no `rolling` aggregation can propagate"
is an inference from three measured cells plus where pandas' documentation
puts the conversion, not a reading of the code. Round 3 of the review
caught an earlier draft stating the mechanism by name (`_prep_values`) and
crediting §G5 with printing it, which §G5 does not. What §G5 prints is the
behaviour. (`docs/JGatorMeasured.md` and `pandas_ta/momentum/j_gator.py`
already name `_prep_values` as that conversion, for the `ewm` path; this
receipt does not re-derive it and does not lean on the name.)

First, the rebinding must not change the clean column, or the comparison
would be about the mean rather than about the guard:

| frame (clean) | fired | fired w/ propagating mean | bit-equal | max \|abs\| |
|---|---|---|---|---|
| walk | 1479 | 1479 | **True** | 0.000e+00 |
| tied | 1479 | 1479 | **True** | 0.000e+00 |

Then, one bad value at bar 700 of a `walk`, with the matching guard removed:

| guard removed | planted | fired | fired w/o | inf | inf w/o | bit-equal | differ |
|---|---|---|---|---|---|---|---|
| high is finite | +inf | 1457 | 1457 | 0 | 0 | **True** | 0 |
| high is finite | −inf | 1457 | 1457 | 0 | 0 | **True** | 0 |
| low is finite | +inf | 1457 | 1457 | 0 | 0 | **True** | 0 |
| low is finite | −inf | 1457 | 1457 | 0 | 0 | **True** | 0 |
| close is finite | +inf | 1478 | 1478 | 0 | 0 | **True** | 0 |
| close is finite | −inf | 1478 | 1478 | 0 | 0 | **True** | 0 |

Identical cell for cell under the reduced CPU dispatch.

**So the three input guards stay no-ops even then**, because the final
`isfinite` mask converts the propagated infinity to a NaN at exactly the
bars the guard already blanks. The "pandas might change" story does
**not** justify the three lines. What does, as §G2 says, is defence in
depth and consistency with the two sibling ports — and a later session is
told where to look if it wants them gone.

⚠ **TWO of this port's tests would fail on such an upgrade, not one**, and
that is round 2 of the review's MAJOR: a draft of this section said "the
only test … is `..._into_nan`", in four files, having measured none of it.
§G3's route 1 ships **0** infinite readings without the final mask today,
and that zero is the absorption rather than anything this module does. The
three routes under the propagating mean:

| route (propagating mean) | bars | fired | inf | fired w/o the mask | inf w/o the mask |
|---|---|---|---|---|---|
| 1. range (+DBL_MAX high, −DBL_MAX low) | 120 | 0 | 0 | 99 | **99** |
| 2. stop (2 × an average range near DBL_MAX/2) | 120 | 0 | 0 | 99 | **99** |
| 3. division (1e300 stop over a 1e-300 close) | 120 | 0 | 0 | 99 | **99** |

So `test_route_1_never_reaches_the_output`, which asserts 0 infinite
readings without the mask, would fail too, and §G3's route-1 row would move
from 0 to 99 — three of three rather than two of three.
`test_route_1s_zero_is_the_absorption_and_would_move_without_it` is that
measurement. ⚠ What does **not** change is the shipped column: with the
mask in place all three routes ship 0 infinite readings even then, which is
the limb that matters for a feature.

---

## §L — in-fork overlap: A DISCLOSURE, NOT GATE E

Six synthetic frames, fork columns and rules retyped here; Gate E is 89 real
BIST frames against 687 engine comparators. Per-frame median \|ρ\|:

| column | frames | per-frame median \|ρ\| | min | max |
|---|---|---|---|---|
| `lean_avgrange_14` (retyped) | 6 | **0.5506** | 0.5214 | 0.5813 |
| `j_chandelier_dist:J_CHANDELIER_DIST_22_3.0` | 6 | 0.1436 | 0.0432 | 0.2442 |
| `Stop_2ATR_pct` (retyped) | 6 | 0.1366 | 0.0707 | 0.1747 |
| `true_range/close` (retyped) | 6 | 0.1096 | 0.0145 | 0.1733 |
| `natr:NATR_14` | 6 | 0.1092 | 0.0759 | 0.1319 |
| `j_safezone_dist:J_SAFEZONE_DIST_22_2.5_3` | 6 | 0.0497 | 0.0169 | 0.0704 |
| `Swing_Range_pct` (retyped) | 6 | 0.0094 | 0.0014 | 0.1095 |

Identical cell for cell under the reduced CPU dispatch.

⚠ **These figures are LOW, and that is a warning about the measurement
rather than a clean bill for the column.** `natr` is the one comparator with
both a synthetic and a real figure: **0.1092 here against the screen's
0.8611** — the six synthetic frames understate by 0.75, where #122's six
*overstated* by 0.0575. So §L cannot stand in for Gate E in **either**
direction.

What this section can say about why, measured on the synthetic side only —
the column is a wick term plus a range term:

| frame | std `(close-low)/close` | std `2*avg/close` | ratio | \|ρ\| vs the wick | \|ρ\| vs the range term |
|---|---|---|---|---|---|
| walk | 1.123e-03 | 7.395e-04 | 0.6587 | 0.8678 | 0.5875 |
| trend | 1.150e-03 | 7.224e-04 | 0.6283 | 0.8839 | 0.6083 |
| range-bound | 1.150e-03 | 7.212e-04 | 0.6269 | 0.8814 | 0.5741 |
| grid | 1.158e-03 | 8.108e-04 | 0.7001 | 0.8586 | 0.6198 |
| heavy-tailed | 1.171e-03 | 8.005e-04 | 0.6839 | 0.8659 | 0.6087 |
| jump | 1.155e-03 | 7.973e-04 | 0.6902 | 0.8570 | 0.6150 |
| tied | 1.292e-03 | 6.578e-04 | 0.5089 | 0.9203 | 0.5719 |

On these frames the **wick** term carries more of the column than the range
term does — over the six varying frames \|ρ\| 0.857 … 0.884 against the
wick and 0.574 … 0.620 against the range term, and 0.920 against 0.572 on
the `tied` frame the table adds to them — so a range-based comparator can
only reach so far. ⚠ **That real
ranges vary more is NOT measured here** — no real frame is readable from
this worktree — and the inference is left to the port's own Gate E run.

⚠ §L is also **not** blind to Gate E: `natr` is the screen's own top
comparator, and `Stop_2ATR_pct` and `Swing_Range_pct` are named in issue
#124's comparator list. What the engine computes under those names, and
whether it routes through this fork, was **not checked** here —
`Stop_2ATR_pct`, `Swing_Range_pct`, `lean_avgrange_14` and
`true_range/close` are rules **retyped from their names** (the first two
from issue #124, `lean_avgrange_14` from the screen file's own candidate,
which measured 0.8646 against this one), not the engine's columns.

⚠ **One consequence, and it is a risk signal rather than a to-do.**
`lean_avgrange_14` — the screen's own `SMA(H - L, 14)/close` candidate,
which paired at 0.8646 with this one (`cand_pairs_r2.csv`) — was itself
measured at max |ρ| **0.9489221914865852** vs `natr` over n = 397,692,
per-frame max median 0.9458059808195928, and **dropped STRUCK**
(`candidates_r2.csv`, verdict `STRUCK`, catalog `FORKDUP`, status
`dropped: Gate E STRUCK`; `skipped_r7.py:42` repeats it). So there is no
port to measure this pair against, and the right reading is the other way
round: **the nearest range-family candidate of the same round was struck
against the same comparator this column reads 0.8776 against.** ⚠ Earlier
drafts of this receipt called it an "unported candidate" to be measured
"before shipping both", which inverted what the CSV it quotes four of §E's
figures out of actually records; round 4 of the review caught it.

---

## §Z — cost: THIS MACHINE AND THIS RUN ONLY

```
j_kaufmanstop_dist       1.112 ms per call on 1500 bars
j_chandelier_dist        2.419 ms per call on 1500 bars
```

One subtraction, one rolling mean, one multiply-subtract, one division.
Linear in bars.

---

## §F — Gate F: suites

* `tests/test_j_kaufmanstop_dist.py` — **380 passed**: 306 as first written,
  369 after round 1 of the review (+63: the extreme-level cells widened to
  all nine frames, the 1,495 plant point, §G5's probe) and 380 after round 2
  (+11: the bar-5 plant point, the propagating-mean premise and the
  route-1 contingency). **Three** of the 380 read documents rather than the
  column — `test_the_receipt_says_gate_e_is_pending` reads this file,
  `test_no_gate_e_row_is_recorded_yet` reads the ledger and
  `test_the_docstrings_first_paragraph_survives_the_dictionary_cut` lifts
  `desc` out of `docs/gen_indicator_dictionary.py` (round 2 counted two) —
  and the same **380** run under
  `NPY_DISABLE_CPU_FEATURES="AVX512F AVX512_SKX AVX2 FMA3"` via
  `python docs/measure_j_kaufmanstop_dist_cpu.py`, which prints the
  dispatchable features still enabled and refuses to run if any of the four
  survived.
* `tests/test_j_kaufmanstop_dist.py` with `tests/test_gate_e_ledger.py` —
  **1,486 passed, 1 failed**:
  `test_every_indicator_that_needs_a_row_has_one`, whose message reads
  `no Gate E ledger row for ['j_kaufmanstop_dist']` and names nothing else.
  **Owed, not failed** — CI into `dev` sets `GATE_E_PENDING_OK=1` and skips
  it with a reason starting "Gate E owed".
* full suite — **2 failed, 12,700 passed, 86 skipped** in 409 s: the owed
  Gate E row above, and `test_regenerating_reproduces_the_committed_rows`,
  the `../AlternativeRepos`-dependent talib CSV test that CI deselects by
  name.
  These two totals are from a **re-run after the rebase onto `dev`** of
  2026-11-20, which brought in issue #125's `c22_ami_timescale` port: the
  review folder's copies of them (1,478 / 1 and 2 / 12,496 / 86) are the
  pre-rebase run of the same two selections, and the two failures are the
  same two. The module's own **380** is unchanged by the rebase, re-run
  under the reduced CPU dispatch after it.
  The 86 skips are the upstream correlation suite (`data/SPY_D.csv` is
  gitignored) plus the usual optional-dependency skips.
* the five wiring touch points: `pandas_ta/trend/j_kaufmanstop_dist.py`,
  `pandas_ta/trend/__init__.py`, `Category["trend"]` in
  `pandas_ta/__init__.py`, the `df.ta.j_kaufmanstop_dist()` accessor in
  `pandas_ta/core.py`, and `tests/test_j_kaufmanstop_dist.py`. Counts moved
  with it: `CATEGORY_TOTAL` 358 → **359** in
  `tests/test_altport2_ports.py`, README 358 → **359** registered / 366 →
  **367** callable / **trend (65)**, `docs/IndicatorDictionary.md`
  regenerated, and `docs/MLCompanionContract.md` 703 → **704** tagged
  columns / 340 → **341** `SF`.
* the parent repo's suite is the launcher's.

---

## What a later session should know

1. **Gate E is owed and so is Gate C's real-data limb.** Both come from the
   launcher's run of
   `gate_e_overlap.py run --module pandas_ta.trend.j_kaufmanstop_dist`. The
   receipt session records the ledger row, writes the measured numbers into
   §E, fills §C1's real counts and replaces the two pending tests.
2. **The screen's figure is this arithmetic's** (§A3, bit-equal), so a run
   landing near 0.8776 vs `natr` is the expected outcome rather than a
   surprise — which also makes it the easiest row to copy over by mistake.
   The replacement test should pin the run id, not only the numbers.
3. **§L is not a floor.** Six synthetic frames read 0.75 **below** the real
   fork figure on `natr`. Do not read §L's 0.1092 as "this column is
   independent of `natr`".
4. **The nearest candidate of the same family was STRUCK.**
   `lean_avgrange_14` (`SMA(H - L, 14)/close`), which paired at 0.8646 with
   this column, measured 0.9489 vs `natr` and was dropped
   (`candidates_r2.csv`, `dropped: Gate E STRUCK`). There is nothing to
   measure the pair against — read it as the risk on this column's own run
   instead, against the same comparator.
5. **The three input finite guards are measured no-ops** (§G2) — and they
   stay no-ops even with a mean that propagates an infinity (§G5), so the
   "pandas might change" story does not save them. If a later session wants
   to simplify the module, that is the honest place to look. What the
   column *does* lean on is pandas turning an infinite observation into a
   NaN before a `rolling` aggregation sees it — measured on three
   aggregations in §G5, mechanism not claimed. Two tests would fail if that
   went (`test_a_pandas_rolling_mean_turns_an_infinite_observation_into_nan`
   and `test_route_1_never_reaches_the_output`), and neither depends on the
   guards.
