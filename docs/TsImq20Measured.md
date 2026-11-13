# TS_IMQ_20 — measured

PandasTa issue **#99**, TS-IMQ-20. `pandas_ta/statistics/ts_imq_20.py`,
column **`TS_IMQ_20`**, category `statistics`.

    x          = the trailing 20 simple returns
    TS_IMQ_20  = (argmax(cumsum(|x|) / sum(|x|) >= 0.5) + 1) / 20

**What it answers: WHERE in the last 20 bars half of the absolute-return mass
sits**, as a fraction of the window. Near 1 the big moves are the recent ones,
near 0 they are the old ones, 0.5 is an even spread. It is a POSITION, not a
size — scaling every |return| by a positive constant cannot move it.

Every number in **§§A–D, Guards, O and Z** is printed by
**`docs/measure_ts_imq_20.py`** (`python docs/measure_ts_imq_20.py
[A B C D G O Z]`), on this machine, with numpy 1.26.4 / pandas 2.3.3.
Nothing here was written before it was run. The exceptions are named at
point of use and are these three: **§F**'s test count comes from pytest and
from `docs/measure_ts_imq_20_cpu.py` (which re-runs the test module with
numpy's `AVX512F AVX512_SKX AVX2 FMA3` dispatch disabled); **§Z**'s 800 MB
is arithmetic, labelled "computed, not traced"; and the counts in **§The
wiring** come from the live package and are asserted by
`tests/test_readme_counts.py`, `tests/test_ml_companions.py` and
`tests/test_altport2_ports.py`.

**Verdict: SHIP WITH DISCLOSURE, pending Gate E.** The disclosure is §O: the
column overlaps the shipped `TFCENTROID_20` at pooled +0.8466 on synthetic
frames, which is DISCLOSE_GAP and not STRUCK under `r3-perframe-0.90`, and
there is no real-frame figure for that pair. §E names what would reverse it.

---

## Gate A — correctness

Gate A starts from the SOURCE formula, not from the prototype.

### A0. the source, and what could not be checked

tsfresh `feature_calculators.index_mass_quantile`, MIT. The published
definition:

    abs_x = np.abs(x)
    s = sum(abs_x)
    if s == 0:
        NaN                      # all values zero, or length 0
    else:
        mass_centralized = np.cumsum(abs_x) / s
        (np.argmax(mass_centralized >= q) + 1) / len(x)

Issue #99 applies it as `index_mass_quantile(q=0.5) on 20 |returns|`, so `x`
is the window's 20 simple returns and `q` is 0.5.

⚠ **tsfresh is NOT installed in this worktree and web access is
unavailable.** What Gate A checks is the published definition quoted above
plus the issue's line — not a read of tsfresh's own source. The `20` and the
`q = 0.5` are the issue's own parameters. This is the same limitation the
`ts_medskew_20` receipt (#98) records, and it is stated here rather than
papered over.

The issue hands the function `|returns|` and the function takes its own
`np.abs`, so the second absolute value is a no-op. **Measured** (A1b):
bit-equal on **1,480 of 1,480** bars of each of the walk, heavy-tailed and
two-point frames, masks identical, max |difference| **0.0**.

### A1. the expression, window by window — bit-equal everywhere

The published expression applied one window at a time, sharing no code with
the module (a Python loop, `np.cumsum`, Python's `sum`, `np.argmax`):

| frame | bit-equal | masks equal | max \|d\| |
|---|---|---|---|
| walk | 1,480 / 1,480 | yes | 0.0 |
| tick-rounded | 1,480 / 1,480 | yes | 0.0 |
| ar1+ | 1,480 / 1,480 | yes | 0.0 |
| ar1- | 1,480 / 1,480 | yes | 0.0 |
| heavy-tailed | 1,480 / 1,480 | yes | 0.0 |
| right-skewed | 1,480 / 1,480 | yes | 0.0 |
| left-skewed | 1,480 / 1,480 | yes | 0.0 |
| two-point | 1,480 / 1,480 | yes | 0.0 |
| trending | 1,480 / 1,480 | yes | 0.0 |

### A2 / A3. two more oracles, neither sharing code with the module

* **`math.fsum` scalar loop** — every partial sum and the total correctly
  rounded exactly once, where the module's running `acc` rounds at each step:
  bit-equal on **1,480 of 1,480** bars of each of the nine frames, masks
  identical.
* **An EXACT rational oracle** (`fractions.Fraction`) — every float return is
  a rational, so the partial sums, the total and the `>= 0.5` comparison
  round not at all: bit-equal on **13,320 of 13,320** bars pooled over all
  nine frames, masks identical on each.

⚠ **Bit-equality against these two is measured, not guaranteed, and the
tests say so.** The statistic's output is one of 20 discrete values, so a
last-bit difference in the accumulation either changes nothing or moves the
answer by a whole position — and `math.fsum` and `Fraction` both round
differently from the module's running `acc`. On these frames it changed
nothing; on the `two-point` frame, where §D2 shows every window sitting on
the `>= 0.5` tie, it easily could. `tests/test_ts_imq_20.py` therefore
asserts the exact equality for each of these two oracles on the EIGHT
non-tie frames, and holds the tie frame to one position of tolerance for
both of them plus the prototype
(`test_the_tie_frame_is_held_to_a_tolerance_and_not_to_the_bits`).

The ONE oracle that IS bit-identical by construction is §A1's: it
accumulates with Python's `sum` and `np.cumsum`, strictly left to right,
which is the same order and so the same doubles as the module's two loops.
That one is asserted as an equality on all nine frames.

### A3b. the closed form, and the one thing float arithmetic can cost

Closes that **DOUBLE** give a return of exactly 1.0 on every bar, so the
window's values are exactly equal with no rounding anywhere and the crossing
is exactly at `ceil(length * q)`:

| length | measured | expected |
|---|---|---|
| 2 | 0.5 | 0.5 |
| 4 | 0.5 | 0.5 |
| 20 | 0.5 | 0.5 |
| 60 | 0.5 | 0.5 |

⚠ The one cost float arithmetic can impose here is a **TIE**, not a loss of
precision: where the exact cumulative mass lands within a rounding of half
the total, the crossing can be reported one position early or late — a
difference of `1 / length`, which the floats realise as
**0.050000000000000044**. 200 windows built to straddle
the threshold produced **0** disagreements with the exact oracle. The bound
is structural (the two answers differ by at most one position); the
`two-point` frame under a ×10 rescale (§D2) is the witness that the straddle
is reachable at all.

### A4. the value set, and the `found` backstop

The output is `k / length` for an integer `k` in `1 .. length`. `0` is
unreachable (the source's `+ 1`), and so is anything above 1.

| frame | distinct values | min | max |
|---|---|---|---|
| walk | 12 | 0.25 | 0.80 |
| tick-rounded | 12 | 0.25 | 0.80 |
| ar1+ | 15 | 0.15 | 0.85 |
| ar1- | 14 | 0.20 | 0.85 |
| heavy-tailed | **20** | 0.05 | 1.00 |
| right-skewed | 12 | 0.25 | 0.80 |
| left-skewed | 12 | 0.25 | 0.80 |
| two-point | **2** | 0.50 | 0.55 |
| trending | 8 | 0.35 | 0.70 |

⚠ **A consumer that treats this as a continuum is wrong.** It is an ordinal
with at most 20 levels, and how many a frame reaches swings from 2 to 20.

The module's `found` flag is a labelled BACKSTOP with no witness **at
`q = 0.5`**: re-running the module's own two loops, `found` and `s > 0`
disagree on **0** windows of each of the nine frames, which is arithmetic
rather than luck (the last `acc` is the same double as `s`, and
`s / s >= 0.5`).

It is kept for the case that DOES have a witness, and the witness is two
mutants rather than a re-implementation of the module inside its own test —
the first raising `Q` to 1.5, the second also deleting `& found`. Printed by
the script's A4 section and asserted by
`tests/test_ts_imq_20.py::test_the_found_backstop_is_what_stops_a_q_above_one_reporting_zero`,
on a 300-bar walk:

| module | non-NaN | values |
|---|---|---|
| the real module | 280 / 280 | the column |
| `Q = 1.5`, backstop KEPT | **0** | — |
| `Q = 1.5`, backstop DROPPED | 280 | max **0.0** on every bar |

Without the backstop every bar reports position 0 — the value this column
must never emit. It costs one pass over a `(rows,)` array.

### A5. the readings the wording leaves open — priced, not assumed

All on the 1,500-bar walk, 1,480 fired bars.

| reading | kept | measured against the alternative |
|---|---|---|
| SIMPLE returns (`c/c[1] - 1`) | yes | log returns: rho **0.996198**, bit-equal 1,440 / 1,480, max \|d\| 0.050000000000000044 — **one position** |
| of the RETURNS | yes | of the 20 CLOSES: rho **-0.069354** (and not scale-free) |
| `length` counts RETURNS (21 closes) | yes | 20 closes, i.e. 19 returns: rho **0.906430**, max \|d\| 0.1842 |
| the source's `+ 1` | yes | dropping it: see below — rho **1.000000**, but the floor becomes 0.0 |
| `>= q` | yes | `> q`: bit-equal **1,480 / 1,480** |
| `acc / s >= q` (divide first) | yes | `acc >= q * s`: bit-equal **1,480 / 1,480** |
| `q = 0.5` | yes | q = 0.25: rho **0.595231**, mean 0.2828 · q = 0.75: rho **0.594006**, mean 0.7665 |

`q` is a module CONSTANT and not an argument: the column name carries only
`length`, so a second parameter could not reach the name without changing it
for every caller, and q = 0.25 / 0.75 are different columns (rho ~0.59), not
variants of this one.

**The `+ 1` row, measured rather than reasoned.** The alternative is built
from scratch in the script (`_no_plus_one_variant`, the source expression
with `argmax(...) / len(x)` and no `+ 1`) — NOT as `module - 1/length`,
which would be the conclusion subtracted from itself and would agree with
anything:

| frame | rho | shift (min, max) | variant min | module min | variant bars at 0.0 |
|---|---|---|---|---|---|
| walk | 1.000000 | 0.049999999999999933 … 0.050000000000000044 | 0.20 | 0.25 | 0 |
| heavy-tailed | 1.000000 | 0.049999999999999933 … 0.050000000000000044 | **0.00** | 0.05 | **6** |

So what the `+ 1` buys is the floor: without it the column is the 0-based
position and reads **0.0** on 6 bars of the heavy-tailed frame, a value that
every other consumer reads as "no mass anywhere". The shift is `1 / length`
to within a rounding (1.1e-16) and NOT exactly 0.05, which is why the test
asserts a tolerance.

### A6. the distribution

On the walk (1,480 fired bars): 12 distinct values over [0.25, 0.80], median
**0.5500**, mean **0.5255**, sd **0.0880**; the mode is 0.55 at **309** bars
and the rarest value 0.80 at **2**.

Autocorrelation: **0.8424** at lag 1, **0.2759** at lag 5, **-0.3465** at lag
10, **-0.0361** at lag 20. The negative lag-10 reading is structural and not
noise: a cluster of big returns sitting late in window T (a high reading) has
slid to the OLD half of window T+10 (a low one).

On 20,000 INDEPENDENT windows:

| return law | mean | sd | min | max |
|---|---|---|---|---|
| gaussian | 0.5264 | 0.0849 | 0.20 | 0.85 |
| student-t(2) | 0.5251 | 0.1438 | 0.05 | 1.00 |
| exponential (one-signed) | 0.5246 | 0.1088 | 0.15 | 0.90 |

The CENTRE barely moves with the law — the other side of it being a position
— while the SPREAD nearly doubles with the tails.

### A1c. the screen prototype

`docs/issues/screen/ind_screen.py`, candidate `ts_imq_20`
(`roll(ret(c), 20, w_index_mass_quantile)`), retyped in the measurement
script and in the test module because that tree is the owner's and is
gitignored. It differs from the module in two spellings — a PAIRWISE
`A.sum(1)` where the module accumulates the total sequentially, and a
materialised `(rows, length)` `np.cumsum(A, 1)`.

**Bit-equal on 1,480 of 1,480 bars of each of the nine frames**, masks
identical, max |difference| 0.0 — and bit-equal again on the three frames
built to break it:

| frame | module non-NaN | prototype non-NaN | bit-equal |
|---|---|---|---|
| flat (300 identical closes) | 0 | 0 | — (both empty) |
| 1 %-a-bar ladder | 280 | 280 | 280 / 280 |
| quiet (returns 1e-6) | 580 | 580 | 580 / 580 |

⚠ Where the two DO part company — the guards this module adds and the screen
has no need of:

| frame | module non-NaN | prototype non-NaN |
|---|---|---|
| `close[200] = 0.0` (400-bar walk) | 359 | 360 |
| `close[200] = -1.0` | 359 | **380** |
| `close[200] = 1e-310` | 359 | 360 |
| `close[200] = inf` | 359 | 360 |
| a 1e+307 return at bar 200 (2,000 bars) | 1,960 | 1,980 |

Every extra bar the prototype reports is a window built on a close a market
cannot print, or on a return whose window total would overflow.

---

## Gate B — causality, by MUTANT

Prefix truncation cannot see back-dating, so causality is tested by
future-perturbation: replace every close from bar J on and assert that no bar
before J moves. **37 offsets**, J = 40 … 1480, on three frames.

### B1. the real module

| frame / parameter | leaks |
|---|---|
| walk | **0 / 37** |
| tick-rounded | **0 / 37** |
| heavy-tailed | **0 / 37** |
| walk at `length` 5 | 0 / 37 (first fired bar 5) |
| walk at `length` 60 | 0 / 37 (first fired bar 60) |
| walk at `length` 250 | 0 / 37 (first fired bar 250) |

### B2. five mutants, each LIVE and each caught

Read with `importlib`, string-patched, `exec`'d in memory. Every one changes
the column (otherwise the test proves nothing).

| mutant | what it does | walk | tick-rounded | heavy-tailed |
|---|---|---|---|---|
| `back_date_two` | writes the block two bars early | 37 / 37 | 36 / 37 | 37 / 37 |
| `back_date_full` | writes it at bar 0 | 37 / 37 | 37 / 37 | 37 / 37 |
| `forward_window` | rolls the window one bar forward | 37 / 37 | 36 / 37 | 37 / 37 |
| `forward_return` | reads the return one bar ahead | 37 / 37 | 36 / 37 | 37 / 37 |
| `future_total` | divides by the NEXT window's total mass | 37 / 37 | **35 / 37** | 37 / 37 |

`future_total` is the one worth reading: it back-dates nothing and moves no
index. It simply lets bar T's ratio be divided by window T+1's total — and
that alone leaks on 35 to 37 of the 37 offsets.

`tests/test_ts_imq_20.py` pins the band **30 … 37**, five below the smallest
measured, so a last-bit difference on another CPU cannot fail the suite while
a mutant going dead still does.

**No floor-index mutant exists here**, unlike `ts_medskew_20`'s sixth: this
module has no dispersion floor to shift (see Guards G3).

---

## Gate C — reachability

⚠ **The real-data counts are OWED.** `../Backtesting`'s 89 frozen ALTPORT-1
frames are outside this worktree, so the counts below are SYNTHETIC. The
launcher's Gate E run produces the real-data reachability figures and the
receipt session writes them here.

| frame (1,500 bars) | non-NaN | non-zero | distinct | first fired bar |
|---|---|---|---|---|
| walk | 1,480 | 1,480 | 12 | 20 |
| tick-rounded | 1,480 | 1,480 | 12 | 20 |
| ar1+ | 1,480 | 1,480 | 15 | 20 |
| ar1- | 1,480 | 1,480 | 14 | 20 |
| heavy-tailed | 1,480 | 1,480 | 20 | 20 |
| right-skewed | 1,480 | 1,480 | 12 | 20 |
| left-skewed | 1,480 | 1,480 | 12 | 20 |
| two-point | 1,480 | 1,480 | 2 | 20 |
| trending | 1,480 | 1,480 | 8 | 20 |

The column cannot be 0, so "non-zero" equals "non-NaN" by construction and is
reported only because Gate D asks for it.

Degenerate frames: a **flat** frame (300 identical closes) fires on **0** —
the source's own `s == 0` rule. A **1 %-a-bar ladder** fires on 280 of 300.
A **quiet** frame (returns of 1e-6) fires on 580 of 600 over 10 distinct
values.

---

## Gate D — scale-free

### D1. ×8 and ×64 — BIT-IDENTICAL

`8a / 8b` is the same double as `a / b`, so the returns, and therefore every
later step, are unchanged. All nine frames, both factors:

    walk tick-rounded ar1+ ar1- heavy-tailed right-skewed left-skewed
    two-point trending          ×8  1,480/1,480   ×64  1,480/1,480
                                NaN masks identical in all 18 cases

At other lengths on the walk, at **both** factors: **1,498 / 1,498** at
`length` 2, **1,495 / 1,495** at 5, **1,440 / 1,440** at 60,
**1,250 / 1,250** at 250, NaN masks identical in all 8 cases.

### D2. ×10, ×3.7, ×0.1 — bit-identical on eight frames of nine

Not bit-identical by construction. Measured:

| frame | ×10 | ×3.7 | ×0.1 | max \|d\| |
|---|---|---|---|---|
| walk | 1,480 / 1,480 | 1,480 / 1,480 | 1,480 / 1,480 | 0.0 |
| tick-rounded | 1,480 / 1,480 | 1,480 / 1,480 | 1,480 / 1,480 | 0.0 |
| ar1+ | 1,480 / 1,480 | 1,480 / 1,480 | 1,480 / 1,480 | 0.0 |
| ar1- | 1,480 / 1,480 | 1,480 / 1,480 | 1,480 / 1,480 | 0.0 |
| heavy-tailed | 1,480 / 1,480 | 1,480 / 1,480 | 1,480 / 1,480 | 0.0 |
| right-skewed | 1,480 / 1,480 | 1,480 / 1,480 | 1,480 / 1,480 | 0.0 |
| left-skewed | 1,480 / 1,480 | 1,480 / 1,480 | 1,480 / 1,480 | 0.0 |
| **two-point** | **1,029 / 1,480** | **1,071 / 1,480** | **1,038 / 1,480** | **0.050000000000000044** |
| trending | 1,480 / 1,480 | 1,480 / 1,480 | 1,480 / 1,480 | 0.0 |

NaN masks match in **all 27** cases.

⚠ **The two-point frame is the honest exception, and it is named rather than
averaged away.** There every |return| is the same size, so every window's
cumulative mass lands on the `>= 0.5` threshold and a last-bit change in the
returns flips the crossing between position 10 and 11. The difference is
`1 / length` — ONE position, realised as 0.050000000000000044, the smallest
step this column can take and also the largest error this failure mode can
produce. The Gate D tolerance
for a non-power-of-two rescale is therefore stated as `1 / length`, not as a
float epsilon, and `tests/test_ts_imq_20.py` gives that frame its own test.

### D3. stronger than a price rescale

The statistic divides by the window's own total mass, so a positive rescale
of the RETURNS cancels exactly:

| transform | bit-equal | masks |
|---|---|---|
| `r × 2` | 1,480 / 1,480 | identical |
| `r × 0.5` | 1,480 / 1,480 | identical |
| `r × 1e-6` | 1,480 / 1,480 | identical |
| `r + 0.004` (a SHIFT) | **639 of 1,480 bars move**, rho 0.8534 | identical |

The shift MUST move it — it changes which bars carry the mass. That is the
column working, not failing.

### D4. `0 < fires < n`, and what it cannot see

Fires on 1,480 of 1,500 bars on every frame (so `0 < fires < n`), with at
least 2 distinct values everywhere, so a constant column cannot pass. On the
walk it reads Spearman **-0.0156** against the window's own return standard
deviation, **-0.0486** against its mean return and **-0.0096** against the
close itself.

---

## Gate E — attribution

**Gate E: pending, run by issue-solver after this session.**

`tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
reports `ts_imq_20` as owed until the receipt session records the row with
`python docs/gate_e_ledger.py record <run dir> --measured YYYY-MM-DD`.
`tests/test_ts_imq_20.py::test_the_gate_e_row_is_owed` asserts the row is
absent, so it fails at the moment the row lands — deliberately, as the
receipt session's cue to replace it with one pinning the recorded numbers.

What the 2026-10-24 screen measured on the PROTOTYPE (a prototype is not a
port): max |rho| **0.5254** vs `ATR_Ratio_5_20_Pctl` over n = 391,818,
per-frame max median 0.5258 → SHIP; next comparators `ATR_Ratio_5_20` 0.5237
and `ATR_Ratio_5_20_State` 0.5004. Since this module is bit-equal to the
prototype on every frame measured in §A1c, those figures are expected to
carry over — but the launcher's run on THIS module is the number that
decides.

A local stand-in for that comparator family, `mean|r| over 5 / mean|r| over
20`, reads **+0.6121** on a walk, +0.5285 heavy-tailed and +0.5582 trending
(§O2), which is the same direction and magnitude.

**What would reverse the ship decision:** a pooled |rho| ≥ 0.90 or a top-five
comparator's per-frame median ≥ 0.90 in the launcher's run (STRUCK → revert
or waiver), or an owner's question-redundancy ruling on the `TFCENTROID_20`
overlap in §O, which the bands do not make on their own.

---

## Gate F — suites

* `tests/test_ts_imq_20.py`: **212 passed**.
* The same 212 under `NPY_DISABLE_CPU_FEATURES="AVX512F AVX512_SKX AVX2
  FMA3"`, via `docs/measure_ts_imq_20_cpu.py`, which asserts the dispatch
  actually took (still enabled on this machine: `SSSE3`, `SSE41`, `POPCNT`,
  `SSE42`, `AVX`, `F16C`, `AVX512CD`, `AVX512_CLX`, `AVX512_CNL`,
  `AVX512_ICL`).
* Full-suite result and the Backtesting suite: the launcher runs both in
  clean worktrees.

---

## Guards

### G1. a bad close empties its windows and nothing before them

A close that is not a finite, normal, positive float (NaN, inf, 0, negative,
or subnormal such as 1e-310) has no return to take. It spoils TWO returns, so
it empties the `length + 1` = 21 windows holding it — fewer near either end.
Measured on a 400-bar walk:

| bad close at bar | newly NaN | bars before it that moved |
|---|---|---|
| 0 | 1 | 0 |
| 1 | 2 | 0 |
| 19 | 20 | 0 |
| 200 | 21 | 0 |
| 398 | 2 | 0 |
| 399 | 1 | 0 |

Over all **30** (bad value, position) pairs — {NaN, inf, 0.0, -1.0, 1e-310} ×
{0, 1, 19, 200, 398, 399} — the number of pairs with a bar before the bad
close moving is **0**.

### G2. the source's own `s == 0` rule

21 identical closes give 20 returns of exactly 0, which have no mass to find
a quantile of: the value is **NaN**, and a 300-bar flat frame fires on **0**
bars. This is tsfresh's rule, not an addition.

The two extremes of the column come from the same construction: 19 zero
returns followed by one 1 % move reads **1.00** (all the mass on the last
bar), and the mirror reads **0.05**.

### G3. there is deliberately NO dispersion floor

`statistics/ts_medskew_20.py` and `statistics/ts_above_mean_20.py` both
refuse a window whose returns span 4096 ulps or less of the largest of them,
because both read a centre estimate whose own rounding the statistic then
amplifies. **This column does not, and that is a decision with a
measurement behind it.**

On a 1 %-a-bar geometric ladder — a mathematically CONSTANT return that
float64 reproduces only to rounding:

| column | result |
|---|---|
| `ts_imq_20` | 280 of 280 windows: **0.50 on 178, 0.55 on 102** |
| a DOUBLING ladder (returns exactly 1.0, no rounding) | **0.5 on all 281** |
| `ts_medskew_20` (which HAS the floor) | **0** windows |
| the same statistic WITHOUT its floor | 280 windows spanning **[-0.3300, +0.3033]** |

The sibling's unfloored statistic wanders across two thirds of its range on
pure rounding, which is why it floors. This column's whole excursion is **one
position** — 0.50 or 0.55 against an exact answer of 0.50 — and the doubling
ladder shows the jitter is in the DATA's rounding, not in the module: with
returns of exactly 1.0 there is nothing to jitter on and every window reads
0.5. Adding the siblings' floor here would empty **280 honest windows and 0
dishonest ones**.

On a quiet-but-honest frame (returns of 1e-6) the column fires on **580 of
600** bars over 10 distinct values and is **bit-equal to the exact rational
oracle on all 580** — which an absolute ulp floor would not have permitted.
(`ts_medskew_20`'s RELATIVE floor also reports 580 there; the ladder, not the
quiet frame, is where the two modules differ.)

### G4. locality — and why the O(n) spelling is not used

A 2,000-bar frame priced at 1e-198 (so even a 1e+307 planted return keeps the
close path finite), with one return planted at bar 200:

| spike | its 20 windows | bars 220… vs the unspiked frame |
|---|---|---|
| ×1e+02 | all 20 fire | **1,780 / 1,780 bit-identical** |
| ×1e+06 | all 20 fire | 1,780 / 1,780 bit-identical |
| ×1e+08 | all 20 fire | 1,780 / 1,780 bit-identical |
| ×1e+100 | all 20 fire | 1,780 / 1,780 bit-identical |
| ×1e+300 | all 20 fire | 1,780 / 1,780 bit-identical |
| ×1e+307 (past the bound) | **0 fire** | 1,780 / 1,780 bit-identical |

The same frames through a GLOBAL `np.cumsum` differenced per window — the
O(n) spelling this module does not use:

| spike | bars 220… bit-identical | the tail itself |
|---|---|---|
| ×1e+02 | 1,780 / 1,780 | [0.25, 0.80], 12 distinct |
| ×1e+08 | 1,780 / 1,780 | [0.25, 0.80], 12 distinct |
| ×1e+100 | **0 / 1,780** | **every bar NaN** |

At 1e+100 the two partial sums cancel to exactly zero, every later window
reads no mass, and the whole tail is destroyed — bars on which this module
spans [0.25, 0.80] over 12 distinct values. That is the entire argument for
the per-window accumulation, and it is a run rather than an assertion.

### G5. the per-return bound

`|r| < max / (2 * length)` = **4.494e+306** at `length` 20, so a window's 20
values sum to at most half the float maximum and the total is a real number
rather than an infinity. Nothing a market can produce reaches it.

---

## O — what the column overlaps

### O1. the fork's own statistics columns

Spearman per frame, and pooled over the nine (n = 13,320):

| frame | TFCENTROID_20 | TS_ABOVE_MEAN_20 | TS_MEDSKEW_20 | TS_CID_CE_20 | TS_PEAKS_20 |
|---|---|---|---|---|---|
| walk | +0.8527 | +0.0032 | +0.0061 | +0.1032 | -0.0034 |
| tick-rounded | +0.8521 | +0.0037 | +0.0061 | +0.1034 | -0.0037 |
| ar1+ | +0.8669 | +0.0352 | -0.0465 | -0.0051 | +0.0919 |
| ar1- | +0.8738 | +0.0047 | -0.0130 | -0.0181 | -0.0091 |
| heavy-tailed | **+0.8857** | +0.0370 | -0.0331 | +0.0088 | +0.0135 |
| right-skewed | +0.8545 | +0.0543 | -0.0285 | -0.0189 | -0.0513 |
| left-skewed | +0.8545 | -0.0543 | +0.0285 | -0.0189 | +0.0592 |
| two-point | **+0.7252** | -0.0211 | +0.0627 | +0.0585 | -0.0194 |
| trending | +0.8042 | -0.0275 | -0.0084 | -0.0512 | -0.0030 |
| **pooled** | **+0.846649** | +0.010188 | -0.008356 | +0.011482 | +0.011861 |
| per-frame \|rho\| median | **0.8545** | 0.0275 | 0.0285 | 0.0189 | 0.0135 |
| per-frame \|rho\| max | **0.8857** | 0.0543 | 0.0627 | 0.1034 | 0.0919 |
| frames ≥ 0.90 | **0 / 9** | 0 / 9 | 0 / 9 | 0 / 9 | 0 / 9 |

⚠ **`TFCENTROID_20` is the disclosure, and it is the reason this port ships
with a warning in five places.** TSFEL's temporal centroid (issue #116,
merged 2026-10-30) is the energy-weighted **MEAN** position of the same 20
returns where this column is the absolute-mass **MEDIAN** position. The two
answer the same question — where in the window did the volatility sit — with
different weights (`r²` against `|r|`) and different summaries (a mean
against a median crossing). A high correlation is the expected outcome, not a
surprise, and the measurement is what decides whether it is tolerable.

Under `r3-perframe-0.90`: pooled 0.8466 and per-frame median 0.8545 are both
in **DISCLOSE_GAP** (0.80 ≤ ρ < 0.90), not STRUCK. 0 of 9 frames reach 0.90.

⚠ **These are SYNTHETIC frames.** No real-frame figure for this pair exists:

* The 2026-10-24 screen's stage-2 fork overlap (max |rho| 0.6127 vs
  `cvi:CVI_10_10`, 12 frames) was taken on **2026-10-24**, six days before
  `tf_centroid_20` entered `Category` on **2026-10-30** (commit `4f1063b`,
  issue #116), so it cannot bound this pair. This is the same trap
  `ts_above_mean_20` fell into with `osap_retskew_21` and `ts_medskew_20`
  recorded for `ts_above_mean_20`.
* Gate E cannot re-measure it either: its 687 comparators are the engine's
  `compute_all` ∪ the `ml_features` manifest, and neither holds a pandas_ta
  port.

Against the fork's other 20-return statistics columns the per-frame |rho| is
at most **0.1034**. They answer different questions: how BIG (`TS_CID_CE_20`),
how SKEWED (`TS_MEDSKEW_20`, `TS_ABOVE_MEAN_20`), how many local maxima
(`TS_PEAKS_20`) — this one answers WHERE.

### O2. the recency of volatility

What the column DOES see, and the reason the screen's top comparators are the
`ATR_Ratio_5_20` family. Against `mean|r| over 5 / mean|r| over 20`:

| frame | rho |
|---|---|
| walk | **+0.6121** |
| heavy-tailed | +0.5285 |
| trending | +0.5582 |

Consistent in sign and magnitude with the screen's 0.5254 against
`ATR_Ratio_5_20_Pctl` on real frames.

---

## Z — cost

On 400,000 bars, this machine, `tracemalloc` peak, **three runs per row**
reported as a range rather than as the fastest one:

| length | time (3 runs) | traced peak |
|---|---|---|
| 2 | 21.2 – 22.1 ms | **30.0 MB** |
| 20 | 50.3 – 53.7 ms | **30.0 MB** |
| 60 | 115.1 – 115.7 ms | **30.0 MB** |
| 250 | 445.7 – 470.0 ms | **30.0 MB** |

The peak does not grow with `length` at all, which is the point of the
per-position loops: `np.cumsum(aw, axis=1)` would materialise a
`(rows, length)` copy of the view — **computed, not traced**: rows × length
× 8 bytes = 800 MB at `length` 250 and n = 400,000.

The window-by-window oracle takes ~0.2 s on 20,000 bars, which is why it
lives in `docs/measure_ts_imq_20.py` and not in the module.

⚠ Every wall-clock figure here is this machine's and moves between runs and
between days, on **every** row. Observed across sweeps: `length` 2 at 28.5 /
21.8 / 39.8 ms single-run and 21.1–36.2 and 21.3–21.8 ms in three-run
sweeps; `length` 20 at 48.1–53.7 ms; `length` 60 at 114.0–132.8 ms against
the table's 115.1–115.7; `length` 250 at 427.2–505.3 ms against the table's
445.7–470.0. **The intervals in the table are ONE invocation's three runs
and a reader's re-run will fall outside them** — treat the column as an
order of magnitude, not a benchmark. The 30.0 MB peak, by contrast,
reproduced at all four lengths in every sweep. The PEAK is the claim. **This file is the only place the
timings are quoted** — the module docstring deliberately carries none, so
the two cannot drift apart.

---

## The wiring — five touch points

| # | file | what |
|---|---|---|
| 1 | `pandas_ta/statistics/ts_imq_20.py` | the indicator |
| 2 | `pandas_ta/statistics/__init__.py` | package export |
| 3 | `pandas_ta/__init__.py` → `Category["statistics"]` | discovery / `df.ta.strategy()` |
| 4 | `pandas_ta/core.py` | `df.ta.ts_imq_20()` |
| 5 | `tests/test_ts_imq_20.py` | the suite |

`Category` 331 → **332**; statistics 40 → **41**; `df.ta.<name>()` 339 →
**340**. `README.md`, `docs/IndicatorDictionary.md` (regenerated) and
`docs/MLCompanionContract.md` (676 → 677 tagged columns, 318 → 319 `SF`)
carry the counts, and `tests/test_altport2_ports.py`'s pinned
`CATEGORY_TOTAL` is 332.

⚠ Recorded, not fixed: running `tests/test_wiring_accessors.py` before
`tests/test_altport2_ports.py` in one process leaves `Category` three names
short (329 against 332) because `pandas_ta/core.py:453` hands out the live
`Category[name]` list and `core.py:692` removes names from it. Pre-existing,
outside this issue's scope, already recorded on #98; alphabetical collection
hides it, and `tests/test_altport2_ports.py` alone passes.

---

## What this port did NOT do

* It did not run Gate E (the launcher does), and it did not write a ledger
  row.
* It did not measure anything on real data: `../Backtesting` is outside this
  worktree. Every count above is synthetic, and the ones that are owed are
  named as owed (§C, §E).
* It did not read tsfresh's source (§A0).
* It did not touch `pandas_ta/statistics/tf_centroid_20.py` or its receipt,
  although §O1 is new information about that column too. A reader of
  `docs/TfCentroid20Measured.md` will not find this overlap there; recording
  it on that side is the receipt session's or the owner's call, since that
  file is outside this session's allowed-modify list.
