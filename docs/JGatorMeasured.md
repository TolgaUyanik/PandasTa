# J-GATOR — `j_gator`, measured

PandasTa issue **#104** (parent #31 ALPHASETS, screen of 2026-10-24).
Module `pandas_ta/momentum/j_gator.py`, column **`J_GATOR_13_8_5`**.
Tests `tests/test_j_gator.py` (137).

Every number in §A, §B, §C, §D, §G, §L, §W and §Z is printed by
`python docs/measure_j_gator.py` on this worktree (**pandas 2.3.3, numpy
1.26.4** — which that script prints as its first line, so this parenthesis
is a quote and not a guess), section by section. The headings take their
letters from the script. §E and §F are headings of this file only.

What does NOT come from that command, marked again where it appears:

* **§Z's milliseconds**, which it does print but which are not a claim:
  they are this machine's and this run's, and two runs of §Z on one
  worktree printed 6.33 ms and 4.12 ms for the same 100,000 bars. The
  claims there are the traced peak, the linear shape and the ordering.
* **§E**, which is the launcher's Gate E run — **pending, run by
  issue-solver after this session**.
* **§E0**, the 2026-10-24 screen's figures, measured on the PROTOTYPE and
  quoted from issue #104.
* **§F**, which is pytest's own output.
* **§C2's dictionary and contract deltas**, which are read off
  `git diff docs/IndicatorDictionary.md` and re-derived against the live
  package by
  `tests/test_ml_companions.py::test_the_contract_quotes_the_dictionarys_actual_ml_form_counts`
  and `tests/test_readme_counts.py`.
* **the reduced-CPU figures**, which come from
  `python docs/measure_j_gator_cpu.py A1 D` and are marked as such.

```
mid     = (high + low) / 2
jaw     = SMMA(mid, 13) displaced 8 bars
teeth   = SMMA(mid, 8)  displaced 5 bars
lips    = SMMA(mid, 5)  displaced 3 bars
J_GATOR = (|jaw - teeth| - |teeth - lips|) / close
```

