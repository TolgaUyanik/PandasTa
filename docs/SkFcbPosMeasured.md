# SK-FCB-POS — position inside the Fractal Chaos Bands (span 2)

Receipt for PandasTa issue **#108**. Column `SK_FCB_POS_2`, module
`pandas_ta/momentum/sk_fcb_pos.py`, tests `tests/test_sk_fcb_pos.py`.

    upper[T]      = level of the last CONFIRMED fractal high, held forward
    lower[T]      = level of the last CONFIRMED fractal low, held forward
    SK_FCB_POS_2  = (close - lower) / (upper - lower)

Source: Skender Stock.Indicators (Apache-2.0), `Fcb`, as issue #108 names it —
*"Fcb.Series.cs: bands = last fractal high / low"*, span 2. The quotient is the
fork's, from the screen prototype's scale-free form
(`docs/issues/screen/ind_screen_r2.py`, candidate `sk_fcb_pos`).

**Every number below is printed by `python docs/measure_sk_fcb_pos.py`** (one
section per gate limb; `python docs/measure_sk_fcb_pos.py A1 D` for named
sections). Nothing here is derived by hand. Where a figure is this machine's
rather than the formula's, it says so.

---

## The one-paragraph verdict

The port **ships**, with Gate E owed. Gates A–D are clean and the column is
not a restatement of its sibling `sk_fcb_width` on this frame set (max
|ρ| 0.2096, §F) although both are built from the same two band legs.

**What a consumer must know before using it, and it is not the formula:**
the denominator `upper - lower` is **not positive and is not guarded to be**.
The two legs are the last fractal *high* and the last fractal *low*, read from
*different* bars, so the band can be crossed or collapsed. §C4 is the section
to read first. Second: the column is **not bounded to [0, 1]** — only
593 … 944 of each synthetic frame's fired bars land inside the band, and the
span over seven frames is **−182.0 … +187.0**, driven by a small denominator
rather than by an extreme close (§C4, and
`test_the_extreme_tail_comes_from_a_small_denominator`).

---

## What this port does NOT establish

Stated here rather than buried, because the repo's dominant defect is a claim
written before it was measured.

1. **`Fcb.Series.cs` was never read.** Stock.Indicators is not installed,
   `docs/pine/` is absent, and a repo-wide search for `Fcb.Series.cs` finds
   nothing — all three pinned by
   `test_the_source_library_is_not_readable_here`. Web access was also
   unavailable in the session that wrote this, and that fourth route is **not**
   pinned by anything: a test cannot see it. Gate A checks the formula the
   issue *names*, spelled two ways; the attribution is to the issue's naming.
2. **What Skender does with the fractal's index is not established.** This
   port reads a fractal `SPAN` bars after its centre; Skender's `Fractal`
   returns it *on* the centre. That divergence is measured (§A3) and the
   centre reading is the `centre-read` Gate B mutant — but which one
   `Fcb.Series.cs` uses is unknown here.
3. **Gate E is owed.** See §E. The screen's 0.8348 against `pgo` was measured
   on the **prototype** on 2026-10-24, not on this module.
4. **No real-data figure in this file.** Every count, range and ρ below is
   from eight synthetic frames of 1,500 bars. Per `CLAUDE.md`, 86,415 of
   408,253 real BIST daily bars (21.17%) close exactly at an extreme, so the
   real-data regime is the *tick-grid* end of §C2 and these continuous frames
   do not predict it.
5. **Why the synthetic ρ against `cci` (0.8860, §F) sits so close to the
   screen's real-data ρ against `cci` (0.8556) is not established.** It is a
   coincidence of two different measurements until something measures the
   link.

---

## Gate A — correctness

### §A1 The source formula by explicit loops

`_fractals` transcribes Skender's `Fractal` with
`leftSpan = rightSpan = SPAN` and `EndType.HighLow`:

```csharp
if (i >= leftSpan && i < length - rightSpan) {
    for (int p = i - leftSpan; p <= i + rightSpan; p++) {
        if (p == i) continue;
        if (evalHigh <= pHigh) isHigh = false;
        if (evalLow  >= pLow)  isLow  = false;
    }
    if (isHigh) fractalBear = evalHigh;
    if (isLow)  fractalBull = evalLow;
}
```

`_carry` is `Fcb`'s roll-forward (`upperLine = f.FractalBear ?? upperLine`).
Both are Python loops over numpy and share **no code** with the module, which
is four rolling windows, four shifts and two `ffill`s.

| frame | fired | NaN masks | max \|diff\| | bit-equal |
|---|---:|---|---:|---|
| walk | 1491 | True | 0.000e+00 | True |
| trend | 1479 | True | 0.000e+00 | True |
| range-bound | 1491 | True | 0.000e+00 | True |
| grid | 1477 | True | 0.000e+00 | True |
| heavy-tailed | 1493 | True | 0.000e+00 | True |
| jump | 1488 | True | 0.000e+00 | True |
| flat | 0 | True | — | True |
| coarse | 1326 | True | 0.000e+00 | True |

**10,245 fired bars over the eight frames**, bit-equal with identical NaN
masks. Nothing is a tolerance: the legs are *selected* price levels, so once
the selection agrees the arithmetic is two subtractions and one division on
the same doubles.

### §A2 The screen prototype, retyped

Bit-equal on all eight frames with identical NaN masks.

⚠ **Not a second derivation, and not offered as one.** The prototype's
`last_fractal` is the imported `_last_fractal` operation for operation and its
`sdiv` is the module's `replace`. What bit-equality buys is the **tie to the
screen's Gate E figure** — 0.8348 against `pgo` was measured on *this
expression* — plus the module's high/low mask priced at zero on a finite
frame.

### §A3 The divergence: Skender's index vs the confirmed index

