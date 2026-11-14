# J-DAMIANI — `j_damiani`, measured

PandasTa issue **#105** (parent #31 ALPHASETS, screen of 2026-10-24).
Module `pandas_ta/volatility/j_damiani.py`, column **`J_DAMIANI_13_40`**.
Tests `tests/test_j_damiani.py` (191).

Every number in §A, §B, §C, §D, §G, §L, §W and §Z is printed by
`python docs/measure_j_damiani.py` on this worktree (**pandas 2.3.3, numpy
1.26.4** — which that script prints as its first line, so this parenthesis
is a quote and not a guess), section by section. The headings take their
letters from the script. §E and §F are headings of this file only.

What does NOT come from that command, marked again where it appears:

* **§Z's milliseconds**, which it does print but which are not a claim:
  they are this machine's and this run's, and so is every quotient of
  them (the loop's share, the µs/bar, the two-spelling ratio). Four runs
  of §Z on this worktree printed 32.35 / 30.46 / 30.13 / 30.78 ms for the
  same 100,000 bars. The claims there are the traced peak, the linear
  shape, the ordering, and the bit-identical output.
* **§E**, which is the launcher's Gate E run — **pending, run by
  issue-solver after this session**.
* **§E0**, the 2026-10-24 screen's figures, measured on the PROTOTYPE and
  quoted from issue #105.
* **§F**, which is pytest's own output.
* **§C2's dictionary and contract deltas**, which are read off
  `git diff docs/IndicatorDictionary.md` and re-derived against the live
  package by
  `tests/test_ml_companions.py::test_the_contract_quotes_the_dictionarys_actual_ml_form_counts`
  and `tests/test_readme_counts.py`.
* **the reduced-CPU figures**, which come from
  `python docs/measure_j_damiani_cpu.py A1 A5 D` and are marked as such.

```
TR           = max(high - low, |high - close[-1]|, |low - close[-1]|)
ATR(n)       = TR.ewm(alpha=1/n, adjust=False).mean()
base         = ATR(13) / ATR(40)
J_DAMIANI[T] = base[T] + 0.5 * (J_DAMIANI[T-1] - J_DAMIANI[T-3])
```

**Source.** jesse indicators (MIT), `damiani_volatmeter`, as issue #105
quotes it: "`vol = ATR13/ATR40 + 0.5*(vol[-1] - vol[-3])`".

⚠ **jesse is not installed in this worktree and web access is
unavailable.** It is an ATTRIBUTION, not an oracle:
`tests/test_j_damiani.py::test_the_source_library_is_not_installed_here`
records that, so the claim cannot rot into "checked against jesse". What
Gate A checks is the formula the issue quotes, spelled two independent
ways (§A1, §A2).

⚠ **One column, not two.** The issue's title and its quote name the
VOLATILITY line, and that is what ships. Whether jesse's own
`damiani_volatmeter` also returns a threshold line is not something this
worktree can see, and no threshold line was screened at Gate E, so
shipping one would be both the wider scope and the unmeasured one.

The screen prototype is `docs/issues/screen/ind_screen.py` candidate
`j_damiani` (that file is gitignored, so it exists only on the owner's
machine):

```python
base = sdiv(atr_wilder(h, l, c, 13), atr_wilder(h, l, c, 40)).to_numpy()
out = np.full(len(base), np.nan)
for i in range(len(base)):
    if np.isnan(base[i]):
        continue
    p1 = out[i - 1] if i >= 1 and not np.isnan(out[i - 1]) else 0.0
    p3 = out[i - 3] if i >= 3 and not np.isnan(out[i - 3]) else 0.0
    out[i] = base[i] + 0.5 * (p1 - p3)
return pd.Series(out, index=c.index).where(pd.Series(base, index=c.index).shift(3).notna())
```

with `atr_wilder(h, l, c, n)` the plain three-way max through
`ewm(alpha=1/n, adjust=False)` and `sdiv` a division that maps ±inf to
NaN.

**Eight frames**, 1,500 bars each, built by the script and retyped with
the same seeds in the test module: `walk`, `trend`, `range-bound`,
`grid` (a walk on a 0.01 tick grid), `heavy-tailed`, `jump` (a ×1.5 gap
at bar 700), `flat` (a constant price) and `flat-start` (a walk whose
first 50 bars are a constant price). The first six are the script's
`VARYING` and each fires on **1,497** bars — the warm-up is the feedback
loop's `vol[-3]` and nothing else — which makes the pooled figure 8,982
over the six. `flat` fires on **0** and `flat-start` on **1,447**, both
for the reason in §C1.

The first seven frames and their seeds are `docs/measure_j_gator.py`'s,
kept identical on purpose: two ports measured on the same frames can be
compared. `flat-start` is new here, because this column — unlike
`j_gator`'s — has a NaN reading, and a frame that begins without movement
is how a real one reaches it.

---

## §A1 Gate A — the issue's formula, spelled independently

A hand-written true range, a hand-written Wilder recursion and a
hand-written feedback loop, sharing no code with the module, against the
module:

| frame | masks equal | bars | bit-equal | max \|diff\| | max \|rel\| |
|---|---|---|---|---|---|
| walk | True | 1,497 | 1,497 | 0.000e+00 | 0.000e+00 |
| trend | True | 1,497 | 1,497 | 0.000e+00 | 0.000e+00 |
| range-bound | True | 1,497 | 1,497 | 0.000e+00 | 0.000e+00 |
| grid | True | 1,497 | 1,497 | 0.000e+00 | 0.000e+00 |
| heavy-tailed | True | 1,497 | 1,497 | 0.000e+00 | 0.000e+00 |
| jump | True | 1,497 | 1,497 | 0.000e+00 | 0.000e+00 |

and the three legs separately on the walk: the true range bit-equal on
1,500 of 1,500 bars, `ATR(13)` and `ATR(40)` bit-equal on 1,500 of 1,500
with max \|diff\| 0.000e+00.

Measured bit-equal on every frame, and **the test asserts a bound of
1e-12 — absolute AND relative — rather than bit-equality**. The two
spellings are not obliged to round the same way: pandas' `ewm` computes
`((1-a)*s + a*x) / ((1-a) + a)` and the oracle computes `(1-a)*s + a*x`,
which agree only because `(1-a) + a` is exactly 1.0 for both alphas on
this machine — printed as `True` for 1/13 and for 1/40. The same table
under numpy's `AVX512F AVX512_SKX AVX2 FMA3` dispatch disabled
(`python docs/measure_j_damiani_cpu.py A1`) is also 0.000e+00 on all six.

⚠ The oracle has NO NaN handling, because the issue's formula has none:
it is comparable only on the six frames whose `base` is defined from bar
0. `flat` and `flat-start` are covered by §A2 against the prototype, and
their masks by §A3 and §C1.

## §A2 Gate A — the screen prototype, bit for bit

The prototype performs the SAME operations in the same order (pandas'
`ewm`, then the same loop with the same missing-predecessor convention),
so this limb is exact and machine-independent, and it is asserted
bit-exactly on **all eight** frames:

| frame | masks equal | bars | bit-equal | max \|diff\| |
|---|---|---|---|---|
| walk | True | 1,497 | 1,497 | 0.000e+00 |
| trend | True | 1,497 | 1,497 | 0.000e+00 |
| range-bound | True | 1,497 | 1,497 | 0.000e+00 |
| grid | True | 1,497 | 1,497 | 0.000e+00 |
| heavy-tailed | True | 1,497 | 1,497 | 0.000e+00 |
| jump | True | 1,497 | 1,497 | 0.000e+00 |
| flat | True | 0 | 0 | — (both fire nowhere) |
| flat-start | True | 1,447 | 1,447 | 0.000e+00 |

The two frames with a NaN `base` are the interesting rows: that is where
the module's `slow.where(slow > 0.0)` has to agree with the prototype's
`_fin(a / b)` — two different spellings of what `0 / 0` means. It does,
and the guard removed from the module's own source (the mutant machinery
of §B) reproduces the column bit-for-bit on all eight frames as well, so
the guard changes no reading anywhere. What it DOES buy is §G3.