**Source.** jesse indicators (MIT), `gatorosc`, as issue #104 quotes it:
"`|jaw-teeth| - |teeth-lips|; jaw = SMMA(mid,13) lag 8, teeth =
SMMA(mid,8) lag 5, lips = SMMA(mid,5) lag 3`". The `/ close` is this
fork's, from the screen prototype's scale-free form.

⚠ **jesse is not installed in this worktree and web access is
unavailable.** It is an ATTRIBUTION, not an oracle:
`tests/test_j_gator.py::test_the_source_library_is_not_installed_here`
records that, so the claim cannot rot into "checked against jesse". What
Gate A checks is the formula the issue quotes, spelled two independent
ways (§A1, §A2).

⚠ **One column, not two.** The issue quotes a single DIFFERENCE, and that
is what ships; whether jesse's own `gatorosc` also returns the two spreads
apart is not something this worktree can see. The two spreads the formula
is built from are priced separately in §L2 anyway, because shipping them
would have been the wider scope.

The screen prototype is `docs/issues/screen/ind_screen.py` candidate
`j_gator` (that file is gitignored, so it exists only on the owner's
machine):

```python
mid = (h + l) / 2
sm = lambda n: mid.ewm(alpha=1 / n, adjust=False).mean()
jaw, teeth, lips = sm(13).shift(8), sm(8).shift(5), sm(5).shift(3)
return ((jaw - teeth).abs() - (teeth - lips).abs()) / c
```

**Seven frames**, 1,500 bars each, built by the script and retyped with
the same seeds in the test module: `walk`, `trend`, `range-bound`,
`grid` (a walk on a 0.01 tick grid), `heavy-tailed`, `jump` (a ×1.5 gap at
bar 700) and `flat` (a constant price, where all three lines coincide and
the column is exactly 0.0). The six excluding `flat` are the script's
`VARYING`. Each frame fires on **1,492** bars — the warm-up is the
longest LAG, 8, and nothing else — which makes the pooled figure 10,444
over the seven.

---

## §A1 Gate A — the issue's formula, spelled independently

A hand-written Python recursion with hand-written lags, sharing no code
with the module, against the module:

| frame | masks equal | bars | bit-equal | max \|diff\| |
|---|---|---|---|---|
| walk | True | 1,492 | 1,492 | 0.000e+00 |
| trend | True | 1,492 | 1,492 | 0.000e+00 |
| range-bound | True | 1,492 | 1,492 | 0.000e+00 |
| grid | True | 1,492 | 1,492 | 0.000e+00 |
| heavy-tailed | True | 1,492 | 1,492 | 0.000e+00 |
| jump | True | 1,492 | 1,492 | 0.000e+00 |
| flat | True | 1,492 | 1,492 | 0.000e+00 |

Measured bit-equal on every frame, and **the test asserts a relative bound
of 1e-12 rather than bit-equality**. The two spellings are not obliged to
round the same way: pandas' `ewm` computes `((1-a)*s + a*x) / ((1-a) + a)`
and the oracle computes `(1-a)*s + a*x`, which agree only because
`(1-a) + a` is exactly 1.0 for these three alphas on this machine. The
same table under numpy's `AVX512F AVX512_SKX AVX2 FMA3` dispatch disabled
(`python docs/measure_j_gator_cpu.py A1`) is also 0.000e+00 on all seven.

## §A2 Gate A — the screen prototype, bit for bit

The prototype performs the SAME operations in the same order (pandas'
`ewm`), so this limb is exact and machine-independent, and it is asserted
bit-exactly: **1,492 of 1,492** bars on each of the seven frames, max
\|diff\| 0.000e+00, NaN masks identical. `(h + l) / 2` and `0.5 * (h + l)`
agree on all bars (both are exact), so the module's spelling of `mid` is
not a difference.

**This is the limb that ties the port to §E0's Gate E figures:** the
prototype the screen measured and this module are the same column, bit for
bit, on every synthetic frame tried.

## §A3 the lag is a BACKWARD read, and the warm-up is that lag

A line "displaced 8 bars into the future" on a chart is, for the value at
bar T, the smoothed value of bar T − 8. Checked against an explicit index
walk, per line:

| line | `shifted[T] == line[T - lag]` | NaN bars |
|---|---|---|
| SMMA(13) lag 8 | True on all 1,492 | 8 |
| SMMA(8) lag 5 | True on all 1,495 | 5 |
| SMMA(5) lag 3 | True on all 1,497 | 3 |

The column therefore first fires at bar **8** and has exactly 8 NaNs:
1,492 of 1,500. There is no `length - 1` warm-up, because the EWMA is
seeded at bar 0 — which is also §A4's subject.

`MIN_BARS` = `JAW[0] + JAW[1]` = **21** is a floor on the INPUT, not the
warm-up: a 20-bar frame returns `None` (`verify_series` declines) and a
21-bar frame fires on 13 bars.

⚠ **The early bars are a transient and they are kept.** Bar 8's jaw is
`SMMA(13)` of a single observation. The source and the prototype do the
same, and §A4 measures how long the transient lasts; NaN-ing it away would
depart from the form Gate E measured.

## §A4 WHICH SMMA — the seed and the alpha, priced

The issue says "SMMA" and the prototype spells it `ewm(alpha=1/n,
adjust=False)`, seeded at the FIRST value. Three other readings of that
name exist. Two are a WARM-UP difference; the third, the alpha, is a
different column.

⚠ **jesse's own smoother is not read here**, so none of this is evidence
about what jesse computes. The reading rests on the issue's word "SMMA"
— whose standard meaning is Wilder's `alpha = 1/length` — and on the
prototype that Gate E measured in §E0.

**(a) SMA-seeded SMMA** (the usual textbook "smoothed moving average",
and TradingView's `ta.rma`): the same recursion seeded with
`SMA(x[:length])` at bar `length - 1`.

| frame | shared | bit-equal | max \|diff\| | Spearman |
|---|---|---|---|---|
| walk | 1,480 | 1,076 | 1.874e-03 | 0.9998 |
| trend | 1,480 | 1,049 | 4.464e-03 | 0.9981 |
| range-bound | 1,480 | 1,079 | 5.554e-03 | 0.9989 |
| grid | 1,480 | 1,057 | 6.820e-03 | 0.9976 |
| heavy-tailed | 1,480 | 1,080 | 6.174e-03 | 0.9978 |
| jump | 1,480 | 1,095 | 4.563e-03 | 0.9992 |

and the convergence on the walk — max \|diff\| over bars ≥ k, monotone by
construction, against a column whose max \|value\| is 2.442e-02:

| from bar | 8 | 20 | 50 | 100 | 200 | 400 |
|---|---|---|---|---|---|---|
| max \|diff\| | 1.874e-03 | 1.874e-03 | 2.595e-04 | 5.270e-06 | 1.956e-09 | 4.397e-16 |

**(b) this fork's `rma`** — pandas' `ewm` at its DEFAULT `adjust=True`
with `min_periods=length`, a third reading of the same name:

| frame | shared | bit-equal | max \|diff\| | Spearman |
|---|---|---|---|---|
| walk | 1,480 | 42 | 4.967e-03 | 0.9981 |
| trend | 1,480 | 91 | 9.744e-03 | 0.9943 |
| range-bound | 1,480 | 50 | 1.007e-02 | 0.9967 |
| grid | 1,480 | 53 | 1.415e-02 | 0.9932 |
| heavy-tailed | 1,480 | 54 | 9.448e-03 | 0.9964 |
| jump | 1,480 | 64 | 4.599e-03 | 0.9991 |

**(c) a plain EMA** — `alpha = 2/(n+1)`, i.e. `ewm(span=n, adjust=False)`,
which is what reading "SMMA" as "EMA" would give. This is the reading the
issue's wording excludes, and the only one of the three that changes the
smoother's MEMORY rather than its warm-up. `adjust=False` is held fixed —
it is the axis (b) isolates — so the alpha is the only difference from the
shipped column:

| frame | shared | bit-equal | max \|diff\| | Spearman |
|---|---|---|---|---|
| walk | 1,492 | 0 | 2.583e-02 | 0.5509 |
| trend | 1,492 | 0 | 2.547e-02 | 0.7075 |
| range-bound | 1,492 | 0 | 4.141e-02 | 0.6065 |
| grid | 1,492 | 0 | 2.735e-02 | 0.5716 |
| heavy-tailed | 1,492 | 0 | 6.389e-02 | 0.5165 |
| jump | 1,492 | 0 | 7.218e-02 | 0.5490 |

So the SEED is a **transient** worth 1.9e-3 to 1.4e-2 early and 4.4e-16
from bar 400, while the ALPHA is the **load-bearing** reading: 0.5165 ..
0.7075 against 0.9932 .. 0.9998, with max \|diff\| of the same order as
the column's own range (§C1). A port that read "SMMA" as "EMA" would have
shipped a different feature and invalidated §E0's figures.

`tests/test_j_gator.py` pins the shape of each: the seed variants
different somewhere before bar 50 and agreeing absolutely to 1e-12 from
bar 400 with Spearman > 0.99 (and `rma` "not all bars equal", Spearman >
0.98); the EMA reading under 1% of bars in common, max \|diff\| > 1e-3 and
Spearman in 0.40 .. 0.80. Not the digits.

⚠ The bit-equal counts in all three tables are last-bits facts, not
claims: they are printed here and nowhere asserted.

⚠ **Review round 1 corrected a claim here.** The first version of the
module docstring and of this section's decision log cited "jesse's
`numpy_ewma`" as corroboration for the alpha. That function name appears
nowhere in issue #104, in the screen's `candidates.csv`, or in the
prototype — it was asserted from outside the evidence, in a port that
states two paragraphs earlier that jesse cannot be read here. The citation
is gone, and (c) is the measurement that replaced it.

## §B Gate B — causality, five mutants and one honest gap

The blind sweep is 36 perturbation offsets (bars 1,464 … 1,499): every bar
≥ J multiplied by 1.03, and "caught" means at least one bar < J moved.
Each mutant is the SHIPPED module read off disk, one unique substring
replaced, `exec`'d in memory — never a re-implementation.

**The module itself: caught 0 of 36 on each of the six varying frames.**

| mutant | what it does | live (bars moved / shared) | caught of 36 |
|---|---|---|---|
| `jaw-lead` | `JAW = (13, -8)`: the jaw reads 8 bars ahead | 1,484 / 1,484 on all six | 36 on all six |
| `teeth-lead` | `TEETH = (8, -5)` | 1,371–1,453 / 1,487 | **5 … 30** |
| `lips-lead` | `LIPS = (5, -3)` | 1,489 / 1,489 on all six | 36 on all six |
| `output-early` | the column written one bar early | 1,491 / 1,491 on all six | 36 on all six |
| `divisor-lead` | the divisor is tomorrow's close | 1,485–1,491 / 1,491 | 36 on all six |

### §B1 why `teeth-lead` is the interesting one

Per frame: walk 30, trend **5**, range-bound 22, grid 12, heavy-tailed 29,
jump 25 of 36. That is a fact about the COLUMN, not a weak mutant:

> **Whenever the teeth line is the OUTER one of the three, it cancels.**
> If `teeth ≥ max(jaw, lips)` then `|jaw-teeth| - |teeth-lips|` =
> `(teeth-jaw) - (teeth-lips)` = `lips - jaw`, and symmetrically
> `jaw - lips` when the teeth are below both. The gator oscillator is the
> jaw-lips spread there and does not read the teeth at all.

Measured on the shipped column, over fired bars, with the agreement to the
signed jaw-lips spread on exactly those bars:

| frame | teeth outer | of | share | max \|identity diff\| | mutant's own outer share | sweep |
|---|---|---|---|---|---|---|
| walk | 288 | 1,492 | 0.1930 | 0.000e+00 | 0.7323 | 30 |
| trend | 53 | 1,492 | 0.0355 | 0.000e+00 | 0.9085 | 5 |
| range-bound | 420 | 1,492 | 0.2815 | 0.000e+00 | 0.6779 | 22 |
| grid | 300 | 1,492 | 0.2011 | 0.000e+00 | 0.7364 | 12 |
| heavy-tailed | 292 | 1,492 | 0.1957 | 0.000e+00 | 0.7176 | 29 |
| jump | 324 | 1,492 | 0.2172 | 0.000e+00 | 0.7108 | 25 |

A teeth line that reads 5 bars into the future is systematically outside
the jaw-lips pair — 0.6779 to **0.9085** of bars against the shipped
column's 0.0355 to 0.2815 — and on a trending frame it is outside almost
always, which is why the blind sweep nearly stops seeing it.

⚠ The catch count is NOT a monotone function of that share (grid 0.7364 →
12 catches against walk 0.7323 → 30), because the sweep reads only the
five bars J−5 … J−1 at each offset. The share explains the extreme case;
it does not rank the others.

### §B2 what carries Gate B for `teeth-lead`

Two things, neither of which is the blind count:

1. **Liveness.** It moves 1,371 to 1,453 of the ~1,487 shared bars on
   every frame — it is the column, back-dated.
2. **A mechanism-aware sweep.** An offset can only expose it if the
   unperturbed mutant has an INTERIOR teeth within its 5-bar reach.
   Among those offsets it is caught every time:

| frame | exposed offsets | caught among them | caught elsewhere | of |
|---|---|---|---|---|
| walk | 24 | 24 | 6 | 36 |
| trend | 5 | 5 | 0 | 36 |
| range-bound | 15 | 15 | 7 | 36 |
| grid | 11 | 11 | 1 | 36 |
| heavy-tailed | 20 | 20 | 9 | 36 |
| jump | 20 | 20 | 5 | 36 |

**95 of 95** pooled. The "caught elsewhere" column is the perturbation
itself flipping which line is outer; it is printed, not asserted. The test
asserts the implication plus a floor of one exposed offset per frame, so
neither limb can quietly become vacuous.

## §C Gate C — reachability

### §C1 synthetic

| frame | fired | of | distinct | >0 | <0 | ==0 | min | max |
|---|---|---|---|---|---|---|---|---|
| walk | 1,492 | 1,500 | 1,492 | 960 | 532 | 0 | −2.114e-02 | 2.442e-02 |
| trend | 1,492 | 1,500 | 1,492 | 1,343 | 149 | 0 | −9.624e-03 | 2.624e-02 |
| range-bound | 1,492 | 1,500 | 1,492 | 744 | 748 | 0 | −4.477e-02 | 2.963e-02 |
| grid | 1,492 | 1,500 | 1,492 | 926 | 566 | 0 | −2.614e-02 | 2.328e-02 |
| heavy-tailed | 1,492 | 1,500 | 1,492 | 922 | 570 | 0 | −9.666e-02 | 4.383e-02 |
| jump | 1,492 | 1,500 | 1,492 | 882 | 610 | 0 | −1.240e-01 | 4.459e-02 |
| flat | 1,492 | 1,500 | 1 | 0 | 0 | 1,492 | 0.0 | 0.0 |

The flat frame reads **exactly 0.0** on all 1,492 bars — a reading, not
missing data: all three lines coincide, so both spreads are zero. Pooled
over the seven frames: 10,444 bars, min −1.240384e-01, max 4.458722e-02,
mean 2.406780e-03, and \|value\| ≤ 0.1 on 10,443 of 10,444.

⚠ **The column is NOT bounded in [−1, 1] by construction.** It is a spread
difference over a price; those are the values the frames reach, not a
theorem. Nothing in the module or the tests claims a bound.

⚠ **The sign is informative and is not symmetric across regimes.** The
trending frame reads positive on 1,343 of 1,492 bars (the slow pair open
wider than the fast one) against the mean-reverting frame's 744 / 748.

### §C2 real data, and the dictionary

**Gate C's real-data limb is OWED with the Gate E run** (§E): the only
real frames in reach are the launcher's 89 ALTPORT-1 BIST frames.
`data/SPY_D.csv` is gitignored and absent, so there is no real frame in
this worktree.

`docs/IndicatorDictionary.md`, regenerated by
`python docs/gen_indicator_dictionary.py`, probes the live package and
tags the column **`SF`** with warm-up **8** — it fires on the probe and is
in neither the "Never fires" nor the "needs a companion" list. **Six counts
moved by one each:** 344 → **345** probed, 342 → **343** registered in
`Category`, 350 → **351** callable on `df.ta`, momentum 83 → **84**; and in
`docs/MLCompanionContract.md` 687 → **688** tagged columns, 326 → **327**
`SF`. `tests/test_readme_counts.py` and
`tests/test_ml_companions.py` re-derive all of those against the package.

## §D Gate D — scale-free

### §D1 ×8 / ×64, bit-identical

Every step is linear in the price — the EWMA's `(1-a)*s + a*x`, the
subtractions, the `abs` — and a power-of-two factor is exact at each of
them, so the final division by a close scaled by the same factor cancels
it exactly. **1,492 of 1,492 bars bit-identical on each of the seven
frames at both factors**, NaN masks identical, max \|diff\| 0.000e+00.
Asserted bit-exactly in the test module, because the operation sequence is
identical by construction and so is machine-independent.

At extreme price LEVELS, the same: at 1e−6, 1e+6 and 1e+100 the walk fires
on 1,492 bars — all 1,492 **finite**, which §G5 cites and which the script
counts separately, because an infinity is not a NaN and `fired` alone
would not say it — and ×8 / ×64 are bit-identical on all of them.

### §D2 ×10 / ×3.7 / ×0.1 / ×1.0000001, a tolerance

NaN masks match in all 24 frame-and-factor cells. The worst relative
difference is **6.480e-10** (range-bound, ×3.7), and the test asserts
1e-7.

⚠ **That is six orders of magnitude worse than the inputs' own 1e-16, and
it is the column's shape rather than a defect.** `|jaw - teeth|` and
`|teeth - lips|` are differences of nearby EWMAs, so the result is a small
number carrying the absolute rounding of a price, and their difference
cancels again.

⚠ **Those figures are kernel-dependent.** The same section under
`python docs/measure_j_gator_cpu.py D` prints a worst case of **9.221e-10**
(range-bound, ×0.1) and different bit-equal counts per cell — while ×8/×64
stay bit-identical on 1,492 of 1,492 and §A1 stays at 0.000e+00. This is
why the test pins 1e-7 and not the measured digit.

### §D3 `0 < fires < n`

1,492 of 1,500 on every frame, including `flat`, so a column that never
warmed up or was NaN everywhere could not pass Gate D by being invariant.

## §E Gate E

**Gate E: pending, run by issue-solver after this session.**

The harness is `../Backtesting/Backtesting/scripts/analysis/gate_e_overlap.py
run --module pandas_ta.momentum.j_gator` (Backtesting #107), over the 89
frozen ALTPORT-1 BIST frames against the engine's `compute_all` ∪
`ml_features` manifest (329 + 358 = 687 comparators). This session does
not run it and does not read `../Backtesting`.

Until the receipt session records the row,
`tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
reports `j_gator` as owed, and
`tests/test_j_gator.py::test_the_gate_e_row_is_owed` asserts the ledger has
no row for it — which is the receipt session's cue to replace that test
with one pinning the row's identity.