Skender's `Fractal` returns a fractal **on** its centre bar. This port reads it
`SPAN` bars later, when the right-hand bars exist. Read at the centre, the band
would be knowable before its right-hand bars existed, and Gate B catches that
reading (it is the `centre-read` mutant).

| frame | both fire | differ | Spearman | max \|diff\| |
|---|---:|---:|---:|---:|
| walk | 1491 | 785 | 0.8294 | 10.4681 |
| trend | 1479 | 651 | 0.7765 | 34.0372 |
| range-bound | 1491 | 841 | 0.8346 | 73.9429 |
| grid | 1477 | 789 | 0.7825 | 186.9073 |
| heavy-tailed | 1493 | 815 | 0.7956 | 29.0056 |
| jump | 1488 | 724 | 0.8349 | 10.5657 |
| coarse | 1322 | 42 | 0.9845 | 4.1667 |

A real choice, not a rounding: **42 … 841 bars differ at ρ 0.7765 … 0.9845**.
The confirmed reading is the prototype's and the only one of the two that
survives Gate B.

### §A4 The strict predicate, and the EndType.Close reading

`>` and not `>=`: Skender's loop sets `isHigh = false` on `evalHigh <= pHigh`,
so a **tie on either side destroys the fractal**.

| frame | differ | Spearman | max \|diff\| |
|---|---:|---:|---:|
| walk | 0 | 1.0000 | 0.0000 |
| trend | 0 | 1.0000 | 0.0000 |
| range-bound | 0 | 1.0000 | 0.0000 |
| grid | 43 | 0.9957 | 7.4872 |
| heavy-tailed | 0 | 1.0000 | 0.0000 |
| jump | 0 | 1.0000 | 0.0000 |
| coarse | 1256 | 0.3417 | 6.0000 |

Identical on all five continuous frames, 43 bars on a 0.01-tick frame, and a
**different column** on a 2.0-tick frame (ρ 0.3417). That is FVGDEAD's lesson
spent in advance; see §C2 for the tie counts behind it.

`EndType.Close`, Skender's other option — judge and return the *close* instead
of the high and the low — differs on **906 … 1,493** bars at ρ 0.7581 … 0.9670
across the seven firing frames. The issue names the high/low form.

---

## Gate B — causality

### §B The blind sweep

Each boundary `j` splits a frame into one shared past and two **wholly
different** futures: one with every bar `>= j` scaled up by a per-bar random
factor in [1, 4], one scaled down by its reciprocal. A causal column is
bit-identical on the shared prefix.

⚠ Deliberately **not** "multiply the tail by 1.03": a fractal is a
*comparison*, so a look-ahead only shows when a decision within `SPAN` bars of
the boundary actually flips, and a weak detector returning 0 would be weak
evidence.

| frame | offsets | caught |
|---|---:|---:|
| walk | 1499 | 0 |
| trend | 1499 | 0 |
| range-bound | 1499 | 0 |
| grid | 1499 | 0 |
| heavy-tailed | 1499 | 0 |
| jump | 1499 | 0 |
| flat | 1499 | 0 |
| coarse | 1499 | 0 |

**0 of 1,499 offsets on each of the eight frames** — every boundary but bar 0.
`tests/test_sk_fcb_pos.py` asserts the same at 36 offsets per frame and over
all 295 offsets of a 300-bar walk.

### §B1 Six look-ahead mutants, read off the shipped source

Prefix truncation cannot see back-dating, so each mutant is an edit to a
**shipped** file, read off disk, `exec`'d in memory and swept by the same
detector. `live` is the number of the eight frames on which the mutant's output
differs from the module's at all — an edit that failed to take would sweep
clean and look like evidence.

⚠ **Three of the six edit `pandas_ta/volatility/sk_fcb_width.py`, which this
module imports `_last_fractal` from.** That is the point rather than a
convenience: this module's causality is not decidable from this module's file
alone, so Gate B has to reach into the file it imports from. The mutated helper
replaces the name in a fresh copy of this module's globals, which works because
`sk_fcb_pos` looks `_last_fractal` up on every call.

| mutant | in | live | walk | trend | range-bound | grid | heavy-tailed | jump | flat | coarse |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| centre-read | band | 7 | 33 | 34 | 33 | 35 | 33 | 33 | 0 | 0 |
| right-window-lead | band | 7 | 6 | 6 | 9 | 6 | 8 | 4 | 0 | 0 |
| band-bfill | band | 7 | 36 | 35 | 35 | 35 | 35 | 35 | 28 | 32 |
| upper-lead | pos | 7 | 6 | 6 | 7 | 4 | 6 | 8 | 0 | 0 |
| output-early | pos | 7 | 36 | 36 | 36 | 36 | 36 | 36 | 0 | 36 |
| numerator-lead | pos | 7 | 36 | 36 | 36 | 36 | 36 | 36 | 0 | 36 |

36 offsets per frame (1464 … 1499).

⚠ **A 36-of-36 headline is not available for this indicator and is not
claimed.** Two of the six look ahead through something discrete —
`right-window-lead` through a strict comparison, `upper-lead` through a step
function shifted by one bar — and are caught on as few as **4 of 36**. `flat`
has no fractals at all and catches 1 of the 6; `coarse` catches 3 of the 6.
§B2 takes the two weak ones apart instead of asserting them away.

### §B2 The two weak mutants, swept densely

Each weak mutant gets a **necessary condition** for being catchable, *computed*
from the two futures rather than argued. `outside` must be 0, or the condition
is wrong and the section proves nothing.

* `right-window-lead`: `exposed(j)` = the **mutated** band differs on some bar
  `< j`. If the mutated band is identical on the whole prefix, nothing
  downstream of it can differ there.
* `upper-lead`: `exposed(j)` = `upper[j]` differs between the two futures. The
  edit makes bar `t` read `upper[t + 1]`; for `t + 1 <= j - 1` that is still a
  prefix bar and identical in both futures, so bar `j - 1` is the only prefix
  bar the shift can reach.