**This is the limb that ties the port to §E0's Gate E figures:** the
prototype the screen measured and this module are the same column, bit
for bit, on every synthetic frame tried.

## §A3 the warm-up is the LOOP's, and bar 0's ratio is exactly 1

Both EWMAs are seeded at the first true range, so `base[0]` is
`TR[0] / TR[0]` = **1.0 exactly** (printed as `1.0`) and `base` has 0 NaNs
on the six varying frames. The column's only NaNs are the loop's:

| frame | base NaN | first fired bar | column NaN | fired |
|---|---|---|---|---|
| walk, trend, range-bound, grid, heavy-tailed, jump | 0 | 3 | 3 | 1,497 of 1,500 |
| flat-start | 50 | 53 | 53 | 1,447 of 1,500 |

The three masked bars are **computed and then dropped** — they are what
bar 3 recurses from, and the identity is checked bar by bar:

| bar | base | loop | column |
|---|---|---|---|
| 0 | 1.000000000 | 1.000000000 | NaN |
| 1 | 1.028128273 | 1.528128273 | NaN |
| 2 | 1.036558684 | 1.800622821 | NaN |
| 3 | 1.124497185 | 1.524808595 | 1.5248085953143053 |
| 4 | 1.127512319 | 1.125852480 | 1.1258524802566947 |

with `column[3] == base[3] + 0.5*(loop[2] - loop[0])` printed as `True`.

`MIN_BARS` = `SLOW + FAR` = **43** is a floor on the INPUT, not the
warm-up: a 42-bar frame returns `None` (`verify_series` declines) and a
43-bar frame fires on 40 bars, whose values match the full frame's first
43 bars (`True`) — the column has no look-back beyond its own recursion.

⚠ **The early bars are a transient and they are kept.** Bar 0's `ATR(40)`
is one observation, so the first reading of the ratio is 1.0 by
construction rather than by measurement. The source formula and the
prototype do the same, and §A4 measures how long that transient lasts;
NaN-ing it away would depart from the form Gate E measured.

## §A4 WHICH ATR — the smoother and the true range, priced

The issue says `ATR13/ATR40` and the prototype spells it
`ewm(alpha=1/n, adjust=False)` over the plain three-way max, seeded at
bar 0. **Four** other readings are in reach, three of them inside this
fork, and every one of them is a different column.

⚠ **jesse's own code is not read here**, so none of this is evidence
about what jesse computes. The reading rests on the issue's word "ATR"
— whose standard meaning is Wilder's `alpha = 1/length` — and on the
prototype that Gate E measured in §E0.

**(a) SMA-seeded** (this fork's `wilder_rma`, Pine's `ta.rma`): the same
recursion, seeded with `SMA(TR[:n])` at bar `n - 1`.

| frame | masks equal | shared | bit-equal | max \|diff\| | Spearman |
|---|---|---|---|---|---|
| walk | False | 1,458 | 15 | 5.965e-01 | 0.9617 |
| trend | False | 1,458 | 98 | 6.590e-01 | 0.9630 |
| range-bound | False | 1,458 | 79 | 7.285e-01 | 0.9356 |
| grid | False | 1,458 | 62 | 7.287e-01 | 0.9297 |
| heavy-tailed | False | 1,458 | 18 | 6.335e-01 | 0.9925 |
| jump | False | 1,458 | 114 | 5.878e-01 | 0.9744 |

**(b) this fork's `rma`** (pandas' DEFAULT `adjust=True`,
`min_periods=n`):

| frame | masks equal | shared | bit-equal | max \|diff\| | Spearman |
|---|---|---|---|---|---|
| walk | False | 1,458 | 0 | 5.830e-01 | 0.9633 |
| trend | False | 1,458 | 0 | 6.831e-01 | 0.9488 |
| range-bound | False | 1,458 | 0 | 7.214e-01 | 0.9470 |
| grid | False | 1,458 | 0 | 7.189e-01 | 0.9382 |
| heavy-tailed | False | 1,458 | 0 | 1.072e+00 | 0.9838 |
| jump | False | 1,458 | 0 | 5.915e-01 | 0.9695 |

**(c) a plain EMA** (`alpha = 2/(n+1)`, `ewm(span=n, adjust=False)`, with
`adjust` held fixed so the alpha is the only change) — the reading the
issue's wording excludes, and the only one that changes the smoother's
MEMORY rather than its warm-up:

| frame | masks equal | shared | bit-equal | max \|diff\| | Spearman |
|---|---|---|---|---|---|
| walk | True | 1,497 | 0 | 2.456e-01 | 0.8743 |
| trend | True | 1,497 | 0 | 2.639e-01 | 0.8885 |
| range-bound | True | 1,497 | 0 | 3.887e-01 | 0.8644 |
| grid | True | 1,497 | 0 | 4.011e-01 | 0.8503 |
| heavy-tailed | True | 1,497 | 0 | 5.012e-01 | 0.8380 |
| jump | True | 1,497 | 0 | 4.101e-01 | 0.8278 |

**(d) this fork's `true_range`**, same smoother — and this is why the
true range is spelled in the module instead of imported. It differs
twice over: it routes `high - low` through `non_zero_range`, which adds
an epsilon to EVERY bar of the series as soon as ONE bar has
`high == low`, and it NaNs bar 0.

| frame | masks equal | shared | bit-equal | max \|diff\| | Spearman |
|---|---|---|---|---|---|
| walk | False | 1,496 | 117 | 4.587e-01 | 0.9833 |
| trend | False | 1,496 | 91 | 7.335e-01 | 0.7826 |
| range-bound | False | 1,496 | 22 | 1.107e+00 | 0.7401 |
| grid | False | 1,496 | 72 | 7.634e-01 | 0.9838 |
| heavy-tailed | False | 1,496 | 19 | 8.539e-01 | 0.9287 |
| jump | False | 1,496 | 193 | 4.758e-01 | 0.9958 |

On these six frames **no bar has `high == low`** (measured: 0 on each),
so only the bar-0 divergence is in play there and the true range itself
is bit-equal on all 1,499 shared bars. The epsilon shows up where ties
do: on `flat` (1,500 bars with `high == low`) the fork's true range is
bit-equal on **0 of 1,499** shared bars, and the whole column changes
character — the script's own `fired:` cells print **module 0, fork TR
1,496**, the latter reading a RATIO of two epsilons. On `flat-start` (50
tied bars) the true range is bit-equal on 1,195 of 1,499 and both fire
(1,447 against 1,496).

**(e) this fork's `atr()` at its defaults** (`mamode="rma"` over that
true range — both divergences at once, and the nearest thing a reader
would reach for):

| frame | masks equal | shared | bit-equal | max \|diff\| | Spearman |
|---|---|---|---|---|---|
| walk | False | 1,457 | 0 | 5.917e-01 | 0.9606 |
| trend | False | 1,457 | 0 | 6.814e-01 | 0.9485 |
| range-bound | False | 1,457 | 0 | 6.953e-01 | 0.9490 |
| grid | False | 1,457 | 0 | 7.016e-01 | 0.9375 |
| heavy-tailed | False | 1,457 | 0 | 1.100e+00 | 0.9828 |
| jump | False | 1,457 | 0 | 5.807e-01 | 0.9701 |

⚠ **A SEED difference is a warm-up difference, and here it dies SLOWLY.**
max \|diff\| over bars ≥ k, on the best and worst Spearman frames of
(a) and (d):

| reading | frame | ≥ 3 | ≥ 50 | ≥ 100 | ≥ 200 | ≥ 400 | ≥ 800 | column max \|value\| over the shared bars |
|---|---|---|---|---|---|---|---|---|
| (a) SMA-seeded | walk | 6.0e-01 | 3.2e-01 | 4.9e-02 | 4.1e-03 | 2.8e-05 | 1.5e-09 | 1.2597 (1,458 bars) |
| (a) SMA-seeded | range-bound | 7.3e-01 | 4.1e-01 | 7.6e-02 | 5.4e-03 | 3.8e-05 | 1.5e-09 | 1.3730 (1,458) |
| (d) fork true_range | walk | 4.6e-01 | 8.1e-02 | 2.3e-02 | 1.9e-03 | 1.3e-05 | 7.0e-10 | 1.5666 (1,496) |
| (d) fork true_range | range-bound | 1.1e+00 | 4.5e-01 | 1.4e-01 | 1.1e-02 | 7.6e-05 | 3.0e-09 | 2.2789 (1,496) |

