# TF-IQR-RET-60 — `tf_iqr_ret_60`, measured

PandasTa issue **#117** (parent: the library catalog screen, round 2, of
2026-10-24). Module `pandas_ta/statistics/tf_iqr_ret_60.py`, column
**`TFIQRRET_60`**. Tests `tests/test_tf_iqr_ret_60.py` (273 collected: 272
pass, 1 skip — see §F1 for the skip).

Every number in §A1–§A6, §B, §C, §D, §G, §O, §S and §Z is printed by
`python docs/measure_tf_iqr_ret_60.py` on this worktree (pandas 2.3.3,
numpy 1.26.4), section by section. Those headings take their letters from
the script, with one join: the script's section **M** (the mutant table) is
printed here under §B, since it is Gate B's evidence. §E and §F are
headings of this file and not of the script. What does NOT come from the
script, and is marked where it appears:

* **§E**, which is the launcher's Gate E run `is117-tf_iqr_ret_60-7149d122`
  of 2026-11-16, recorded into `docs/gate_e_ledger.csv` and read out of
  that run's `overlap_max.csv`, `perframe.csv`, `top25.csv`,
  `degenerate.csv` and `meta.json`;
* **§E0**, the 2026-10-24 screen's figures, measured on the PROTOTYPE and
  quoted from the issue;
* **§F**, which is pytest's own output.

```
r         = close / close.shift(1) - 1
s         = the window's `length` returns, SORTED
i(q)      = q * (length - 1);  k = floor(i);  f = i - k
Q(q)      = s[k] + (s[k + 1] - s[k]) * f
TFIQRRET  = Q(0.75) - Q(0.25)
```

At `length` 60: `i(0.75) = 44.25` and `i(0.25) = 14.75`, so

```
TFIQRRET_60 = (s[44] + 0.25*(s[45] - s[44])) - (s[14] + 0.75*(s[15] - s[14]))
```

— ranks **15, 16, 45 and 46** of the window's 60 returns, counting up from
the smallest, and nothing else.

**Source.** TSFEL (BSD-3-Clause), `features.py` `interq_range`:
`np.percentile(signal, 75) - np.percentile(signal, 25)`, as issue #117
states the formula — `q75 - q25` on 60 daily returns. The screen prototype
is `docs/issues/screen/ind_screen_r2.py` candidate `tf_iqr_ret_60`,
`ret(c).rolling(60).quantile(0.75) - ret(c).rolling(60).quantile(0.25)`
with `ret(c) = c / c.shift(1) - 1`.
⚠ **TSFEL is not installed in this worktree and web access is
unavailable.** It is an ATTRIBUTION, not an oracle;
`tests/test_tf_iqr_ret_60.py::test_the_source_library_is_not_installed_here`
records that. What Gate A checks is the published definition of
`interq_range` plus the issue's own line. Anything TSFEL does that the line
does not say — its NaN handling, whether it has its own windowing — is
unverified here.
⚠ And TSFEL applies `interq_range` to the **signal**; the 60 and the daily
**returns** are the screen's framing. That is not a detail: the same
statistic on the price LEVEL is a different column (Spearman 0.0620 on a
walk, §A5) and is not scale-free at all.

---

## Verdict

| Gate | Result |
|---|---|
| A Correctness | **PASS.** BIT-equal to an independent retyping of pandas' own `roll_quantile` spelling on 1,440 of 1,440 bars of each of **ten** frames and at `length` 2, 5, 20, 21 and 250; BIT-equal to the source's own spelling (`np.percentile(w,75) - np.percentile(w,25)`) on the same 14,400 bars, per quantile and not by cancellation; BIT-equal to an EXACT rational oracle on all ten frames at 0.00 ulp. |
| B Causality | **PASS.** 0 of 35 offsets leak on three frames and at `length` 2/5/250; prefix truncation clean at all 35. Six mutants: five live and caught 24–35 of 35, the sixth dead on a clean frame and caught 12 of 12 on a designed one, moving exactly bar J−1. |
| C Reachability | **PASS.** Real data (the Gate E run, §E): fires **393,509** of 398,849 pooled bars on the 89 ALTPORT-1 frames, of which 393,370 are non-zero. Synthetic: fires 1,440 of 1,500 on each of ten frames, 5–896 distinct values, non-negative on every fired bar. |
| D Scale-free | **PASS.** x8/x64 bit-identical on 1,440 of 1,440 of each of ten frames, at `length` 2/5/20/250 and at price 1e-6/1e+6/1e+100. x10/x3.7/x0.1/x1.0000001: masks identical, max relative difference 2.672e-14. A level SHIFT is **not** invariant (every fired bar moves), so the bit-identity is not vacuous. `0 < fires < n` and >1 distinct value on every frame. |
| E Attribution | **PASS — SHIP.** Run `is117-tf_iqr_ret_60-7149d122`, measured 2026-11-16, in `docs/gate_e_ledger.csv`: `TFIQRRET_60` max \|ρ\| **0.6730** vs `natr` (compute_all, n = 393,509), per-frame max median **0.6565** (89 frames, 0.0% of them ≥ 0.90), 687 comparators. Under the 0.76 ship line on both limbs. ⚠ The `ts_q05_60` check of §O is **still OWED** — that run's comparators do not appear to carry it. |
| F Suites | This repo: 272 for the module, 272 again with AVX-512/AVX2/FMA3 disabled; full suite in §F. The Backtesting suite is the launcher's. |

---

## A1 — bit-equality against pandas' own spelling, retyped

`_pandas_spelling` in the measurement script sorts the window, takes the
two order statistics around `q * (n - 1)` for each quartile, blends them
`vlow + (vhigh - vlow) * frac`, and subtracts. It shares no code with the
module: a Python loop over `np.sort` against pandas' skiplist.

| frame | masks | shared | bit-equal | max \|diff\| |
|---|---|---|---|---|
| walk | True | 1440 | **1440** | 0.000e+00 |
| tick-rounded | True | 1440 | **1440** | 0.000e+00 |
| ar1+ | True | 1440 | **1440** | 0.000e+00 |
| ar1− | True | 1440 | **1440** | 0.000e+00 |
| heavy-tailed | True | 1440 | **1440** | 0.000e+00 |
| right-skewed | True | 1440 | **1440** | 0.000e+00 |
| left-skewed | True | 1440 | **1440** | 0.000e+00 |
| two-point | True | 1440 | **1440** | 0.000e+00 |
| trending | True | 1440 | **1440** | 0.000e+00 |
| vol-cycle | True | 1440 | **1440** | 0.000e+00 |

At other lengths, on the walk: `length` 2 → 1,498 of 1,498; 5 → 1,495;
20 → 1,480; 21 → 1,479; 250 → 1,250. All bit-equal, masks identical.

One `rolling` object reused for both quartiles instead of two is also
bit-equal on 1,440 of 1,440 (walk), so the module's two-object spelling —
which matches the prototype literally — is legibility and not arithmetic.

---

## A2 — against the source's own spelling