**right-window-lead**

| frame | offsets | exposed | caught | in exposed | outside | missed |
|---|---:|---:|---:|---:|---:|---:|
| walk | 1495 | 270 | 270 | 270 | 0 | 0 |
| trend | 1495 | 249 | 249 | 249 | 0 | 0 |
| range-bound | 1495 | 314 | 314 | 314 | 0 | 0 |
| grid | 1495 | 293 | 293 | 293 | 0 | 0 |
| heavy-tailed | 1495 | 281 | 280 | 280 | 0 | 1 |
| jump | 1495 | 262 | 262 | 262 | 0 | 0 |
| coarse | 1495 | 27 | 17 | 17 | 0 | 10 |

10,465 offsets, 1,696 exposed, **1,685 caught, 0 caught outside the
condition**, 8,769 unexposed, 11 exposed-but-missed.

**upper-lead**

| frame | offsets | exposed | caught | in exposed | outside | missed |
|---|---:|---:|---:|---:|---:|---:|
| walk | 1495 | 262 | 262 | 262 | 0 | 0 |
| trend | 1495 | 294 | 293 | 293 | 0 | 1 |
| range-bound | 1495 | 280 | 280 | 280 | 0 | 0 |
| grid | 1495 | 273 | 273 | 273 | 0 | 0 |
| heavy-tailed | 1495 | 279 | 278 | 278 | 0 | 1 |
| jump | 1495 | 268 | 268 | 268 | 0 | 0 |
| coarse | 1495 | 20 | 10 | 10 | 0 | 10 |

10,465 offsets, 1,676 exposed, **1,664 caught, 0 caught outside the
condition**, 8,789 unexposed, 12 exposed-but-missed.

**Every one of the 23 misses is classified, with none left over:**

| mutant | frame | missed | all-NaN | value-tie |
|---|---|---:|---:|---:|
| right-window-lead | heavy-tailed | 1 | 1 | 0 |
| right-window-lead | coarse | 10 | 3 | 7 |
| upper-lead | trend | 1 | 1 | 0 |
| upper-lead | heavy-tailed | 1 | 1 | 0 |
| upper-lead | coarse | 10 | 4 | 6 |

`all-NaN` = every bar the band moved on reads NaN in **both** columns, so the
move cannot reach the output. `value-tie` = it reads a number and the two
quotients coincide anyway; 13 of the 13 ties are on a frame where the column
takes only 27 distinct values (§C), which is where a tie is cheap. Totals:
10 all-NaN + 13 value-tie = 23.

---

## Gate C — reachability

### §C Fired bars, and the warm-up

| frame | bars | fired | first | distinct | min | max |
|---|---:|---:|---:|---:|---:|---:|
| walk | 1500 | 1491 | 9 | 1491 | −9.4931 | 7.4538 |
| trend | 1500 | 1479 | 21 | 1479 | −28.4678 | 34.9752 |
| range-bound | 1500 | 1491 | 9 | 1491 | −72.9536 | 19.0593 |
| grid | 1500 | 1477 | 23 | 1464 | −182.0000 | 187.0000 |
| heavy-tailed | 1500 | 1493 | 7 | 1493 | −11.4082 | 29.9193 |
| jump | 1500 | 1488 | 12 | 1488 | −8.5652 | 11.5649 |
| flat | 1500 | 0 | — | 0 | — | — |
| coarse | 1500 | 1326 | 89 | 27 | −6.0000 | 3.0000 |

**Gate D's `0 < fires < n` guard** is read off the same rows: it holds on all
seven firing frames. `flat` fires 0, which is a reading about a constant price
rather than a defect (§C3).

⚠ **The warm-up is data-dependent and there is no constant to quote.** First
fire lands on bar **7 … 89** across the seven firing frames and never on
`flat`. The earliest *possible* fire is bar `2 * SPAN = 4` and it needs one bar
to be both the strict high and the strict low of its window — an outside bar.
Reachable, and pinned by a hand frame:

| bar | high | low | close | SK_FCB_POS |
|---:|---:|---:|---:|---:|
| 0 | 10.00 | 9.00 | 9.50 | NaN |
| 1 | 10.00 | 9.00 | 9.50 | NaN |
| 2 | 12.00 | 7.00 | 9.50 | NaN |
| 3 | 10.00 | 9.00 | 9.50 | NaN |
| 4 | 10.00 | 9.00 | 11.00 | 0.8000 |
| 5 | 10.00 | 9.00 | 7.50 | 0.1000 |
| 6 | 10.00 | 9.00 | 9.50 | 0.5000 |

`MIN_BARS = 2 * SPAN + 1 = 5` is a floor on the **input** only, not the
warm-up.

### §C2 The strict predicate against a tick grid

| tick | upper fractals | lower fractals | ready | fired | den=0 | den<0 | distinct |
|---|---:|---:|---:|---:|---:|---:|---:|
| none | 216 | 205 | 1491 | 1491 | 0 | 20 | 1491 |
| 0.01 | 212 | 199 | 1491 | 1491 | 0 | 33 | 1469 |
| 0.5 | 71 | 82 | 1476 | 1455 | 21 | 100 | 121 |
| 2.0 | 15 | 12 | 1411 | 1326 | 85 | 20 | 27 |

Rounding **starves** the band — 216 upper fractals unrounded against 15 at a
2.0 tick — and a starved band is this column's zero-denominator regime: 0
collapsed bars at ticks none and 0.01, **21 at 0.5 and 85 at 2.0**.

Ties counted directly — bars whose high equals the high of a bar within `SPAN`
of it, which is where a fractal can be lost:

| frame | high ties | low ties |
|---|---:|---:|
| walk | 0 | 0 |
| grid | 22 | 16 |
| coarse | 1448 | 1450 |

