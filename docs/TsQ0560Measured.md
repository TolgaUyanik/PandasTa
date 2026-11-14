# TS-Q05-60 — `ts_q05_60`, measured

PandasTa issue **#101** (parent #31 ALPHASETS, screen of 2026-10-24).
Module `pandas_ta/statistics/ts_q05_60.py`, column **`TS_Q05_60`**.
Tests `tests/test_ts_q05_60.py` (213). Every number in §A1–§A6, §B, §C,
§D, §G, §O's synthetic tables, §S and §Z is printed by
`python docs/measure_ts_q05_60.py` on this worktree (pandas 2.3.3, numpy
1.26.4), section by section. Those headings take their letters from the
script, with one join: the script's section **M** (the mutant table) is
printed here under §B, since it is Gate B's evidence. §E and §F are
headings of this file and not of the script. What does NOT come from the
script, and is marked where it appears:
**§E and §O's screen paragraph**, which are the 2026-10-24 screen's
figures, measured on the PROTOTYPE and quoted from the issue; and **§F**,
which is pytest's own output.

    r        = close / close.shift(1) - 1
    s        = the window's `length` returns, SORTED
    i        = q * (length - 1) = 2.95,  lo = 2,  frac = 0.9500000000000002
    TS_Q05   = s[2] + (s[3] - s[2]) * frac