TSFEL's `interq_range` is `np.percentile(signal, 75) -
np.percentile(signal, 25)`. `_source_windowed` applies exactly that,
window by window.

| frame | masks | shared | bit-equal | max ulps | ρ |
|---|---|---|---|---|---|
| all ten frames | True | 1440 each | **1440 each** | **0.00** | 1.000000 |

That is the DIFFERENCE. The per-quantile account is below, because a
difference can agree by cancellation.

⚠ **That is not what `ts_q05_60` found**, and the difference is
instructive rather than lucky. numpy's `_lerp` evaluates
`b - (b - a) * (1 - t)` for `t >= 0.5` and `a + (b - a) * t` below it,
so at `length` 60 the two quartiles here take **different branches from
each other** (q0.75 has frac 0.25, q0.25 has frac 0.75). So the agreement
could in principle be a cancellation in the difference. It is not: the
script compares each quartile **alone** against `np.percentile` — all ten
frames, both quartiles, **28,800 of 28,800** single-quartile readings
bit-equal, plus **14,404 of 14,404** at `length` 2, 5, 20, 21 and 250 on
the walk.

Which branch numpy takes is **probed and not recalled**, over 20,000
random 60-draw windows:

| quartile | `np.percentile == a + d*f` | `== b - d*(1-f)` |
|---|---|---|
| q0.25 (frac 0.75) | 19,984 / 20,000 | **20,000 / 20,000** |
| q0.75 (frac 0.25) | **20,000 / 20,000** | 19,983 / 20,000 |

So `t = frac` and the `b - d*(1-t)` branch is the one taken at
`t >= 0.5` — at **q0.25** here, and not at q0.75, whose spelling is
already pandas'. The q0.25 column is therefore the only non-trivial half
of this section, and the two ALGEBRAIC FORMS genuinely CAN differ: they do
on 16 of those 20,000 random windows at q0.25 and on 17 at q0.75 (the
19,984 and 19,983 of the table, read the other way round).
⚠ Those 17 are NOT pandas/numpy disagreements. At q0.75 numpy takes the
form that already IS pandas', so the pandas-versus-numpy disagreement
count over the same 20,000 windows is **16 at q0.25 and 0 at q0.75** — the
17 is what pandas would have differed by had it taken numpy's other
branch there, and it takes neither.

⚠ **So A2's zero is a property of these frames, not a theorem.** Asked
directly — on the windows this column actually sees, do the two spellings
differ? — the answer is **0 of 1,440 windows on each of the ten frames**,
at both quartiles. Where they did differ, pandas and numpy would differ
too. That is why the module's comment says "the same double on every bar
measured" rather than "the same arithmetic", and why nothing here claims
the equality holds for every input.

`np.percentile`, `np.quantile` and `pandas.Series.quantile` are the same
double on a 60-draw window (`0.01409881822747289`), so the oracle does not
depend on which spelling the source is read as.

---

## A3 — against an exact rational oracle

Every return is a double, so a rational. `_exact` sorts exactly, does both
blends and the subtraction in `fractions.Fraction`, and rounds **once** at
the end. The module rounds seven times (two subtractions inside the
blends, two multiplications, two additions, the final difference).

| frame | shared | bit-equal | max ulp | mean ulp | numpy max | numpy mean |
|---|---|---|---|---|---|---|
| all ten frames | 1440 each | **1440 each** | **0.00** | 0.0000 | 0.00 | 0.0000 |

So seven roundings land on the correctly rounded answer on every one of
14,400 bars. The reason is that both quantiles are exact binary fractions:
`Fraction(0.25) == 1/4` and `Fraction(0.75) == 3/4`, where `ts_q05_60`'s
`Fraction(0.05)` is `3602879701896397/72057594037927936` and its module is
one ulp out (that figure is `docs/TsQ0560Measured.md` §A3's, not
re-measured here). That is a property of this `q`, not a general claim
about `rolling.quantile` arithmetic.

---

## A4 — the column reads four returns, and that is all

```
length    0.75*(n-1)          0.25*(n-1)
     2    0.75  -> s[0]  f .75    0.25  -> s[0]  f .25
     5    3.0   -> s[3]  f 0.0    1.0   -> s[1]  f 0.0
    20   14.25  -> s[14] f .25    4.75  -> s[4]  f .75
    21   15.0   -> s[15] f 0.0    5.0   -> s[5]  f 0.0
    60   44.25  -> s[44] f .25   14.75  -> s[14] f .75
   250  186.75  -> s[186] f .75  62.25  -> s[62] f .25