⚠ Per `CLAUDE.md` (FVGDEAD), 86,415 of 408,253 real BIST daily bars (21.17%)
close exactly at an extreme, so the real-data regime is the right-hand end of
this table and the continuous frames predict nothing about it.

### §C3 What the rest of the momentum bucket does on a flat price

§C says this column fires 0 of 1,500 bars on `flat`. Whether that is unusual is
a claim about 85 other indicators, so it was **run**: every name in
`Category["momentum"]` on a flat OHLCV frame of 600 bars, through its `df.ta`
accessor at defaults, column by column.

**139 columns probed; 0 indicators raised or returned `None`.**

| bucket | columns |
|---|---:|
| all NaN | 41 |
| all 0.0 | 78 |
| other | 20 |

`sk_fcb_pos:SK_FCB_POS_2` is one of the 41, in the company of
`willr:WILLR_14`, `rsi:RSI_14`, `cci:CCI_14_0.015`, `cmo:CMO_14`,
`stochrsi:STOCHRSIk_14_14_3_3`, `tsi:TSI_13_25`, `uo:UO_7_14_28` and
`imi:IMI_14`, among others. All-NaN on a constant price is the normal reading
for a position or oscillator column in this bucket, not a divergence.
`tests/test_sk_fcb_pos.py::test_a_flat_price_never_fires_and_that_is_a_reading`
re-runs four of the 41 so the company is asserted and not only cited.

### §C4 THE DENOMINATOR — the section to read first

`upper - lower` is **not positive and is not guarded to be**. Three regimes
ship:

* **`den > 0`** — the column means what its name says.
* **`den == 0`** — the quotient is `±inf` and the `replace` **empties the
  bar**. The column *loses* bars the sibling width keeps, where the width
  reads exactly 0.0.
* **`den < 0`** — the bar is **kept with the scale inverted**: a close above
  both legs reads below 0 instead of above 1.

`ready` is the bars where both legs and the close exist, i.e. the bars the
column could fire on.

| frame | ready | fired | den>0 | den=0 | den<0 | lost |
|---|---:|---:|---:|---:|---:|---:|
| walk | 1491 | 1491 | 1471 | 0 | 20 | 0 |
| trend | 1479 | 1479 | 1388 | 0 | 91 | 0 |
| range-bound | 1491 | 1491 | 1486 | 0 | 5 | 0 |
| grid | 1477 | 1477 | 1444 | 0 | 33 | 0 |
| heavy-tailed | 1493 | 1493 | 1472 | 0 | 21 | 0 |
| jump | 1488 | 1488 | 1468 | 0 | 20 | 0 |
| flat | 0 | 0 | 0 | 0 | 0 | 0 |
| coarse | 1411 | 1326 | 1306 | 85 | 20 | 85 |

The band is **crossed on 5 … 91 bars of every firing frame** and the `lost`
column is **exactly** the `den=0` column on every row — asserted as that
identity in
`test_a_collapsed_band_is_the_whole_gap_on_a_coarse_grid`, not as 85.

Where the values land:

| frame | <0 | [0,1] | >1 | min | max | min (den<0) | max (den<0) |
|---|---:|---:|---:|---:|---:|---:|---:|
| walk | 400 | 788 | 303 | −9.4931 | 7.4538 | −9.4931 | 3.6708 |
| trend | 142 | 593 | 744 | −28.4678 | 34.9752 | −28.4678 | 0.1623 |
| range-bound | 314 | 863 | 314 | −72.9536 | 19.0593 | −72.9536 | 1.5221 |
| grid | 335 | 787 | 355 | −182.0000 | 187.0000 | −182.0000 | 187.0000 |
| heavy-tailed | 359 | 795 | 339 | −11.4082 | 29.9193 | −8.2038 | 7.5745 |
| jump | 358 | 803 | 327 | −8.5652 | 11.5649 | −6.6965 | 6.8931 |
| coarse | 345 | 944 | 37 | −6.0000 | 3.0000 | 0.5000 | 1.5000 |

**Not bounded to [0, 1], and not nearly:** 593 … 944 inside, 142 … 400 below
0, 37 … 744 above 1. The extreme tail comes from a **small denominator** — on
`grid` the ten most extreme bars have a median |den| under a fifth of the
rest's, asserted in `test_the_extreme_tail_comes_from_a_small_denominator`,
and the −182 / +187 pair is a 0.01-tick frame where the two legs sat a tick or
two apart.

**The reading not taken, priced.** Masking the inverted band instead of keeping
it:

| frame | differ | Spearman | max \|diff\| |
|---|---:|---:|---:|
| walk | 20 | 1.0000 | 0.0000 |
| trend | 91 | 1.0000 | 0.0000 |
| range-bound | 5 | 1.0000 | 0.0000 |
| grid | 33 | 1.0000 | 0.0000 |
| heavy-tailed | 21 | 1.0000 | 0.0000 |
| jump | 20 | 1.0000 | 0.0000 |
| coarse | 20 | 1.0000 | 0.0000 |

The two readings are **identical on every bar both fire** — the `differ` column
is exactly the `den<0` count, i.e. bars the masked version drops. So the cost
of the choice is a *count*, not a shape. Keeping them is the screen prototype's
reading, and the prototype is what Gate E's 0.8348 was measured on, so keeping
them is the tie to that figure.

How long an inversion lasts:

| frame | den<0 runs | longest run |
|---|---:|---:|
| walk | 5 | 5 |
| trend | 17 | 19 |
| range-bound | 2 | 3 |
| grid | 10 | 8 |
| heavy-tailed | 10 | 5 |
| jump | 6 | 6 |
| coarse | 1 | 20 |

---

## Gate D — scale

### §D Exact factors

