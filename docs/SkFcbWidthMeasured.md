# SK-FCB-WIDTH — `sk_fcb_width` measured (PandasTa issue #107)

**Port:** `pandas_ta/volatility/sk_fcb_width.py` → one column, `SK_FCB_WIDTH_2`.
**Source:** Skender Stock.Indicators (Apache-2.0), `Fcb`, as issue #107 names it —
*"`Fcb.Series.cs: upper - lower`"*, span 2. The `/ close` is the fork's, from the
screen prototype's scale-free form.
**Measured:** 2026-11-14, on this tree, by `python docs/measure_sk_fcb_width.py`.
Every figure below is printed by that script; nothing here is derived or carried over.
**§E and §E1–§E3 are the exception**: they are read out of the launcher's Gate E run
`is107-sk_fcb_width-8f25baf3` (2026-11-15) — `overlap_max.csv`, `top25.csv`,
`perframe.csv`, `degenerate.csv`, `meta.json` — and out of the row
`python docs/gate_e_ledger.py record` wrote into `docs/gate_e_ledger.csv`.
`python docs/measure_sk_fcb_width_cpu.py` re-runs it (and the test module) with
numpy's `AVX512F`, `AVX512_SKX`, `AVX2` and `FMA3` dispatch disabled — §CPU records
which figures moved.

    upper[T]       = level of the last CONFIRMED fractal high, held forward
    lower[T]       = level of the last CONFIRMED fractal low,  held forward
    SK_FCB_WIDTH_2 = (upper - lower) / close

A fractal high is centred on a bar whose high beats all 2 highs on each side
**strictly**; it is confirmed 2 bars later, when those right-hand bars exist.

---

## ⚠ What this port does NOT establish