```

Shown rather than asserted: on a 60-draw window, pushing the other 56
returns arbitrarily far away while keeping every rank leaves the value
**bit-identical** and equal to the closed form — checked through the pandas
blend and through `Series.quantile`, both reading
`0.026245555145105313` before and after.

Two consequences:

* it is a **middle** reading. The largest and smallest 14 returns of every
  window are invisible to it; a crash day enters only by demoting the
  ordinary returns one rank. That is the opposite trade from `ts_q05_60`,
  which reads the 3rd and 4th smallest and nothing else.
* its **resolution is high**, not coarse. Reading four order statistics
  rather than two gives 714–896 distinct values over the 1,440 fired bars
  of the nine frames other than `two-point`, against `TS_Q05_60`'s 149 on
  the same walk builder and seed (that figure is `docs/TsQ0560Measured.md`'s,
  not re-measured here).

| frame | fired | distinct | min | max |
|---|---|---|---|---|
| walk | 1440 | 735 | 1.178554e-02 | 3.083563e-02 |
| tick-rounded | 1440 | 738 | 1.174619e-02 | 3.077617e-02 |
| ar1+ | 1440 | 825 | 1.337159e-02 | 3.521395e-02 |
| ar1− | 1440 | 714 | 1.357507e-02 | 3.137763e-02 |
| heavy-tailed | 1440 | 729 | 9.612152e-03 | 2.269895e-02 |
| right-skewed | 1440 | 721 | 6.945260e-03 | 1.779546e-02 |
| left-skewed | 1440 | 721 | 6.945260e-03 | 1.779546e-02 |
| two-point | 1440 | **5** | 1.9999999999999907e-02 | 2.000000000000013e-02 |
| trending | 1440 | 768 | 7.847763e-03 | 1.919336e-02 |
| vol-cycle | 1440 | 896 | 4.374652e-03 | 4.917498e-02 |

⚠ The two-point frame is the exception and is the Gate D tie frame: the
window holds 2 distinct returns, so the column holds **5** doubles
spanning **2.220e-16** (1.110e-14 relative) around 0.02 — numerically a
constant. The test pins that as a band (2–12 doubles, relative span
< 1e-12) because the count of last-bit-distinct values moves with the CPU.

⚠ `right-skewed` and `left-skewed` read the same min / median / max to
seven figures. That is the sign-blindness of §C3, not a copy-paste: the
returns the two frames are BUILT from are exact negations of each other
(same seed, `sigma*(E - 1)` against `sigma*(1 - E)`). Seven figures and
not bit-equality because the price path is rebuilt by `cumprod` and the
module then re-derives the returns from it, which re-rounds them — §C3
measures that gap at 5.829e-16.

---

## A5 — the readings the source's line leaves open

Measured on the walk.

| reading | Spearman vs the shipped column | max \|diff\| | verdict |
|---|---|---|---|
| LOG returns instead of simple | 0.999890 | 1.067e-04 | rejected: the prototype's `ret` is simple |
| `interpolation="lower"` | 0.978853 | 2.720e-03 | rejected: not the default, not the source's |
| `interpolation="higher"` | 0.984061 | 3.372e-03 | rejected |
| `interpolation="nearest"` | 0.994839 | 2.058e-03 | rejected |
| `interpolation="midpoint"` | 0.995164 | 2.058e-03 | rejected |
| 60 CLOSES (59 returns) | 0.983863 | 2.878e-03 | rejected: the off-by-one, first bar 59 not 60 |
| the price LEVEL's IQR | 0.061962 | — | rejected: a support band, and not scale-free |
| the price level's IQR / close | 0.095948 | — | rejected |
| q0.10..q0.90 | 0.487714 | 2.843e-02 | a different column |
| q0.05..q0.95 | 0.156273 | 4.654e-02 | a different column |
| q0.20..q0.80 | 0.820524 | 1.248e-02 | a different column |
| q0.30..q0.70 | 0.850732 | 1.525e-02 | a different column |
| q0.40..q0.60 | 0.558305 | 2.356e-02 | a different column |

⚠ The LOG-return row is the one worth reading, because it is where this
column differs in KIND from `ts_q05_60`. A quantile commutes with a
monotone transform, so `ts_q05_60`'s ranks are identical under a log
return (Spearman exactly 1.000000 there). A **difference** of two
quantiles does not commute, so here the ranks move: 0.999890, not 1. The
simple return is the prototype's and the shipped choice; a consumer
switching to log returns gets a slightly different ordering, not only
slightly different values.

`interpolation` is left unspelled in the module because the keyword has
moved between pandas versions while the default has not;
`test_the_default_interpolation_is_linear` pins that the default is what
the module means, and that the module equals the explicit `"linear"`
spelling bar for bar.

`0.25` / `0.75` are module constants and not arguments: the source names
the INTERQUARTILE range, so the two quartiles are the statistic rather
than a setting, and the column name carries neither of them — a second
argument could not reach the name without renaming the column for every
caller.

---

## A6 — the screen prototype

| frame | masks | shared | bit-equal | max \|diff\| |
|---|---|---|---|---|
| all ten frames | True | 1440 each | **1440 each** | 0.000e+00 |

So what the 2026-10-24 screen measured and what this module computes are
the same arithmetic wherever both fire. They part company only on the
guards. A 400-bar walk fires 340 bars; a bad close at bar 200:

| bad close at 200 | module fires | prototype fires | why |
|---|---|---|---|
| `inf` | 279 | 280 | one INFINITE return (`inf / c`), so the prototype loses 60 windows; the module guards the close and loses 61 |
| `0.0` | 279 | 280 | the return AFTER it overflows; same arithmetic as above |
| `1e-310` (subnormal) | 279 | 280 | same |
| `-100.0` | 279 | **340** | both returns stay finite, so the prototype loses NOTHING and quietly computes an IQR of meaningless returns |
| `NaN` | 279 | 279 | pandas propagates a NaN on its own; the guard adds nothing |

A flat frame needs no floor either: module and prototype agree on all 240
windows, both reading exactly `0.0`.

Because Gate E's statistic is a Spearman over the bars where both fire,
the screen's figures were expected to carry over, and they did: the
launcher's run on THIS module reads 0.6730 vs `natr` over 393,509 bars
(§E), the same comparator and the same figure to four places as the
prototype's (§E0).

---

## B — causality

The sweep replaces every close from bar J on with a different frame's and
asks whether any bar **before** J moved — a value change or a NaN-mask
change. 35 offsets (120, 160, … 1480), past the 60-bar warm-up.

| frame | leaked |
|---|---|
| walk | **0 of 35** |
| tick-rounded | **0 of 35** |
| heavy-tailed | **0 of 35** |

At other lengths on the walk: `length` 2 → 0 of 35 (first fired bar 2),
5 → 0 of 35 (bar 5), 250 → 0 of 35 (bar 250).

Prefix truncation — recomputing on `close[:j]` and comparing with the full
column's first `j` bars — differs on **0 of 35** prefixes. ⚠ That is
necessary and not sufficient: a prefix cannot see a BACK-DATED write,
which is what the mutants below exist for.

### The mutants

Each is the module's own source, read off disk, one line replaced, and
`exec`-d in memory. A mutant that does not CHANGE the column proves
nothing, so liveness is asserted first.

| mutant | what it does | live | caught (of 35) |
|---|---|---|---|
| `back_date_two` | `(hi - lo).shift(-2)` | yes, all 3 frames | walk 34, tick-rounded 28, heavy-tailed 31 |
| `back_date_full` | `.shift(-(length - 1))` | yes | 35 / 35 / 35 |
| `forward_return` | `px.shift(-1) / px - 1` | yes | 25 / 25 / 24 |
| `centered_window` | `center=True` on both quartiles | yes | 35 / 35 / 35 |
| `rolled_window` | the whole window shifted 30 bars forward | yes | 35 / 35 / 35 |

⚠ The counts below 35 are a finding, not a defect in the mutant. Splicing
a different frame in at J moves bar J−2 or J−1 only if it changes one of
the window's four READ ranks (§A4), and often it does not — a 60-draw
window's 15th and 45th order statistics are robust by construction.
`back_date_full` shifts by 59 bars and so always lands on a different
window; `centered_window` and `rolled_window` move the whole window by 30.
The test pins bands and not these digits, because the splice is a random
frame: `forward_return` 18–35 on each of the three frames,
`back_date_two` 26–35 / 20–35 / 24–35 per frame (walk / tick-rounded /
heavy-tailed), the other three 30–35 on each.

### The sixth mutant, which the sweep cannot catch at all

`FORWARD_MASK` replaces

```python
r = r.where(np.isfinite(r))
```

with

```python
r = r.where(np.isfinite(r).shift(-1, fill_value=True))
```

so bar T's mask reads whether bar **T+1**'s return is finite. That is a
real look-ahead. On a clean frame it is not merely invisible — it is
**DEAD**: every return but the first is finite there, so the shifted mask
admits exactly the same bars and the mutant is **bit-identical** to the
module on all three frames, leaking 0 of 35.

What it can move is derived rather than guessed. A bad close at J spoils
the returns at J and J+1, so the shifted mask drops the return at J−1; the
window ending at **J−1** is the only one before J that holds that return
without also holding J. The designed probe is a walk with a NaN close at
each of 12 offsets 120 bars apart:

* the real module fires 709 of 1,500 bars there and leaks **0 of 12**;
* the mutant is caught **12 of 12**;
* and at all twelve offsets the set of bars it moves is exactly `[J - 1]`
  — counting a changed VALUE as a move, not only a changed NaN mask.

---

## C — reachability

### C1 — real data

From the launcher's Gate E run (`non_nan`, `non_zero`, `pooled_bars` of
the ledger row, §E), on the 89 frozen ALTPORT-1 BIST daily frames:

| figure | value |
|---|---|
| pooled bars | 398,849 |
| `TFIQRRET_60` fires (`non_nan`) | **393,509** |
| of those, non-zero | **393,370** |
| not fired | 5,340 = 89 × 60 |

The 5,340 NaNs are exactly the warm-up, every frame: one bar for the
first return plus 59 for the first full window, 60 per frame on 89
frames. So the column fires wherever a 60-return window exists on real
data and nowhere else, which is also Gate D's anti-constant limb on real
prices — `0 < 393,509 < 398,849`, and 393,370 of the fired bars are not
zero, so the column is not the constant 0.0 there.

⚠ The 139 fired bars that read exactly `0.0` are real, not a defect: an
IQR of 60 returns is zero exactly when ranks 15 through 46 of the sorted
window are one and the same value (the blend reads 15/16 and 45/46, and
sortedness forces everything between them to agree), which on BIST daily
data means a stretch flat enough that the middle half of the returns is a
single number — most plainly a halted or untraded run of equal closes,
all returns 0.0 (§C2 shows the same on the flat synthetic frame). This
file does not claim which frames they fall on: the run reports the pooled
count only.

### C2 — synthetic frames

Every frame: fires 1,440 of 1,500, `0 < fires < n`, more than one distinct
value, and **non-negative on every fired bar**. The per-frame table is in
§A4.

Degenerate frames:

| frame | fired | distinct | min | max |
|---|---|---|---|---|
| flat (300 bars) | 240 | 1 | 0.0 | 0.0 |
| ladder, 1%/bar (300) | 240 | 2 | 0.0 | 5.551115123125783e-17 |
| quiet, returns 1e-6 (600) | 540 | 289 | 9.200668e-07 | 1.890070e-06 |

⚠ **The ladder's row moves between numpy dispatches**, and §F2 records it
rather than hiding it: with `AVX512F AVX512_SKX AVX2 FMA3` disabled the
ladder reads **1** distinct value, exactly `0.0`, instead of 2 values up to
5.551e-17. The dispatched step is the divide that builds the return —
`px / px.shift(1)` — not the blend above it, which is three scalar
operations per quartile. Both readings are honest; the test therefore pins
the BOUND (min and max both in `[0, 1e-15)`, at most 4 distinct values) and
not either value. ⚠ It is one of **two groups** of figures that move
between the dispatches apart from the wall-clock — the other is §D2's
**three** walk cells: ×3.7 in BOTH its relative (1.890e-14 → 1.972e-14)
and its absolute (3.331e-16 → 4.163e-16) figure, ×0.1 in its relative one
(1.923e-14 → 2.223e-14), and ×1.0000001 in its ulp figure alone
(160 → 176) — and §F2 is the single place that lists them all.

Warm-up: the first fired bar is **60** — `length` RETURNS, so `length + 1`
closes. 61 closes fire 1 bar; 60 closes return `None` (`verify_series`
refuses the input).

### C3 — the sign, the bounds, and sign-blindness

**Non-negative: a measurement, not a proof.** `q75 >= q25` holds exactly
in real arithmetic. In float the two blends could only round into each
other where ranks 15..46 collapse onto one value — and there both blends
return that value exactly, because `v + (v - v) * f` is `v`. The script
probes exactly that collapse:

* 400 windows with ranks 15..46 tied on one value and the tails pushed
  ±1 away: **0 negative**, worst value `0.0`;
* 2,000 windows rounded onto a grid ten times coarser than their own
  spread, so ties are everywhere: **0 negative**, worst value `0.0`.

**Lower bound 0, and it is reached.** A flat frame reads exactly `0.0` on
all 240 of its windows.

**No upper bound.** A 90-bar cycle of `[1e308, 1e-300, 1e8]` closes —
every close finite, positive and normal, so no guard fires — has returns
of `1e308`, and the column reads **1e+308** on all 30 of its fired bars.

**The subtraction cannot overflow**, and that is checked both ways:

* a return is `> -1` whenever both closes are positive and normal, which
  the guard enforces, so the widest span either blend can see is
  `DBL_MAX - (-1)`, which IS `DBL_MAX` (`1.7976931348623157e+308`) rather
  than `inf`. Probed at that corner: `q75 = DBL_MAX`, `q25 = -1.0`,
  `q75 - q25 = DBL_MAX`, finite.
* a frame whose largest finite return is `1.5e+308` fires 40 of 100 bars
  at a maximum of `3.75e+307` with no infinity anywhere.

**Sign-blind.** `q75(-x) = -q25(x)`, so negating every return leaves the
statistic unchanged: a crash and a melt-up of the same shape read the
**same** value. Two limbs, because the frame-level one cannot be exact — a
price path rebuilt from negated returns re-rounds them:

* a Student-t(3) frame (seed 41, not the named `heavy-tailed` builder) and
  its exact negation: identical NaN masks,
  Spearman **1.000000**, 89 of 1,440 bars bit-equal and the rest within
  **5.829e-16**;
* 300 windows of exact doubles, where no price path intervenes: **298 of
  300** bit-equal under negation, worst difference **2.220e-16**.

A direction feature this is not. Pair it with `osap_retskew_21` or
`ts_q05_60` if the sign matters.

---

## D — scale-freedom

### D1 — x8 and x64 are bit-identical BY CONSTRUCTION

`8a / 8b` is the same double as `a / b`, so a ×2^k rescale of the price
leaves every return bit-identical, and therefore the sort order and both
blends.

| | x8 | x64 |
|---|---|---|
| all ten frames | masks True, **1440 of 1440** each | masks True, **1440 of 1440** each |

At other lengths on the walk: 2 → 1,498 of 1,498; 5 → 1,495; 20 → 1,480;
250 → 1,250. At price levels 1e-6, 1e+6 and 1e+100: 1,440 of 1,440 each.

### D2 — x10 / x3.7 / x0.1 / x1.0000001 are a tolerance

A non-binary factor perturbs the returns in their last bits, which can
swap two nearly equal order statistics.

Each cell is the range over the four factors, under the DEFAULT numpy
dispatch, with the AVX-off reading in brackets where it differs. `max ulp`
is the same distance as `max |diff|`, expressed in units of the last place
of the COLUMN's own value — which is what "how far apart are these two
readings" actually means, and the reason this table does not describe the
gap as "one ulp" of anything:

| frame | max \|diff\| | max relative | max ulp | ρ |
|---|---|---|---|---|
| walk | 3.053e-16 .. 3.886e-16 **[.. 4.163e-16]** | 1.890e-14 .. 2.295e-14 **[1.972e-14 .. 2.295e-14]** | 144 .. 160 **[.. 176]** | 1.000000 |
| tick-rounded | 3.331e-16 .. 3.886e-16 | 1.891e-14 .. 2.479e-14 | 144 .. 192 | 1.000000 |
| heavy-tailed | 3.331e-16 .. 4.163e-16 | 2.004e-14 .. 2.672e-14 | 144 .. 208 | 1.000000 |
| two-point | 1.110e-16 .. 2.220e-16 | 5.551e-15 .. 1.110e-14 | 32 .. 64 | **0.3417 .. 0.7377** |

Across BOTH dispatches the bounds are max \|diff\| ≤ **4.163e-16**, max
relative ≤ **2.672e-14** and max **208 ulps**; the test asserts relative
< 1e-12, four orders of margin, and the walk's cells are the ones §F2
records as moving.

⚠ The two-point Spearman is **not** a scale failure. The column there is
5 doubles spanning 2.220e-16 (1.110e-14 relative), so a rank correlation
is reading rounding and nothing else — which is why Gate D's reading on
that frame is the relative difference and the NaN masks, which is what the
scale claim actually means. The masks match exactly on all 16 (frame,
factor) pairs.

### D3 — ⚠ a level SHIFT is NOT invariant, so the bit-identity is not vacuous

Unlike `tf_higuchi_30`, whose input is a difference of closes, this
column's input is a RATIO, so `close + k` is a different frame:

| shift | bars moved | max \|diff\| |
|---|---|---|
| +1 | **1440 of 1440** | 2.744e-04 |
| +50 | 1440 of 1440 | 9.200e-03 |
| +1000 | 1440 of 1440 | 2.747e-02 |

This is the anti-vacuity check Gate D asks for: a column hard-wired to a
constant would pass ×8 and fail here. The `0 < fires < n` limb and the
">1 distinct value" limb hold on every one of the ten frames as well.

---

## G — the guards

### G1 — a bad close empties its own windows and nothing earlier

A close that is not a finite, normal, positive float has no return to take,
so it is treated as missing. It spoils the returns at `pos` and `pos + 1`,
so it empties the `length + 1` = 61 windows that hold either — clipped at
the ends of the frame. Measured on a 400-bar walk (340 fired bars), for
each of six bad values at each of five positions, 30 pairs:

| position | windows emptied | bars moved BEFORE the bad bar |
|---|---|---|
| 0 | 1 | **0** |
| 1 | 2 | **0** |
| 60 | 61 | **0** |
| 200 | 61 | **0** |
| 399 | 1 | **0** |

Identical for `NaN`, `inf`, `-inf`, `0.0`, `-100.0` and `1e-310`. The
"0 bars moved earlier" column is the causal half of the guard's claim and
holds in all 30 pairs.

### G2 — an overflowing ratio empties 60, not 61 — and the mask line is defence in depth

`1e-300` followed by `1e50` is a ratio of `1e+350`, so the return at that
bar is infinite and the one after it is finite — ONE spoiled return, so 60
windows (340 → 280). `np.errstate(over="ignore")` is scoped to the ratio,
so nothing is raised.

⚠ **The module's `r = r.where(np.isfinite(r))` line does not do that work,
and this file says so rather than implying it does.** pandas' own
`rolling.quantile` already returns NaN for the WHOLE window on a single
infinity — at both quartiles, not only the one near the infinity:

| 60-point window | q0.75 | q0.25 |
|---|---|---|
| `1..60`, no infinity | 45.25 | 15.75 |
| one `+inf` | **nan** | **nan** |
| one `-inf` | **nan** | **nan** |
| sixteen `+inf` | **nan** | **nan** |

So a mutant with the line DELETED is bit-identical to the module:

| frame | masks equal | shared | bit-equal | max \|diff\| |
|---|---|---|---|---|
| clean walk (400) | True | 340 | **340** | 0.000e+00 |
| overflowing ratio | True | 280 | **280** | 0.000e+00 |
| 1e308 cycle (90) | True | 30 | **30** | 0.000e+00 |

The line is kept for intent and because it does not depend on a pandas
version continuing to blank such a window — not because it moves a value
today. `test_pandas_already_blanks_a_window_holding_an_infinity` and
`test_deleting_the_mask_line_changes_nothing_on_this_pandas` pin both
halves, and this is also the mechanism behind §B's sixth mutant being DEAD
on a clean frame.

### G3 — ⚠ the mirror case: a ratio that UNDERFLOWS is KEPT

`1e308` followed by `1e-300` is a ratio of `1e-608`, which flushes to
`0.0`, so the return is exactly `-1.0`. That is the correctly rounded value
of `-1 + 1e-608`, not a failure, so it is kept rather than guarded away.
numpy's underflow state is "ignore" by default, so this raises nothing
either. ⚠ This is the asymmetry a reader will question: overflow is
silenced and dropped, underflow is kept, and the reason is that one has no
value and the other has the right one.

### G4 — the overflow that is NOT reachable

See §C3: a return is `> -1` under the guard, so neither blend nor the
subtraction can reach `inf`. Probed at the `DBL_MAX` / `-1.0` corner and
on a frame whose largest return is `1.5e+308`. Stated as a probed bound
rather than "no floating-point error exists".

### G5 — and there is NO dispersion floor, which is a decision

Siblings `statistics/ts_kurt_60.py`, `ts_medskew_20.py` and
`ts_above_mean_20.py` refuse a window whose returns span 4096 ulps or
less, because each divides by a centre or a spread whose own rounding the
statistic then amplifies. **This column divides by nothing**: it selects
four order statistics, blends them with FIXED weights and subtracts, so a
window with no dispersion has a perfectly good interquartile range — zero.

Against the exact rational oracle:

| frame | fired | distinct | max ulp of error |
|---|---|---|---|
| flat | 240 | 1 (`0.0`) | **0.00** |
| ladder | 240 | 2 (`0.0`, `5.551e-17`); 1 (`0.0`) with AVX off | **0.00** both ways |
| quiet, 1e-6 returns | 540 | 289 | **0.00** |

What the siblings' ABSOLUTE floor (window return range ≤ 4096 eps =
9.095e-13) would cost here:

| frame | windows it would empty | smallest window return range |
|---|---|---|
| flat | **240 of 240** | 0.000e+00 (widest 0.000e+00) |
| ladder | **240 of 240** | 4.441e-16 (widest 6.661e-16; both 4.441e-16 with AVX off) |
| quiet | 0 of 540 | 3.751e-06 (widest 6.972e-06) |
| walk | 0 of 1440 | 4.470e-02 (widest 9.688e-02) |
| tick-rounded | 0 of 1440 | 4.460e-02 (widest 9.686e-02) |
| ar1+ | 0 of 1440 | 5.267e-02 (widest 1.110e-01) |
| ar1− | 0 of 1440 | 5.174e-02 (widest 1.080e-01) |
| heavy-tailed | 0 of 1440 | 6.913e-02 (widest 7.414e-01) |
| right-skewed | 0 of 1440 | 2.588e-02 (widest 6.821e-02) |
| left-skewed | 0 of 1440 | 2.588e-02 (widest 6.821e-02) |
| two-point | 0 of 1440 | 2.000e-02 (widest 2.000e-02) |
| trending | 0 of 1440 | 3.132e-02 (widest 6.067e-02) |
| vol-cycle | 0 of 1440 | 2.007e-02 (widest 1.944e-01) |

480 honest windows lost, 0 dishonest ones. All **ten** ordinary frames are
in the table rather than inferred from the walk: their smallest window
return ranges run 2.000e-02 (two-point) to 6.913e-02 (heavy-tailed), four
to five orders of magnitude above the 9.095e-13 floor.

⚠ The ladder is the case worth reading, because its return is only
MATHEMATICALLY constant: float64 renders `100 * 1.01**n`'s ratio as
**four** distinct doubles across the frame (0.009999999999999565 up, span
6.661e-16) under the default dispatch and **three** with AVX off (span
4.441e-16). Its 60-bar windows therefore span 4.441e-16 at the
narrowest and **6.661e-16** at the widest by default, and 4.441e-16 both
ways with AVX off — printed by `section_G` as both figures so neither can
be quoted under the other's label. So
the column reads a `5.551e-17` spread where the mathematics says 0 by
default, and exactly 0 with AVX off, because which of those doubles land
on ranks 15/16 and 45/46 changes. An order statistic PICKS one of those
doubles, so the jitter reaches the column as a choice between nearly equal
numbers rather than as an amplified error — which is the whole reason a
statistic that divides by a spread needs a floor and this one does not.

### G6 — no warning, and the input is not mutated

Under `warnings.simplefilter("error")`, a 400-bar walk carrying `inf`,
`0.0`, `-5.0` and `1e-310` closes raises nothing. The input Series is
unchanged after the call.

---

## O — overlap, on synthetic frames

⚠ **This section is not Gate E.** Gate E is 89 real BIST frames against
687 engine comparators and is in §E. This is the fork's own columns on
the ten synthetic frames of this file, which is what can be measured here.

Per-frame Spearman over the ten frames, and the pooled figure over the
concatenated bars:

| comparator | per-frame min | max | median \|ρ\| | max \|ρ\| | pooled |
|---|---|---|---|---|---|
| return sd of the same window (**not** a fork column) | −0.0609 | 0.9687 | 0.4979 | 0.9687 | 0.6866 |
| `NATR_60` | 0.0735 | 0.9511 | 0.5641 | 0.9511 | **0.7858** |
| `TS_Q05_60` | −0.9364 | 0.3075 | 0.3246 | **0.9364** | −0.6238 |
| `STDEV_60` | −0.4004 | 0.8597 | 0.1716 | 0.8597 | −0.1309 |
| `MAD_60` | −0.3985 | 0.8546 | 0.1605 | 0.8546 | −0.1327 |
| `TS_KURT_60` | −0.6762 | 0.0776 | 0.4203 | 0.6762 | −0.5789 |
| `UI_60` | −0.4672 | 0.6489 | 0.4321 | 0.6489 | 0.4819 |
| `TS_AC1_60` | −0.3153 | 0.4319 | 0.1769 | 0.4319 | 0.0228 |
| `QTL_60_0.75` | −0.4030 | 0.1507 | 0.0718 | 0.4030 | −0.3704 |
| `TFSPECENT_64` | −0.3251 | 0.1110 | 0.1351 | 0.3251 | −0.3066 |
| `TFDFA_100` | −0.1386 | 0.2655 | 0.1076 | 0.2655 | −0.0310 |
| `TFHIGUCHI_30` | −0.2176 | 0.2076 | 0.1478 | 0.2176 | 0.1362 |
| `TFCENTROID_20` | −0.2155 | 0.0520 | 0.0270 | 0.2155 | −0.0373 |
| `TS_STRIKE_20` | −0.2066 | 0.1914 | 0.1220 | 0.2066 | 0.0194 |
| `TS_IMQ_20` | −0.1967 | 0.0421 | 0.0210 | 0.1967 | −0.0346 |
| `TS_AGGAC_60_10` | −0.1231 | 0.1879 | 0.0956 | 0.1879 | 0.1273 |
| `TFZEROCROSS_20` | −0.0953 | 0.1665 | 0.1107 | 0.1665 | 0.1178 |
| `LOT_ZERORET_60` | 0.1450 | 0.1450 | 0.1450 | 0.1450 | 0.0794 |

⚠ Two readings of this table that would be wrong:

1. **`LOT_ZERORET_60`'s row is one frame, not ten.** Measured, not
   inferred: it takes **1** distinct value — exactly `0.0` — on nine of the
   ten frames, and 2 (`0.0` and `0.016666…`) on the tick-rounded one, which
   is the only frame whose returns can be exactly zero. A rank correlation
   against a constant is undefined, so pandas returns NaN with a
   `ConstantInputWarning` on those nine, and the 0.1450 is the
   tick-rounded frame alone. The pooled figure (0.0794) IS defined, because
   the concatenated series is not constant.
2. **The 0.95-ish maxima are the `vol-cycle` frame**, which is built so
   that volatility is the ONLY thing that moves. There every volatility
   measure agrees with every other: this column reads 0.9511 against
   `NATR_60`, −0.9364 against `TS_Q05_60` and 0.9687 against the window's
   own return standard deviation. That says what the frame is, not that
   the columns are the same. The frame is in the set to show the CEILING;
   the tests assert the 0.90 line on the nine ORDINARY frames and give
   `vol-cycle` its own named test.

Per-frame detail, every comparator, in the frame order walk,
tick-rounded, ar1+, ar1−, heavy-tailed, right-skewed, left-skewed,
two-point, trending, vol-cycle:

```
return sd       0.4668  0.4651  0.7550  0.6605  0.2063  0.4979  0.4979 -0.0609  0.6974  0.9687
NATR_60         0.5644  0.5638  0.3363  0.6812  0.5245  0.0735  0.5658  0.2675  0.5985  0.9511
TS_Q05_60      -0.2725 -0.2740 -0.3346 -0.3146 -0.4565  0.3075 -0.4753 -0.0017 -0.4528 -0.9364
STDEV_60        0.1163  0.1168 -0.4004  0.1349  0.1378  0.2055  0.2422  0.1331 -0.3076  0.8597
MAD_60          0.1027  0.1034 -0.3985  0.1282  0.1278  0.1838  0.2278  0.1372 -0.3069  0.8546
TS_KURT_60     -0.6758 -0.6762 -0.6373 -0.3413 -0.0071 -0.2777 -0.2777  0.0776 -0.5710 -0.4993
UI_60           0.3971  0.3968 -0.0912  0.0631  0.5781 -0.4672  0.4714  0.1507  0.5141  0.6489
TS_AC1_60      -0.1007 -0.0992  0.4319 -0.3153  0.2138  0.1333  0.1333 -0.2181  0.1400  0.2604
QTL_60_0.75    -0.0320 -0.0315 -0.4030 -0.0253  0.1507 -0.0481  0.0954  0.0245 -0.2971  0.1210
TFSPECENT_64    0.1110  0.1104 -0.3251 -0.2810 -0.1435 -0.1351 -0.1351  0.0518 -0.1212 -0.1547
TFDFA_100      -0.1024 -0.1017  0.2655 -0.1334  0.0991  0.1127  0.1127 -0.1386  0.0947  0.1011
TFHIGUCHI_30    0.1085  0.1074 -0.0289  0.2076  0.0178 -0.2036 -0.2123  0.0025  0.1871 -0.2176
TFCENTROID_20  -0.0278 -0.0275  0.0520  0.0265  0.0010 -0.0063 -0.0063 -0.0529 -0.0218 -0.2155
TS_STRIKE_20   -0.1908 -0.1923  0.1252 -0.0783  0.0866  0.1188  0.0283 -0.2066 -0.0112  0.1914
TS_IMQ_20      -0.0223 -0.0220  0.0421  0.0080  0.0063 -0.0201 -0.0201 -0.0222 -0.0154 -0.1967
TS_AGGAC_60_10   0.0951  0.0961  0.0273 -0.0345  0.0889  0.1879  0.1879 -0.0097 -0.1231  0.1395
TFZEROCROSS_20  0.1343  0.1290 -0.0953  0.1665  0.0120  0.1061  0.1061  0.1369  0.1153 -0.0667
LOT_ZERORET_60     nan  0.1450     nan     nan     nan     nan     nan     nan     nan     nan
```

Where each comparator's maximum lands, measured rather than asserted:
`vol-cycle` holds it for **9** of the 18 — the return sd (0.9687),
`NATR_60` (0.9511), `TS_Q05_60` (0.9364), `STDEV_60` (0.8597), `MAD_60`
(0.8546), `UI_60` (0.6489), `TFHIGUCHI_30` (0.2176), `TFCENTROID_20`
(0.2155) and `TS_IMQ_20` (0.1967). `ar1+` holds four
(`TS_AC1_60` 0.4319, `QTL_60_0.75`, `TFSPECENT_64`, `TFDFA_100`),
`tick-rounded` two (`TS_KURT_60` 0.6762, `LOT_ZERORET_60`), and
`two-point`, `right-skewed` and `ar1−` one each.

**What this column is.** A volatility reading, measured: positive against
`NATR_60` on all ten frames, per-frame median 0.5641. The 2026-10-24
screen found the same on real data and on the PROTOTYPE (§E0): `natr` was
its top comparator at |ρ| 0.6730 over 393,509 bars, under the 0.76 ship
line but the highest of the 687.

**What it is not.** Not the fork's `quantile` of the price LEVEL (|ρ| ≤
0.4030, median 0.0718) — a quantile of a price level is a support line.
Not the fourth moment of the same window (`TS_KURT_60`, median 0.4203),
not the ulcer index (median 0.4321), and not any of the recent `tf_*` or
`ts_*` shape statistics (median ≤ 0.1769 on every one).

### ⚠ OWED from the Gate E run — the `ts_q05_60` check

`TS_Q05_60` is the closest thing in the fork to a restatement of this
column: it reads the 5% quantile of the **same 60 returns**, where this one
reads the same window's middle spread. It is also the one overlap the
2026-10-24 screen **could not** have seen — `ts_q05_60` was merged on
2026-11-14, three weeks after that screen — so Gate E's 687 comparators
(the engine's `compute_all` ∪ the `ml_features` `1d` manifest) may not
carry it at all.

Measured here: pooled Spearman **−0.6238**, per-frame −0.9364 .. +0.3075,
median |ρ| **0.3246** — below the owner's 0.90 line on nine of ten frames,
and at −0.9364 on the `vol-cycle` frame, where every volatility measure
agrees with every other.

**The rule, so a green Gate E row cannot quietly settle this.** After the
launcher's run: check whether `ts_q05_60` (or a column equal to it) is
among that run's 687 comparators. If it is **not**, measure Spearman ρ
against `TS_Q05_60` over the same 89 ALTPORT-1 frames, read it against the
same `r3-perframe-0.90` band, and **revert `tf_iqr_ret_60` if it is**
STRUCK. `tests/test_tf_iqr_ret_60.py::
test_the_ts_q05_60_overlap_check_is_owed_from_the_gate_e_run` fails if this
block is dropped.

**What the 2026-11-16 receipt settled, and what it did not.** The run's
`top25.csv` lists the 25 strongest of the 687 comparators; its floor is
**0.2680** (`dist_from_high_20`) and no row of it names `ts_q05_60`,
`TS_Q05_60` or any `q05` spelling — grepped, not skimmed. Pooled |ρ| on
the ten synthetic frames is 0.6238, which would place such a comparator
well inside that top 25 if the engine carried it, so the comparator set
almost certainly does **not** carry it. That is an inference from an
absence, not a measurement: the run's artefacts do not list all 687 names,
and a synthetic pooled ρ is not the 89-frame one.
So the **89-frame measurement against `TS_Q05_60` is still owed to the
owner**, with the revert rule above attached. Nothing in the recorded SHIP
row speaks to it.

Against the 2026-10-24 screen's own stage-2 fork overlap (12 real frames,
scale-free `Category` outputs at defaults, quoted from the issue): max |ρ|
**0.7102** vs `covariance:COV_30_1`, per-frame max median 0.6934 — not a
restatement at the 0.90 line. That run predates `ts_q05_60`, which is the
whole reason the item above is owed.

---

## S — the statistic itself

**The level to expect**, from 20,000 INDEPENDENT windows of 60 draws
(`numpy` default_rng(101)):

| law | mean | sd | min | max |
|---|---|---|---|---|
| gaussian | **1.3187** σ | 0.1982 | 0.6520 | 2.1166 |
| student-t(2) | 1.6140 | 0.2757 | 0.7738 | 3.2551 |
| one-sided exponential | 1.0751 | 0.2044 | 0.4968 | 2.0173 |

The gaussian's own interquartile range is **1.3490** σ. The estimator
reads slightly low because it blends ranks 15/16 and 45/46 of 60 rather
than the true quartiles. What the law's tails change is the SPREAD, which
is the other side of reading order statistics.

**It is a slow state.** Two consecutive windows share 59 of their 60
returns, so on a walk:

| lag | autocorrelation |
|---|---|
| 1 | **0.9718** |
| 5 | 0.8801 |
| 30 | 0.5401 |
| 60 | 0.1849 |
| 120 | 0.1638 |

**One bar moves exactly `length` bars.** Scaling a walk from bar 700 on by
**0.5** — a power of two, so every return after 700 is the same double and
exactly ONE return changes — moves bars 700..759 and nothing else: 60
bars, first 700, last 759. It is not an event flag.

---

## Z — cost

Two `rolling.quantile` passes over an `(n,)` array, which pandas evaluates
with a skiplist, plus two vectorised passes for the returns and the mask
and one subtraction. On 400,000 bars:

| length | best of three, over three runs | traced peak |
|---|---|---|
| 5 | 124 / 150 / 180 ms | **22.4 MB** |
| 60 | 257 / 272 / 351 ms | **22.4 MB** |
| 250 | 319 / 327 / 432 ms | **22.4 MB** |

Nothing allocated grows with `length`; the TIME does, because the skiplist
is O(n log length). ⚠ **Wall-clock moves between runs and machines, and the
three columns are the demonstration**: the same three measurements on the
same machine, once on an idle box and twice with a review subagent
running, spread by 35–45% (180/124, 351/257, 432/319 between the extremes).
The ORDERING (5 < 60 < 250) and the PEAK are the claims; the milliseconds
are not, and nothing in the test module asserts them. This file keeps the
one copy of the numbers, and §F2 lists the wall-clock as the one figure
that moves for a reason unrelated to numpy's dispatch.

---

## E — Gate E

**MEASURED 2026-11-16 — SHIP.** Run `is117-tf_iqr_ret_60-7149d122`, run by
issue-solver after the porting session (the harness lives in the sibling
Backtesting repo and needs its private engine and its 827 MB BIST cache,
so the porting session could not run it) and recorded with
`python docs/gate_e_ledger.py record <run dir> --measured 2026-11-16`.

| figure | value |
|---|---|
| column | `TFIQRRET_60` |
| max \|ρ\| (pooled) | **0.6729913089712128** → **0.6730** |
| against | `natr`, the engine's `compute_all` |
| n (pooled, shared bars) | **393,509** |
| per-frame max median \|ρ\| | **0.6564801250820403** → **0.6565**, again `natr` |
| frames | **89** (ALTPORT-1, 398,849 pooled bars) |
| frames with \|ρ\| ≥ 0.90 against `natr` | **0.0%** (max over frames 0.8230, min 0.4359) |
| comparators | **687** = 329 `compute_all` + 358 `ml_features` `1d` manifest |
| degenerate comparators skipped | **1** (`squeeze_SQZ_NO`, constant) |
| `non_nan` / `non_zero` | 393,509 / 393,370 (Gate C's real limb, §C1) |
| canary | `AKBNK.IS, BIENY.IS, AGHOL.IS, SASA.IS` bit-equal |
| verdict schema | `r3-perframe-0.90` |
| verdict | **SHIP** (pooled and per-frame both under 0.76) |

The manifest limb reads the same number against a different name:
`Stop_2ATR_pct` at 0.6729913089712128 over the same 393,509 bars — the
same figure as `natr` to every digit printed, which is what a
percent-of-ATR stop distance is. The run's next comparators:

| rank | comparator | set | \|ρ\| |
|---|---|---|---|
| 1 | `natr` | compute_all | 0.6730 |
| 2 | `Stop_2ATR_pct` | manifest | 0.6730 |
| 3 | `Swing_Range_pct` | manifest | 0.5701 |
| 4 | `mad_pct` | manifest | 0.5305 |
| 5 | `BB_BWidth` | compute_all | 0.5177 |
| … | `dist_from_high_20` (25th, the floor of `top25.csv`) | compute_all | 0.2680 |

Bands (`r3-perframe-0.90`): STRUCK if pooled |ρ| ≥ 0.90 or a top-5
comparator's per-frame median ≥ 0.90 · DISCLOSE_GAP 0.80 ≤ ρ < 0.90 ·
DISCLOSE 0.76 ≤ ρ < 0.80 · SHIP < 0.76. The measured pair is 0.6730 /
0.6565, so the column is **SHIP** with 0.087 of room on the pooled limb,
and it ships.

⚠ What this run does NOT settle: the **`ts_q05_60` overlap check** of §O,
which stays owed with its revert rule — `ts_q05_60` is absent from the
run's `top25.csv` (floor 0.2680), so it is almost certainly not among the
687, and the 89-frame measurement against `TS_Q05_60` has not been made.

The ledger row (`docs/gate_e_ledger.csv`, pinned by
`tests/test_tf_iqr_ret_60.py::test_the_gate_e_row_is_recorded_and_ships`)
also carries the output fingerprint and the module sha1
`17c0f67576de5236fb491e1ca5e6c852e483a886`, so
`tests/test_gate_e_ledger.py` fails if the module's code or its output
moves after this measurement.

The re-run recipe, from `../Backtesting/Backtesting`:

```sh
python scripts/analysis/gate_e_overlap.py build --rebuild
python scripts/analysis/gate_e_overlap.py run \
    --module pandas_ta.statistics.tf_iqr_ret_60 --name tf_iqr_ret_60