### §E0 what the screen measured, on the PROTOTYPE

From issue #104 (2026-10-24; a prototype is not a port):

* max \|ρ\| **0.3736** vs `TK_Cross_Age` (manifest, n = 396,624), top-5
  per-frame max median 0.3784 → **SHIP** under `r3-perframe-0.90`;
* next comparators `ICHI_TK_CROSS_AGE` 0.3635, `chop` 0.2859;
* stage-2 fork overlap (not Gate E; scale-free `Category` outputs at
  defaults, 12 frames): max \|ρ\| 0.5214 vs `qqe:QQEs_14_5_4.236`,
  per-frame max median 0.5151;
* pre-flight on 6 frames: prefix-causal, unchanged under price ×8 and
  volume ×8.

§A2 measures this module BIT-equal to that prototype on 1,492 of 1,492
bars of each of seven synthetic frames, so the run on this module is
expected to reproduce those figures. **An expected agreement is the
easiest kind of row to copy over by mistake**, which is why the receipt
session must pin the row's own run id.

## §F Gate F — suites

The launcher runs both repos' suites in clean worktrees. In this worktree:

* `python -m pytest tests/test_j_gator.py -q` → **137 passed**;
* `python docs/measure_j_gator_cpu.py` → the same **137 passed** with
  `NPY_DISABLE_CPU_FEATURES="AVX512F AVX512_SKX AVX2 FMA3"` (the script
  prints the dispatchable features still enabled and refuses to run if any
  of the four survived, so the claim cannot drift);