`Fcb.Series.cs` was **not read**. Stock.Indicators is not installed in this worktree,
`docs/pine/` is absent (and holds Pine, not C#, in any case), and a repo-wide search for
`Fcb.Series.cs` finds nothing — those three are pinned by
`tests/test_sk_fcb_width.py::test_the_source_library_is_not_readable_here`, so the claim
cannot rot into "checked against Skender" if a dependency or a vendored corpus appears.
⚠ Web access was also unavailable in this session, and that one is **not pinned by
anything**: a test cannot see it. An earlier draft of this paragraph said the test
"records all three" with web access among them, which round 1 of the review caught.

What Gate A checks is **the formula issue #107 names**, spelled two ways — **one** of them
independent of this module (§A1's loop transcription, which shares no code with it) and
one of them the screen prototype's same rolling expression retyped, whose bit-equality
buys the tie to the screen's Gate E figures and prices the module's guards at zero rather
than giving a second derivation.
The attribution in the module docstring is to that naming, not to a reading of the code.
One consequence is carried openly rather than buried: see §A3 — Skender's `Fractal`
returns a level **on its centre bar**, and what `Fcb` then does with that index is
exactly the thing this worktree cannot check.

## The eight frames

Seven are `tests/test_j_acosc.py`'s, unchanged, so the frame set is shared across ports:
`walk`, `trend`, `range-bound`, `grid` (0.01 tick), `heavy-tailed`, `jump`, `flat`.
The eighth, `coarse`, is this indicator's own: a walk rounded to a **2.0** tick, coarser
than its own bar-to-bar move, so that **ties are common instead of impossible**. It
exists because the fractal predicate is strict and FVGDEAD (`CLAUDE.md`) is this repo's
record of a column whose behaviour on synthetic continuous floats said nothing about its
behaviour on rounded prices.

1,500 bars each; 10,330 fired bars pooled.

---

## A1 — Gate A, limb 1: the source formula by explicit loops

Skender's `Fractal` double loop (`if (evalHigh <= pHigh) isHigh = false;`, guarded by
`i >= leftSpan && i < length - rightSpan`) plus `Fcb`'s roll-forward
(`upperLine = f.FractalBear ?? upperLine`), transcribed and sharing no code with the
module.

| frame | fired | masks match | max \|diff\| | bit-equal |
|---|---|---|---|---|
| walk | 1,491 | yes | 0.000e+00 | **yes** |
| trend | 1,479 | yes | 0.000e+00 | **yes** |
| range-bound | 1,491 | yes | 0.000e+00 | **yes** |
| grid | 1,477 | yes | 0.000e+00 | **yes** |
| heavy-tailed | 1,493 | yes | 0.000e+00 | **yes** |
| jump | 1,488 | yes | 0.000e+00 | **yes** |
| flat | 0 | yes | — | **yes** (both all-NaN) |
| coarse | 1,411 | yes | 0.000e+00 | **yes** |

**Bit-equal, not within a tolerance** — and that is structural rather than lucky: a band
leg is a *selected* price level, so the whole computation is one subtraction and one
division. There is no accumulator to disagree about. ⚠ This limb is the independent one:
the double loop shares no code with the module. §A2's does not — see its note.

## A2 — Gate A, limb 2: the screen prototype, bit for bit

`docs/issues/screen/ind_screen_r2.py`, candidate `sk_fcb_width`, retyped (that file is
gitignored). ⚠ **Not an independent spelling, and it is not claimed as one:** the
prototype's `last_fractal` is the module's `_last_fractal` operation for operation, so its
bit-equality on a clean frame is structural. What the limb buys is the **tie to the
screen's Gate E figures** — those were measured on this expression — and the guards priced
at zero.
**Bit-equal on all eight frames**: max \|diff\| 0.000e+00 on the seven firing frames, and
on `flat` there is no shared bar at all, so the script prints `nan` there and
bit-equality is the two all-NaN masks matching.

That also prices the module's guards at **zero on a clean frame**: the prototype has
none, and the two are bit-identical anyway.

## A3 — ⚠ the index, which is this port's one divergence

Skender's `Fractal` returns the level **on the centre bar**. Read there, the band would
be knowable 2 bars before its right-hand bars existed. This port reads it 2 bars later;
so does the screen prototype. Both readings are measured, so the divergence is a number
rather than a preference:

| frame | both fire | bars differing | bars shared | Spearman | sweep (of 36) |
|---|---|---|---|---|---|
| walk | 1,491 | 783 | 708 | 0.4638 | 33 |
| trend | 1,479 | 649 | 830 | 0.5301 | 34 |
| range-bound | 1,491 | 839 | 652 | 0.5324 | 33 |
| grid | 1,477 | 787 | 690 | 0.4910 | 35 |
| heavy-tailed | 1,493 | 813 | 680 | 0.5355 | 33 |
| jump | 1,488 | 722 | 766 | 0.5901 | 33 |
| coarse | 1,411 | 46 | 1,365 | 0.9643 | **0** |

`sweep` is §B's detector run on the centre reading: a look-ahead, caught. It is **not 36
of 36 and cannot be** — the look-ahead reaches exactly 2 bars and only shows when a
fractal decision within 2 bars of the boundary flips. On `coarse` it is invisible
(0 of 36), which is the same fact as that row's 46 differing bars: a starved band has
almost nothing to look ahead *at*. **That is why Gate B is the mutant comparison and not
this sweep alone.**

The confirmed reading is the one the screen measured and the only one of the two that
passes Gate B. What `Fcb.Series.cs` itself does with the index is **not established**
(§"What this port does NOT establish").

## A4 — the other readings not taken

Spearman against the shipped column, and the count of bars where they differ at all.

**Non-strict (`>=` / `<=`) — a tie still makes a fractal:**

| frame | column fires | alt fires | bars differing | Spearman |
|---|---|---|---|---|
| walk | 1,491 | 1,491 | **0** | 1.0000 |
| trend | 1,479 | 1,479 | **0** | 1.0000 |
| range-bound | 1,491 | 1,491 | **0** | 1.0000 |
| heavy-tailed | 1,493 | 1,493 | **0** | 1.0000 |
| jump | 1,488 | 1,488 | **0** | 1.0000 |
| grid | 1,477 | 1,477 | 43 | 0.9556 |
| coarse | 1,411 | 1,495 | 1,235 | **0.0567** |

⚠ **On continuous prices the choice is invisible; on a coarse tick grid it is the whole
column.** Bit-identical on all five continuous frames, and a *different* column at a 2.0
tick. Per `CLAUDE.md`, 86,415 of 408,253 real BIST daily bars — **21.17%** — close
exactly at an extreme, so the real-data regime is the right-hand rows of this table and
the continuous frames predict nothing about it. Gate A's care about `<=` versus `<` is
therefore not pedantry; it is the difference between two columns.

**`EndType.Close` — Skender's other option, judging and returning the close:**
Spearman **0.1857 .. 0.9132** across the seven firing frames, differing on **896 .. 1,491**
of the bars they share (896 is `coarse`; the other six run 1,473 .. 1,491). A near
neighbour, not a restatement; `Fcb` uses `HighLow` and so does this port.

---

## B — Gate B, causality

**The detector is not the usual "multiply the tail by 1.03", and that is deliberate.**
Each frame is split into one shared past and two *wholly different* futures: bars `>= j`
scaled up by a per-bar random factor in [1, 4] in one, down by its reciprocal in the
other. Bars `< j` are multiplied by exactly 1.0 (exact in binary), one factor multiplies
high, low and close together so `high >= close >= low` survives, and the question is
whether any bar `< j` moved. A fractal is a **comparison**, so a 3% nudge leaves most
decisions intact — a weak detector returning 0 would be weak evidence.

**The module, over 36 offsets (1464..1499) and then over every bar but bar 0 — 1,499 of
1,500, a split at bar 0 having no prefix to compare:**

| frame | caught of 36 | caught of 1,499 |
|---|---|---|
| walk | 0 | **0** |
| trend | 0 | **0** |
| range-bound | 0 | **0** |
| grid | 0 | **0** |
| heavy-tailed | 0 | **0** |
| jump | 0 | **0** |
| flat | 0 | **0** |
| coarse | 0 | **0** |

**Five look-ahead mutants**, read off the shipped source, edited and `exec`'d in memory
(`centre-read` = the confirmed level moved back onto its centre bar, i.e. §A3's reading;
`right-window-lead` = one extra bar of right-hand window; `band-bfill` = `ffill` → `bfill`;
`output-early` = the column shifted back one bar; `divisor-lead` = `close.shift(-1)`),
out of 36:

| frame | centre-read | right-window-lead | band-bfill | output-early | divisor-lead |
|---|---|---|---|---|---|
| walk | 33 | 6 | 36 | 36 | 36 |
| trend | 34 | 6 | 35 | 36 | 36 |
| range-bound | 33 | 9 | 35 | 36 | 36 |
| grid | 35 | 6 | 35 | 36 | 36 |
| heavy-tailed | 33 | 8 | 35 | 36 | 36 |
| jump | 33 | 4 | 35 | 36 | 36 |
| **flat** | **0** | **0** | 28 | **0** | **0** |
| **coarse** | **0** | **0** | 32 | 36 | 36 |

⚠ **A 36-of-36 headline is not available for this indicator and is not claimed.** Three
of the five look ahead through a comparison, so an offset where the boundary decisions
agree either way sees nothing; `right-window-lead` — one single bar of extra reach, the
most insidious kind — is caught on as few as **4 of 36**. `flat` never fires, so only
`band-bfill` reaches it at all — **1 of the 5**; `coarse`'s two band legs move 15 and 12
times in 1,500 bars, and it catches **3 of the 5**. Neither frame is dropped from the
receipt to improve the table.

**The gate is therefore a pair of statements, both asserted in
`tests/test_sk_fcb_width.py`:**

1. the module is caught on **0** of 36 offsets on **each of the eight frames**, and on
   **0 of 299** — every bar but bar 0 — of a 300-bar walk, which is the dense form the
   suite does run; the 0-of-1,499 (every bar but bar 0, of 1,500) table above is this
   script's and the suite does **not** run it. (An earlier draft of this receipt
   advertised the 1,499 figure as if a test asserted it, which round 1 of the review
   caught; the dense 299-offset test was added in response, so the claim now has an
   assertion behind it.) And
2. every mutant is caught **somewhere on each of the six frames other than `flat` and
   `coarse`**, and is independently shown to be **live** — it moves the column on the
   unperturbed `walk`:

| mutant | bars both fire | same | moved | max \|rel\| |
|---|---|---|---|---|
| centre-read | 1,491 | 708 | 783 | 1.067e+01 |
| right-window-lead | 1,491 | 1,274 | 217 | 1.333e+01 |
| band-bfill | 1,490 | 0 | 1,490 | 1.029e+02 |
| output-early | 1,490 | 0 | 1,490 | 1.066e+01 |
| divisor-lead | 1,490 | 0 | 1,490 | 3.199e-02 |

`centre-read` is asserted bit-equal to §A3's independently-built centre reading, so it is
the documented alternative reading rather than an invented edit.

## B2 — the weakest mutant, swept where its edit is exposed

A blind margin of **4 of 36** is not evidence, so `right-window-lead` — one extra bar of
right-hand window — is carried by reading the edit instead. That mutant's right window
for centre `c` is `{c+2, c+3}` instead of `{c+1, c+2}` and the verdict still lands on bar
`c + 2`, so bar `T` reads `x[T+1]` and **bar `j - 1` is the only prefix bar a split at `j`
can reach**. Its verdict there is `ref > max(left) and ref > max(x[j-1], x[j] * f)` for
whichever factor `f` a future applies, so it can be True under *some* future only when

    x[j-3] > max(x[j-5], x[j-4], x[j-1])

— **necessary by construction**. Swept densely over every offset from 5 on, which is
1,495 of each frame's 1,500 (the condition reads back to bar `j - 5`):

| frame | offsets | exposed | caught of exposed | caught of unexposed |
|---|---|---|---|---|
| walk | 1,495 | 272 | 270 | **0** |
| trend | 1,495 | 250 | 249 | **0** |
| range-bound | 1,495 | 320 | 314 | **0** |
| grid | 1,495 | 295 | 293 | **0** |
| heavy-tailed | 1,495 | 283 | 280 | **0** |
| jump | 1,495 | 266 | 262 | **0** |
| coarse | 1,495 | 36 | 24 | **0** |
| **POOLED** | **10,465** | **1,722** | **1,692** | **0** |
| unexposed | **8,743** | — | — | **0** |

The last column is the control: 0 on all seven frames, over **8,743** unexposed offsets,
which is the derivation confirmed rather than asserted. ⚠ Both pooled rows are **printed
by the script**, not added up here: an earlier draft hand-added that control to 8,730 and
round 3 of the review caught the 13.

Exposure is necessary and **not** sufficient, and all 30 misses are classified rather
than waved at — three mechanisms, nothing left over:

| frame | missed | verdicts agree anyway | flipped level equals the carried one | column not fired by bar j-1 | other |
|---|---|---|---|---|---|
| walk | 2 | 2 | 0 | 0 | **0** |
| trend | 1 | 1 | 0 | 0 | **0** |
| range-bound | 6 | 6 | 0 | 0 | **0** |
| grid | 2 | 2 | 0 | 0 | **0** |
| heavy-tailed | 3 | 2 | 0 | 1 | **0** |
| jump | 4 | 4 | 0 | 0 | **0** |
| coarse | 12 | 0 | 9 | 3 | **0** |
| **POOLED** | **30** | **17** | **9** | **4** | **0** |

The pooled row is printed too, for the same reason. "Verdicts agree anyway" is the up-future's factor being only `[1, 4]`, which need not
clear `ref`; "level equals" is the flipped verdict writing the price the band already
carried, which is why it is `coarse`'s whole story — ties make equal levels common there.
`tests/test_sk_fcb_width.py::test_gate_b_mutant_the_weakest_edit_is_swept_where_it_is_exposed`
asserts both halves (0 outside, and 0 unexplained inside) on 300-bar `walk` and `coarse`
frames.

---

## C — Gate C, reachability (synthetic; the real-data counts are §E2)

| frame | bars | fired | first fire | distinct | min | max | `< 0` | `== 0` |
|---|---|---|---|---|---|---|---|---|
| walk | 1,500 | 1,491 | 9 | 1,491 | -0.0527 | 0.1157 | 20 | 0 |
| trend | 1,500 | 1,479 | 21 | 1,479 | -0.1173 | 0.1750 | 91 | 0 |
| range-bound | 1,500 | 1,491 | 9 | 1,491 | -0.0590 | 0.1687 | 5 | 0 |
| grid | 1,500 | 1,477 | 23 | 1,472 | -0.0341 | 0.1425 | 33 | 0 |
| heavy-tailed | 1,500 | 1,493 | 7 | 1,493 | -0.1294 | 0.3441 | 21 | 0 |
| jump | 1,500 | 1,488 | 12 | 1,488 | -0.0257 | 0.4052 | 20 | 0 |
| **flat** | 1,500 | **0** | — | 0 | — | — | 0 | 0 |
| coarse | 1,500 | 1,411 | 89 | **60** | -0.0556 | 0.3158 | 20 | **85** |

`0 < fires < n` holds on all seven firing frames. Three readings of this table matter
more than the counts:

⚠ **The warm-up is data-dependent, and there is no constant to quote.** The column is NaN
until a fractal high **and** a fractal low have both confirmed: bar **7** on one frame
here, bar **89** on another. The earliest it can ever be is bar `2 * SPAN` = 4, which
needs one bar to be both the strict high and the strict low of its window — an outside
bar. That is reachable, and §L pins it with a hand frame. `MIN_BARS` = 5 is a floor on
the **input**, and `docs/IndicatorDictionary.md`'s warm-up column shows **10**, which is
that one probe frame's figure and not a property of the column. §E2 is the real-data form
of the same finding: 1,240 empty bars over 89 frames, i.e. 13.93 per frame, which no
per-frame constant can produce.

⚠ **A flat price never fires**, on all 1,500 bars. A constant price has no strict local
extreme, so no fractal ever confirms. That is a statement about the instrument, not
missing data. **Whether it is unusual for this category is §C3, which runs the other 36
indicators instead of guessing** — it is not: 13 of the bucket's 63 columns read all-NaN
on a flat frame, this one among them.