```

then, in this repo:

```sh
python docs/gate_e_ledger.py record <run dir> --measured YYYY-MM-DD
```

Any re-run must be recorded again: `record` refuses a run whose
`pandas_ta_src_sha1` is not this tree's, so the row and the code cannot
drift apart silently.

### E0 — what the 2026-10-24 screen measured, on its PROTOTYPE

Quoted from issue #117; **a prototype is not a port**, and §A6 is the
evidence that this module is the same arithmetic as that prototype.

* Gate E: max |ρ| **0.6730** vs `natr` (compute_all, n = 393,509); top-5
  per-frame max median **0.6565** → **SHIP**.
* Run `screen_r2_20261024`: `gate_e_overlap.py run --module ind_screen_r2
  --fn screen`, Backtesting `main` b2d94243, 89 ALTPORT-1 frames, 398,849
  bars, 329 + 358 = 687 comparators, canary bit-equal.
* Next comparators: `natr` 0.6730, `Stop_2ATR_pct` 0.6730,
  `Swing_Range_pct` 0.5701.
* Fork overlap (stage 2, **not** Gate E: scale-free `Category` outputs at
  defaults, 12 frames): max |ρ| 0.7102 vs `covariance:COV_30_1`, per-frame
  max median 0.6934 → not a restatement at the 0.90 line.
* Pre-flight on 6 frames (`sanity_r2.csv`): prefix-causal, unchanged under
  price ×8 and volume ×8.

The 2026-11-16 run on the MODULE (§E) reproduced the first and third
bullets to the digits printed there: 0.6730 vs `natr` over the same
393,509 bars, the same 0.6565 per-frame max median, and the same first
three comparators in the same order with `Swing_Range_pct` at 0.5701.
That is a prototype and a port agreeing, which §A6 predicted from their
arithmetic being bit-equal wherever both fire; it is not a second
independent measurement of the statistic.

⚠ That run's comparator set is from 2026-10-24 and so predates every
`ts_*` and `tf_*` column §O compares against. Read out of git rather than
assumed — `git log --diff-filter=A --format="%ad %cd" --date=short --
<one module file>`, **run once per file** and with BOTH date fields shown,
because they differ on one row and because passing several paths at once
prints one line per commit in reverse-chronological order rather than one
per path, which is how an earlier draft of this table got three dates
wrong:

| column | author date | committer date |
|---|---|---|
| `tf_centroid_20` | 2026-10-30 | 2026-10-30 |
| `lot_zeroret_60` | 2026-11-02 | 2026-11-02 |
| `ts_strike_20` | **2026-11-12** | **2026-11-15** |
| `ts_kurt_60` | 2026-11-13 | 2026-11-13 |
| `ts_ac1_60` | 2026-11-13 | 2026-11-13 |
| `ts_aggac_60` | 2026-11-13 | 2026-11-13 |
| `ts_imq_20` | 2026-11-13 | 2026-11-14 |
| `ts_q05_60` | 2026-11-14 | 2026-11-14 |
| `tf_dfa_100` | 2026-11-15 | 2026-11-15 |
| `tf_spec_entropy_64` | 2026-11-15 | 2026-11-15 |
| `tf_zero_cross_20` | 2026-11-15 | 2026-11-15 |
| `tf_higuchi_30` | 2026-11-16 | 2026-11-16 |

So the range is **2026-10-30 to 2026-11-16** on either date field, and
every one is after 2026-10-24 — none of them could have been in the
screen's stage-2 fork overlap. The upstream comparators `natr`, `ui`,
`quantile`, `mad` and `stdev` date from the fork import (2026-03-16, both
fields) and so could. §O measures this module against all of them on
synthetic frames; the one with a real restatement risk is `ts_q05_60`, and
its 89-frame measurement is the OWED item above.

---

## F — suites

### F1 — the runs

| run | result |
|---|---|
| `python -m pytest tests/test_tf_iqr_ret_60.py -q` | **272 passed, 1 skipped** |
| `python docs/measure_tf_iqr_ret_60_cpu.py` — the same module with `NPY_DISABLE_CPU_FEATURES="AVX512F AVX512_SKX AVX2 FMA3"` | **272 passed, 1 skipped** |
| `python -m pytest -q` (full suite) | see below |

The CPU-restricted run goes through `docs/measure_tf_iqr_ret_60_cpu.py`
rather than an environment prefix, because `NPY_DISABLE_CPU_FEATURES` is
read during numpy's dispatch init and so must be set before numpy is
imported. That script refuses to run if any of the four features is still
enabled, so the claim cannot drift from what was actually turned off; it
reported `AVX512F`, `AVX512_SKX`, `AVX2` and `FMA3` all disabled, with
`SSSE3 SSE41 POPCNT SSE42 AVX F16C AVX512CD AVX512_CLX AVX512_CNL
AVX512_ICL` still enabled, on numpy 1.26.4.

The one skip is `test_a4_the_resolution_that_follows[two-point]`: the tie
frame has its own tests
(`test_the_tie_frame_is_a_handful_of_nearly_equal_doubles`,
`test_gate_d_scale_on_the_tie_frame_reads_rounding_and_not_a_failure`) and
a distinct-value band built for ordinary frames does not apply to it.

Full suite, on this worktree, **after the Gate E row was recorded**:
**1 failed, 11,435 passed, 86 skipped**. The one failure is known and
expected:

* `tests/test_altrepo_talib_csv.py::test_regenerating_reproduces_the_committed_rows`
  — needs the sibling `../AlternativeRepos` checkout, which this worktree
  does not have. CI deselects it by name.

Before the row was recorded the porting session measured **2 failed,
11,427 passed, 86 skipped**: the second failure was
`tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
reporting `['tf_iqr_ret_60']`, the owed row of §E, which CI into `dev`
skips under `GATE_E_PENDING_OK=1`. It passes now, and the pass count rose
by 8: that one flip plus **7** new collected items, because seven of
`tests/test_gate_e_ledger.py`'s tests are parametrized over the ledger's
rows or indicators (read off its `@pytest.mark.parametrize` decorators,
not inferred from the delta) and this row adds one of each.