* the four guards this port's doc edits touch
  (`tests/test_readme_counts.py`, `tests/test_ml_companions.py`,
  `tests/test_wiring_accessors.py`, `tests/test_altport2_ports.py`) → green
  when each runs on its own, and **red in one process in that order**:
  `test_altport2_ports.py::test_the_category_count_moved_by_exactly_three`
  reads "Category total 340, expected 343" (1 failed, 105 passed, 3
  skipped, measured). That is a PRE-EXISTING trap and not this port's:
  `pandas_ta/core.py:453` hands out the live `Category[name]` list and
  `core.py:692` removes names from it, so `test_wiring_accessors.py`'s
  category sweeps delete three entries for the rest of the process.
  Issues #100, #101 and #102 recorded the same thing. Alphabetical
  collection hides it, which is why the full suite below is green;
* the full suite → §F1.

## §G the guards, and the one case nothing guards

### §G1 a bad close empties its own bar and no other

The close is only the divisor, so this is not recursive. At bar 700 of the
walk, with the unguarded module (the same source with the guard removed)
for comparison:

| `close[700]` | bars emptied | bar 700 itself | other bars moved | unguarded reads |
|---|---|---|---|---|
| NaN | 1 | True | 0 | nan |
| 0.0 | 1 | True | 0 | **inf** |
| −1.0 | 1 | True | 0 | **−0.47782701** |
| +inf | 1 | True | 0 | 0.0 |
| −inf | 1 | True | 0 | −0.0 |
| 1e−310 | 1 | True | 0 | **inf** |