A comparison is rescale-invariant, so the fractal **selection** does not move,
and an exact binary factor then cancels between numerator and denominator:
`(c*f − lo*f) / (up*f − lo*f)` rounds to the same double as
`(c − lo) / (up − lo)`.

x8 and x64 are **bit-identical on all 10,245 fired bars of all eight frames**.
Repeated at price levels 1e−6, 1e+6 and 1e+100: bit-identical there too, 1,491
fired bars at each level.

⚠ Unlike the sibling width, the factor cancels between numerator *and*
denominator here, which is also why this column needs no `/ close`.

### §D2 Inexact factors

| frame | worst max \|rel\| over the four factors |
|---|---:|
| walk | 7.390e-12 |
| trend | 4.170e-13 |
| range-bound | 7.428e-12 |
| grid | 1.426e-12 |
| heavy-tailed | 6.637e-12 |
| jump | 9.633e-11 |
| coarse | 8.882e-15 |

Over the 28 frame/factor pairs (x10, x3.7, x0.1, x1.0000001 × seven firing
frames): NaN masks matched on all 28, **worst relative difference 9.633e-11**,
and **0 bars where an inexact rescale moved the fractal SELECTION** — the
failure mode peculiar to a comparison-selected band, where a rescale that
collapsed two distinct neighbouring prices onto one double would move a leg by
a whole price level. Measured, not proved impossible.

⚠ The test asserts **1e-7**, three orders looser than the measurement, on
purpose: a small denominator amplifies a last-bit move, and the frames
themselves shift in their last bits on a different CPU.

### §D3 More than scale-free: a level shift cancels too

`(c + s) − (lo + s)` over `(up + s) − (lo + s)` is the same quotient, and a
shift changes no comparison, so the column is invariant under any **increasing
affine map of price** — which the sibling's `/ close` is not.

| shift | masks | differ | Spearman | max \|rel\| |
|---|---|---:|---:|---:|
| +1 | True | 12 | 1.0000 | 4.260e-14 |
| +50 | True | 1071 | 1.0000 | 9.854e-12 |
| +1e6 | True | 1491 | 1.0000 | 1.307e-07 |

⚠ **Not bit-identical**, and that is stated rather than hidden: adding a
constant re-rounds every price, so the quotient moves in its last bits. The
`differ` column counts bars that moved *at all*, which is why it grows with
the shift while the relative size stays tiny.

---

## Gate E — attribution

**Gate E: pending, run by issue-solver after this session.**

The launcher runs
`gate_e_overlap.py run --module pandas_ta.momentum.sk_fcb_pos` in the
Backtesting worktree; a later receipt session records the row in
`docs/gate_e_ledger.csv` and writes the measured numbers into this section.
Until then:

* `tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
  reports `sk_fcb_pos` among the indicators owing a measurement — a skip under
  `GATE_E_PENDING_OK=1` on the way to `dev`, a failure locally and toward
  `main`.
* `tests/test_sk_fcb_pos.py::test_the_gate_e_row_is_owed` asserts the row is
  **absent**, so it fails the moment the receipt session records it. That is
  the cue, deliberately placed.

**What the screen measured, on the PROTOTYPE, on 2026-10-24 — not on this
module.** Run `screen_r2_20261024`,
`gate_e_overlap.py run --module ind_screen_r2 --fn screen`, Backtesting `main`
b2d94243, 89 ALTPORT-1 frames, 398,849 bars, 329 + 358 = 687 comparators,
canary bit-equal:

| comparator | pooled \|ρ\| | n |
|---|---:|---:|
| `pgo` | **0.8348** | 397,262 |
| `willr` | 0.8303 | — |
| `kdj_J_9_3` | 0.8256 | — |

Top-5 per-frame max median **0.8405** → **DISCLOSE_GAP** (0.80 ≤ ρ < 0.90 in
`r3-perframe-0.90`). The screen's stage-2 fork overlap (scale-free `Category`
outputs at defaults, 12 frames) put it at 0.8556 against `cci:CCI_14_0.015`,
per-frame max median 0.8567 — not a restatement at the 0.90 line.

§A2 asserts this module bit-equal to the retyped prototype on all eight
synthetic frames, so the port's own run is **expected** to agree. "Expected" is
not "measured", and nothing in this file is written as if it were.

---

## §F Non-redundancy — a disclosure, not a gate

⚠ **Synthetic.** Gate E measures 687 engine comparators over 89 real BIST
frames and none of them is a `pandas_ta` port. What follows is this session's
own frames and is not a substitute for §E.

Spearman ρ of `SK_FCB_POS_2` against each comparator, per frame:

| comparator | walk | trend | range-bound | grid | heavy-tailed | jump | coarse |
|---|---:|---:|---:|---:|---:|---:|---:|
| close | −0.0112 | −0.0014 | 0.5049 | 0.1309 | 0.1762 | 0.0989 | 0.2955 |
| willr_14 | 0.8293 | 0.6141 | 0.8531 | 0.8018 | 0.8193 | 0.8306 | 0.3958 |
| pgo_14 | 0.8367 | 0.6807 | 0.8644 | 0.8020 | 0.8116 | 0.8433 | 0.4068 |
| cci_14 | 0.8623 | 0.6343 | 0.8860 | 0.8300 | 0.8527 | 0.8623 | 0.4075 |
| stochk_14_3_3 | 0.7437 | 0.6258 | 0.7103 | 0.7265 | 0.7136 | 0.7479 | 0.3703 |
| sk_fcb_width_2 | 0.1140 | −0.2096 | −0.1053 | 0.0583 | −0.0123 | −0.0386 | 0.0834 |
| numerator | 0.8480 | 0.3669 | 0.8680 | 0.8211 | 0.8244 | 0.8476 | 0.8919 |
| denominator | 0.0931 | 0.0108 | −0.0711 | 0.0953 | 0.0234 | −0.0358 | 0.1241 |

Ranked by the largest |ρ| any frame gives:

| comparator | max \|ρ\| | median ρ |
|---|---:|---:|
| numerator | 0.8919 | 0.8476 |
| cci_14 | 0.8860 | 0.8527 |
| pgo_14 | 0.8644 | 0.8116 |
| willr_14 | 0.8531 | 0.8193 |
| stochk_14_3_3 | 0.7479 | 0.7136 |
| close | 0.5049 | 0.1309 |
| sk_fcb_width_2 | 0.2096 | −0.0123 |
| denominator | 0.1241 | 0.0234 |

Three rows matter, and one of them refutes the obvious story.

* ⚠ **`numerator` — `close - lower` alone, in price units — is the top row.**
  Most of what this column *ranks* is already in the numerator; the
  denominator contributes the scale-freedom rather than the ranking. That is
  consistent with the screen finding `pgo`, `willr` and `kdj_J` — all
  close-position measures — as the nearest real-data comparators.
* ⚠ **`close` itself is NOT the story, and the guess that it would be is
  refuted here: −0.0112 … 0.5049.** Between two confirmations the column is
  affine in close, but the legs step and the slope's *sign* flips with the
  denominator, so the pooled rank correlation is low. §L has the
  within-stretch figure, which is exactly ±1.
* ⚠ **`sk_fcb_width_2`, built from the SAME two legs, reads at most
  |0.2096|.** The two ports are not restatements of each other on this frame
  set.

---

## §G Guards, each priced

### §G1 A bad close — and a DIVERGENCE from the sibling

Close is in the **numerator** here, not the divisor, so it needs no mask of its
own for the non-finite cases: the quotient goes NaN or infinite and the
prototype's `±inf → NaN` fold empties the bar. `other` counts bars **other**
than the plant whose value moved (plant at bar 700 of `walk`):

| plant | fired | plant bar | other |
|---|---:|---:|---:|
| NaN | 1490 | NaN | 0 |
| +inf | 1490 | NaN | 0 |
| −inf | 1490 | NaN | 0 |
| 0.0 | 1491 | **−29.1085** | 0 |
| −1.0 | 1491 | **−29.7735** | 0 |
| 1e−310 | 1491 | **−29.1085** | 0 |
| 1e+300 | 1491 | **6.65015e+299** | 0 |

⚠ **A zero, negative or subnormal close is NOT emptied**, where the sibling
masks it out. That is arithmetically what "position relative to a band" means
for such a close and it is not a defect — but a consumer that feeds a bad tick
through as a price gets a **number** rather than a gap. Asserted in
`test_a_zero_or_negative_close_is_not_emptied`.

What the `±inf → NaN` fold buys, with the edit read off the shipped source:
**one bar**. Without it, an infinite close leaves `inf` in the column; the
`1e+300` row is unchanged either way, so the fold is **not** a magnitude guard
and is not claimed as one.

| plant | plant bar (unfolded) | non-finite bars |
|---|---:|---:|
| NaN | NaN | 0 |
| +inf | inf | 1 |
| 0.0 | −29.1085 | 0 |
| 1e+300 | 6.65015e+299 | 0 |

### §G2 A bad high or low is absorbed

A comparison against NaN is False, so the bar makes no fractal and no reading
goes missing. The cost is that the reach **forward** is not bounded by a
window: `ffill` carries the older leg until the next fractal replaces it.

| leg | plant | fired | later moved | earlier moved |
|---|---|---:|---:|---:|
| high | NaN | 1491 | 10 | **0** |
| high | +inf | 1491 | 10 | **0** |
| high | −inf | 1491 | 10 | **0** |
| low | NaN | 1491 | 4 | **0** |
| low | +inf | 1491 | 4 | **0** |
| low | −inf | 1491 | 4 | **0** |

10 bars for a bad high at bar 700 and 4 for a bad low, with **0 earlier bars
moved** — the causality-relevant half. A frame with sparser fractals would
carry it further; `coarse` holds one leg for up to 429 bars (§L).

### §G3 What the high/low mask buys — and a QUIETER failure than the sibling's

`+inf > x` is True, so an unguarded `+inf` high **becomes** a fractal.

| leg | plant | guarded fired | unguarded fired | differ | first moved | NaN ≡ ±inf |
|---|---|---:|---:|---:|---|---|
| high | +inf | 1491 | 1491 | 9 | bar 702: 2.11671 → **0** | True |
| high | −inf | 1491 | 1491 | 0 | — | True |
| low | +inf | 1491 | 1491 | 0 | — | True |
| low | −inf | 1491 | 1486 | 5 | bar 702: 1.04192 → NaN | True |

⚠ **The unguarded failure here is quieter than the sibling's.** There an `inf`
leg makes the width read `inf`, which any check catches. Here the `inf` lands
in the **denominator**, so the quotient reads a plausible **0.0**. With the
mask, a NaN and an infinite price give **bit-identical** columns, which is what
`test_the_high_low_mask_is_what_keeps_an_infinity_out` asserts. Four of the six
plants cost nothing even unguarded.

### §G4 Degenerate frames

| frame | fired | name |
|---|---:|---|
| all NaN (40 bars) | 0 | SK_FCB_POS_2 |
| all zero (40 bars) | 0 | SK_FCB_POS_2 |
| all +inf (40 bars) | 0 | SK_FCB_POS_2 |

Nothing raises. A frame of `MIN_BARS - 1 = 4` bars returns `None`, which is
`verify_series`' refusal.

### §G5 What this column does NOT inherit

High/low at 1e+300 with close at 1e−300 leaves the **sibling width infinite on
every fired bar**. Here the factor cancels and the column stays finite: **52
fired bars, 0 non-finite, −90.2228 … −50.3638**. Asserted in
`test_the_cross_scale_overflow_the_sibling_has_does_not_happen_here`.

---

## §H Hand frames

### An inverted band, bar by bar

A high fractal confirms at 13.00 on bar 4; the price gaps up and a **low**
fractal confirms at 18.00 on bar 9, *above* it. From bar 9 the denominator is
−5.00 and the column walks **down** while the close walks up.

| bar | high | low | close | upper | lower | den | SK_FCB_POS |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 10.00 | 9.00 | 9.50 | NaN | NaN | NaN | NaN |
| 1 | 10.50 | 9.50 | 10.00 | NaN | NaN | NaN | NaN |
| 2 | 13.00 | 9.40 | 11.00 | NaN | NaN | NaN | NaN |
| 3 | 10.40 | 9.30 | 10.00 | NaN | NaN | NaN | NaN |
| 4 | 10.30 | 9.20 | 9.80 | 13.00 | NaN | NaN | NaN |
| 5 | 20.00 | 19.00 | 19.50 | 13.00 | NaN | NaN | NaN |
| 6 | 20.50 | 19.50 | 20.00 | 13.00 | 9.20 | 3.80 | 2.8421 |
| 7 | 21.00 | 18.00 | 19.00 | 13.00 | 9.20 | 3.80 | 2.5789 |
| 8 | 21.50 | 19.60 | 20.50 | 13.00 | 9.20 | 3.80 | 2.9737 |
| 9 | 22.00 | 19.70 | 21.00 | 13.00 | 18.00 | **−5.00** | **−0.6000** |
| 10 | 22.50 | 19.80 | 21.50 | 13.00 | 18.00 | −5.00 | −0.7000 |
| 11 | 23.00 | 19.90 | 22.00 | 13.00 | 18.00 | −5.00 | −0.8000 |
| 12 | 23.50 | 20.00 | 22.50 | 13.00 | 18.00 | −5.00 | −0.9000 |
| 13 | 24.00 | 20.10 | 23.00 | 13.00 | 18.00 | −5.00 | −1.0000 |
| 14 | 24.50 | 20.20 | 23.50 | 13.00 | 18.00 | −5.00 | −1.1000 |
| 15 | 25.00 | 20.30 | 24.00 | 13.00 | 18.00 | −5.00 | −1.2000 |

### A collapsed band, and the sharpest difference from the sibling

The low fractal confirms at **exactly** the high fractal's level, so `den == 0`
from bar 11, the quotient is `±inf` and the bar is **emptied** — while
`sk_fcb_width` reads exactly **0.0** on the same bars.

| bar | high | low | close | upper | lower | den | SK_FCB_POS | width |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 10.00 | 9.00 | 9.50 | NaN | NaN | NaN | NaN | NaN |
| 1 | 10.00 | 9.00 | 9.50 | NaN | NaN | NaN | NaN | NaN |
| 2 | 12.00 | 9.00 | 10.50 | NaN | NaN | NaN | NaN | NaN |
| 3 | 10.00 | 8.00 | 9.00 | NaN | NaN | NaN | NaN | NaN |
| 4 | 10.00 | 9.00 | 9.50 | 12.00 | NaN | NaN | NaN | NaN |
| 5 | 10.00 | 9.00 | 9.50 | 12.00 | 8.00 | 4.00 | 0.3750 | 0.4211 |
| 6 | 10.00 | 9.00 | 9.50 | 12.00 | 8.00 | 4.00 | 0.3750 | 0.4211 |
| 7 | 14.00 | 13.00 | 13.50 | 12.00 | 8.00 | 4.00 | 1.3750 | 0.2963 |
| 8 | 14.00 | 13.00 | 13.50 | 12.00 | 8.00 | 4.00 | 1.3750 | 0.2963 |
| 9 | 13.00 | 12.00 | 12.50 | 12.00 | 8.00 | 4.00 | 1.1250 | 0.3200 |
| 10 | 14.00 | 13.00 | 13.50 | 12.00 | 8.00 | 4.00 | 1.3750 | 0.2963 |
| 11 | 14.00 | 13.00 | 13.50 | 12.00 | **12.00** | **0.00** | **NaN** | **0.0000** |
| 12 | 10.00 | 9.00 | 9.50 | 12.00 | 12.00 | 0.00 | NaN | 0.0000 |
| 13 | 10.00 | 9.00 | 9.50 | 12.00 | 12.00 | 0.00 | NaN | 0.0000 |
| 14 | 10.00 | 9.00 | 9.50 | 12.00 | 12.00 | 0.00 | NaN | 0.0000 |
| 15 | 10.00 | 9.00 | 9.50 | 12.00 | 12.00 | 0.00 | NaN | 0.0000 |

Bars 7 and 8 also show the column leaving [0, 1] upwards (1.3750) on an
ordinary, well-ordered band.

---

## §L A step function's quotient

Both legs change only when a fractal confirms:

| frame | upper steps | lower steps | longest upper held | longest lower held |
|---|---:|---:|---:|---:|
| walk | 216 | 205 | 20 | 19 |
| trend | 172 | 178 | 30 | 32 |
| range-bound | 229 | 230 | 19 | 19 |
| grid | 213 | 211 | 27 | 30 |
| heavy-tailed | 215 | 220 | 19 | 21 |
| jump | 191 | 195 | 20 | 26 |
| flat | 0 | 0 | 0 | 0 |
| coarse | 15 | 12 | **428** | **429** |

So between confirmations the column moves **only** because `close` does, and it
moves affinely, with the slope's **sign** set by the denominator. On the
longest constant-leg stretch of each frame:

| frame | stretch | bars | ρ vs close |
|---|---|---:|---:|
| walk | den>0 | 13 | **+1.0000** |
| walk | den<0 | 5 | **−1.0000** |
| trend | den>0 | 22 | +1.0000 |
| trend | den<0 | 15 | −1.0000 |
| range-bound | den>0 | 15 | +1.0000 |
| range-bound | den<0 | 3 | −1.0000 |
| grid | den>0 | 17 | +1.0000 |
| grid | den<0 | 8 | −1.0000 |
| heavy-tailed | den>0 | 13 | +1.0000 |
| heavy-tailed | den<0 | 5 | −1.0000 |
| jump | den>0 | 16 | +1.0000 |
| jump | den<0 | 6 | −1.0000 |
| coarse | den>0 | 222 | +1.0000 |
| coarse | den<0 | 20 | −1.0000 |

⚠ The `bars` column here is **not** §C4's "longest run": this one is the
longest stretch of *constant legs* inside the sign's bars, and a run of
consecutive `den < 0` bars can contain a leg change. They differ on `trend`
(§C4 19, here 15) and agree on `grid`, `jump` and `coarse`. Both are printed
by their own sections rather than reconciled into one number.

⚠ Pooled over a whole frame the column is **not** a close proxy (§F,
−0.0112 … 0.5049). The ±1 above is a within-stretch figure and is asserted as
such in
`test_the_band_is_a_step_function_and_the_column_is_affine_in_close`.

---

## §W Wiring — the five touch points

| # | file | state |
|---|---|---|
| 1 | `pandas_ta/momentum/sk_fcb_pos.py` | added |
| 2 | `pandas_ta/momentum/__init__.py` | `from .sk_fcb_pos import sk_fcb_pos` |
| 3 | `pandas_ta/__init__.py` → `Category["momentum"]` | added; momentum now holds **86** |
| 4 | `pandas_ta/core.py` → `df.ta.sk_fcb_pos()` | added |
| 5 | `tests/test_sk_fcb_pos.py` | 218 tests |

Column name `SK_FCB_POS_2`, category tag `momentum`, accessor output
bit-equal to the direct call. `offset=2` shifts by exactly 2 bars;
`fillna=-9.0` fills the 9 NaN bars of a 400-bar walk.

⚠ **Why `momentum` and not `volatility`.** The sibling width went to
volatility; this is a *position* in a range, which is what `willr`, `stoch`,
`cci` and `pgo` are, and those are exactly the comparators the screen found
nearest (§E). ASSUMPTION, taken as the conservative reading rather than asked:
the category is the porting session's call, the issue does not name one, and
`AskUserQuestion` was unavailable.

**The dictionary cut.** `docs/gen_indicator_dictionary.py`'s `desc` shows
`d[:150].rsplit(' ', 1)[0]` of the docstring's first paragraph, so a paragraph
over 150 characters loses a **whole word**. This one is **134 characters, 16 to
spare**, measured by growing the sentence one character at a time against the
generator's own `desc` (lifted out with `ast`, not retyped).

---

## §Z Cost

Four rolling passes, four shifts, two `ffill`s, two subtractions, one division
and one `replace` — no Python loop, so time and memory are linear in bars.

| bars | peak MB | peak MB (2nd) | ms | ms (2nd) |
|---|---:|---:|---:|---:|
| 100,000 | 6.6 | 6.6 | 16.2 | 15.0 |
| 400,000 | 26.4 | 26.4 | 57.3 | 57.5 |

⚠ The wall clock is **disclosed, not claimed**: two invocations of the same
section already disagree, and both are printed so the spread is visible rather
than averaged away. The memory figures are `tracemalloc` peaks and were
identical on both invocations.

---

## Gate F — suites

* `python -m pytest tests/test_sk_fcb_pos.py -q` → **218 passed**.
* `python docs/measure_sk_fcb_pos_cpu.py` → the same **218 passed** with
  `NPY_DISABLE_CPU_FEATURES="AVX512F AVX512_SKX AVX2 FMA3"`, numpy 1.26.4,
  dispatchable features still enabled printed by the run and the four asserted
  absent. §A1 and §C4 re-run under that environment are **identical cell for
  cell**.
* `python -m pytest -q` (whole suite, this worktree) → **3 failed, 9,516
  passed, 85 skipped** in 340 s. All three failures are expected and none is
  this port's:
  1. `tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
     — the owed row, which reports
     `['arch_lm', 'diff2_acf1', 'edge', 'firstzero_ac', 'halflife', 'lumpiness', 'mtd_ret', 'sk_fcb_pos']`.
     A skip under `GATE_E_PENDING_OK=1` on the way to `dev`.
  2. `tests/test_pine_coverage_csv.py::test_audited_rows_carry_their_evidence`
     — `dev`'s known clean-checkout break (`CLAUDE.md` *Known breaks*).
  3. `tests/test_altrepo_talib_csv.py::test_regenerating_reproduces_the_committed_rows`
     — needs the sibling `../AlternativeRepos` checkout; deselected by name in
     CI (`CLAUDE.md`, *CI*).
* The Backtesting suite, and both suites in clean worktrees: run by
  issue-solver after this session.

⚠ One pre-existing defect, recorded and not fixed because it is outside this
issue's scope and `#100 … #107` already recorded it: `pandas_ta/core.py` hands
out the live `Category[name]` list and removes names from it, so a module that
exercises `df.ta.strategy()` shrinks `Category` for every module collected
after it in the same process. Measured again here —
`pytest tests/test_wiring_accessors.py tests/test_altport2_ports.py` gives
*"Category total 344, expected 347"*, while `tests/test_altport2_ports.py`
alone and the full alphabetical run both pass.

Counts, distinct-value counts and Spearman figures are **not** pinned to their
digits anywhere in `tests/test_sk_fcb_pos.py`: the frames are built with
`np.exp` and `np.cumsum`, a band leg is chosen by a strict comparison, and a
small denominator amplifies a last-bit move. Every count there is a bound or a
relation, with the figure measured on this machine stated in the docstring.