The 21 upstream correlation skips are `tests/config.py`'s, which skips at
import when the gitignored `data/SPY_D.csv` fixture is absent.

### F2 — which figures move between the two numpy dispatches

Read under the default dispatch and again under
`NPY_DISABLE_CPU_FEATURES="AVX512F AVX512_SKX AVX2 FMA3"`, which is what
the launcher re-runs this module's tests with (a GitHub runner without
AVX-512).

| figure | default | AVX-512/AVX2/FMA3 off |
|---|---|---|
| §A1 bit-equal counts (ten frames) | 1440 each | **identical** |
| §A2 difference bit-equal counts | 1440 each | **identical** |
| §A2 single-quartile totals | 28,800/28,800 and 14,404/14,404 | **identical** |
| §A2 numpy-branch probe | 20,000/20,000 and 19,984 / 19,983 | **identical** |
| §A2 spelling disagreements on the real windows | 0 of 1,440 × 10, both quartiles | **identical** |
| §A3 max ulp vs the exact oracle | 0.00 | **identical** |
| §A4 distinct values, all ten frames | 714 .. 896, two-point 5 | **identical** |
| §A4 two-point span | 2.220e-16 | **identical** |
| §A6 prototype bit-equal counts, and the guard table | 1440 each; 279/280/340 | **identical** |
| §B sweep and mutant catch counts | 0 of 35; 24 .. 35 | **identical** |
| §C non-negativity, all ten frames | True | **identical** |
| §C sign-blindness: bit-equal under negation | 89 of 1440; 298 of 300 | **identical** |
| §C tie-window negative search | 0 of 2400 | **identical** |
| §D1 x8 / x64 bit-equal counts | 1440 each | **identical** |
| §D2 overall max relative difference and max \|diff\| | 2.672e-14, 4.163e-16 | **identical** |
| §D2 individual (frame, factor) cells | walk ×3.7 1.890e-14 / 3.331e-16 / 144 ulp; walk ×0.1 1.923e-14; walk ×1.0000001 160 ulp | **moves**: 1.972e-14 / 4.163e-16 / 144 ulp; 2.223e-14; **176 ulp** |
| §D3 level-shift bars moved | 1440 of 1440 | **identical** |
| §G1–§G4 guard counts and bounds | 61 / 60 / 1e+308 | **identical** |
| §G2 infinity-window NaN table, and the mask-line mutant | nan / bit-equal | **identical** |
| §G5 ladder distinct values and max | 2, 5.551e-17 | **moves**: 1, 0.0 |
| §G5 ladder distinct RETURN doubles | 4, span 6.661e-16 | **moves**: 3, span 4.441e-16 |
| §G5 max ulp vs the exact oracle, all three frames | 0.00 | **identical** |
| §G5 floor-cost table, all thirteen rows | 480 emptied; smallest 2.000e-02 .. 6.913e-02 | **identical**, except the ladder's WIDEST return range — see the row below |
| §G5 ladder widest window return range | 6.661e-16 | **moves**: 4.441e-16 |
| §O every per-frame and pooled ρ | as tabulated | **identical to 4 dp** |
| §S gaussian / t(2) / exponential means | 1.3187 / 1.6140 / 1.0751 | **identical to 4 dp** |
| §S autocorrelations, and "60 bars moved" | 0.9718 …; 60 | **identical** |
| §Z wall-clock | 124 / 257 / 319 ms | moves (it always does) |

So **two** things move on this machine besides the timing, and both are the
same mechanism: the dispatched divide that builds the return. The ladder,
whose returns are mathematically one number, gets 4 distinct doubles by
default and 3 with AVX off, which changes what lands on ranks 15/16 and
45/46; and **three** Gate D cells move — walk ×3.7 in both its relative
(1.890e-14 → 1.972e-14) and its absolute (3.331e-16 → 4.163e-16) figure,
walk ×0.1 in its relative one (1.923e-14 → 2.223e-14), and walk
×1.0000001 in its ULP figure alone (160 → 176, with its absolute
3.608e-16 and relative 2.251e-14 identical either way). The BOUNDS do
not move: max \|diff\| ≤ 4.163e-16, max relative ≤ 2.672e-14 and max
**208 ulps** of the column's own value under both dispatches, where §D2's
`max ulp` column is the same distance expressed in the honest unit.
Everything that depends on a real spread is identical.

⚠ That is a reading of this machine under two dispatches, not a guarantee
for every CPU, which is why the tests pin bands and tolerances rather than
these digits — the one exception being the bit-equality counts, which are
the claim Gate A makes and which are asserted as "all shared bars" rather
than as the literal 1,440.