That is what the guard buys, and the third row is the dangerous one: a
negative close reads a finite, plausible-looking number of the wrong sign.

### §G2 a bad mid is recursive, and it decays

A bad `high` **or `low`** is inside the filter. Bars before it are
**bit-identical** (692 shared bars at J = 700), nothing is emptied, and the
contamination decays with the filter's own memory — max \|rel change\| over
bars ≥ J + k, monotone by construction:

| k | 0 | 1 | 13 | 50 | 100 | 300 |
|---|---|---|---|---|---|---|
| max \|rel\| | 2.440e+00 | 2.440e+00 | 2.440e+00 | 1.222e-01 | 1.601e-03 | 1.538e-10 |

Those are the same six figures in all **four** cells — `high`/`low` ×
`NaN`/`inf`. `mid` is `(high + low) / 2`, so a bad low has to behave like a
bad high, and this runs BOTH legs rather than arguing it from the symmetry.
The test pins the shape (strictly falling across 0 / 50 / 100 / 300 and
under 1e-6 by +300), not the digits.

### §G3 an infinite high or low needs no guard here, and that is measured

pandas' `_prep_values` turns an infinity into a NaN before the `ewm`
kernel runs, and `ewm` SKIPS a NaN observation. So, on each of the four
cells (`high`/`low` × `+inf`/`−inf`):