**Source.** tsfresh `feature_calculators.quantile` (MIT) and QuantConnect
Lean's `ValueAtRisk`, as issue #101 states the formula: `quantile(q=0.05)
on 60 returns`. The screen prototype is
`docs/issues/screen/ind_screen.py` candidate `ts_q05_60`,
`ret(c).rolling(60).quantile(0.05)`.
⚠ **Neither library is installed in this worktree and web access is
unavailable.** Both are ATTRIBUTIONS, not oracles:
`tests/test_ts_q05_60.py::test_neither_source_library_is_installed_here`
records that. What Gate A checks is the published definition of
`feature_calculators.quantile` -- `pandas.Series.quantile`, linear
interpolation -- plus the issue's own line. Lean's own windowing and sign
convention are unverified here.

---

## Verdict

| Gate | Result |
|---|---|
| A Correctness | **PASS.** Bit-equal to an independent retyping of pandas' own `roll_quantile` spelling on 1,440 of 1,440 bars of each of nine frames; within ONE ulp of the source's spelling and of an exact rational oracle. |
| B Causality | **PASS.** 0 of 35 offsets leak on three frames and at `length` 2/5/250. Six mutants: five live and caught 6–35 of 35, the sixth dead on a clean frame and caught 12 of 12 on a designed one. |
| C Reachability | **PASS on synthetic frames; real-data counts owed** with the Gate E run. Fires 1,440 of 1,500 on each of nine frames, 5–170 distinct values. |
| D Scale-free | **PASS.** x8/x64 bit-identical on 1,440/1,440 of each of nine frames, at `length` 2/5/20/250 and at price 1e-6/1e+6/1e+100. x10/x3.7/x0.1/x1.0000001: masks identical, max relative difference 1.3e-14. `0 < fires < n` on every frame. |
| E Attribution | **Pending, run by issue-solver after this session.** |
| F Suites | This repo: 213 for the module, 213 again with AVX-512/AVX2/FMA3 disabled; full suite below. The Backtesting suite is the launcher's. |

---

## A1 — bit-equality against pandas' own spelling, retyped

`_pandas_spelling` in the measurement script sorts the window, takes the
two order statistics around `q * (n - 1)` and blends them
`vlow + (vhigh - vlow) * frac`. It shares no code with the module.

| frame | masks | shared | bit-equal | max \|diff\| |
|---|---|---|---|---|
| walk | True | 1440 | **1440** | 0.0 |
| tick-rounded | True | 1440 | **1440** | 0.0 |
| ar1+ | True | 1440 | **1440** | 0.0 |
| ar1- | True | 1440 | **1440** | 0.0 |
| heavy-tailed | True | 1440 | **1440** | 0.0 |
| right-skewed | True | 1440 | **1440** | 0.0 |
| left-skewed | True | 1440 | **1440** | 0.0 |
| two-point | True | 1440 | **1440** | 0.0 |
| trending | True | 1440 | **1440** | 0.0 |

At other lengths on the walk, all bit-equal with identical masks:
1,498 / 1,495 / 1,480 / 1,479 / 1,250 fired bars at `length`
2 / 5 / 20 / 21 / 250.

Which order statistics each `length` reads (exact doubles):

| `length` | `q*(n-1)` | floor | frac | reads |
|---|---|---|---|---|
| 2 | 0.05 | 0 | 0.05 | s[0], s[1] |
| 5 | 0.2 | 0 | 0.2 | s[0], s[1] |
| 20 | 0.9500000000000001 | 0 | 0.9500000000000001 | s[0], s[1] |
| 21 | 1.0 | 1 | **0.0** | s[1] alone |
| 22 | 1.05 | 1 | 0.050000000000000044 | s[1], s[2] |
| **60** | **2.95** | **2** | **0.9500000000000002** | **s[2], s[3]** |
| 250 | 12.450000000000001 | 12 | 0.45000000000000107 | s[12], s[13] |

## A2 — against the source's own spelling

tsfresh's `quantile` is `pandas.Series.quantile`, which goes through
numpy's `_lerp` and so evaluates `vhigh - (vhigh - vlow) * (1 - frac)`.
`Series.quantile` and `np.quantile` are bit-equal to each other on all
1,440 bars of the walk (measured), so there are two spellings here and not
three.

| frame | masks | shared | bit-equal | max \|diff\| | max rel | max ulp | spearman |
|---|---|---|---|---|---|---|---|
| walk | True | 1440 | 1364 | 3.469e-18 | 2.095e-16 | 1.00 | 1.000000 |
| tick-rounded | True | 1440 | 1230 | 3.469e-18 | 1.981e-16 | 1.00 | 1.000000 |
| ar1+ | True | 1440 | 1405 | 6.939e-18 | 2.128e-16 | 1.00 | 1.000000 |
| ar1- | True | 1440 | 1369 | 3.469e-18 | 1.762e-16 | 1.00 | 1.000000 |
| heavy-tailed | True | 1440 | 1228 | 6.939e-18 | 2.076e-16 | 1.00 | 1.000000 |
| right-skewed | True | 1440 | **1440** | 0.0 | 0.0 | 0.00 | 1.000000 |
| left-skewed | True | 1440 | 1394 | 3.469e-18 | 1.886e-16 | 1.00 | 1.000000 |
| two-point | True | 1440 | **1440** | 0.0 | 0.0 | 0.00 | 1.000000 |
| trending | True | 1440 | 1358 | 1.735e-18 | 2.005e-16 | 1.00 | 1.000000 |

## A3 — against an exact rational oracle

Every return is a double, so a rational; the sort is exact and the blend is
done in `fractions.Fraction` and rounded exactly once. `q` is
`Fraction(0.05)` -- the exact value of the double the source is handed,
`3602879701896397/72057594037927936` -- and not 1/20.

| frame | bars | module bit-eq | max ulp | mean ulp | numpy bit-eq | max ulp | mean ulp |
|---|---|---|---|---|---|---|---|
| walk | 1440 | 1364 | 1.00 | 0.0528 | **1440** | 0.00 | 0.0000 |
| tick-rounded | 1440 | 1247 | 1.00 | 0.1340 | 1423 | 1.00 | 0.0118 |
| ar1+ | 1440 | 1405 | 1.00 | 0.0243 | **1440** | 0.00 | 0.0000 |
| ar1- | 1440 | 1379 | 1.00 | 0.0424 | 1430 | 1.00 | 0.0069 |
| heavy-tailed | 1440 | 1262 | 1.00 | 0.1236 | 1406 | 1.00 | 0.0236 |
| right-skewed | 1440 | **1440** | 0.00 | 0.0000 | **1440** | 0.00 | 0.0000 |
| left-skewed | 1440 | 1373 | 1.00 | 0.0465 | 1419 | 1.00 | 0.0146 |
| two-point | 1440 | **1440** | 0.00 | 0.0000 | **1440** | 0.00 | 0.0000 |
| trending | 1440 | 1390 | 1.00 | 0.0347 | 1408 | 1.00 | 0.0222 |

⚠ **This is the one check that can witness what the module's spelling gets
wrong, and the answer is: one bit.** numpy's lerp branch is closer to the
correctly rounded answer on seven of the nine frames and tied on two; on no
frame is pandas' branch closer. The module keeps pandas' branch because it
is the prototype's and the shipped `quantile`'s, and the disagreement is at
most 1 ulp in either direction.

The same oracle prices the other float detail the formula hides: the exact
answer at `q = Fraction(0.05)` and at `q = 1/20` are bit-equal on 1,348 of
1,440 bars of the walk and differ by at most 1.00 ulp on the other 92.
(`Fraction(0.05) * 59` happens to be exactly 2.95 as a double.)

## A4 — the column reads two returns, and that is all

A window whose returns are exactly `2**e - 1` is exact end to end (every
close is a power of two times 100). Two such windows share only their 3rd
and 4th smallest returns, `2**-3 - 1` and `2**-2 - 1`; the 56 above the
pair move from +1.0 to +3.0, the two below from -0.96875 / -0.9375 to
-0.999999 / -0.999998, and the order inside the window is shuffled
differently.

    frame A  -0.75625
    frame B  -0.75625
    bit-equal: True
    closed form s[2] + (s[3] - s[2]) * 0.9500000000000002 = -0.75625  equal: True

**What that costs: coarseness.** Two neighbouring windows usually have the
same 3rd and 4th smallest returns, so the column plateaus.

| frame | distinct returns per window (min / median) | distinct column values |
|---|---|---|
| walk | 60 / 60 | 149 of 1,440 bars |
| tick-rounded | 59 / 60 | 149 of 1,440 bars |
| two-point | 5 / 6 | **5** of 1,440 bars |

On the two-point frame the five values are
-0.010000000000000231 (21 bars), -0.010000000000000125 (32),
-0.01000000000000012 (**1,305**), -0.010000000000000014 (62) and
-0.010000000000000009 (20) -- a spread of 2.220e-16, 2.220e-14 relative.
Numerically that column is a constant, and §D2 is where it matters.

## A5 — the readings the issue's line leaves open

All on the walk, all against the module at its default.

| # | reading | spearman | max \|diff\| | decision |
|---|---|---|---|---|
| 1 | LOG returns instead of simple | 1.000000 | 5.446e-04 | SIMPLE, the prototype's `ret`. A quantile commutes with an increasing transform, so a rank miner cannot see the choice; a threshold rule can. |
| 2 | `interpolation="lower"` (take `s[2]`) | 0.891866 | 1.104e-02 | `linear`, pandas' and numpy's default and so the source's. |
| 2 | `"higher"` / `"nearest"` (both `s[3]`) | 0.998307 | 5.808e-04 | ditto |
| 2 | `"midpoint"` | 0.965027 | 5.227e-03 | ditto |
| 3 | 60 CLOSES (59 returns) | 0.983016 | 9.362e-03 | 60 RETURNS, 61 closes, first value at bar 60 (the other reading fires at bar 59). |
| 4 | `-quantile`, the usual VaR sign | -1.000000 | — | the QUANTILE's own sign, so a worse tail is a SMALLER number. |
| 5 | `q = 0.01` (reads `s[0]`/`s[1]`) | 0.662418 | 1.80e-02 | `q = 0.05`, the issue's. |
| 5 | `q = 0.10` (`s[5]`/`s[6]`) | 0.673904 | 1.92e-02 | ditto |
| 5 | `q = 0.25` (`s[14]`/`s[15]`) | 0.442682 | 2.87e-02 | ditto |
| 5 | `q = 0.50` (`s[29]`/`s[30]`) | 0.291534 | 3.69e-02 | ditto |
| 6 | `Series.quantile` instead of `rolling.quantile` | 1.000000 | ≤ 1 ulp | the ROLLING spelling, which is the prototype's. §A2/§A3. |

`q` is a module constant and not an argument, for the reason `ts_imq_20`
gives: the column NAME carries the `05`, so a second argument could not
reach the name without renaming the column for every caller.

## A6 — the screen prototype

`ret(c).rolling(60).quantile(0.05)`, retyped (the owner's tree is
gitignored, so it is copied rather than imported).

Bit-equal on **1,440 of 1,440** bars of each of the nine frames, masks
identical, max |difference| 0.0 everywhere.

Where the two part company — only on the guards, at bar 200 of a 400-bar
walk whose unspoiled column fires on 340 bars:

| input | module fires | prototype fires |
|---|---|---|
| `close[200] = NaN` | 279 | **279** (pandas propagates a NaN; no guard needed) |
| `close[200] = inf` | 279 | 280 |
| `close[200] = 0` | 279 | 280 |
| `close[200] = 1e-310` (subnormal) | 279 | 280 |
| `close[200] = -100` | 279 | **340** (returns computed across a sign change) |
| `close[200] = 1e-300`, `close[201] = 1e50` (ratio overflows) | 280 | 280 |
| a FLAT 300-bar frame | 240 | 240 (both read 0.0 — there is no floor here) |

Because Gate E's statistic is a Spearman over the bars where both fire, the
screen's figures are expected to carry over; the launcher's run on THIS
module is still the number that decides ship or revert.

---

## B — causality

The sweep replaces every close from bar J on with another frame's and
checks that no bar before J moved. 35 offsets, `range(120, 1500, 40)`,
past the 60-bar warm-up.

| frame | leaks |
|---|---|
| walk | **0 of 35** |
| tick-rounded | **0 of 35** |
| heavy-tailed | **0 of 35** |
| walk at `length` 2 / 5 / 250 | **0 / 0 / 0 of 35** |

### The mutants

| mutant | what it breaks | walk | tick-rounded | heavy-tailed |
|---|---|---|---|---|
| `back_date_two` | `.shift(-2)` on the output | 35 | **9** | 34 |
| `back_date_full` | `.shift(-(length-1))` | 35 | 35 | 35 |
| `forward_return` | `px.shift(-1) / px` | 34 | **6** | 34 |
| `centered_window` | `rolling(..., center=True)` | 35 | 35 | 35 |
| `rolled_window` | `r.shift(-(length//2))` before rolling | 35 | 35 | 35 |

All five are LIVE on all three frames (the mutant's column differs from the
module's).

⚠ **The two low counts are a finding, not a weak mutant.** The sweep can
only see a mutant that changes a bar before J, and this column changes only
when the window's 3rd or 4th SMALLEST return changes. On a tick-rounded
frame, splicing a different walk in at J often leaves that pair alone. Gate
B's sweep is therefore weaker here than on the fork's other return
statistics, and the test module records the counts as bands.

### The sixth mutant, which the sweep cannot catch at all

`FORWARD_MASK` shifts the NaN mask's own index by one bar:
`r.where(np.isfinite(r))` becomes
`r.where(np.isfinite(r).shift(-1, fill_value=True))`. Bar T's mask would
then read whether bar T+1's return is finite — a real look-ahead.

On a clean frame every return but the first is finite, so the shifted mask
admits exactly the same bars and the mutant's column is **bit-identical**
to the real one: not merely invisible to the sweep but DEAD. Measured on
all three frames: identical column, 0 of 35 caught.

What it can move is derived rather than guessed. A bad close at J spoils
the returns at J and J+1, so the shifted mask drops the return at J-1; the
window ending at **J-1** is the only one before J that holds that return
without also holding J. A frame with a NaN close at every offset (12
offsets, 120 bars apart, so each empties its 61 windows and the frame still
fires on 709 of 1,500 bars) gives it that:

    the real module leaks   0 of 12
    the mutant is caught   12 of 12
    at offset 240 the bar it moves is [239]   (derived: J - 1)

---

## C — reachability

Nine 1,500-bar frames, `length` 60, so 1,440 fired bars each.

| frame | fires | distinct | min | median | max | share < 0 |
|---|---|---|---|---|---|---|
| walk | 1440/1500 | 149 | -0.032628 | -0.023078 | -0.015538 | 1.000 |
| tick-rounded | 1440/1500 | 149 | -0.032647 | -0.023061 | -0.015593 | 1.000 |
| ar1+ | 1440/1500 | 170 | -0.041803 | -0.029183 | -0.013997 | 1.000 |
| ar1- | 1440/1500 | 139 | -0.035016 | -0.028146 | -0.018892 | 1.000 |
| heavy-tailed | 1440/1500 | 152 | -0.074878 | -0.027296 | -0.010568 | 1.000 |
| right-skewed | 1440/1500 | 150 | -0.009901 | -0.009420 | -0.008346 | 1.000 |
| left-skewed | 1440/1500 | 143 | -0.034731 | -0.017825 | -0.008641 | 1.000 |
| two-point | 1440/1500 | **5** | -0.010000 | -0.010000 | -0.010000 | 1.000 |
| trending | 1440/1500 | 149 | -0.018358 | -0.011230 | **-0.005264** | 1.000 |

Degenerate frames, all of which are legitimate readings here:

| frame | fires | distinct | range |
|---|---|---|---|
| flat (300 identical closes) | 240/300 | 1 | **0.0** |
| 1%-a-bar ladder | 240/300 | 1 | **+0.009999999999999787** |
| quiet (returns 1e-6) | 540/600 | 48 | [-2.298e-06, -1.124e-06] |

**The bounds.** Every close is finite, positive and normal by the time the
ratio is taken, so every return is at least -1 and so is any blend of two
of them. The lowest value over the nine frames is -0.074878; a frame of
exactly -50% bars reads **-0.5 bit for bit** (`1 + r` is a power of two
there). The bound is **CLOSED** at -1, not open, because a ratio can
underflow — §G2b. There is no upper bound: the ladder's
+0.009999999999999787 is the witness, and it means "95% of the last 60 bars
were up".

⚠ **Real-data reachability is owed** with the Gate E run — these counts are
synthetic.

---

## D — scale-freedom

### D1 — x8 and x64 are bit-identical BY CONSTRUCTION

`8a / 8b` is the same double as `a / b`, so the window's values cannot move
at all, nor their sort order, nor the blend.

All nine frames: **1,440 of 1,440** fired bars bit-equal at x8 AND at x64,
masks identical.
On the walk at `length` 2 / 5 / 20 / 250: 1,498 / 1,495 / 1,480 / 1,250,
all bit-equal.
At price levels 1e-6, 1e+6 and 1e+100 — all three swept by the script's §D
(`docs/measure_ts_q05_60.py`, `for price in (1e-6, 1e6, 1e100)`), and
1e+100 pinned again by
`tests/test_ts_q05_60.py::test_gate_d_scale_x8_at_extreme_price_levels`:
1,440 of 1,440, all bit-equal.

### D2 — x10 / x3.7 / x0.1 / x1.0000001 are a tolerance

A factor that is not a power of two perturbs the returns in their last
bits, which can swap two nearly equal order statistics. Masks match
exactly in all 16 cases.

| frame | factor | bit-equal | max \|diff\| | max rel | spearman |
|---|---|---|---|---|---|
| walk | 10.0 | 417/1440 | 2.220e-16 | 1.336e-14 | 1.000000 |
| walk | 3.7 | 743/1440 | 2.082e-16 | 1.030e-14 | 1.000000 |
| walk | 0.1 | 486/1440 | 1.110e-16 | 6.810e-15 | 1.000000 |
| walk | 1.0000001 | 368/1440 | 2.186e-16 | 9.327e-15 | 1.000000 |
| tick-rounded | 10.0 | 340/1440 | 2.220e-16 | 1.131e-14 | 1.000000 |
| tick-rounded | 3.7 | 478/1440 | 1.110e-16 | 6.346e-15 | 1.000000 |
| tick-rounded | 0.1 | 536/1440 | 1.110e-16 | 6.116e-15 | 1.000000 |
| tick-rounded | 1.0000001 | 322/1440 | 2.186e-16 | 9.716e-15 | 1.000000 |
| heavy-tailed | 10.0 | 459/1440 | 2.082e-16 | 9.356e-15 | 1.000000 |
| heavy-tailed | 3.7 | 538/1440 | 2.186e-16 | 1.037e-14 | 1.000000 |
| heavy-tailed | 0.1 | 376/1440 | 2.151e-16 | 9.520e-15 | 1.000000 |
| heavy-tailed | 1.0000001 | 275/1440 | 2.082e-16 | 1.051e-14 | 1.000000 |
| **two-point** | 10.0 | 974/1440 | 1.110e-16 | 1.110e-14 | **0.335248** |
| **two-point** | 3.7 | 1138/1440 | 1.110e-16 | 1.110e-14 | **0.227171** |
| **two-point** | 0.1 | 935/1440 | 1.110e-16 | 1.110e-14 | **0.040140** |
| **two-point** | 1.0000001 | 1150/1440 | 1.110e-16 | 1.110e-14 | **0.334111** |

⚠ **The two-point Spearman is rounding, not a scale failure.** On that
frame the column's 1,440 bars hold 5 distinct doubles spanning 2.220e-16
(§A4), so a rank correlation on it ranks noise. The reading that survives
is the relative difference, which is 1.110e-14 there — the same order as
everywhere else. `tests/test_ts_q05_60.py` asserts masks and relative
difference on that frame and Spearman on the other three.

### D3 — a monotone transform, which is stronger than a rescale

`price ** 2` is not a rescale at all: it doubles every log return. But a
quantile is equivariant under any INCREASING transform of the return, so
the ranks survive anyway.

| transform | spearman | max \|diff\| |
|---|---|---|
| `price ** 2` | 1.000000 | 0.031563 |
| `price ** 0.5` | 1.000000 | 0.016179 |

---

## G — the guards

### G1 — a bad close empties its own windows and nothing earlier

Six bad values (NaN, inf, -inf, 0, -100, 1e-310) at each of five positions
(0, 1, 60, 200, 399) of a 400-bar walk — 30 pairs.

| position | windows emptied | bars moved BEFORE the bad bar |
|---|---|---|
| 0 | 1 | **0** |
| 1 | 2 | **0** |
| 60 | 61 | **0** |
| 200 | 61 (bars 200..260) | **0** |
| 399 | 1 | **0** |

Identical for all six values. A bad close spoils TWO returns — its own and
the next bar's — so it empties the `length + 1` = 61 windows it sits in.

### G2 — an overflowing ratio

`close[200] = 1e-300`, `close[201] = 1e50`: the ratio is 1e+350, so an
infinite return. Both closes are themselves normal and positive, so only
ONE return is spoiled: **60** windows emptied, bars 201..260.

### G2b — the mirror case: a ratio that UNDERFLOWS, and the closed bound

`close[200] = 1e308`, `close[201] = 1e-300`. Both are finite, positive and
normal (1e-300 is well above `tiny` = 2.225e-308), so neither is touched by
the close guard — but the ratio 1e-608 **flushes to 0.0**, so the return is
**exactly -1.0**.

    the ratio 0.0, so the return -1.0
    finite: True   >  -1: False   == -1: True
    the module fires 340 of 400; unspiked minimum -0.032628306936088716, spiked minimum -0.032628306936088716
    the OTHER perturbation this frame makes: the return at 200 is 9.521e+305, finite and kept (the window maximum)
    bars reading exactly -1.0: 0

⚠ **That frame perturbs TWO returns, not one.** `close[200] = 1e308` on a
walk priced near 100 makes the return at bar 200 about **+9.521e+305** —
finite, normal, kept, and the window MAXIMUM of the 60 windows ending at
bars 200..259 — and the ratio at bar 201 underflow to exactly -1.0. The 60
bars that move are the windows holding the **-1.0**; bar 200, which holds
the +9.5e305 but not the -1.0, does not move, and that is a property of
THIS frame rather than of the arithmetic: it holds because this walk's own
return at bar 200 does not rank among its window's four smallest. The
asserted range in the test is measured on this frame at its lower end and
structural at its upper end (`201 + length - 1 = 260`).

That return is finite, so `r.where(np.isfinite(r))` KEEPS it — and should:
the true return is -1 + 1e-608 and -1.0 is its correctly rounded value, not
a failure. This is why the column's lower bound is **[-1, +inf)** and not
`(-1, +inf)`, and the docstring and `Returns:` say so.

Reaching -1.0 in the COLUMN takes FOUR such returns in one window, because
`q = 0.05` reads the 3rd and 4th smallest. ONE of them is the window's own
minimum `s[0]`, so it never reaches `s[2]`/`s[3]` and the column's floor is
untouched — unspiked and spiked minimum both -0.032628306936088716, 0 bars
at -1.0. It does MOVE the
column, by the same mechanism: a -1.0 at `s[0]` demotes every ordinary
return by one rank, so the window reads the 2nd and 3rd smallest ordinary
returns where it used to read the 3rd and 4th.

    bars it MOVES: 60 ([201]..[260]), none of them to -1.0

A 90-bar frame cycling
`[1e308, 1e-300, 1e8]` reaches the bound while keeping every close normal and
every other ratio finite (1e-300 → 1e8 is 1e+308, 1e8 → 1e308 is 1e+300):

    30 returns of exactly -1.0, 89 finite of 89
    the column fires 30 and its minimum is -1.0  (== -1.0: True)

⚠ This was found by the round-1 review, not by the author: the module
comment previously called overflow "the one float error the ratio can still
raise" and three documents stated an OPEN bound. Both are corrected, and
`tests/test_ts_q05_60.py::
test_the_bound_is_CLOSED_because_a_price_ratio_can_underflow` pins the
return, the one-underflow case and the four-underflow case.

### G3 — there is no accumulator, so one huge return stays local

The spike changes TWO returns, at bars 200 and 201, so the windows HOLDING
a spiked return are the **61** ending at bars 200..260. The slice the
script checks is wider on purpose — bars 141..262, **122** bars — so that
it brackets those 61 on both sides.

| spike at bar 200 | bars 141..262 that fire | later bars bit-equal to the unspiked frame |
|---|---|---|
| x1e+10 | 122/122 | 137/137 |
| x1e+100 | 122/122 | 137/137 |
| x1e+200 | 122/122 | 137/137 |
| x1e+300 | 122/122 | 137/137 |

So all 61 windows holding a spiked return fire, at every magnitude.

This is the structural difference from `ts_kurt_60`, whose
`rolling.kurt` accumulates raw power sums online and, without its
fourth-power guard, empties the whole remainder of the frame. A quantile
sorts; an unbounded return is simply the largest order statistic and
`q = 0.05` never looks at it. **No magnitude bound is needed here, and
none is imposed.**

### G4 — and there is NO dispersion floor, which is a decision

`ts_kurt_60`, `ts_medskew_20` and `ts_above_mean_20` refuse a window whose
returns span 4096 ulps or less, because each divides by a centre or a
spread whose rounding the statistic then amplifies. This column divides by
nothing: it selects two order statistics and blends them with a fixed
weight.

| frame | fires | distinct | worst error vs the exact oracle |
|---|---|---|---|
| flat | 240 | 1 (0.0) | **0.00 ulp** |
| ladder | 240 | 1 | **0.00 ulp** |
| quiet 1e-6 | 540 | 48 | 1.00 ulp |

⚠ **The ladder is the case worth reading.** Its return is only
MATHEMATICALLY constant: float64 renders it as FOUR distinct doubles, the
smallest 0.009999999999999565. An order statistic PICKS one of them
(0.009999999999999787, on all 240 windows), so the jitter reaches the
column as a choice between four nearly equal numbers rather than as an
amplified error.

**What the siblings' floor would cost here** (window return range
<= 4096 eps = 9.095e-13):

| frame | fires | the floor would empty | smallest window return range |
|---|---|---|---|
| flat | 240 | **240** | 0.000e+00 |
| ladder | 240 | **240** | 4.441e-16 |
| quiet 1e-6 | 540 | 0 | 3.751e-06 |
| the nine ordinary frames | 1440 each | 0 | 2.000e-02 (the smallest of the nine) |

So the floor would throw away 480 correctly rounded windows and buy
nothing. It is not imposed.

---

## O — overlap

### Against the window's own statistics (six frames)

| frame | return sd | min return | mean return |
|---|---|---|---|
| walk | **-0.6538** | +0.5194 | +0.5092 |
| tick-rounded | **-0.6540** | +0.5205 | +0.5086 |
| heavy-tailed | -0.2974 | +0.5917 | +0.5375 |
| trending | **-0.6894** | +0.6491 | +0.3214 |
| ar1+ | -0.4864 | +0.7371 | +0.6691 |
| ar1- | **-0.6907** | +0.5675 | +0.3481 |

### Against the fork's own columns

Synthetic high/low = close x 1.004 / x 0.996, because these frames have
only closes.

| frame | `NATR_60` | `UI_60` | `QTL_60_0.05` | `STDEV_60/close` | `TS_KURT_60` | `TS_AC1_60` | `OSAP_RETSKEW_21` |
|---|---|---|---|---|---|---|---|
| walk | **-0.6194** | -0.3949 | +0.0345 | -0.1815 | -0.0169 | +0.0903 | +0.2145 |
| tick-rounded | **-0.6196** | -0.3980 | +0.0394 | -0.1836 | -0.0134 | +0.0902 | +0.2145 |
| heavy-tailed | **-0.7143** | -0.5365 | +0.0402 | -0.1154 | -0.0465 | -0.0765 | +0.3468 |
| trending | **-0.6721** | -0.6120 | +0.2006 | +0.2171 | +0.1094 | +0.0161 | +0.3314 |
| ar1+ | **-0.7406** | -0.5454 | +0.0268 | -0.4451 | +0.0735 | -0.2787 | +0.0360 |
| ar1- | **-0.5804** | -0.2513 | -0.0273 | -0.2795 | -0.1803 | +0.4315 | +0.1135 |

⚠ **The column is NEGATIVE VOLATILITY**, at -0.5804 .. -0.7406 against
`NATR_60` over those six frames (shallowest `ar1-`, deepest `ar1+`). A big
value means a quiet window.
The 2026-10-24 screen found the same thing on real data and on the
PROTOTYPE: `natr` was the top of the 687 comparators at |rho| **0.6455**
(n = 393,509), with `Stop_2ATR_pct` at 0.6455 and `Swing_Range_pct` at
0.5607 behind it — under the 0.76 ship line, but the highest of them. The
screen's stage-2 fork overlap (scale-free `Category` outputs at defaults,
12 frames) put it at 0.7107 vs `covariance:COV_30_1`, per-frame max median
0.6963.

It is **not** the fork's `quantile` of the price LEVEL, which is the same
pandas machinery one step earlier: -0.0273 .. +0.2006.

⚠ The figures in this section are SYNTHETIC apart from the screen's, and
the screen's are the prototype's. Gate E's 687 comparators are the
engine's and hold no pandas_ta port, so the `NATR_60` / `UI_60` pairs above
are the only in-fork measurement that exists; the engine's own `natr` IS in
the comparator set, which is why the screen's 0.6455 is the number that
matters for the band.

---

## S — the statistic itself

20,000 INDEPENDENT windows of 60 draws, so the figures are not an artefact
of overlapping windows:

| law | mean | sd | range |
|---|---|---|---|
| gaussian | **-1.5664** | 0.2555 | [-2.872, -0.602] |
| student-t(2) | -2.8003 | 0.9387 | [-13.602, -0.742] |
| exponential - 1 | -0.9329 | 0.0336 | [-0.997, -0.714] |

The gaussian distribution's own 5% point is -1.6449: the estimator reads
the 3rd and 4th of 60 draws, so it sits inside the true tail. What the
law's tails change is mostly the SPREAD.

**It is a slow state.** Consecutive windows share 59 of their 60 returns.

| lag | 1 | 5 | 30 | 60 | 120 |
|---|---|---|---|---|---|
| autocorrelation | **0.9672** | 0.8473 | 0.3287 | **-0.3241** | -0.1246 |

The sign flip at lag 60 is structural: the window has moved past the bars
that set the old reading. A -20% bar planted at bar 700 moves bars
**700..759** and nothing else — exactly `length` bars.

---

## Z — cost

400,000 bars, best of three, `tracemalloc` peak:

| `length` | time | traced peak |
|---|---|---|
| 5 | 67.3 ms | **19.2 MB** |
| 60 | 115.6 ms | **19.2 MB** |
| 250 | 148.8 ms | **19.2 MB** |

Nothing allocated grows with `length`; the TIME does, because pandas'
`roll_quantile` is a skiplist, O(n log length). ⚠ Wall-clock moves between
runs and machines — this file is the one copy of these numbers and the
PEAK is the claim.

---

## E — Gate E

**Gate E: pending, run by issue-solver after this session.**

`docs/gate_e_ledger.csv` therefore has no row for `ts_q05_60`, and
`tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
fails locally; CI sets `GATE_E_PENDING_OK=1` and turns it into a skip whose
reason starts "Gate E owed".
`tests/test_ts_q05_60.py::test_the_gate_e_row_is_owed` asserts the row is
ABSENT, so it fails the moment the receipt session records it — which is
that session's cue to replace it with a test pinning the row's IDENTITY
(its `run`, module and column), the way #99 and #100 did.

What the 2026-10-24 screen measured, on the PROTOTYPE and not on this
module: max |rho| **0.6455** vs `natr` (compute_all, n = 393,509), top-5
per-frame max median 0.6131 → **SHIP**; run `screen_20261024`, 89
ALTPORT-1 frames, 398,849 bars, 329 + 358 comparators, canary bit-equal.
This port is bit-equal to that prototype on 1,440 of 1,440 bars of each of
nine frames (§A6), so the figure is expected to carry over — but the
launcher's run on THIS module is the number that decides ship or revert.

Owed with that run: Gate C's real-data counts.

---

## F — suites

* `python -m pytest tests/test_ts_q05_60.py -q` → **213 passed**.
* `python docs/measure_ts_q05_60_cpu.py` → the same **213 passed** with
  `NPY_DISABLE_CPU_FEATURES="AVX512F AVX512_SKX AVX2 FMA3"`, the script
  asserting that the dispatch took and printing the features that survive
  (`SSSE3 SSE41 POPCNT SSE42 AVX F16C AVX512CD AVX512_CLX AVX512_CNL
  AVX512_ICL` on this machine).
* Full suite `python -m pytest -q`: **3 failed, 8,125 passed, 85 skipped**.
  ⚠ This line is written LAST, after every other file in the branch was
  final, and the suite is re-run once more afterwards to confirm the write
  itself did not move it — because it once did: quoting a review verdict
  into `docs/reviews/` tripped a prose guard and turned a recorded 3 into
  a 4 (see that folder's round-3 section). The three are CLAUDE.md's known
  `test_pine_coverage_csv.py::test_audited_rows_carry_their_evidence`
  break, `test_altrepo_talib_csv.py::
  test_regenerating_reproduces_the_committed_rows` (needs the sibling
  `../AlternativeRepos` checkout; CI deselects it by name), and the owed
  Gate E row, which reports `['arch_lm', 'diff2_acf1', 'edge',
  'firstzero_ac', 'halflife', 'lumpiness', 'mtd_ret', 'ts_q05_60']` — the
  seven already owed on this branch's base, plus this port.

⚠ One pre-existing interaction, recorded and not fixed (it is outside this
issue's scope and was already recorded by #100): `pandas_ta/core.py:453`
hands out the live `Category[name]` list and `core.py:692` removes names
from it, so running `tests/test_wiring_accessors.py` before
`tests/test_altport2_ports.py` in one process fails the pinned
`CATEGORY_TOTAL` (337 against 340, measured this session). Alphabetical
collection — which is what the full suite does — hides it.