⚠ **It is not a non-negative width, despite the name.** `upper` and `lower` are read from
*different* bars, so nothing makes the difference positive: **5 .. 91** negative
readings on each firing frame (the `< 0` column above: 20 / 91 / 5 / 33 / 21 / 20 / 20),
down to **-0.1294**, plus **85** readings of exactly **0.0** on `coarse`, where both legs
land on one tick — so the `<= 0` count runs to **5 .. 105** once those zeros are included,
and the two figures are different things. §H is the mechanism. A consumer clipping at
zero, or taking a log, discards a real reading. The exact zeros are **not** a synthetic
artefact: §E2's Gate E run reads **108** of them on 397,609 fired real BIST bars. The
negative readings are a synthetic figure only — the ledger row counts NaNs and zeros, not
signs.

### The band is a step function over a moving divisor

| frame | upper steps | lower steps | max age, upper | max age, lower | mean age |
|---|---|---|---|---|---|
| walk | 216 | 205 | 19 | 18 | 5.76 |
| trend | 172 | 178 | 29 | 31 | 7.52 |
| range-bound | 229 | 230 | 18 | 18 | 5.26 |
| grid | 213 | 211 | 26 | 29 | 6.06 |
| heavy-tailed | 215 | 220 | 18 | 20 | 5.62 |
| jump | 191 | 195 | 19 | 25 | 6.56 |
| coarse | **15** | **12** | **427** | **428** | **191.59** |

The band changes only when a fractal confirms; between confirmations the column moves
**only because `close` does** — and on a coarse grid one leg is held for up to 428 bars.
That last sentence is counted, not reasoned: bars where *neither* leg moved and the
column moved anyway.

| frame | band held | of which the column still moved | column held too |
|---|---|---|---|
| walk | 1,071 | **1,071** | 0 |
| trend | 1,131 | **1,131** | 0 |
| range-bound | 1,033 | **1,033** | 0 |
| grid | 1,054 | **1,050** | 4 |
| heavy-tailed | 1,059 | **1,059** | 0 |
| jump | 1,103 | **1,103** | 0 |
| coarse | 1,387 | **271** | 1,116 |

On the five continuous frames every band-held bar still moves, because the close does. On
the 0.01-tick frame all but **4** of 1,054 do, and on the 2.0-tick frame only **271** of
1,387 — the rounded close repeats as well, which is also why that frame takes just 60
distinct values. ⚠ How much of the column's *level* the
divisor accounts for is a different question, and §F measures it: not much.

## C2 — the strict predicate against a tick grid

The same walk at four tick sizes:

| tick | upper fractals | lower fractals | fired | first fire |
|---|---|---|---|---|
| none | 216 | 205 | 1,491 | 9 |
| 0.01 | 212 | 199 | 1,491 | 9 |
| 0.5 | 71 | 82 | 1,476 | 24 |
| 2.0 | **15** | **12** | 1,411 | 89 |

Ties counted directly — bars whose high equals the high of a bar within 2 of it, which is
where a fractal is lost:

| frame | high ties | low ties |
|---|---|---|
| walk | **0** | **0** |
| grid (0.01) | 22 | 16 |
| coarse (2.0) | 1,448 | 1,450 |

Continuous floats never tie; rounded prices do, and rounding starves the band
monotonically in the tick — **on both legs**, 216 → 212 → 71 → 15 upper and
205 → 199 → 82 → 12 lower, which is what
`tests/test_sk_fcb_width.py::test_a_tick_grid_starves_the_band` asserts per leg.

---

## C3 — what the rest of the volatility bucket does on a flat price

"This column reads NaN where the others read 0.0" is a claim about 36 other indicators,
so it was **run**: every name in `Category["volatility"]` on a 600-bar flat OHLCV frame,
through its own `df.ta` accessor at defaults. 63 columns, 0 raised.

| behaviour on a flat frame | columns | examples |
|---|---|---|
| **all NaN** | **13** | `cvi:CVI_10_10`, `edge:EDGE_21`, `g191_023`, `g191_109`, `g191_188`, `har_park`, **`j_damiani:J_DAMIANI_13_40`**, `range_profile` (all 3), `roll_spread:ROLL_20`, `rvi:RVI_14`, **`sk_fcb_width:SK_FCB_WIDTH_2`** |
| **all exactly 0.0** | **26** | `atr2`, `atr_ma_multiple`, `bbands:BBB_5_2.0`, `corwin_schultz`, `g191_158`, `g191_160`, `g191_174`, `garman_klass`, `range_compress_run`, `rogers_satchell`, `tf_median_absdiff_20`, `thermo` (5), `ui`, `volvol`, `wvma` (5), `yang_zhang`, `hwc` (2 dist-pct) |
| other (price levels, or non-zero) | 24 | `aberration` (4), `accbands` (3), `atr:ATRr_14`, `bbands` (3 bands), `donchian` (3), `hwc` (3 lines), `kc` (3), `massi`, `natr`, `pdist`, `true_range` |