* fired 1,492, **0 non-finite readings**, 8 NaNs (the warm-up);
* against the same bar as NaN: masks identical, bit-equal on 1,492 of
  1,492, max \|diff\| 0.000e+00.

⚠ **This is a pandas BEHAVIOUR the module relies on**, and
`tests/test_j_gator.py::test_an_infinite_price_never_reaches_the_output`
pins it — on both legs and both signs — so an upgrade that stops doing it
fails here rather than silently
shipping an infinite feature. The fix in that case is one line,
`mid = mid.where(np.isfinite(mid))`, which was in the module until this
section measured it to be a no-op.

### §G4 degenerate frames

All-NaN, all-zero and all-negative 60-bar frames: no float error is
reachable under `np.errstate(all="raise")`, and 0 of 60 bars fire in each.

### §G5 the one case NOTHING guards, stated rather than hidden

A frame whose high/low and close live hundreds of orders of magnitude
apart overflows the division: high/low ≈ 1e+300 with close = 1e−300 reads
**52 of 60 bars infinite**, 0 finite. That is bad data rather than a
price — the same walk at ONE scale fires 1,492 bars and all 1,492 are
finite at 1e−6, 1e+6 and 1e+100, which is §D1's `finite` column and not
its `fired` one, an infinity being not-NaN — and
`tests/test_j_gator.py::test_the_cross_scale_overflow_is_disclosed_and_unguarded`
pins it so the disclosure cannot rot into silence.

## §L what the column reads — in-fork overlap, SYNTHETIC

⚠ These are synthetic frames and they are **not Gate E**, whose 687
comparators are the engine's. The screen's top comparator `TK_Cross_Age`
is one of those and has no counterpart here; its runner-up
`ICHI_TK_CROSS_AGE` **is** a shipped column of this fork
(`pandas_ta/overlap/ichimoku_ml.py:45`, `SF` in the dictionary), so it is
measured below rather than excused.

### §L1 against shipped fork columns

Spearman per frame:

| frame | `ao`/close | `natr` | `chop` | `qqe:QQEs` | `ICHI_TK_CROSS_AGE` | `ICHI_TK_DIST` | \|gator\| vs `natr` |
|---|---|---|---|---|---|---|---|
| walk | −0.1942 | −0.0901 | 0.3389 | 0.1794 | **0.4910** | −0.2161 | 0.0491 |
| trend | 0.0017 | −0.2420 | 0.3421 | 0.2963 | 0.2415 | 0.4151 | −0.2266 |
| range-bound | −0.0096 | −0.0482 | 0.2786 | 0.3848 | 0.2661 | −0.0068 | 0.1821 |
| grid | 0.0045 | −0.0249 | 0.3397 | 0.4291 | 0.4717 | 0.0693 | 0.1602 |
| heavy-tailed | −0.0796 | −0.0996 | 0.3004 | 0.1532 | 0.4187 | −0.1662 | 0.2602 |
| jump | −0.0059 | −0.0786 | 0.3594 | 0.3576 | 0.4377 | −0.0443 | 0.0311 |

It is **not** a restatement of `ao`, which reads the same `(high+low)/2`
through two SMAs (\|ρ\| ≤ 0.1942 here), and it is **not** a volatility
column (\|ρ\| ≤ 0.2420 against `natr`, and ≤ 0.2602 even on its absolute
value). The largest figure on these frames is `ICHI_TK_CROSS_AGE` at
**0.4910** (0.2415 … 0.4910 across the six), then `qqe`'s smoothed RSI
line at 0.4291 and `ICHI_TK_DIST` at 0.4151 — all far under the 0.76 ship
line, and the first two
consistent with the two real-data figures that exist: the screen measured
the engine's `ICHI_TK_CROSS_AGE` at 0.3635 against the identical
prototype column over n ≈ 396,624, and bounded its stage-2 fork sweep at
0.5214 against `qqe:QQEs_14_5_4.236` over 12 real frames.