The last column is the scale to read those differences against, and it is
printed rather than asserted: an earlier revision of this file said "a
column whose own span on the walk is ~1.26", which was neither printed by
the script at the time nor a span (§C1's span for the walk is 0.875;
1.2597 is the max \|value\| over the 1,458 bars row (a) shares).
**This is the disclosure for a consumer**: the column fires from bar 3, but several
HUNDRED bars of it are seed-dependent — the 40-bar memory and the loop's
resonance (§A5) between them. It is also why the Spearman figures in (a)
and (d) are as low as 0.73 for what is "only" a warm-up difference: a
rank correlation over 1,458 bars of which the first few hundred disagree
lands there.

## §A5 the feedback loop IS the column — a stable resonator

`vol[T] = base[T] + 0.5*(vol[T-1] - vol[T-3])` is an IIR filter with
transfer function `1 / (1 - 0.5 z^-1 + 0.5 z^-3)`. Five things about it,
measured rather than argued, because they are what makes this column
something other than an ATR ratio.

**(a) stability** — the roots of `z^3 - 0.5 z^2 + 0.5 = 0`:

| root | \|z\| |
|---|---|
| +0.578649 + 0.652576j | 0.872175 |
| +0.578649 − 0.652576j | 0.872175 |
| −0.657298 | 0.657298 |

largest **0.872175** < 1, so an impulse decays.

**(b) gain** — `|H(e^-iw)|` over a 2,000,001-point frequency grid:

| | value |
|---|---|
| H(DC) | 1.000000 |
| peak \|H\| | **3.674235** at a period of **7.4705 bars** |
| H(Nyquist) | 1.000000 |

So the loop leaves the mean level of the ratio alone and amplifies
roughly weekly volatility cycles three and a half times.

**(c) the impulse response**, run through the loop itself:

```
k:   1.0000   0.5000   0.2500  -0.3750  -0.4375  -0.3438   0.0156   0.2266
```

| max \|h\| over k ≥ | 0 | 10 | 50 | 100 | 200 | 300 |
|---|---|---|---|---|---|---|
| | 1.000e+00 | 1.655e-01 | 6.293e-04 | 8.203e-07 | 9.565e-13 | 1.026e-18 |

with **sum \|h\| = 4.598374**.

**(d) what dropping the loop would cost** — the bare `ATR(13)/ATR(40)`
against the shipped column:

| frame | shared | bit-equal | max \|diff\| | Spearman |
|---|---|---|---|---|
| walk | 1,497 | 0 | 4.003e-01 | 0.9049 |
| trend | 1,497 | 0 | 5.857e-01 | 0.8989 |
| range-bound | 1,497 | 0 | 9.405e-01 | 0.9142 |
| grid | 1,497 | 0 | 5.807e-01 | 0.9322 |
| heavy-tailed | 1,497 | 0 | 6.706e-01 | 0.8978 |
| jump | 1,497 | 0 | 7.732e-01 | 0.9194 |

⚠ **That is the disclosure, not the defence.** The loop RESHAPES the
column — no bar in common, differences up to 0.94 — but it does not
RE-RANK it: Spearman 0.8978 .. 0.9322 against the bare ratio. "This is
not just an ATR ratio" is therefore not available as an argument at Gate
E, where every comparator is compared by rank.

**(e) so the column is BOUNDED, and the bound is the ratio's.** Both
ATRs are weighted means of the SAME true ranges whose weights each sum to
1, so the ratio cannot exceed the largest ratio of those weights — which
is at lag 0, where `ATR(13)`'s weight is `1/13` and `ATR(40)`'s is
`1/40`:

| | value |
|---|---|
| sup `base` | `SLOW/FAST` = 40/13 = **3.076923** |
| sum of positive taps | 2.799187 |
| sum of negative taps | −1.799187 |
| so `J_DAMIANI` ∈ | **(−5.5360, 8.6129)** |

The supremum is **attained, not approached**: on a frame that is flat and
then moves, the first moving bar is the only non-zero true range, so
every weight but lag 0 multiplies a zero. `flat-start`'s `base[50]` reads
`3.0769230769230766` against `40/13 = 3.076923076923077` — not bit-equal,
**1 ulp** below it (relative 1.443e-16), which is the honest form of that
sentence, and the max `base` over all eight frames is that same value.
The test asserts "within 4 ulp and never above".

What the frames actually reach is narrower: over the 10,429 fired bars of
the seven non-flat frames, **0.691678 .. 3.628336** (the six varying ones
alone, §C1: 0.691678 .. 2.858073).

⚠ **That bound is EXACT-ARITHMETIC, and §G5(d) measures floating point
breaking it.** Not in the underflow stall of §G5(c), which is where this
file first guessed the exception would be: at SUBNORMAL true ranges.
Subnormal multiplication rounds absolutely, so `1/13` and `1/40` of `k`
ulps both round to a whole number of ulps and the ratio is whatever those
two integers say — 5 ulps over 1 ulp at k = 59, i.e. `base` = **5.0**,
1.63× the supremum above, with the column reading 6.8750. The weight
argument has no force there. It is still nowhere near an overflow, and
§G5(d) also measures the one `inf` that regime CAN produce and the guard
that removes it.

## §B Gate B — causality, five mutants, no gap

36 perturbation offsets (bars 1,464 .. 1,499), every bar ≥ J multiplied by
1.03, caught = some bar < J moved.

⚠ 1.03 on high, low AND close is **not** a global rescale — the column is
invariant under one of those, which is Gate D — it is a rescale of a
SUFFIX, which moves the true range at bar J and so is visible to a column
that reads ahead.

**The shipped module: caught 0 of 36 on each of the six varying frames.**

Five mutants, each an edit to the shipped source read off disk and
`exec`'d in memory — never a re-implementation, which could differ from
the module for reasons that have nothing to do with causality:

| mutant | what it does | live (bars moved of shared) | caught |
|---|---|---|---|
| `tr-lead` | the true range gaps against TOMORROW's close | 1,497 of 1,497, all six frames | 36 of 36, all six |
| `fast-atr-lead` | the fast ATR smooths a one-bar-early true range | 1,497 of 1,497, all six | 36 of 36, all six |
| `base-lead` | the loop reads tomorrow's ratio | 1,496 of 1,496, all six | 36 of 36, all six |
| `loop-lead` | the feedback term reads `base[T+1]` instead of `vol[T-1]` | 1,497 of 1,497, all six | 36 of 36, all six |
| `output-early` | the whole column shifted one bar earlier | 1,496 of 1,496, all six | 36 of 36, all six |

Every mutant moves EVERY shared bar, and every one is caught at every
offset. `j_gator` needed a mechanism-aware sweep for its teeth mutant
because the teeth cancel out of its formula on some bars; nothing cancels
here, so the blind sweep is enough.

### §B1 how LOUD each catch is

36 of 36 could still mean "caught by one bar in the last bits", so the
sweep's actual signal, on the walk at the two extreme offsets:

| mutant | J = 1,464 | J = 1,499 |
|---|---|---|
| `tr-lead` | 1 bar of 1,461, max \|diff\| 1.238e-01 | 1 of 1,496, 1.205e-01 |
| `fast-atr-lead` | 1 of 1,461, 1.911e-01 | 1 of 1,496, 1.700e-01 |
| `base-lead` | 1 of 1,461, 1.235e-01 | 1 of 1,496, 1.165e-01 |
| `loop-lead` | 1 of 1,461, 6.175e-02 | 1 of 1,496, 5.825e-02 |
| `output-early` | 1 of 1,462, 1.235e-01 | 1 of 1,497, 1.165e-01 |