**So an all-NaN flat frame is NOT a divergence in this bucket** — 13 of 63 columns do it,
including `j_damiani`, the previous port into this same category. The earlier draft of
this receipt asserted the opposite ("a divergence from every rolling-window column in
this category, which would read 0.0") without running anything, and round 1 of the review
caught it. The reason here is a missing strict local extreme rather than a guard or a
zero divisor; **the other twelve all-NaN columns were not inspected**, so no claim is
made about their mechanisms.

For the record, the comparison that draft also got loose: `j_acosc` reads exactly 0.0 on
all **1,463 of its fired bars** of a flat frame (its own receipt), not "on every bar" of
1,500 — its warm-up is 37 bars.

## D — Gate D, scale

**Exact factors.** `x8` and `x64` are exact in binary. The band legs are selected by
comparisons, which no positive rescale changes; `(a*f - b*f) / (c*f)` then has the same
real quotient as `(a - b) / c` and is rounded once, so bit-identity is structural.

**Bit-identical on every fired bar of all eight frames** (10,330 pooled) under both
factors, and the same run repeated at three price levels:

| level | fired | x8 | x64 | max \|value\| (17 digits) |
|---|---|---|---|---|
| 1e-06 | 1,491 | bit-equal | bit-equal | 0.11567335156432018 |
| 1e+06 | 1,491 | bit-equal | bit-equal | 0.11567335156432024 |
| 1e+100 | 1,491 | bit-equal | bit-equal | 0.1156733515643201 |

⚠ Across those three levels the column is **not** bit-equal to itself, and the only
figure measured for that is the one in the table: the three `max |value|` statistics
agree to 17 significant digits except in their last two (…018 / …024 / …01, i.e. about
5e-16 apart on that statistic). The cause is that 1e-6, 1e+6 and 1e+100 are not exact
binary multiples, so the frame builder's `level * exp(...)` already differs in its last
bits — these are three different price paths, not one path at three scales, and no
per-bar bound across levels is claimed. The 17-digit print is the disclosure; a
four-digit one would have hidden it.

**Inexact factors** (`x10`, `x3.7`, `x0.1`, `x1.0000001`, over the seven firing frames —
28 pairs): NaN masks match on all 28, max \|rel\| **1.229e-12** (on `grid` at `x3.7`),
asserted at 1e-9.

⚠ **The risk peculiar to this column is not that last bit.** A rescale that collapsed two
distinct neighbouring prices onto one double would destroy a strict inequality and move a
band leg by a *whole price level*. Measured: **0** such selection flips over all 28
pairs, both legs. That is a measurement over these frames, **not** a proof that it cannot
happen — two doubles one ulp apart can round together under a multiplication, and ties,
once present, survive any rescale.

---

## E — Gate E, measured on this port

**Run `is107-sk_fcb_width-8f25baf3`, measured 2026-11-15** by issue-solver on the code at
this branch's HEAD, recorded in `docs/gate_e_ledger.csv` by
`python docs/gate_e_ledger.py record`. One column, one row:

| column | max \|ρ\| | against | set | n | per-frame max median | frames | verdict |
|---|---|---|---|---|---|---|---|
| `SK_FCB_WIDTH_2` | **0.6103868035919393** | `natr` | compute_all | **397,416** | **0.584568208291009** (`natr`) | 89 | **SHIP** |

Under `r3-perframe-0.90` that is the **SHIP** band — pooled \|ρ\| < 0.76 and no top-5
comparator's per-frame median at 0.90 — so **nothing is removed** and no waiver is needed
(only STRUCK needs one). `verdict_pooled_only` is the same `SHIP`, so neither limb carried
the other. Run facts from `meta.json`: default parameters (`kwargs {}`), 89 frames,
398,849 pooled bars, 329 compute_all + 358 manifest = **687** comparators, canary
`AKBNK.IS, BIENY.IS, AGHOL.IS, SASA.IS bit-equal`, **0** comparators dropped as degenerate
(`degenerate.csv` is empty), data stamp `1be6495e`, pandas 2.3.3 / numpy 1.26.4.

**The run reproduced the 2026-10-24 screen's prototype figures to every digit issue #107
printed** — same comparator `natr`, same n = 397,416, the same 0.6104 and 0.5846, and the
same runners-up `Stop_2ATR_pct` 0.6104 and `Swing_Range_pct` 0.5530. That is the expected
outcome rather than a surprise: §A2 asserts this module **bit-equal** to the retyped
prototype on all eight frames. An expected agreement is also the easiest kind of row to
copy over by mistake, which is why
`tests/test_sk_fcb_width.py::test_the_gate_e_row_is_this_ports_own_measurement` pins the
row's own **run id** and not only its arithmetic.

### E1 — what the row says beyond the band

Top five by pooled \|ρ\| (`top25.csv`), with each one's per-frame figures over the 89
frames (`perframe.csv`):

| comparator | set | pooled ρ | per-frame median | per-frame max | per-frame min | % frames ≥ 0.80 |
|---|---|---|---|---|---|---|
| `natr` | compute_all | 0.6104 | 0.5846 | 0.6785 | 0.4382 | **0.0** |
| `Stop_2ATR_pct` | manifest | 0.6104 | 0.5846 | 0.6785 | 0.4382 | **0.0** |
| `Swing_Range_pct` | manifest | 0.5530 | 0.5262 | 0.6412 | 0.2948 | **0.0** |
| `BB_BWidth` | compute_all | 0.4998 | 0.4755 | 0.5785 | 0.2570 | **0.0** |
| `mad_pct` | manifest | 0.4463 | 0.4172 | 0.5191 | 0.1604 | **0.0** |

Stronger than the band requires, and reported because the band reads a top-5 comparator's
per-frame **median**: **no single one of the 89 frames reaches 0.80** on any of the top
five, let alone 0.90 — the worst single frame of that table is **0.6785**, on the top
comparator. `top25.csv` then falls away to 0.2632 (`BOS_BULL`) at rank 25.

⚠ **`natr` and `Stop_2ATR_pct` are rank-identical here**, and that is read off the files
rather than reasoned: both are printed with the same pooled ρ to all 16 digits
(0.6103868035919393), the same n = 397,416 and the same five per-frame statistics to all
their digits. Spearman sees only ranks, and `2 * ATR / close` is an increasing function of
`100 * ATR / close`, so the two comparators are one measurement under two names — the
engine's columns are not this session's to inspect, so that mechanism is a reading of
their names and the identity is the measurement.

The nearest comparators are all **range or dispersion over price** — NATR, a 2-ATR stop
distance, a swing range, Bollinger bandwidth, mean absolute deviation. That is the same
family §F names, so the band is driven by the thing this column measures and not by an
unrelated column.

### E2 — Gate C's real-data limb, which this run closes

Read off the ledger row rather than retyped: **397,609 of 398,849** pooled bars fire, so
`0 < fires < n` holds on 89 real BIST frames and not only on the synthetic ones of §C.

⚠ **The 1,240 empty bars are NOT a constant warm-up**, and that is §C's data-dependent
warm-up confirmed on real data: 1,240 / 89 = **13.93 bars per frame on average**, which is
not a whole number of bars, so no per-frame constant can produce it. The floor is
`2 * SPAN` = 4 bars per frame, i.e. 356 of the 1,240, and the rest is how long each
instrument took to confirm a fractal high **and** a fractal low. ⚠ 13.93 is **empty bars
per frame**, not a mean first-fire bar, and the two are the same number only if the real
NaNs are a leading prefix — which this row cannot show, since §G1's bad close empties its
own bar wherever it sits. §C's synthetic first fires ran bar 7 .. 89, so the mean is inside
that range; nothing here says each frame is.

**108 fired bars read exactly 0.0** (`non_nan` 397,609 − `non_zero` 397,501, the harness's
`non_zero` being the non-NaN readings that are not exactly 0.0, as `j_acosc`'s receipt reads
it). That is §C's `coarse`-frame disclosure holding on real prices: both band legs land on
one tick, so the width is exactly zero. ⚠ The row carries **no** count of NEGATIVE real
readings — it reports NaN and zero only — so §C's 5 .. 91 negatives per frame stay a
**synthetic** figure, and the real-data question is open. A consumer clipping at zero or
taking a log is throwing away at least those 108 bars.

### E3 — what the run does not settle

The 687 comparators are the engine's and hold no pandas_ta port, so **every in-fork figure
of §F stays synthetic-only** — including the `natr:NATR_14` pair, which is the fork's
column and not the engine's `natr` of this table. The run's `natr` shares a NAME with it;
this session did not read the engine, so no claim is made that the two are the same
computation. What §F's gap paragraph said before the run still stands unexplained: the
synthetic frames read 0.0722 .. 0.3202 against the fork's `natr:NATR_14`, and the engine's
comparator reads 0.6104 here — roughly 0.29 apart.

The module's docstring is deliberately **not** edited. The ledger row's `module_sha1`
(`6e27a955`) is the sha1 of `sk_fcb_width.py` as the harness imported it, so a
one-character docstring edit would move the hash and make `tests/test_gate_e_ledger.py`
read the row as a measurement of code that no longer exists.

## F — non-redundancy against the fork's own volatility columns

⚠ **Synthetic, and a disclosure rather than a gate.** The 687 engine comparators hold no
pandas_ta port, so a Gate E run cannot see any of these.

Spearman against `SK_FCB_WIDTH_2`, per frame, ordered by **max \|ρ\|** — the metric the
screen, the issue and the other receipts use. ⚠ **Seven frames, not eight:** `flat` never
fires, so it has no Spearman at all.

| comparator | max \|ρ\| | walk | trend | range-bound | grid | heavy-tailed | jump | coarse |
|---|---|---|---|---|---|---|---|---|
| `natr:NATR_14` | **0.3202** | 0.2337 | 0.1144 | 0.3095 | 0.2617 | 0.3202 | 0.2979 | 0.0722 |
| `rvi:RVI_14` | **0.2858** | 0.1409 | -0.2858 | -0.1012 | 0.0601 | -0.0462 | -0.0886 | 0.1227 |
| `true_range`/close (invented) | 0.2422 | -0.0055 | -0.0377 | 0.0354 | 0.0167 | -0.0059 | 0.0119 | 0.2422 |
| donchian width/close (invented) | 0.2302 | 0.0005 | -0.0930 | 0.2160 | 0.1393 | 0.1833 | 0.2302 | 0.0484 |
| `chop:CHOP_14_1_100` | 0.2023 | 0.0213 | 0.1763 | -0.1706 | -0.0826 | -0.1556 | -0.2023 | 0.0898 |
| `massi:MASSI_9_25` | 0.1551 | 0.1370 | 0.0357 | -0.0022 | 0.1551 | 0.0509 | -0.0433 | -0.1195 |

⚠ The two metrics disagree, and the first draft of this section was sorted by the SIGNED
maximum — which ranks `rvi:RVI_14` **last of the six**, behind both invented proxies *and*
two shipped siblings, because its strongest reading is negative. Both orderings are now
**printed** by `section_F` rather than described:

| ordered by max \|ρ\| | | ordered by max signed ρ | |
|---|---|---|---|
| `natr:NATR_14` | 0.3202 | `natr:NATR_14` | 0.3202 |
| **`rvi:RVI_14`** | **0.2858** | `true_range`/close (invented) | 0.2422 |
| `true_range`/close (invented) | 0.2422 | donchian width/close (invented) | 0.2302 |
| donchian width/close (invented) | 0.2302 | `chop:CHOP_14_1_100` | 0.1763 |
| `chop:CHOP_14_1_100` | 0.2023 | `massi:MASSI_9_25` | 0.1551 |
| `massi:MASSI_9_25` | 0.1551 | **`rvi:RVI_14`** | **0.1409** |

Round 3 of the review caught the sort; round 4 caught the sentence that replaced it, which
had written "second-from-last by signed ρ" without running it. Hence the second printed
table.

### The real-data figure for this same pair, which the screen already measured

⚠ **These numbers understate the overlap badly, and the apples-to-apples comparison is
not §E's engine figure of 0.6104.** The 2026-10-24 screen ran a second, *fork* stage — scale-free
`Category` outputs at defaults, 12 real frames — and it put the prototype's nearest fork
comparator at **`natr:NATR_14` 0.5873**, per-frame max median **0.5772**, i.e. not a
restatement at the 0.90 line (`docs/issues/106-sk-fcb-width.md`, which is the owner's
copy of issue #107). That is the identical pair this table measures, and §A2's
bit-equality to the prototype is what carries it to this port.

| measurement | comparator | frames | value |
|---|---|---|---|
| this file, synthetic | `natr:NATR_14` | **7** synthetic (`flat` cannot contribute) | **0.0722 .. 0.3202** |
| screen stage 2, fork columns | `natr:NATR_14` | **12 real** | **0.5873** (per-frame max median 0.5772) |
| screen Gate E, engine comparators | `natr` | **89 real** | **0.6104** (top-5 per-frame max median 0.5846) |
| **§E, Gate E on THIS port** | `natr` | **89 real** | **0.6104** (top-5 per-frame max median 0.5846) |

The last row is this port's own run, `is107-sk_fcb_width-8f25baf3` of 2026-11-15, and it
reproduced the screen's digits exactly (§E). So the synthetic frames fall short of the
real fork figure by roughly **0.27**, and of the engine figure by roughly **0.29**. The same asymmetry hit `j_acosc`, whose invented
`fwma` proxy understated the engine's comparator by about 0.22.

**Why they fall short is not established here, and the obvious explanation was tested and
refuted.** The
guess — "on a continuous frame the band is re-drawn every few bars, so the close in the
divisor carries the column" — predicts a high correlation with `1/close`. Measured, the
column tracks its own **numerator**:

| frame | vs `1/close` | vs `upper - lower` (price units) | steps of `upper - lower` |
|---|---|---|---|
| walk | 0.0914 | **0.9179** | 420 |
| trend | -0.0330 | **0.5357** | 348 |
| range-bound | -0.0092 | **0.9973** | 458 |
| grid | 0.0930 | **0.9335** | 423 |
| heavy-tailed | -0.0068 | **0.9528** | 434 |
| jump | 0.1565 | **0.9719** | 385 |
| coarse | 0.4571 | **0.9488** | 24 |

So the gap is **not** the divisor drowning the band on synthetic frames. No mechanism is
offered in its place: Gate E's real frames are the measurement, and these figures are
recorded as a disclosure that synthetic in-fork overlap did not predict them.

---

## G — guards, and what each one buys

### G1 — the close guard

`close.where(np.isfinite(close) & (close >= np.finfo(float).tiny))`. Plant at bar 700 of
`walk`:

| close[700] | fired | bars emptied | other bars moved | unguarded, that bar reads |
|---|---|---|---|---|
| NaN | 1,490 | **1** | **0** | NaN |
| 0.0 | 1,490 | **1** | **0** | `inf` |
| -1.0 | 1,490 | **1** | **0** | **-1.503724** |
| +inf | 1,490 | **1** | **0** | **0.000000** |
| -inf | 1,490 | **1** | **0** | **-0.000000** |
| 1e-310 | 1,490 | **1** | **0** | `inf` |

One bar each, no other bar moved. The last column is what the guard buys: unguarded, a
zero or subnormal close reads `inf`, and a negative or infinite close reads a
**plausible-looking** number no consumer would question.

### G2 — a bad high or low is absorbed, with an unbounded-by-window reach

A comparison against a NaN is False, so the bar simply makes **no fractal**: nothing is
emptied and nothing is non-finite.

| leg | value | fired | emptied | moved | first moved | last moved | max \|rel\| |
|---|---|---|---|---|---|---|---|
| high | NaN / ±inf | 1,491 | **0** | 10 | 701 | 710 | 1.409e+00 |
| low | NaN / ±inf | 1,491 | **0** | 4 | 703 | 706 | 8.526e-01 |

All three values give **bit-identical** columns per leg, which is the guard working: an
infinity behaves exactly like a NaN. **No bar before the plant moves** — the causal half.

⚠ The disclosure: the reach is **not bounded by a window** the way a rolling mean's is.
`ffill` carries the older level until the *next* fractal replaces it, which happened to
be 10 bars (high) and 4 bars (low) here. A frame with sparser fractals would carry it
further — §C's `coarse` holds one leg for 428 bars. **10 and 4 are this plant on this
frame, not a bound.**

### G3 — what the high/low guard is actually for

The same plants with `h = high.where(np.isfinite(high))` removed:

| leg | value | fired | non-finite readings | first |
|---|---|---|---|---|
| high | +inf | 1,491 | **9** | 702 |
| high | -inf | 1,491 | 0 | — |
| high | NaN | 1,491 | 0 | — |
| low | -inf | 1,491 | **5** | 702 |
| low | +inf | 1,491 | 0 | — |
| low | NaN | 1,491 | 0 | — |

`+inf > x` is True, so an unguarded `+inf` high **becomes a fractal** and the band
carries `inf` until the next fractal replaces it — 9 infinite readings here, 5 for a
`-inf` low. ⚠ And the four plants it buys nothing for, stated rather than implied: an
infinity on the wrong side of the comparison is never an extreme, and a NaN already
declined. **The guard is for infinities only**, it changes nothing on a clean frame
(§A2's bit-equality with the guard-free prototype), and the 9 is bounded by the next
fractal rather than running to the end of the frame.

## H — the width goes negative, by construction

A 16-bar hand frame. Bars 0..4 make a fractal high at 10.5 and a fractal low at 9.5; the
price then steps to ~100 and **plateaus**, so no bar's high strictly beats both
neighbours and the rally gets no fractal high; the dip at bar 11 still makes a fractal
low at 99.0, far above the stale upper band.

| bar | high | low | close | upper | lower | width |
|---|---|---|---|---|---|---|
| 4 | 9.90 | 9.70 | 9.80 | 10.50 | — | — |
| 5 | 100.00 | 99.50 | 99.80 | 10.50 | 9.50 | 0.0100 |
| 11 | 99.50 | 99.00 | 99.20 | 10.50 | 9.50 | 0.0101 |
| 12 | 100.00 | 99.50 | 99.80 | 10.50 | 9.50 | 0.0100 |
| 13 | 100.00 | 99.50 | 99.80 | 10.50 | **99.00** | **-0.8868** |
| 15 | 100.00 | 99.50 | 99.80 | 10.50 | 99.00 | **-0.8868** |

11 fired, 3 negative, min **-0.8868**. The mechanism is §C2's tie: the plateau is what
denies the rally its fractal high.

## L — degenerate frames and the shortest accepted frame

| input | result |
|---|---|
| 4 bars (`MIN_BARS - 1`) | `None` |
| 5 bars (`MIN_BARS`), `walk` | 0 fired — one bar *could* carry a band; data-dependent |
| 10 bars, `walk` | 1 fired |
| 5 bars, outside bar at index 2 | **1 fired, first at bar 4 = `2 * SPAN`**, value 0.204082 |
| 60 bars all-NaN | 0 fired |
| 60 bars all 0.0 | 0 fired |
| 60 bars all -5.0 | 0 fired |
| 60 bars all 100.0 | 0 fired |
| high/low 1e+300, close 1e-300 | 51 fired, **51 infinite** |

No float error is reachable on any of them under `errstate(all="raise")`.

⚠ The last row is **not guarded** and is stated rather than hidden: a frame whose
high/low and close live hundreds of orders of magnitude apart overflows the division.
That is bad data rather than a price — the same walk at one scale fires finite at 1e-6,
1e+6 and 1e+100 (§D).

The outside-bar row is what makes "the earliest possible fire is bar `2 * SPAN`" a
measurement instead of an argument: one bar that is both the strict high and the strict
low of its window confirms both legs at once.

## M — the wiring counts, re-derived rather than incremented

`docs/IndicatorDictionary.md` is regenerated from a live probe
(`python docs/gen_indicator_dictionary.py`), and the counts below are read back out of it
and out of the live package — `tests/test_readme_counts.py` and
`tests/test_ml_companions.py` re-derive them independently.

| surface | before | after |
|---|---|---|
| registered in `Category` | 345 | **346** |
| callable as `df.ta.<name>()` | 353 | **354** |
| probed by the dictionary | 347 | **348** |
| `volatility` bucket | 36 | **37** |
| dictionary tagged columns | 690 | **691** |
| of which `SF` | 329 | **330** |

The row the generator wrote:

| indicator | inputs | params | outputs — ML form | warm-up | what it measures |
|---|---|---|---|---|---|
| `sk_fcb_width` | H/L/C | — | `SK_FCB_WIDTH_2` SF | 10 | The last confirmed fractal high minus the last confirmed fractal low, over close: how wide the Fractal Chaos Band stands. |

⚠ That warm-up **10** is the generator's one probe frame, not a constant — see §C.

Five wiring touch points, all five done: `pandas_ta/volatility/sk_fcb_width.py`,
`pandas_ta/volatility/__init__.py`, `Category["volatility"]` in `pandas_ta/__init__.py`,
the `df.ta.sk_fcb_width()` accessor in `pandas_ta/core.py`, and
`tests/test_sk_fcb_width.py`.

## W — the docstring against the dictionary's cut

`desc()` shows `d[:150].rsplit(' ', 1)[0]` of the first paragraph, dropping the trailing
word **whole**, and only when the paragraph exceeds 150 characters. The paragraph is
**121** characters with **29** to spare, measured by calling the generator's own `desc()`
and growing the sentence until it loses a word.

## Z — cost

⚠ Machine- and run-dependent. Best of 5, over two repeats so the spread is visible.

| bars | ms (best of 5, two runs) | ms (a second invocation) | peak MB |
|---|---|---|---|
| 100,000 | 14.1 .. 14.2 | 14.0 .. 14.1 | 6.6 |
| 400,000 | 52.3 .. 52.3 | 51.9 .. 52.0 | 26.4 |

Four rolling passes, four shifts, two `ffill`s and one division; no Python loop, so time
and memory are linear in bars. **The milliseconds are a disclosure and no digit of them
is claimed** — the second column is there because re-running the section moved them, which
is what "machine- and run-dependent" means. The peak-memory figures were identical on
both invocations, and 26.4 / 6.6 = 4.0 for 4x the bars.

## CPU — reduced numpy dispatch

`python docs/measure_sk_fcb_width_cpu.py` with
`NPY_DISABLE_CPU_FEATURES="AVX512F AVX512_SKX AVX2 FMA3"` (the four the launcher
re-runs port tests under; the run prints the dispatchable features still enabled and
refuses to continue if any of the four survived).

- `tests/test_sk_fcb_width.py`: **160 passed** under both dispatches in the porting
  session, and **161** under both in the receipt session of 2026-11-15 — the owed-row test
  became `test_the_gate_e_row_is_this_ports_own_measurement` and
  `test_the_gate_e_run_closes_gate_c_on_real_data` was added, so the count moved by one.
- §A3, §B2 and §C are **identical**, cell for cell: the same fired counts, first-fire
  bars, step counts, ages, Spearman figures to four decimals, exposed/caught/missed
  counts and band-held counts. A comparison is either taken or not, so a last-bit move in
  a price does not nudge this column — it either changes nothing or swaps a whole price
  level, and nothing swapped.
- §D: the only figures that moved are the inexact-rescale residuals, in their last
  digits (e.g. `walk` at x10, 2.132e-14 → 2.143e-14; `heavy-tailed` at x10,
  1.914e-14 → 1.147e-13). The maximum over all 28 pairs is **1.229e-12** under both,
  and the selection-flip count is **0** under both.
- That asymmetry is why the test module asserts bands, orderings and structural
  relations rather than fired counts or Spearman values: the quantities a reduced kernel
  could move are exactly the ones not pinned.

---

## Verdict

| gate | requirement | result |
|---|---|---|
| **A** Correctness | against the source formula | **pass** — bit-equal to an INDEPENDENT loop transcription of `Fractal` + `Fcb`, and to the screen prototype (the same rolling expression, so a tie to the Gate E figures rather than a second derivation), on all eight frames; the centre-index divergence named and measured (§A3), the `>=` and `EndType.Close` readings priced (§A4). ⚠ `Fcb.Series.cs` not read |
| **B** Causality | mutant test | **pass** — module caught 0 of 1,499 offsets on each of eight frames (0 of 299 asserted in the suite); five mutants each live and each caught on each of six frames, and the weakest carried by §B2's mechanism-aware sweep: 0 catches on 8,743 unexposed offsets and every one of the 30 exposed-but-missed offsets explained (17 / 9 / 4, 0 left over). ⚠ Not 36 of 36, and why, in §B |
| **C** Reachability | every column fires, counts stated | **pass** — 1,411 .. 1,493 of 1,500 on seven synthetic frames, 0 on `flat` with the reason, and **397,609 of 398,849** real BIST bars in §E2's run, of which **108** read exactly 0.0 |
| **D** Scale-free | x8/x64 bit-identical, `0 < fires < n` | **pass** — bit-identical on all 10,330 fired bars and at three price levels; inexact factors ≤ 1.229e-12 with masks matching and 0 selection flips |
| **E** Attribution | Spearman vs 687 comparators, 89 frames | **pass, SHIP** — run `is107-sk_fcb_width-8f25baf3` (2026-11-15), pooled **0.6104** vs `natr` at n = 397,416, top-five per-frame max median **0.5846** over 89 frames with **no single frame past 0.80** on any top-five comparator, 0 degenerate, no waiver (§E) |
| **F** Suites | both repos green | this module 161 passed in this receipt session, and 161 under reduced CPU dispatch; the full suite and the Backtesting suite are the launcher's, in clean worktrees |

**Shipped**, as one column, `SK_FCB_WIDTH_2`, on Gates A–E: Gate E came back **SHIP** on
this port's own run, at the prototype's figures to every digit, so nothing is reverted and
nothing is waived.