⚠ **Review round 2 corrected a claim here.** §L previously said the
screen's top two comparators "do not exist in this repo at all", which was
false for `ICHI_TK_CROSS_AGE` and was being used to excuse not measuring
the nearest in-fork pair. The row above is the measurement that replaced
the excuse.

### §L2 what the SINGLE column costs against the two spreads it is built from

⚠ The issue quotes ONE difference, and that is what ships. Whether the
source library also returns the two spreads apart is not something this
worktree can see — jesse is not installed and web access is unavailable —
so this section is about scope, not about jesse's return shape. Both
spreads, scale-free, against the shipped difference:

| frame | ρ(col, \|jaw−teeth\|) | ρ(col, \|teeth−lips\|) | ρ between the two spreads |
|---|---|---|---|
| walk | 0.6468 | −0.1906 | 0.5795 |
| trend | 0.5488 | −0.0910 | 0.7534 |
| range-bound | 0.5398 | −0.5644 | 0.3189 |
| grid | 0.6269 | −0.2045 | 0.5825 |
| heavy-tailed | 0.6114 | −0.2237 | 0.5522 |
| jump | 0.6356 | −0.3168 | 0.4484 |

The difference is dominated by `|jaw - teeth|` (0.5398 … 0.6468) and the
two spreads are themselves correlated (0.3189 … 0.7534), so shipping the
pair would have added two columns that restate each other more than either
restates the difference. One column is what issue #104 names; this is the
measurement behind that being the smaller scope rather than a loss.

## §W the dictionary's 150-character cut

`docs/gen_indicator_dictionary.py`'s `desc()` shows the docstring's first
paragraph and, **only when it exceeds 150 characters**, cuts it as
`d[:150].rsplit(" ", 1)[0] + "…"` — dropping the trailing word WHOLE. So
the budget is 150 and the penalty for passing it is a word.

The paragraph is **146 characters** and survives intact, with **4
characters of slack** — measured by `python docs/measure_j_gator.py W`,
which imports the generator, calls its own `desc()`, and grows the
sentence until that function loses a word. Re-run it, and then the
generator, before lengthening it.

## §Z cost

⚠ **The milliseconds are this machine's and this run's.** Two runs of this
section on one worktree printed 6.33 ms and 4.12 ms for 100,000 bars, and
22.92 ms and 20.36 ms for 400,000. The claims are the traced peak, the
linear shape and the ordering.

| bars | best of 5 | traced peak |
|---|---|---|
| 100,000 | 4.1–6.3 ms | 6.4 MB |
| 400,000 | 20.4–22.9 ms | 25.6 MB |

Three `ewm` passes and three `shift`s, no window and no Python loop, so
both time and peak are linear in bars. The peak is exactly 4.0× for 4× the
bars; the time ratio within a single run was 3.62× (22.92 / 6.33) in one
and 4.94× (20.36 / 4.12) in the other, which is the spread of a wall-clock
figure and not a property of the column. The §A1 oracle — the same formula
as a Python recursion —
costs an order of magnitude more (two runs printed 18× and 19× the module
at 100,000 bars), which is why it lives in `docs/` and not in the test
module's long frames.

---

## Verdict

| gate | verdict | the number that carries it |
|---|---|---|
| **A** Correctness | **PASS** | bit-equal to an independently spelled recursion on 1,492 of 1,492 bars of each of seven frames (asserted at 1e-12, absolute and relative); bit-equal to the screen prototype, asserted exactly. The SMMA alpha is the one reading that matters and §A4(c) prices the alternative at Spearman 0.5165 .. 0.7075 |
| **B** Causality | **PASS** | the module caught 0 of 36 perturbation offsets on each of six frames; four mutants caught 36 of 36 on all six; `teeth-lead` carried by liveness (1,371 .. 1,453 of 1,487 bars moved) and by 95 of 95 exposed offsets |
| **C** Reachability | **PASS synthetic, real data OWED** | 1,492 of 1,500 bars on each of seven frames, 1,492 distinct values on the six varying ones, exactly 0.0 on the flat one. The real-data limb comes with §E |
| **D** Scale-free | **PASS** | ×8 / ×64 bit-identical on 1,492 of 1,492 bars of seven frames and at levels 1e−6 / 1e+6 / 1e+100; inexact factors within 6.480e-10 (9.221e-10 under reduced dispatch) against a 1e-7 bound; `0 < 1,492 < 1,500` |
| **E** Attribution | **PENDING, run by issue-solver after this session** | §E0's prototype figure is max \|ρ\| 0.3736 vs `TK_Cross_Age` (SHIP), and §A2 makes this module that prototype bit for bit |
| **F** Suites | **PASS here, both repos are the launcher's** | 137 for the module, the same 137 under reduced CPU dispatch, full suite 3 failed / 8,736 passed / 85 skipped with the three being `dev`'s clean-checkout failures (§F1) |