One bar each — the one the look-ahead reaches — moving by 5.8e-02 to
1.9e-01, which is **twelve** orders of magnitude above the 2.098e-14 an
inexact rescale costs (§D2): 5.8e-02 / 2.098e-14 = 2.8e12. No catch here
is a rounding artefact. (Review round 4 found "five orders" here, in the
test docstring, and quoted back approvingly in an earlier round's own
summary; the conclusion held by a far wider margin than the number
claimed, which is how it survived three readings.)

## §C Gate C — reachability

### §C1 synthetic

| frame | fired | of | distinct | > 1 | < 1 | min | max | median |
|---|---|---|---|---|---|---|---|---|
| walk | 1,497 | 1,500 | 1,497 | 696 | 801 | 0.6917 | 1.5666 | 0.9926 |
| trend | 1,497 | 1,500 | 1,497 | 1,215 | 282 | 0.8646 | 1.9025 | 1.0831 |
| range-bound | 1,497 | 1,500 | 1,497 | 721 | 776 | 0.7071 | 2.8581 | 0.9929 |
| grid | 1,497 | 1,500 | 1,497 | 806 | 691 | 0.7571 | 2.2193 | 1.0106 |
| heavy-tailed | 1,497 | 1,500 | 1,497 | 581 | 916 | 0.7219 | 2.6195 | 0.9661 |
| jump | 1,497 | 1,500 | 1,497 | 708 | 789 | 0.7375 | 2.6560 | 0.9912 |
| flat | **0** | 1,500 | — | — | — | — | — | — |
| flat-start | 1,447 | 1,500 | 1,447 | 687 | 760 | 0.6917 | 3.6283 | 0.9953 |

Pooled over the six varying frames: 8,982 bars, min 0.691678, max
2.858073, mean 1.023274; **8,977 of 8,982** inside 0.25 .. 2.5, 8,964
inside 0.5 .. 2.0, and **0 negative**.

⚠ **A frame with no movement at all reads NaN, not 0.0.** On `flat` the
true range is 0 on all 1,500 bars, so `ATR(13)` and `ATR(40)` are both 0
and the ratio is `0 / 0` — undefined rather than zero. `base` is NaN on
1,500 of 1,500 and the column fires on 0. That is a DIVERGENCE from
`j_gator`, whose flat frame reads exactly 0.0 on every bar, and a
consumer that treats "no reading" and "zero volatility expansion" the
same way would be wrong here.

The same mechanism makes a flat PREFIX a leading NaN run: on
`flat-start`, `base` is NaN on 50 bars and first defined at bar 50, so
the column first fires at bar **53** and fires on 1,447.

**The NaNs are always a leading prefix** — measured contiguous-from-zero
on all eight frames (3 bars on the clean six, 53 on `flat-start`, 1,500
on `flat`) and on the 32,000-bar adversarial frame of §G5. A Wilder EWMA
of non-negative observations that is positive once stays positive, so
`base` cannot go NaN after it is defined: there are no mid-series holes
(§G6).

### §C2 real data, and the dictionary

**Real-data counts are owed with the Gate E run** (§E), which is the
launcher's. Nothing here claims a real-data count.

`python docs/gen_indicator_dictionary.py` regenerated
`docs/IndicatorDictionary.md` from a live probe: 345 → **346** indicators
probed, `volatility (35)` → **(36)**, and the new row is

```
| `j_damiani` | H/L/C | — | `J_DAMIANI_13_40` SF | 3 | Short-term true range over long-term true range, run through a three-bar feedback loop: how far volatility stands above its own slower level. |
```

so the probe sees it as scale-free with a 3-bar warm-up, and it joins the
"no transformation needed" list. `docs/MLCompanionContract.md`'s counts
move 688 → **689** tagged columns and 327 → **328** `SF`;
`tests/test_ml_companions.py::test_the_contract_quotes_the_dictionarys_actual_ml_form_counts`
re-derives both from the dictionary, so they are checked rather than
typed. README: 343 → **344** in `Category`, 351 → **352** on `df.ta`,
`volatility (35)` → **(36)** with `j_damiani` in the list, all three
checked by `tests/test_readme_counts.py`.

## §D Gate D — scale-free

### §D1 ×8 / ×64, bit-identical

Exact in binary at every step — the three-way `max`, the EWMA's
`(1-a)*s + a*x`, and then the division of two quantities scaled by the
same factor, which cancels it:

| frame | ×8 | ×64 |
|---|---|---|
| walk, trend, range-bound, grid, heavy-tailed, jump | 1,497 of 1,497 bit-equal | 1,497 of 1,497 |
| flat | 0 of 0 (fires nowhere) | 0 of 0 |
| flat-start | 1,447 of 1,447 | 1,447 of 1,447 |

max \|diff\| 0.000e+00 everywhere, NaN masks identical everywhere.

### §D2 ×10 / ×3.7 / ×0.1 / ×1.0000001, a tolerance

These round. NaN masks stay identical on all 24 frame-and-factor cells;
the worst relative difference over all of them is **2.098e-14** (grid,
×0.1), and the test asserts **1e-9**.

Under numpy's `AVX512F AVX512_SKX AVX2 FMA3` dispatch disabled
(`python docs/measure_j_damiani_cpu.py D`) the worst is the same
**2.098e-14**, with individual cells moving (walk ×10 reads 4.687e-15 at
full dispatch and 3.955e-15 reduced) — which is why the bound has nearly
five orders of headroom (1e-9 against the measured 2.098e-14, a factor of
4.8e4) and why the bit-equal COUNTS are printed and not pinned: 86 .. 166
of 1,497 per cell at full dispatch, 75 .. 169 reduced.

⚠ This column is roughly four and a half orders of magnitude better
conditioned than `j_gator`'s 6.5e-10 (2.098e-14 against it, a factor of
3.1e4): `base` is a ratio of two POSITIVE nearby means, where that one
was a difference of them, so there is no cancellation to amplify a
last-bit move. ⚠ Both of those exponents are quotients of the two
figures they name, re-derived here after review round 4 found "two
orders" in all three prose surfaces — a figure carried over from
`tests/test_j_gator.py`, where 1e-7 against 6.5e-10 really is two.

### §D3 extreme price levels

| level | ×8 | ×64 | fired | finite |
|---|---|---|---|---|
| 1e−06 | 1,497 of 1,497 | 1,497 of 1,497 | 1,497 | 1,497 |
| 1e+06 | 1,497 of 1,497 | 1,497 of 1,497 | 1,497 | 1,497 |
| 1e+100 | 1,497 of 1,497 | 1,497 of 1,497 | 1,497 | 1,497 |

`finite` is a separate column from `fired` on purpose: an infinity is not
NaN, so a column reading `inf` on every bar would satisfy `fired` and
bit-equality both.

### §D4 `0 < fires < n`

True on the six varying frames (1,497 of 1,500 each) and on `flat-start`
(1,447 of 1,500). **False on `flat`**, which fires on 0 — that is §C1's
`0 / 0`, pinned by its own test rather than covered quietly by this one,
and the reason Gate D's constant-column guard is asserted on the seven
frames that have a reading.

## §E Gate E

**Gate E: pending, run by issue-solver after this session.**