**Why this ships rather than reverts.** Issue #104 closes either way, so the
question is whether anything measured here argues for deleting the column.
Nothing does: it is causal, scale-free, reachable, and no fork column this
worktree can measure comes near restating it — \|ρ\| ≤ 0.1942 against `ao`,
which reads the same `(high + low) / 2`, ≤ 0.2420 against `natr`, ≤ 0.3594
against `chop`, ≤ 0.4291 against `qqe`'s smoothed RSI line, ≤ 0.4151 against
`ichimoku_ml`'s `ICHI_TK_DIST`, and ≤ **0.4910** against the same module's
`ICHI_TK_CROSS_AGE`, which is the fork's copy of the screen's runner-up
comparator and the largest figure measured (§L1, synthetic). The screen's own real-data figures on the identical column were
0.3736 against `TK_Cross_Age` and 0.3635 against the engine's
`ICHI_TK_CROSS_AGE` over 687 comparators — deep in SHIP — with its stage-2
fork sweep bounded at 0.5214 on 12 real frames.

What a consumer must know, in one place:

1. **The teeth cancel** whenever they are the outer line — 0.0355 to 0.2815
   of bars — and the column is the jaw-lips spread there (§B1).
2. **It amplifies the last bits**: a 1e-16 move in a price is up to 6.5e-10
   in the column, because it is a difference of two differences of nearby
   EWMAs (§D2).
3. **The warm-up is 8 bars** — the longest lag — and bar 8's jaw is one
   observation. The transient is the source's and is kept (§A3, §A4).
4. **It is unbounded** in principle; the frames here span −0.1240 .. +0.0446
   and a flat price reads exactly 0.0 (§C1).
5. **One guard, on the divisor.** A bad close empties its own bar; a bad
   high/low decays through the filter; a cross-scale frame overflows and is
   not guarded (§G1, §G2, §G5).
6. **Gate E decides the band**, and it has not run yet (§E).

## Decisions this session made, and why

Eight, all recorded as ASSUMPTIONs in
`docs/reviews/auto-2026-11-14-j-gator/00-manifest.md` because
`AskUserQuestion` is unavailable in a headless run and the skill's rule is
to take the smaller scope:

1. **One column.** Issue #104 quotes a single difference and
   `ind_screen.py`'s `j_gator` returns one series, so one column is both
   the quote and the smaller scope; whether the source library also
   returns the two spreads apart is not visible from this worktree, and
   §L2 prices shipping them anyway (ρ(col, \|jaw−teeth\|) 0.5398 … 0.6468,
   ρ between the two spreads 0.3189 … 0.7534).
2. **No parameter surface.** 13/8, 8/5 and 5/3 are the source's constants.
3. **SMMA read as Wilder's `alpha = 1/n`, `adjust=False`, seeded at the
   first value**, on the issue's wording and the prototype and NOT on
   jesse's unread source (§A4 prices all three alternatives; (c) is the
   one that matters).
4. **Category `momentum`**, where `ao` lives.
5. **Name `j_gator`, column `J_GATOR_13_8_5`** — the issue's candidate
   name, and the suffix is the three SMMA lengths.
6. **No invented warm-up**: the column fires from bar 8, as the source and
   the prototype do (§A3).
7. **One guard, on the divisor only** (§G1), with §G3 measuring that `mid`
   needs none and §G5 naming what is left unguarded.
8. **Gate A is a tolerance against the independent oracle and bit-equality
   against the prototype** (§A1, §A2).

## §F1 suite output

```
$ python -m pytest tests/test_j_gator.py -q
137 passed

$ python docs/measure_j_gator_cpu.py
numpy 1.26.4
NPY_DISABLE_CPU_FEATURES = 'AVX512F AVX512_SKX AVX2 FMA3'
dispatchable features still enabled: ['SSSE3', 'SSE41', 'POPCNT', 'SSE42',
 'AVX', 'F16C', 'AVX512CD', 'AVX512_CLX', 'AVX512_CNL', 'AVX512_ICL']
137 passed
```

```
$ python -m pytest -q
3 failed, 8736 passed, 85 skipped in 221.38s
```

The three failures are `dev`'s clean-checkout failures and `j_gator` is
the cause of none of them beyond being named in the third:

* `tests/test_pine_coverage_csv.py::test_audited_rows_carry_their_evidence`
  — the untracked `docs/pine/` citations, recorded in `CLAUDE.md`;
* `tests/test_altrepo_talib_csv.py::test_regenerating_reproduces_the_committed_rows`
  — needs the sibling `../AlternativeRepos` checkout;
* `tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
  — the owed Gate E rows, which now read
  `['arch_lm', 'diff2_acf1', 'edge', 'firstzero_ac', 'halflife',
  'j_gator', 'lumpiness', 'mtd_ret']`. CI into `dev` sets
  `GATE_E_PENDING_OK=1` and skips it.