The harness is `../Backtesting/Backtesting/scripts/analysis/gate_e_overlap.py
run --module pandas_ta.volatility.j_damiani` (Backtesting #107), over the
89 frozen ALTPORT-1 BIST frames against the engine's `compute_all` ∪
`ml_features` manifest (329 + 358 = 687 comparators). This session does
not run it and does not read `../Backtesting`.

Until the receipt session records the row,
`tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
reports `j_damiani` as owed, and
`tests/test_j_damiani.py::test_the_gate_e_row_is_owed` asserts the ledger
has no row for it — which is the receipt session's cue to replace that
test with one pinning the row's identity.

### §E0 what the screen measured, on the PROTOTYPE

From issue #105 (2026-10-24; a prototype is not a port):

* max \|ρ\| **0.7621** vs `ATR_Ratio_5_20` (manifest, n = 397,069),
  top-5 per-frame max median 0.7639 → **DISCLOSE** under
  `r3-perframe-0.90` (the 0.76 ≤ ρ < 0.80 band);
* next comparators `natr_percentile` 0.7302, `natr_Pctl` 0.7294;
* stage-2 fork overlap (not Gate E; scale-free `Category` outputs at
  defaults, 12 frames): max \|ρ\| 0.7023 vs `massi:MASSI_9_25`,
  per-frame max median 0.7004;
* pre-flight on 6 frames: prefix-causal, unchanged under price ×8 and
  volume ×8.

§A2 measures this module BIT-equal to that prototype on all eight
synthetic frames, so the run on this module is expected to reproduce
those figures. **An expected agreement is the easiest kind of row to copy
over by mistake**, which is why the receipt session must pin the row's own
run id.

⚠ **This is the band to keep in mind when reading the rest of this
file.** DISCLOSE is a ship, but it is a ship with a note attached: the
top comparator is `ATR_Ratio_5_20`, which asks this column's own question
— fast volatility over slow — at different lengths, and §A5(d) shows the
feedback loop does not change the ranking enough to make that a different
question (Spearman 0.8978 .. 0.9322 against the bare ratio). What this
column adds over `ATR_Ratio_5_20` is the 13/40 horizon pair and the
resonator, not a new reading.

## §F Gate F — suites

The launcher runs both repos' suites in clean worktrees. In this worktree:

* `python -m pytest tests/test_j_damiani.py -q` → **191 passed**;
* `python docs/measure_j_damiani_cpu.py` → the same **191 passed** with
  `NPY_DISABLE_CPU_FEATURES="AVX512F AVX512_SKX AVX2 FMA3"` (the script
  prints the dispatchable features still enabled and refuses to run if
  any of the four survived, so the claim cannot drift);
* the four guards this port's doc edits touch, as the commands that were
  actually run:
  * `pytest tests/test_readme_counts.py tests/test_wiring_accessors.py`
    → **73 passed**;
  * `pytest tests/test_ml_companions.py tests/test_readme_counts.py
    tests/test_altport2_ports.py` → **39 passed, 3 skipped**;
  * ⚠ `pytest tests/test_wiring_accessors.py tests/test_altport2_ports.py`
    → **1 failed, 85 passed, 3 skipped**:
    `test_the_category_count_moved_by_exactly_three` reads "Category
    total 341, expected 344". That is the PRE-EXISTING trap issues #100
    .. #104 recorded — `pandas_ta/core.py:453` hands out the live
    `Category[name]` list and `core.py:692` removes names from it, so
    `test_wiring_accessors.py`'s category sweeps delete three entries for
    the rest of the process — and not this port's. Alphabetical
    collection hides it, which is why the full suite below is green on
    that test. **An earlier revision of this bullet said the four guards
    were "green" and attributed 73 / 39 to the wrong module groupings,
    which is how the red combination went unreported for one review
    round.**
* the full suite → §F1: **3 failed, 8,936 passed, 85 skipped**, the three
  being `dev`'s clean-checkout failures with the owed Gate E row among
  them.

⚠ **Those two counts move together, and that is worth stating as a rule
rather than as a number.** 191 of the suite's tests are this module's, so
every test added to `tests/test_j_damiani.py` moves the module count AND
the suite count, and both have to be re-run. Review round 1 added three
tests; the re-run of the module module happened, the re-run of the suite
did not, and this file carried 8,933 into round 2 until that round struck
it.

## §G the guards, and what each one buys

### §G1 a bad price EMPTIES NO BAR

That is the first surprise, and it is the opposite of `j_gator`, where a
bad close empties its own bar. Two mechanisms: the true range is a
three-way `max` that SKIPS a NaN leg, so one bad price still leaves it a
value; and `ewm` skips a NaN observation rather than poisoning the tail.
What a bad price does instead is perturb the column RECURSIVELY — all
three legs are inside both EWMAs, the close through the gap legs — so the
claim is two-sided: bars BEFORE it are bit-identical, and the
contamination decays with the slow filter's memory.

Planted at bars 100, 400, 700, 1,000 and 1,200 of the walk; `moved` is
the range over those five plants, the `k` columns are the worst of the
five:

| leg | planted | pre bit-equal | emptied | moved | k=0 | k=50 | k=100 | k=300 |
|---|---|---|---|---|---|---|---|---|
| high | NaN | True | 0 | 0 .. 1,100 | 2.976e-02 | 1.552e-03 | 4.935e-04 | 3.544e-06 |
| high | +inf | True | 0 | 300 .. 1,262 | **6.541e-02** | **4.182e-03** | 1.475e-03 | **1.358e-05** |
| low | NaN | True | 0 | 0 .. 1,271 | 4.952e-02 | 3.445e-03 | 1.114e-03 | 6.644e-06 |
| low | −inf | True | 0 | 300 .. 1,262 | **6.541e-02** | **4.182e-03** | 1.475e-03 | **1.358e-05** |
| close | NaN | True | 0 | 0 .. 1,270 | 5.204e-02 | 4.073e-03 | **1.482e-03** | 1.030e-05 |
| close | +inf | True | 0 | 299 .. 1,217 | 5.429e-02 | 3.705e-03 | 1.225e-03 | 7.771e-06 |

The bolded cells are the worst of the six, and they are what the module's
docstring and the test module quote. ⚠ They are not all in one row, which
is the trap this table has set twice: the ±inf legs are worst at k = 0,
50 and 300, and the `close`/NaN plant is worst at k = 100 (1.482e-03
against 1.475e-03). Revision 1 of this port quoted the `close`/NaN row
for all four and called it "worst" (understating k = 0 by 26%); revision
2 quoted the ±inf row for all four and mis-attributed k = 100.

⚠ **The `0` at the bottom of three of the `moved` ranges is why this is
measured at five bars and not one.** A NaN high removes two of the three
legs — `high - low` and `|high - prev close|` — and on a bar where the
max was the third one, `|low - prev close|`, the true range does not move
at all. At bar 700 of this walk that is exactly what happens, so a
single-plant measurement would have reported "a NaN high changes
nothing".

### §G2 an INFINITE price is not the same as a NaN, and still never reaches the output

The natural claim — "pandas turns an infinity into a NaN, so an inf bar
and a NaN bar are the same column", which is true of `j_gator` — is
**wrong here, and measuring it is what found that**. `high - low` at an
infinite high is `inf`, which WINS the three-way max rather than being
skipped by it, so the true range at that bar IS infinite:

| planted (bar 700) | TR infinite on | TR NaN on | ATR(13) infinite on | ATR(13) NaN on |
|---|---|---|---|---|
| inf high | 1 bar | 0 | 0 | 0 |
| inf low | 1 bar | 0 | 0 | 0 |
| inf close | 1 bar | 0 | 0 | 0 |

What saves the column is the next step: pandas converts that infinity to
NaN before the `ewm` kernel runs, and `ewm` skips a NaN observation, so
the ATRs carry through the bar and nothing infinite survives:

| leg | planted | fired | finite | infinite | vs the NaN plant, max \|diff\| |
|---|---|---|---|---|---|
| high | ±inf | 1,497 | 1,497 | 0 | 6.288e-02 |
| low | ±inf | 1,497 | 1,497 | 0 | 6.937e-02 |
| close | ±inf | 1,497 | 1,497 | 0 | 7.353e-02 |

⚠ **This is a pandas BEHAVIOUR the module relies on**, and
`tests/test_j_damiani.py::test_an_infinite_price_never_reaches_the_output`
pins all three legs of it — that the true range goes infinite, that the
ATR does not, and that the column stays finite — so an upgrade which
stops doing it fails here rather than silently shipping an infinite
feature. The fix in that case is one line,
`true_range = true_range.where(np.isfinite(true_range))`.

### §G3 the one guard, `slow.where(slow > 0.0)`

It changes no reading **on any of the eight frames**: §A2 measures the
module bit-equal to the unguarded form on all of them. So what it buys
has to be stated exactly, and there are two things, one here and one in
§G5(d).

Here, at a real price scale: the `0 / 0` of a frame with no movement is
decided HERE rather than inside pandas.

| | under `np.errstate(all="raise")` |
|---|---|
| module on `flat` | fired 0, raised nothing |
| module on `walk` | fired 1,497, raised nothing |
| unguarded on `flat` | fired 0, raised nothing |
| unguarded on `walk` | fired 1,497, raised nothing |
| pandas `fast / slow` on `flat` | NaN on 1,500 of 1,500, raised nothing |
| **numpy** `fast / slow` on `flat` | **FloatingPointError: invalid value encountered in divide** |

Today's pandas evaluates the division and suppresses numpy's
invalid-operation flag itself, so the unguarded form survives too — the
last two rows are what makes that a measurement rather than a guess.
The guard is what makes the module's documented behaviour ("a frame with
no movement reads NaN and raises nothing") independent of that pandas
internal. `test_what_the_divisor_guard_buys` pins both halves, so if
pandas ever stops suppressing, the test says so and the guard is already
the fix.

⚠ **Do not read §A2 and this table as "the guard is dead code".** §G5(d)
measures the regime where removing it ships an `inf`, and
`test_the_divisor_guard_is_not_a_no_op_at_subnormal_scale` is the test
that would catch a "simplification" made on the strength of this section
alone.

### §G4 degenerate frames

All-NaN, all-zero, all-negative and all-one-price 60-bar frames: no float
error is reachable under `np.errstate(all="raise")`, and 0 of 60 bars
fire in each. The last of the four is the one that matters — a frame of a
repeated price is a halted instrument, not a pathological input.

### §G5 NO guard on the division's RESULT, and why

§A5(e) bounds `base` by `SLOW/FAST` = 3.076923 in exact arithmetic. The
four adversarial frames below are what that is worth: (a) .. (c) find no
overflow, and (d) finds both the bound's real exception and the one
infinity the DIVISOR guard already removes.

**(a) a first bar whose `high - low` OVERFLOWS to `inf`** (1e+308 against
−1e+308), then a normal 600-bar walk: `TR[0] = inf`, and the column fires
on **596 of 600, all finite**, max 1.361120. The infinite true range is
skipped by the mechanism of §G2; the 4 missing bars are that skipped
observation plus the loop's three.

**(b) the cross-scale frame** — high/low at 1e+300 against a close at
1e−300, which is the frame `j_gator` discloses an overflow on: **57 of 60
fired, all finite**, max 4.679390. The reason is structural rather than
lucky: the close enters only through the true range's gap legs, never as
a divisor, so the ratio does not care about its scale.

**(c) a huge bar followed by 32,000 bars of nothing**, which is where a
divisor could underflow while its numerator had not:

| bar | ATR(13) | ATR(40) | base | column |
|---|---|---|---|---|
| 1 | 9.231e+15 | 9.750e+15 | 9.467e-01 | NaN |
| 1,000 | 1.729e-19 | 1.011e+05 | 1.711e-24 | 1.613e-24 |
| 5,000 | 1.547e-158 | 1.055e-39 | 1.467e-119 | 1.382e-119 |
| 10,000 | 2.964e-323 | 1.112e-94 | 2.666e-229 | 2.731e-229 |
| 20,000 | 2.964e-323 | 1.237e-204 | 2.397e-119 | 2.456e-119 |
| 29,000 | 2.964e-323 | 1.361e-303 | 2.178e-20 | 2.232e-20 |
| 31,999 | 2.964e-323 | 9.387e-323 | 3.158e-01 | 3.158e-01 |

It is the NUMERATOR that underflows first — the fast ATR forgets faster —
so the ratio falls to 0 rather than rising to `inf`. Neither ATR ever
reaches exactly 0 (printed as `None` for both): a subnormal times 0.975
rounds back to itself, so both STALL just above zero. Over the whole
frame `max base` = 1.000000 (bar 0's seed), which does not exceed
`SLOW/FAST`, and the column fires on 31,997 of 32,000 with **0 infinite**
readings, max 1.158444, min 2.995e-232.

The stall is the obvious candidate for breaking §A5(e)'s bound — a
numerator stuck at the subnormal floor over a still-falling denominator —
and on this frame it does not: `max base` = 1.000000. The numerator is
pinned at 2.964e-323 while the denominator falls from 9.750e+15 to
9.387e-323, so the ratio stays **at or below 1** throughout — bar 0's
seed, `TR[0]/TR[0]` = 1.0 exactly (§A3), is the maximum — and never
approaches an overflow. (An earlier revision of this paragraph said "both are trapped
between 5e-324 and ~3e-323" — the table two rows above prints the
denominator at 9.387e-323, outside that interval, so the sentence was
wrong about its own numbers.)

**(d) a true range of a few ULPS, which is where the bound DOES break**
— and the stall above is not it. Subnormal multiplication rounds
ABSOLUTELY, so `1/13 * k` and `1/40 * k` both round to a whole number of
ulps and the ratio is whatever those two integers say. A frame flat for
50 bars and then moving by `k` ulps (high only, low and close at 0.0, so
the true range IS that one number):

| k (ulps) | ATR(13)/ulp | ATR(40)/ulp | base | > SLOW/FAST | column max | UNGUARDED base |
|---|---|---|---|---|---|---|
| 1 | 0 | 0 | NaN | False | NaN | NaN |
| 3 | 0 | 0 | NaN | False | NaN | NaN |
| 7 | 1 | 0 | NaN | False | NaN | **inf** |
| 13 | 1 | 0 | NaN | False | NaN | **inf** |
| 40 | 3 | 1 | 3.0000 | False | 4.1250 | 3.0000 |
| 59 | 5 | 1 | **5.0000** | **True** | 6.8750 | 5.0000 |
| 100 | 8 | 3 | 2.6667 | False | 2.6966 | 2.6667 |
| 1,000 | 77 | 25 | **3.0800** | **True** | 3.7921 | 3.0800 |

Two findings, and both correct a claim this file made before measuring
it.

1. **The weight bound is exact-arithmetic and THIS is where floating
   point breaks it** — not the stall of (c). Worst `base` over those
   eight frames: **5.000000** against `SLOW/FAST` = 3.076923, i.e.
   1.63× it. The column's own reading there, 6.8750, still sits inside
   §A5(e)'s published envelope (−5.5360, 8.6129), but the envelope is
   derived FROM the bound, so it is not a bound in this regime either.
   Pinned by
   `test_the_bound_is_exact_arithmetic_and_subnormals_break_it`.
2. **The divisor guard is not a no-op after all.** At k ≤ 13 the slow ATR
   rounds to exactly 0 while the fast one does not, and the UNGUARDED
   column reads `inf` — 300 bars over these eight frames. The guard
   turns that into NaN, which is the real answer to "why is nothing
   guarding the division's result": the only reachable infinity has
   already been removed one step earlier. Pinned by
   `test_the_divisor_guard_is_not_a_no_op_at_subnormal_scale`.

⚠ None of this is reachable from market data — it needs prices of order
1e-322 — and it is here because a bound in a shipped docstring is worth
exactly as much as the adversarial frame that failed to break it.

### §G6 where `base` can be NaN at all

Only on a LEADING run of bars — while the SLOW ATR is still exactly 0,
which means either nothing has moved yet or (§G5(d)) everything that has
moved rounded to zero at subnormal scale. A Wilder EWMA of non-negative
observations that is positive once stays positive, and §G5(c) measures
the one thing that could end that — an underflow — STALLING above zero
rather than reaching it, so there are no mid-series holes.

Measured as "the NaNs are a contiguous prefix" on all eight frames, on
the 32,000-bar underflow frame (§G5(c)), and on a frame built so the NaN run
HAS to end mid-series: 7 ulps of movement at bar 50, which rounds the
slow ATR to zero, then a real move at bar 100 — **NaN on 103 bars, still
a prefix**, first fired bar 103, 97 of 200 fired, 0 infinite. Pinned by
`test_the_leading_prefix_survives_a_frame_built_to_break_it`, because the
eight frames alone cannot tell "always a prefix" from "these frames are
easy".

(An earlier revision of this section said "plus the underflow of (c)
above", which §G5(c) refutes: the smoothers stall above zero, the
32,000-bar frame's NaNs are still only the loop's three, and no NaN
mechanism beyond the leading run was ever measured.)

The nearest thing to a mid-series hole a caller can reach is a bar whose
high AND low are both NaN, which leaves the true range with no surviving
leg at all. `ewm` skips that observation and the ATRs carry, so `base`
still does not go NaN: at bar 700 of the walk, `base` is NaN on **0**
bars, the column fires on 1,497 of 1,500, and the worst relative change
against the clean column is 5.713e-02.

So the `base`-is-NaN branch of the loop (`continue`, and the next bars
recursing from 0.0 again) is reachable only through a leading run. It is
kept because it is the prototype's and because `flat`/`flat-start` run
through it, not because a bad price can trigger it.

⚠ Both of §G5(d)'s findings reached this file through **Fletcher review
round 1**, which built the subnormal frame this session had not. Round 1
also struck §F's guard-run bullet and §A4's unprinted "~1.26"; all three
were the repo's named dominant defect — a claim written before it was
measured — and all three are now printed by
`docs/measure_j_damiani.py` and asserted by `tests/test_j_damiani.py`.
**Round 2 then struck the fix itself in two places**: §F's full-suite
count was still round 1's run (8,933 against 8,936, three tests out of
date), and `docs/measure_j_damiani.py` was still PRINTING the two
sentences this file had corrected — so a reader who ran the command the
receipt points at got the refuted prose. Both are fixed in the script,
not only here. `docs/reviews/auto-2026-11-14-j-damiani/01-j-damiani.md`
is the log.

## §L what the column reads — in-fork overlap, SYNTHETIC

Spearman \|ρ\| against shipped fork columns on the six varying frames.
⚠ This is **not Gate E**: Gate E is 687 ENGINE comparators over 89 real
BIST frames and the launcher runs it. These are synthetic frames and a
handful of neighbours, chosen as the nearest questions this fork already
answers.

| comparator | walk | trend | range-bound | grid | heavy-tailed | jump | max |
|---|---|---|---|---|---|---|---|
| `natr:NATR_14` | 0.7239 | 0.7817 | 0.8013 | 0.8362 | 0.7205 | 0.8151 | **0.8362** |
| `chop:CHOP_14_1_100` | 0.0545 | 0.1798 | 0.1190 | 0.0267 | 0.3120 | 0.0838 | 0.3120 |
| `volvol:VOLVOL_20_14` | 0.1541 | 0.1609 | 0.1405 | 0.2006 | 0.2614 | 0.2007 | 0.2614 |
| `massi:MASSI_9_25` | 0.1803 | 0.1742 | 0.1059 | 0.2297 | 0.0472 | 0.2103 | 0.2297 |
| `atr_ma_multiple:ATRMAX_14_50` | 0.2186 | 0.0505 | 0.1007 | 0.1910 | 0.0524 | 0.1356 | 0.2186 |
| `rvi:RVI_14` | 0.1348 | 0.1871 | 0.0439 | 0.1086 | 0.1256 | 0.0342 | 0.1871 |
| bare `ATR(13)/ATR(40)` | 0.9049 | 0.8989 | 0.9142 | 0.9322 | 0.8978 | 0.9194 | 0.9322 |

Three things worth saying about that table.

1. **`natr` at 0.8362 is above the 0.80 DISCLOSE_GAP line** — on six
   synthetic frames, which is a disclosure and not a gate. `natr` is
   `ATR / close`, a LEVEL of volatility, where this is a ratio of two
   horizons; they are not the same question, and on real data the screen
   measured the prototype against `natr_percentile` at 0.7302 rather
   than against `natr` itself.
2. **The screen's own fork-overlap stage put `massi` nearest instead**,
   at 0.7023 on 12 REAL frames, where this table puts it sixth at
   0.2297. The two universes disagree — 12 real frames at `Category`
   defaults against six synthetic ones — and neither is Gate E. Both are
   reported rather than reconciled, because this worktree cannot measure
   the real one.
3. **The bare ratio row is §A5(d)'s**, repeated here because it is the
   highest number in the table: the thing this column is nearest to is
   the ATR ratio it is built from.

## §W the dictionary's 150-character cut

`docs/gen_indicator_dictionary.py`'s `desc()` shows
`d[:150].rsplit(' ', 1)[0]` of the docstring's first paragraph, and only
when it EXCEEDS 150 characters — so the budget is 150 and the penalty for
passing it is a whole WORD, not a character. The paragraph is

> Short-term true range over long-term true range, run through a
> three-bar feedback loop: how far volatility stands above its own slower
> level.

**141 characters**, surviving whole, and the script grows it until it
loses a word: it does so at 151, i.e. **9 characters to spare**.
`test_the_docstrings_first_paragraph_survives_the_dictionary_cut` runs
the generator's OWN `desc` (lifted out by `ast`, so importing it does not
run the whole probe) against both the paragraph and a 151-character
version, so a change to the generator's cut fails the test and not only a
change to this sentence.

## §Z cost

⚠ **Milliseconds are this machine's and this run's**, best-of-5 — and so
is everything DERIVED from them: the loop-share column, the µs/bar
figures, and the ratio between the two loop spellings are all quotients
of timings that move. Four runs of §Z printed 32.35 / 30.46 / 30.13 /
30.78 ms for the same 100,000 bars, loop shares from 30.9% to 40.9% at
1,000 bars, and spelling ratios from 13.4 to 14.7. **The only pinned
numbers in this section are the traced peak, the linear shape, the
ordering, and the bit-identical output**; everything else is tabled with
its spread so that no digit here can be mistaken for a claim.

**One run of §Z**, with the span over the four runs of §Z made for this
receipt in the last column, so the reader can see how much of this is
noise:

| bars | column | ratio only | the loop's share | traced peak | spread over four runs |
|---|---|---|---|---|---|
| 1,000 | 1.39 ms | 0.96 ms | 30.9% | 0.1 MB | 1.39 .. 1.66 ms, share 30.9 .. 40.9% |
| 10,000 | 3.69 ms | 1.98 ms | 46.4% | 1.0 MB | 3.66 .. 3.73 ms, share 39.5 .. 48.4% |
| 100,000 | 30.46 ms | 14.78 ms | 51.5% | 9.9 MB | 30.13 .. 32.35 ms, share 50.7 .. 53.4% |
| 400,000 | 119.92 ms | 56.32 ms | 53.0% | 39.7 MB | 119.09 .. 123.29 ms, share 50.6 .. 53.5% |

0.292 µs per bar at 400,000 bars (0.284 .. 0.316 over those runs). Two
`ewm` passes, one three-way `max`, and one Python loop over the bars:
linear in bars, with **about half** the time in the loop — that share,
not its digits, is the claim.

**And what the loop's SPELLING costs**, since it is half the run.
`_volatmeter` works on Python floats (`base.tolist()`) and tests NaN with
`x != x`; the obvious spelling keeps the numpy array and calls
`np.isnan`. At 400,000 bars:

| spelling | time | per bar | spread over four runs |
|---|---|---|---|
| shipped | 61.76 ms | 0.154 µs | 61.26 .. 66.75 ms |
| `np.isnan` on a numpy array | 904.90 ms | 2.262 µs | 876.52 .. 904.90 ms |

**bit-identical outputs** (printed as `True`), a factor of **13 to 15**
over those four runs (13.4, 14.5, 14.6, 14.7) — stated as a shape for the
same reason as every other quotient here. That
is why the shipped loop is written the way it is, and why §A5 and §A3 read
the loop through the OBVIOUS spelling instead: a figure about the FILTER
should not depend on the shipped loop's micro-optimisation.

⚠ The `tolist()` is also why the traced peak is larger than the ratio
alone needs: a Python list of 400,000 floats. 39.7 MB against
`j_gator`'s 25.6 MB at the same length.

---

## Verdict

| gate | result |
|---|---|
| A correctness | **met.** The issue's formula spelled independently, bit-equal on 1,497 of 1,497 bars of each of six frames (§A1); bit-equal to the screen prototype on all eight (§A2); the four alternative readings of "ATR" priced (§A4); the loop characterised as a filter (§A5). |
| B causality | **met.** 0 of 36 offsets on each of six frames; five source-read mutants, each live on every shared bar and caught at 36 of 36 on every frame, each catch 5.8e-02 .. 1.9e-01 loud (§B, §B1). |
| C reachability | **synthetic only.** 1,497 of 1,500 bars with 1,497 distinct values on each varying frame (§C1). Real-data counts are owed with Gate E. |
| D scale-free | **met.** ×8/×64 bit-identical on every frame and at 1e−6 / 1e+6 / 1e+100; ×10/×3.7/×0.1/×1.0000001 within 2.098e-14 against a 1e-9 bound, the same worst figure under reduced CPU dispatch; `0 < fires < n` on seven of eight frames, with `flat` pinned separately (§D). |
| E attribution | **pending, run by issue-solver after this session** (§E). The screen measured the PROTOTYPE — which this port is bit-equal to — at **DISCLOSE**, 0.7621 vs `ATR_Ratio_5_20` (§E0). |
| F suites | **this worktree:** 191 module tests, the same 191 under reduced CPU dispatch, full suite in §F1 (3 failed, 8,936 passed, 85 skipped — `dev`'s clean-checkout failures plus the owed Gate E row). The launcher runs both repos' suites in clean worktrees. |

Six things a reader should carry away:

1. **The feedback loop is a resonator** — stable (pole 0.872175), unity
   gain at DC, peak 3.674235 at a 7.47-bar period — **but it does not
   re-rank the column**: 0.8978 .. 0.9322 Spearman against the bare ATR
   ratio (§A5).
2. **A flat frame reads NaN, not 0.0**, and a flat prefix delays the
   first reading to bar 53 of a 50-flat frame (§C1).
3. **The NaNs are always a leading prefix**; a bad price perturbs the
   column but empties no bar (§G1, §G6).
4. **An infinite price is not the same as a NaN here** — it wins the
   true range's max — and still never reaches the output, on a pandas
   behaviour this module relies on and pins (§G2).
5. **The column is bounded at any real price scale** by the ratio's own
   weight bound, `SLOW/FAST` = 3.076923, which is attained to 1 ulp;
   through the loop, (−5.5360, 8.6129) (§A5(e)). ⚠ That is
   exact-arithmetic: at subnormal true ranges `base` reads 5.0 and the
   column 6.8750, and the divisor guard is what keeps the same regime
   from reading `inf` (§G5(d)).
6. **Gate E decides the band**, and the screen's figure on the identical
   prototype is DISCLOSE rather than SHIP (§E, §E0).

**FOUR Fletcher review rounds, 15 findings, all applied** (one NIT
declined with a reason: `pandas_ta/core.py` is not alphabetical in that
region). Round 4 returned PASS, and five of its findings landed after
that verdict, so they are the only changes no reviewer has seen —
`docs/reviews/auto-2026-11-14-j-damiani/99-summary.md` lists them.
**Not one finding in four rounds was about the mathematics**: every
reviewer re-ran `docs/measure_j_damiani.py` and reported each table
reproducing cell for cell, and round 4 re-ran the full suite, the
reduced-dispatch suite and the three Gate F guard commands as well. All
fifteen were the repo's named dominant defect — a claim written before
it was measured — and the shape worth carrying forward is that **a
correction applied to three of four prose surfaces is not a
correction**: round 1 struck "~1.26", rounds 1 and 2 fixed it in the
receipt, the module docstring and the test docstring, and round 3 found
it still standing in `docs/MLCompanionContract.md`, the one document a
consumer opens. Round 2's pair was the same shape one level down — the
receipt corrected against a measurement script that still printed the
refuted sentence. Two findings changed the deliverable rather than its
prose, and both came from round 1 building an adversarial frame this
session had not: §G5(d)'s subnormal break of the weight bound, and the
discovery that the divisor guard is what removes the only reachable
`inf`.

## Decisions this session made, and why

Nine, all recorded as ASSUMPTIONs in
`docs/reviews/auto-2026-11-14-j-damiani/00-manifest.md` because
`AskUserQuestion` is unavailable in a headless run and the skill's rule is
to take the smaller scope:

1. **One column, the volatility line.** The issue's title and its quote
   name it, and no threshold line was screened, so one column is both the
   quote and the smaller scope.
2. **No parameter surface.** 13 and 40, and the loop's 0.5 / 1 / 3, are
   the source's constants; a `fast=`/`slow=` surface would ship
   combinations nothing has measured.
3. **"ATR" read as Wilder's `alpha = 1/n`, `adjust=False`, seeded at the
   first true range**, on the issue's wording and the prototype and NOT
   on jesse's unread source (§A4 prices all four alternatives; (c), the
   alpha, is the one that changes the smoother rather than its warm-up).
4. **The true range spelled in the module, not imported.** This fork's
   `true_range` adds an epsilon to every bar once any bar has
   `high == low`, and NaNs bar 0; §A4(d) measures both divergences
   rather than assuming they are negligible.
5. **Category `volatility`**, where `natr`, `massi` and `atr` live.
6. **Name `j_damiani`, column `J_DAMIANI_13_40`** — the issue's candidate
   name, and the suffix is the two ATR lengths.
7. **No invented warm-up**: the column fires from bar 3, as the formula
   and the prototype do, and the early transient is kept (§A3).
8. **One guard, on the divisor only**, with §G2 measuring that an
   infinite price needs none, §G3 stating what the guard buys at a real
   price scale, and §G5(d) measuring the subnormal regime where it is the
   only thing between this column and an `inf` — which is also the answer
   to "why no guard on the division's result".
9. **Gate A is a tolerance against the independent oracle and
   bit-equality against the prototype** (§A1, §A2).

## §F1 suite output

```
$ python -m pytest tests/test_j_damiani.py -q
191 passed

$ python docs/measure_j_damiani_cpu.py
numpy 1.26.4
NPY_DISABLE_CPU_FEATURES = 'AVX512F AVX512_SKX AVX2 FMA3'
dispatchable features still enabled: ['SSSE3', 'SSE41', 'POPCNT', 'SSE42',
 'AVX', 'F16C', 'AVX512CD', 'AVX512_CLX', 'AVX512_CNL', 'AVX512_ICL']
191 passed
```

```
$ python -m pytest tests/test_wiring_accessors.py tests/test_altport2_ports.py -q
1 failed, 85 passed, 3 skipped
E  AssertionError: Category total 341, expected 344
```

```
$ python -m pytest -q
3 failed, 8936 passed, 85 skipped in 229.49s (0:03:49)
```

(the last of three full-suite runs this session, made after every edit
above; the counts were identical in the previous one at 251.99s, the
elapsed time being a timing figure and not a claim)

The three failures are `dev`'s clean-checkout failures and `j_damiani` is
the cause of none of them beyond being named in the third:

* `tests/test_pine_coverage_csv.py::test_audited_rows_carry_their_evidence`
  — the untracked `docs/pine/` citations, recorded in `CLAUDE.md`'s
  *Known breaks*;
* `tests/test_altrepo_talib_csv.py::test_regenerating_reproduces_the_committed_rows`
  — needs the sibling `../AlternativeRepos` checkout, which this
  worktree does not have;
* `tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
  — the owed Gate E rows, which now read
  `['arch_lm', 'diff2_acf1', 'edge', 'firstzero_ac', 'halflife',
  'j_damiani', 'lumpiness', 'mtd_ret']`. That is this port's one
  expected failure: CI into `dev` sets `GATE_E_PENDING_OK=1` and turns
  it into a skip whose reason starts "Gate E owed", and the receipt
  session records the row.
