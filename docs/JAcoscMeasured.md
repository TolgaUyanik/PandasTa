# J-ACOSC — `j_acosc`, measured

PandasTa issue **#106** (parent #31 ALPHASETS, screen of 2026-10-24).
Module `pandas_ta/momentum/j_acosc.py`, column **`J_ACOSC_5_34_5`**.
Tests `tests/test_j_acosc.py` (175).

Every number in §A, §B, §C, §D, §F(the filter), §G, §L, §W and §Z is
printed by `python docs/measure_j_acosc.py` on this worktree (**pandas
2.3.3, numpy 1.26.4** — which that script prints as its first line, so this
parenthesis is a quote and not a guess), section by section. The headings
take their letters from the script. §E and §SUITES are headings of this
file only.

What does NOT come from that command, marked again where it appears:

* **§Z's milliseconds**, which it does print but which are not a claim:
  they are this machine's and this run's, and §Z tabulates eight runs to
  show how far they move. The claims there are exactly the four §Z lists
  — the traced peaks, the 4.0× memory ratio, a time ratio within a small
  constant factor of linear with no digit attached, and the ordering.
* **§E**, which is **pending**: issue-solver runs Gate E after this
  session and a later receipt session writes the result here and into
  `docs/gate_e_ledger.csv`.
* **§E0**, the 2026-10-24 screen's figures, measured on the PROTOTYPE and
  quoted from issue #106.
* **§SUITES**, which is pytest's own output.
* **§C2's dictionary and contract deltas**, which are read off
  `git diff docs/IndicatorDictionary.md` and re-derived against the live
  package by
  `tests/test_ml_companions.py::test_the_contract_quotes_the_dictionarys_actual_ml_form_counts`
  and `tests/test_readme_counts.py`.
* **the reduced-CPU figures**, which come from
  `python docs/measure_j_acosc_cpu.py A1 D F L` and are marked as such.

```
mid     = (high + low) / 2
AO      = SMA(mid, 5) - SMA(mid, 34)
J_ACOSC = (AO - SMA(AO, 5)) / close
```

**Source.** jesse indicators (MIT), `acosc`, as issue #106 quotes it:
"`acosc: AO - SMA(AO,5), AO = SMA(mid,5)-SMA(mid,34)`". The `/ close` is
this fork's, from the screen prototype's scale-free form.

⚠ **jesse is not installed in this worktree and web access is
unavailable.** It is an ATTRIBUTION, not an oracle:
`tests/test_j_acosc.py::test_the_source_library_is_not_installed_here`
records that, so the claim cannot rot into "checked against jesse". What
Gate A checks is the formula the issue quotes, spelled three independent
ways (§A1, §A2, §A3).

⚠ **One column.** The issue quotes a single series and `ind_screen.py`'s
`j_acosc` returns one, so that is what ships. Bill Williams' own
presentation of the acceleration oscillator also carries a colour/sign
state; whether jesse's `acosc` returns one is not something this worktree
can see, and a sign column would be `np.sign` of this one.

The screen prototype is `docs/issues/screen/ind_screen.py` candidate
`j_acosc` (that file is gitignored, so it exists only on the owner's
machine):

```python
mid = (h + l) / 2
ao = mean(mid, 5) - mean(mid, 34)
return (ao - mean(ao, 5)) / c
```

with the screen's own helper `def mean(x, n): return x.rolling(n).mean()`.

**Seven frames**, 1,500 bars each, built by the script and retyped with the
same seeds in the test module: `walk`, `trend`, `range-bound` (an
Ornstein-Uhlenbeck path), `grid` (a walk on a 0.01 tick grid),
`heavy-tailed`, `jump` (a ×1.5 gap at bar 700) and `flat` (a constant
price, where both rolling means equal the level and the column is exactly
0.0). The six excluding `flat` are the script's `VARYING`. Each frame fires
on **1,463** bars — `WARMUP` = `SLOW + SIGNAL - 2` = 37 — which makes the
pooled figure **10,241** over the seven.

---

## §A1 Gate A — the issue's formula, spelled independently

An oracle that re-sums every window with `math.fsum` (correctly rounded)
and shares no code with pandas' Kahan-compensated roll-on/roll-off
accumulator.

```
frame          masks   bars  bit-eq   max |diff|   max |rel|
walk            True   1463     273    4.536e-16   2.006e-11
trend           True   1463     316    4.129e-16   2.477e-11
range-bound     True   1463     290    3.730e-16   9.695e-12
grid            True   1463     327    3.626e-16   3.336e-11
heavy-tailed    True   1463     307    3.825e-16   8.784e-11
jump            True   1463     267    3.660e-16   1.339e-11
flat            True   1463    1463    0.000e+00         nan

worst absolute difference over all frames: 4.536e-16
worst relative difference over all frames: 8.784e-11
```

Under reduced CPU dispatch (`python docs/measure_j_acosc_cpu.py A1`) the
same two worst figures read **4.569e-16** and **3.336e-11**, and the masks
and the 1,463 shared bars are unchanged.

⚠ **Here the ABSOLUTE bound is the tight one, which is the reverse of
`j_gator`.** The column is a cancelling difference: some bars read 1e-16,
so a relative difference on those is measuring float dust rather than
disagreement. `tests/test_j_acosc.py` asserts **1e-14 absolute and 1e-9
relative**, and it asserts both, because the relative limb is also vacuous
on the `flat` frame — the oracle is identically 0.0 there and `_rel` has
nothing to divide by, which is the `nan` in the table.

Bit-equality is NOT asserted against this oracle. It is reached on a
minority of bars — 267–327 of 1,463 in the full-dispatch table above, and
266–327 in the reduced-dispatch run (where `walk` moves 273 → 266) — with
all 1,463 on `flat`, where every value is exactly 0.0. That is expected:
`fsum` is exact and pandas' accumulator is not, and nothing is asserted on
the count.

## §A2 Gate A — the screen prototype, bit for bit

The prototype shares the module's spelling of SMA (`rolling(n).mean()`), so
this limb is EXACT and machine-independent, and it is the limb that ties
this port to the 2026-10-24 screen's Gate E figures.

```
frame          masks   bars  bit-eq   max |diff|
walk            True   1463    1463    0.000e+00
trend           True   1463    1463    0.000e+00
range-bound     True   1463    1463    0.000e+00
grid            True   1463    1463    0.000e+00
heavy-tailed    True   1463    1463    0.000e+00
jump            True   1463    1463    0.000e+00
flat            True   1463    1463    0.000e+00
```

## §A3 Gate A — the fork's OWN `ao` and `sma`

The third spelling, and the one that answers "did this port reinvent
something the fork already ships?". `pandas_ta.momentum.ao.ao(high, low)`
is `0.5 * (high + low)` through `sma(.., 5)` and `sma(.., 34)` at its
defaults — the issue's `AO` exactly — and `pandas_ta.overlap.sma.sma` is
the signal leg.

```
frame          masks   bars  bit-eq   max |diff|
walk            True   1463    1463    0.000e+00
trend           True   1463    1463    0.000e+00
range-bound     True   1463    1463    0.000e+00
grid            True   1463    1463    0.000e+00
heavy-tailed    True   1463    1463    0.000e+00
jump            True   1463    1463    0.000e+00
flat            True   1463    1463    0.000e+00
```

Two things follow, and both are the reason this section exists.

1. `0.5 * (high + low)` and `(high + low) / 2` are the same double for
   every input, so the module's spelling of `mid` is not a divergence from
   `ao`'s.
2. `_sma` is spelled in the module rather than imported, and this says what
   that costs: **nothing arithmetically**. `pandas_ta.overlap.sma` computes
   exactly `rolling(length, min_periods=length).mean()`; what the local
   spelling avoids is the rename (`SMA_34`) and a second `verify_series`
   pass per call, which would otherwise run three times per column —
   `_sma` is called exactly three times (`_sma(mid, FAST)`,
   `_sma(mid, SLOW)`, `_sma(ao, SIGNAL)`).

## §A4 the readings NOT taken, priced

### §A4(a) an exponential mean instead of an SMA

`alpha = 2/(n+1)` (`ewm(span=n, adjust=False)`) wherever the formula says
SMA — the other thing "a moving average of period n" can mean.

```
frame               rho   bars  bit-eq   max |diff|
walk             0.9261   1463       0    1.161e-02
trend            0.9175   1463       0    9.328e-03
range-bound      0.8966   1463       0    2.929e-02
grid             0.9255   1463       0    1.222e-02
heavy-tailed     0.9277   1463       0    6.575e-02
jump             0.9256   1463       0    6.953e-02
```

⚠ **This is a NEARBY column, not a far one, and that is stated rather than
spun.** `j_gator` can legitimately argue that its alpha is load-bearing —
its figure is 0.5165 .. 0.7075. Here it is **0.8966 .. 0.9277** with 0 bars
in common, so "the wrong reading would be a different column" is NOT
available as an argument. What defends the reading taken is §A2: the issue
says SMA, the prototype spells `rolling(n).mean()`, and this module is
bit-equal to that prototype.
`test_the_ema_reading_is_a_nearby_column_not_a_far_one` pins the band so a
future session cannot cite distance here.

### §A4(b) the signal averaged over `mid` instead of over `AO`

`SMA(mid,5) - SMA(mid,34) - SMA(mid,5)`, which collapses to
`-SMA(mid,34) / close` — a price-level column, and the shape of the
misreading that would make the warm-up `SLOW - 1` instead of
`SLOW + SIGNAL - 2`.

```
frame               rho   bars  bit-eq   max |diff|
walk             0.3151   1463       0    1.091e+00
trend            0.3776   1463       0    1.018e+00
range-bound      0.5270   1463       0    1.104e+00
grid             0.2999   1463       0    1.096e+00
heavy-tailed     0.2879   1463       0    1.261e+00
jump             0.3453   1463       0    1.088e+00
```

### §A4(c) `min_periods=1` — partial windows

```
frame               rho   bars  bit-eq   max |diff|
walk             1.0000   1463    1463    0.000e+00
trend            1.0000   1463    1463    0.000e+00
range-bound      1.0000   1463    1463    0.000e+00
grid             1.0000   1463    1463    0.000e+00
heavy-tailed     1.0000   1463    1463    0.000e+00
jump             1.0000   1463    1463    0.000e+00

bars where the module fires: 1463
bars where min_periods=1 fires: 1500
of the shared 1463, bit-equal: 1463
```

So `min_periods` is a WARM-UP decision and nothing else: on the tail the
two are the same column, bit for bit. The decision taken is the
prototype's (`rolling(n)` at pandas' default), which is also the fork's
`sma` default and the conservative reading — 37 honest NaNs instead of 37
bars computed from a window that is not there.

---

## §B Gate B — causality, by future perturbation and by mutation

Caught = perturbing high, low and close at every bar ≥ J by ×1.03 moved at
least one bar < J. 36 offsets per frame, J ∈ [1464, 1499].

### §B1 the shipped module

```
frame            caught
walk                  0
trend                 0
range-bound           0
grid                  0
heavy-tailed          0
jump                  0
```

### §B2 five look-ahead mutants

Each is the shipped source read off disk, ONE substring replaced, `exec`'d
in memory. `_mutant` refuses an anchor that is not unique, so a mutation
cannot silently hit a different line after an edit.

| label | what it does |
|---|---|
| `mid-lead` | `mid` is read one bar ahead |
| `fast-lead` | `_sma` becomes `center=True`, so EVERY mean is centred — see §B4, the label is historical and the real reach is 18 bars |
| `ao-lead` | the `AO` leg is read one bar ahead of the signal leg |
| `output-early` | the whole column is written one bar early |
| `divisor-lead` | the scale-free divisor is tomorrow's close |

Liveness first — a mutant that changes nothing would be caught at 0 of 36
and prove nothing — then the sweep. The `max |diff|` column is the min and
the max of the six per-frame figures:

```
mid-lead          moved 1462 of 1462   max |diff| 7.159e-03 .. 6.547e-02   caught 36/36 on all six
fast-lead         moved 1445 of 1445   max |diff| 1.706e-02 .. 1.175e-01   caught 36/36 on all six
ao-lead           moved 1462 of 1462   max |diff| 1.055e-02 .. 9.002e-02   caught 36/36 on all six
output-early      moved 1462 of 1462   max |diff| 7.002e-03 .. 5.272e-02   caught 36/36 on all six
divisor-lead      moved 1462 of 1462 on five frames, 1456 of 1462 on `grid`
                                     max |diff| 2.766e-04 .. 5.503e-03   caught 36/36 on all six
```

(`fast-lead` shares 1,445 bars rather than 1,462, and the reason is §B4
and not "two bars at each end". ⚠ `divisor-lead` on `grid` is the one row
in this table whose numerator is NOT its denominator: six bars are unmoved
because the 0.01 tick grid gives two consecutive EQUAL closes there, so
"tomorrow's close" is today's and the mutation is a no-op on those bars.
`tests/test_j_acosc.py::test_every_mutant_is_live_before_it_is_caught`
therefore asserts full liveness on `walk` only, and says why in its
docstring.)

⚠ **Nothing cancels in this formula.** It is a weighted sum of `mid`
values, not a pair of absolute values, so unlike `j_gator`'s `teeth-lead`
there is no mechanism that can hide a future read on some bars, and every
mutant is asserted at the full 36 of 36 on all six varying frames. Why
SIX and not seven is §B5.

### §B3 the size of a catch, against the noise an inexact rescale costs

A catch is a bar BEFORE the perturbation moving at all, so its size has to
be far above the last-bit noise of §D2 or the sweep is reading float dust.
At the first offset (J = 1464) of the `walk` frame:

```
mid-lead       bars moved   1  smallest move 4.113e-03  largest 4.113e-03
fast-lead      bars moved  18  smallest move 5.971e-08  largest 3.546e-03
ao-lead        bars moved   1  smallest move 5.142e-03  largest 5.142e-03
output-early   bars moved   1  smallest move 4.111e-03  largest 4.111e-03
divisor-lead   bars moved   1  smallest move 7.515e-05  largest 7.515e-05
```

The smallest single catch of the five is **5.971e-08** against §D2's
**1.886e-10** — 316×. `test_a_catch_is_orders_above_the_noise_an_inexact_rescale_costs`
pins it as that ratio with two orders of headroom, not as the digits.

⚠ `fast-lead` is the one row moving more than one bar, and that is §B4.

### §B4 `fast-lead` is misnamed, and this is what it actually does

Written down because the first draft of this receipt explained it wrongly
("`center=True` costs two bars at each end"), and two figures already in
§B2 and §B3 refute that: a 2-bar look-ahead cannot cost 17 shared bars and
cannot move 18 bars at one catch.

The anchor the mutation replaces is `_sma`'s only line, so `center=True`
centres **every** mean — fast, slow AND signal. pandas centres a window of
length `n` by `(n - 1) // 2`, so the composite reach is
`(SLOW - 1)//2 + (SIGNAL - 1)//2` = 16 + 2 = **18** bars.
⚠ Not 17: the round-2 reviewer that found this error priced only the slow
window's centring. The SIGNAL mean is centred too — the anchor is `_sma`'s
only line — and 18 is what the two measured figures below say.

```
module fires bars 37..1499 (1463)
mutant fires bars 19..1481 (1463)
shared 1445; the module's last 18 bars are NaN in the mutant, and 18 is the reach
```

So all three of §B2's and §B3's anomalies are the same number: the mutant
fires 18 bars earlier and 18 bars later-truncated, it shares
1,463 − 18 = **1,445** bars with the module, and perturbing at offset `J`
moves exactly the 18 bars `J-18 … J-1`, which is §B3's "bars moved 18".

The label is kept as `fast-lead` because it is the label the test IDs and
this receipt already use; it is historical, and
`test_the_fast_lead_mutant_reaches_eighteen_bars_not_two` pins the real
reach so the wrong explanation cannot come back.

### §B5 why the `flat` frame is excluded from §B1 and §B2

Also written down because an earlier draft argued it instead of measuring
it. The draft said "a perturbation of a constant price is still a constant
price", which is **false**: the sweep multiplies bars `>= J` by 1.03, so a
perturbed `flat` frame is a two-level STEP. Round 4 caught it.

What a sweep on `flat` actually gives:

```
function          caught of 36
the module                   0
mid-lead                    36
fast-lead                   36
ao-lead                     36
output-early                36
divisor-lead                 0
```

So four of the five mutants ARE caught on `flat`, and excluding the frame
costs nothing for them. The one that is not is **`divisor-lead`, at 0 of
36**, and the mechanism is specific: on a constant price `AO` is exactly
0.0 on every bar, so the numerator of every pre-`J` bar is exactly 0.0 and
swapping the divisor `c` for `c.shift(-1)` leaves `0.0 / x` = `0.0`
whatever `x` is. A divisor-only look-ahead is unobservable through a zero
numerator.

`flat` is therefore left out of `VARYING`
(`docs/measure_j_acosc.py` and `tests/test_j_acosc.py` both define it the
same way) so that §B1 and §B2 can be asserted at full strength — the
module at 0 of 36 and all five mutants at 36 of 36 — on six frames,
instead of carrying a four-of-five exception on seven.
`test_the_flat_frame_is_excluded_because_divisor_lead_cannot_be_caught_there`
pins both halves: the module is still clean on `flat`, the four are still
caught there, and `divisor-lead` is not.

---

## §C Gate C — reachability

### §C1 synthetic

```
frame           fired     of  first  distinct  zeros         min         max
walk             1463   1500     37      1463      0 -2.3860e-02  2.2724e-02
trend            1463   1500     37      1463      0 -1.6766e-02  1.8970e-02
range-bound      1463   1500     37      1463      0 -4.7988e-02  4.5939e-02
grid             1463   1500     37      1463      0 -2.2505e-02  2.8968e-02
heavy-tailed     1463   1500     37      1463      0 -1.1012e-01  4.1982e-02
jump             1463   1500     37      1463      0 -3.1722e-02  1.1981e-01
flat             1463   1500     37         1   1463  0.0000e+00  0.0000e+00

pooled fired bars over the seven frames: 10241
span over all of them: -0.1101 .. 0.1198
|value| <= 0.02 on 9874 of 10241
```

The NaNs are a LEADING PREFIX and nothing else — measured
contiguous-from-zero on all seven frames, 37 each.

The `flat` frame fires on all 1,463 bars and reads exactly 0.0 on every
one. ⚠ The mechanism is NOT "the taps sum to zero in floating point" (§F
measures that sum at 6.939e-18, not 0.0): both rolling means of a constant
ARE that constant, bit for bit, so `AO` is exactly 0.0 before any tap
arithmetic happens. That is why the reading is an exact 0.0 and not a
1e-18 smear, and it is a VALUE rather than missing data.

Short frames — `MIN_BARS` as a floor on the INPUT, not the warm-up:

```
37 bars -> None
38 bars -> fires on 1 bar(s)
```

The warm-up, and the trap it exists to name:

```
WARMUP = SLOW + SIGNAL - 2 = 34 + 5 - 2 = 37, and the AO leg alone would be 33:
    AO's own leading NaNs: 33
    the column's:          37
```

⚠ **The two warm-ups ADD rather than overlapping**, because the signal leg
averages `AO` and not the price: `SMA(AO, 5)` needs five non-NaN `AO`
values, and `AO`'s first is at bar 33. Reading the warm-up as `SLOW - 1`
= 33 is the mistake §A4(b) spells out as a column.

### §C2 real data, and the dictionary

⚠ **Real-data reachability is OWED with Gate E**, which issue-solver runs
after this session. Every count in §C1 is synthetic.

The dictionary regenerated clean
(`python docs/gen_indicator_dictionary.py`, 596 lines):

```
+**347 indicators** probed; 1 raise on this environment
+| registered in `Category` | **345** |
+| callable as `df.ta.<name>()` | **353** |
+## momentum (85)
+| `j_acosc` | H/L/C | — | `J_ACOSC_5_34_5` SF | 37 | The Awesome Oscillator
   minus its own 5-bar mean, over close: how fast the AO is moving rather
   than where it stands. |
```

and `docs/MLCompanionContract.md` moves 689 → 690 tagged columns,
328 → 329 `SF`. The column also joins the dictionary's "Already an ML
feature" list. Both deltas are re-derived against the live package by
`tests/test_ml_companions.py` and `tests/test_readme_counts.py`, so neither
is a hand count.

---

## §D Gate D — scale-free

### §D1 ×8 / ×64, bit-identical

Every step is linear in the price and the final division cancels the
factor, so an exact power of two scales every intermediate exactly:

```
all seven frames, both factors: masks True, 1463 shared bars,
1463 bit-equal, max |diff| 0.000e+00
```

unchanged under reduced CPU dispatch.

### §D2 ×10 / ×3.7 / ×0.1 / ×1.0000001, a tolerance

An inexact factor moves the price in its last bits, and this column
AMPLIFIES that loss: it is a difference of differences of nearby rolling
means.

```
worst relative difference over 6 frames x 4 factors: 1.812e-10
   (walk x10; the next worst are walk x3.7 1.445e-10 and walk x0.1 9.028e-11)
same measurement under reduced CPU dispatch:          1.886e-10
```

NaN masks match on all 24 combinations in both runs. The test asserts
**1e-7**, nearly three orders of headroom, plus the mask equality — which
is the part a tolerance cannot hide.

### §D3 extreme price LEVELS

The same walk REBUILT at each level, not rescaled — and §D1's ×8/×64 run
REPEATED at that level, so the bit-identity claim is measured there rather
than extrapolated from level 100:

```
     level  fired  finite   max |value|, all 17 digits  x8 bit-eq  x64 bit-eq
     1e-06   1463    1463          0.02385959651618156       1463        1463
     1e+06   1463    1463         0.023859596516181567       1463        1463
    1e+100   1463    1463         0.023859596516181653       1463        1463

pairwise relative spread of max |value|:
  1e-6  vs 1e+6    2.908e-16
  1e-6  vs 1e+100  3.926e-15
  1e+6  vs 1e+100  3.635e-15
```

Under reduced CPU dispatch (`python docs/measure_j_acosc_cpu.py D`) the
bit-eq columns are unchanged at 1,463 and the pairwise spreads read
1.890e-15 / 2.472e-15 / **4.362e-15**. ⚠ The 17-digit values themselves
move with the kernel (1e-6 reads `0.02385959651618156` full-dispatch and
`0.02385959651618149` reduced), so the digits above are a transcription of
one run and not a constant.

1,463 of 1,463 bars bit-identical under both exact factors at each of the
three levels, and `max |value|` agreeing to 3.9e-15 relative across a
level ratio of 1e+106 — 4.4e-15 under reduced CPU dispatch.

⚠ **Not bit-equal, and an earlier draft of this section said it was.** It
printed `max |value|` to four digits — "2.3860e-02" three times — and
round 3 reasonably asked for the equality to be asserted; the assertion
FAILED, which is how the 17-digit column above came to exist. 1e-6, 1e+6
and 1e+100 are not exact binary multiples, so `level * np.exp(...)` builds
three price paths that already differ in their last bits. The division
cancels the LEVEL; it cannot cancel a difference that is in the prices.

`test_gate_d_scale_at_extreme_price_levels` asserts all five columns, with
`max |value|` as a 1e-9 relative agreement between the three — three
orders inside §D2's 1.886e-10 and six orders tighter than the `< 0.2`
bound it replaced.

### §D4 `0 < fires < n`

`0 < 1463 < 1500` on all seven frames. ⚠ This limb matters more here than
usual: the `flat` frame IS a constant column (at 0.0) and still fires, so
"it fires" and "it varies" are genuinely separate facts, and §C1's
`distinct` column is what carries the second one.

---

## §F the filter — 38 taps in `mid`, summing to zero to within 7e-18

`AO - SMA(AO, 5)` is a linear FIR filter of `mid`:
`out[T] * close[T] = Σ h[k] · mid[T-k]`.

```
tap count: 38 = SLOW + SIGNAL - 1 = 34 + 5 - 1
sum of taps (fsum): 6.939e-18
max tap +0.136471 at lag 0, min tap -0.160000 at lag 5
sum |tap|: 0.80000000000000004

Frequency response |H(w)|, w in radians/bar (period = 2*pi/w):
    DC       (w = 0)    0.000000
    peak     (w = 0.546653, period 11.4939 bars) 0.673744
    Nyquist  (w = pi)   0.160000
```

Identical under reduced CPU dispatch (the taps are built from the module's
constants, not from data).

Three of those are derivations the test re-does from `FAST`/`SLOW`/`SIGNAL`
rather than copying, so changing a constant fails the test instead of
silently re-describing a different column:

* `h[0] = (1/FAST - 1/SLOW) · (1 - 1/SIGNAL)` = 0.136471;
* `h[FAST] = -1/SLOW - (4·(1/FAST - 1/SLOW) - 1/SLOW)/SIGNAL` = -0.16
  exactly (-136/850), the lightest tap, where the fast window has just
  dropped out;
* `|H(π)| = |odd(FAST) - odd(SLOW)| · |1 - odd(SIGNAL)|` = 0.2 × 0.8 =
  0.16, writing `odd(n) = 1/n` for odd `n` and 0 for even — an SMA of odd
  length passes an alternating input at `1/n` and an even one kills it.

And the taps ARE the column, not a description of it — `h` dotted against
the last 38 `mid` values with `math.fsum`, divided by close:

```
frame            bars  bit-eq   max |diff|   max |rel|
walk             1463      11    3.799e-16    4.054e-11
trend            1463       9    3.170e-16    1.720e-11
range-bound      1463      20    3.018e-16    5.034e-12
grid             1463       6    3.453e-16    1.290e-11
heavy-tailed     1463      12    3.508e-16    3.294e-11
jump             1463      16    3.938e-16    8.135e-12
```

(reduced dispatch: worst max |diff| 4.036e-16). Asserted at 1e-14
absolute — a dot product is not pandas' rolling accumulator.

⚠ **What this buys, and what it does not.** It buys the one structural
sentence about the column: it is blind to the price LEVEL and loudest on
swings of about 11.5 bars. It does NOT buy independence from `AO` — see
§L1, where the column reads 0.8638 .. 0.9016 against `AO`'s own 1-bar
change.

---

## §G the guards, and the cases nothing guards

### §G1 a bad CLOSE empties its own bar and no other

Planted at bar 700 of a 1,500-bar walk:

```
     close  emptied   other bars moved
       nan        1                  0
       0.0        1                  0
      -1.0        1                  0
       inf        1                  0
      -inf        1                  0
    1e-310        1                  0
```

The close enters the column at its own bar only, so "exactly one" is a
structural fact and not an approximation. The guard is
`close.where(np.isfinite(close) & (close >= np.finfo(float).tiny))`, which
also catches a NEGATIVE close, since `>= tiny` excludes them.

### §G2 what the guard BUYS

The same plants with the guard line replaced in the shipped source:

```
     close     reading at bar 700
       0.0                    inf
      -1.0              -0.771217
    1e-310                    inf
```

The negative case is the dangerous one: **-0.771217** is a
plausible-looking number for a tree to split on, roughly 6× the largest
|value| any frame in §C1 reaches, with nothing to mark it as garbage.

### §G3 a bad HIGH or LOW is NOT absorbed — the divergence from `j_gator`

`j_gator`'s `ewm` SKIPS a NaN observation and carries the previous
smoothed value, so a bad bar perturbs the column recursively and nothing
is emptied. `rolling(...).mean()` does the opposite: it EMPTIES a window
holding a NaN or an infinity.

```
   leg      value  emptied  first   last  moved<700  moved>737   max |rel|  non-finite
  high        nan       38    700    737          0        662   9.486e-12           0
  high        inf       38    700    737          0        662   9.486e-12           0
  high       -inf       38    700    737          0        662   9.486e-12           0
   low        nan       38    700    737          0        662   9.486e-12           0
   low        inf       38    700    737          0        662   9.486e-12           0
   low       -inf       38    700    737          0        662   9.486e-12           0
```

Four readings of that table, in order of what they are worth:

1. **An infinite high or low gives a column bit-identical to the one a NaN
   gives**, on both legs and both signs, with **0 non-finite readings**.
   That is measured, not assumed, and it is the reason `mid` carries no
   guard. `test_an_infinite_price_empties_bars_like_a_nan` pins it so a
   pandas upgrade which starts letting an `inf` through fails loudly here
   instead of silently shipping an infinite feature.
2. **The emptied run is exactly `SLOW + SIGNAL - 1` = 38 bars**, 700..737,
   which is the reach of the two windows the bad bar enters.
3. **NO bar before 700 moves.** That is the causal statement, and it is
   the assertion that matters in the test.
4. ⚠ **662 bars AFTER 737 DO move**, by up to **9.486e-12** relative, and
   that is NOT contamination from the bad bar: pandas' rolling accumulator
   re-sums the window from scratch once a NaN has passed through it, so
   later windows round differently. It is disclosed here and bounded at
   1e-9 in the test, so a real leak could not hide inside it.

Both legs and both signs are run because `mid = (high + low) / 2`: a bad
low has to behave like a bad high, and that is measured rather than
inferred.

### §G4 degenerate frames

Under `np.errstate(all="raise")`, 60-bar frames of one repeated value:

```
all      nan: fired   0
all      0.0: fired   0
all     -5.0: fired   0
all    100.0: fired  23, all exactly 0.0
```

No float error is reachable. The last is the one that matters — a frame of
a repeated price is a halted instrument, not a pathological input — and it
fires on 23 = 60 - 37 bars. The zero and negative frames fire nowhere
because the divisor guard empties every bar, which is §G1 at frame scale.

### §G5 the one case NOTHING guards, stated rather than hidden

```
a cross-scale frame: high/low at 1e+300, close at 1e-300.
fired 23 of 60, infinite 23
```

All 23 fired bars read `inf`. That is bad data rather than a price — the
same walk at ONE scale fires 1,463 finite bars at 1e-6, 1e+6 and 1e+100
(§D3) — and the module reports it instead of hiding it.
`test_the_cross_scale_overflow_is_disclosed_and_unguarded` pins it so the
disclosure cannot rot into silence.

---

## §L what the column reads — in-fork overlap, SYNTHETIC

⚠ These are synthetic frames and fork columns. Gate E measures **687
ENGINE** comparators over **89 real BIST frames** and is the only thing
that decides the band; none of the columns below is in it, because the
engine's `compute_all` and the `ml_features` manifest hold no pandas_ta
port.

### §L1 against fork columns and against `AO` itself

```
comparator                                            walk     trend range-bou      grid heavy-tai      jump
ao / close (the level this column differences)      0.1591    0.2103    0.3026    0.1585    0.1187    0.1755
ao, 1-bar change / close                            0.9014    0.8926    0.8638    0.9016    0.8756    0.8989
stochrsi: STOCHRSIk_14_14_3_3                       0.8667    0.8156    0.8454    0.8682    0.7965    0.8630
stochrsi: STOCHRSId_14_14_3_3                       0.8248    0.7626    0.7805    0.8368    0.7268    0.8008
qqe: QQEs_14_5_4.236                                0.2532    0.2864    0.4930    0.2423    0.2128    0.2814
cmo_14                                              0.4123    0.4424    0.6453    0.3935    0.3905    0.4480
er_10                                              -0.0934    0.5407    0.0169    0.0700   -0.0289   -0.0306
chop_14                                             0.0721   -0.4700    0.0099   -0.0363    0.0343    0.0129
natr_14                                            -0.0772    0.3076   -0.0762   -0.0290   -0.0386   -0.1867
⚠ PROXY fwma(10) 1-bar pct change                   0.5863    0.5878    0.5283    0.5755    0.6155    0.5980

max |rho| per comparator, worst first:
    0.9016  ao, 1-bar change / close
    0.8682  stochrsi: STOCHRSIk_14_14_3_3
    0.8368  stochrsi: STOCHRSId_14_14_3_3
    0.6453  cmo_14
    0.6155  ⚠ PROXY fwma(10) 1-bar pct change
    0.5407  er_10
    0.4930  qqe: QQEs_14_5_4.236
    0.4700  chop_14
    0.3076  natr_14
    0.3026  ao / close (the level this column differences)
```

Under reduced CPU dispatch the table moves in the fourth decimal at most
(`stochrsi` K on `trend` 0.8156 → 0.8152, on `jump` 0.8630 → 0.8628);
every row's max |ρ| is unchanged to four decimals.

⚠ **The top row is the finding of this section.** The filter of §F is
blind to the price level, which is exactly why it is NOT independent of the
Awesome Oscillator this fork already ships: against `AO`'s own 1-bar change
over close it reads **0.8638 .. 0.9016**, while against the `AO / close`
LEVEL it reads only 0.1187 .. 0.3026. **The differencing is the column.**
"This is more than the AO" is therefore not an argument available at Gate
E, and `test_the_column_is_near_the_ao_1_bar_change_and_far_from_its_level`
pins the ordering so a future session has to pass it before reaching for
that argument.
⚠ Neither of those two comparators is a shipped `Category` column: `AO_5_34`
itself is a price LEVEL (`PX` in the dictionary), which is why both rows
divide by close.

⚠ **The nearest SHIPPED fork column is `stochrsi`'s `STOCHRSIk_14_14_3_3`
at 0.7965 .. 0.8682** — in the DISCLOSE_GAP band on synthetic frames. That
agrees with the screen's own stage-2 fork overlap, which put the same
column nearest at max |ρ| **0.8233** with a per-frame max median of 0.8245
on **12 REAL** frames, and concluded "not a restatement at the 0.90 line".
Two different universes reaching the same comparator is the strongest
non-redundancy evidence this worktree can produce, and neither of them is
Gate E.

⚠ **The `fwma` row is a PROXY this session invented** and is evidence
about nothing but itself. The screen's top Gate E comparator is the
engine's `FWMA_Slope_pct_Pctl`, whose definition is not readable from this
worktree; `fwma(close, 10)` 1-bar percent change is a guess at its shape,
labelled as one in the script's own output.

---

## §W the dictionary's 150-character cut

`docs/gen_indicator_dictionary.py`'s `desc()` keeps a paragraph of up to
150 characters whole and otherwise drops the trailing WORD
(`d[:150].rsplit(' ', 1)[0] + '…'`), so the penalty for passing the budget
is a whole word rather than a character.

```
paragraph (115 chars): The Awesome Oscillator minus its own 5-bar mean,
over close: how fast the AO is moving rather than where it stands.
desc() returns it whole: True
characters of slack before a word is lost: 35
```

`test_the_docstrings_first_paragraph_survives_the_dictionary_cut` runs the
generator's OWN `desc`, lifted out of its source with `ast` so importing
it does not run the whole indicator probe — so the assertion fails if the
generator's cut changes, and not only if this sentence grows.

---

## §Z cost

Three rolling passes (`_sma(mid, FAST)`, `_sma(mid, SLOW)`,
`_sma(ao, SIGNAL)`), two divisions (`/ 2` for `mid` and `/ close`) and one
`where` for the divisor guard, no Python loop, so time and memory are
linear in bars.

```
    bars     ms (best of 5, two runs)   peak MB
  100000           6.4 .. 6.4                 4.8
  400000          24.2 .. 25.1               19.2
```

⚠ **The milliseconds are this machine's and this run's and are NOT a
claim, and this file has the evidence for saying so.** Eight runs of §Z on
this worktree — three by this session, one by the round-2 reviewer and
four by the round-3 reviewer — printed:

| whose run | 100k ms | 400k ms | ratio |
|---|---|---|---|
| session, 1st | 6.4 | 24.7 | 3.86× |
| session, 2nd | 6.3 | 24.2 | 3.84× |
| session, 3rd | 6.4 | 24.2 | 3.78× |
| round-2 reviewer | 5.8 | 25.1 | 4.33× |
| round-3 reviewer | 5.7 | 25.9 | 4.54× |
| round-3 reviewer | 6.3 | 24.4 | 3.87× |
| round-3 reviewer | 6.4 | 23.8 | 3.72× |
| round-3 reviewer | 6.7 | 24.5 | 3.66× |

so the observed time ratio spans **3.66× to 4.54×** and no ratio digit is
claimed. The spread is visible inside a single run too: the session's
third run printed 24.2 .. 25.1 ms for the two repeats of the 400,000-bar
case, which is most of the between-run spread in one invocation.
⚠ The 3.8×–4.3× band this section carried after round 2 was computed from
three of those runs and did not contain the largest of the three (4.33×);
round 3 caught it, and the lesson is the one this repo keeps relearning —
a band is a claim and needs the same measurement a point estimate does.

What IS claimed, and this is the complete list: the traced peak
(**4.8 MB** at 100,000 bars and **19.2 MB** at 400,000, identical on all
eight runs above), **4.0× the memory for 4× the bars**, a time ratio
within a small constant factor of linear, and the ordering. No test
asserts any of it; §Z is a disclosure.

---

## §E Gate E — **pending, run by issue-solver after this session**

Gate E needs the parent repo's private engine, its 827 MB BIST cache and
`../Backtesting/Backtesting/scripts/analysis/gate_e_overlap.py`, none of
which this session may touch. The launcher runs

```
python scripts/analysis/gate_e_overlap.py run --module pandas_ta.momentum.j_acosc
```

after this session, and a later receipt session writes the result into this
section and records the row with
`python docs/gate_e_ledger.py record <run dir> --measured YYYY-MM-DD`.

Until then `docs/gate_e_ledger.csv` has **no row for `j_acosc`**, and that
is deliberate and pinned twice:

* `tests/test_j_acosc.py::test_the_gate_e_row_is_owed` asserts the row is
  absent, so the receipt session has a cue that fails the moment it
  records one;
* `tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
  fails locally, reporting
  `['arch_lm', 'diff2_acf1', 'edge', 'firstzero_ac', 'halflife', 'j_acosc', 'lumpiness', 'mtd_ret']`.
  On a PR into `dev` that same check SKIPS with a reason starting "Gate E
  owed" (`GATE_E_PENDING_OK=1`); toward `main` it fails, so a release needs
  the row.

**Gate C's real-data limb is owed from the same run**, and so is the
question of whether any BIST bar reads exactly 0.0 (no synthetic varying
frame does; the `flat` frame reads 0.0 on all 1,463).

### §E0 what the 2026-10-24 screen measured, on the PROTOTYPE

Quoted from issue #106. ⚠ A prototype is not a port — but §A2 asserts this
module BIT-equal to that prototype on all seven frames, so the figures
below are the ones the launcher's run is expected to reproduce, and a
material disagreement would be a finding about the port rather than about
the screen.

* **max |ρ| 0.8381** vs `FWMA_Slope_pct_Pctl` (manifest, n = 391,996);
  top-5 per-frame max median **0.8431** → **DISCLOSE_GAP**
  (0.80 ≤ ρ < 0.90 under `r3-perframe-0.90`).
* Next comparators: `FWMA_Slope_pct` 0.8278, `StochRSI_K` 0.8156.
* Run `screen_20261024`:
  `gate_e_overlap.py run --module ind_screen --fn screen`, Backtesting
  `main` b2d94243, 89 ALTPORT-1 frames, 398,849 bars, 329 + 358 = 687
  comparators, canary bit-equal.
* Stage-2 fork overlap (not Gate E; scale-free `Category` outputs at
  defaults, 12 frames): max |ρ| **0.8233** vs
  `stochrsi:STOCHRSIk_14_14_3_3`, per-frame max median 0.8245 → not a
  restatement at the 0.90 line. §L1 reaches the same comparator on
  synthetic frames.
* Pre-flight on 6 frames (`sanity.csv`): prefix-causal, unchanged under
  price ×8 and volume ×8.

⚠ **DISCLOSE_GAP is a ship with a note, not a strike.** If the launcher's
run lands STRUCK instead — pooled |ρ| ≥ 0.90, or a top-5 comparator's
per-frame median ≥ 0.90 — the column is reverted or waived before a
release, and this file stays as the receipt either way.

⚠ **`StochRSI_K` at 0.8156 in that list is the engine's column, and §L1
measures the FORK's `stochrsi` at 0.7965 .. 0.8682 on synthetic frames.**
Those are two different columns on two different universes; the agreement
is encouraging and is not a substitute for either measurement.

---

## Verdict

| gate | verdict | the number that carries it |
|---|---|---|
| **A** Correctness | **PASS** | three independent spellings on 1,463 of 1,463 bars of each of seven frames: a `math.fsum` oracle within 4.536e-16 absolute (asserted 1e-14; 4.569e-16 under reduced dispatch), the screen prototype bit-equal, and the fork's own `ao` + `sma` bit-equal. §A4 prices the three readings not taken, and discloses that the EMA reading is NEAR (0.8966 .. 0.9277) rather than far |
| **B** Causality | **PASS** | the module caught 0 of 36 perturbation offsets on each of six varying frames; all five look-ahead mutants caught 36 of 36 on all six, each live on `walk` at every shared bar (1,445 of 1,445 `fast-lead`, 1,462 of 1,462 the other four), the one exception across the six frames being `divisor-lead` on `grid` at 1,456 of 1,462 (§B2); smallest single catch 5.971e-08 against §D2's 1.886e-10 noise |
| **C** Reachability | **PASS synthetic, real data OWED** | 1,463 of 1,500 bars on each of seven frames, 1,463 distinct values on the six varying ones, exactly 0.0 on all 1,463 of the flat one; NaNs a leading prefix on all seven. Real-data counts come with Gate E (§C2, §E) |
| **D** Scale-free | **PASS** | ×8 / ×64 bit-identical on 1,463 of 1,463 bars of seven frames and at levels 1e−6 / 1e+6 / 1e+100; inexact factors within 1.812e-10 (1.886e-10 under reduced dispatch) against a 1e-7 bound, masks matching; `0 < 1,463 < 1,500` on all seven |
| **E** Attribution | **PENDING — run by issue-solver after this session** | the screen measured the PROTOTYPE at **DISCLOSE_GAP**: max \|ρ\| 0.8381 vs `FWMA_Slope_pct_Pctl` (n = 391,996), top-5 per-frame max median 0.8431 (§E0). §A2 makes this module bit-equal to that prototype, so those are the figures the run is expected to reproduce |
| **F** Suites | **PASS here, both repos are the launcher's** | 175 for the module, the same 175 under reduced CPU dispatch, full suite 3 failed / 9,120 passed / 85 skipped — the three being `dev`'s two clean-checkout failures plus the owed Gate E row (§SUITES) |

**Why this ships into the launcher's Gate E rather than reverting now.**
Issue #106 closes either way, so the question is whether anything measured
here argues for deleting the column before Gate E sees it. Two things come
close and neither decides it:

1. **It is close to a differenced `AO`** — 0.8638 .. 0.9016 against `AO`'s
   1-bar change over close (§L1). But that comparator is NOT a shipped
   column: `AO_5_34` ships as a price LEVEL, which the fork's own ML
   contract says is not a feature, and against that level this column reads
   0.1187 .. 0.3026. So the overlap is with a column the fork does not
   have.
2. **The nearest shipped fork column is in DISCLOSE_GAP** —
   `stochrsi:STOCHRSIk_14_14_3_3` at 0.7965 .. 0.8682 synthetic, matching
   the screen's 0.8233 on 12 real frames. DISCLOSE_GAP is a ship with a
   note under `r3-perframe-0.90`; the strike line is 0.90 and neither
   universe reaches it.

Everything else passes: the formula is right by three spellings, the column
is causal under five mutants, scale-free bit-exactly under ×8/×64, and
reachable on every synthetic frame. The screen's own Gate E figure on the
bit-identical prototype was 0.8381 — DISCLOSE_GAP, not STRUCK. If the
launcher's run on this module lands STRUCK, the column is reverted or
waived and this file is the receipt.

What a consumer must know, in one place:

1. **It is a 38-tap high-pass filter of `mid`** — |H| 0 at DC, peak
   0.673744 at a period of 11.4939 bars, 0.160000 at Nyquist — so it is
   blind to the price level (§F).
2. **That does not make it independent of the AO**: 0.8638 .. 0.9016
   against `AO`'s 1-bar change over close. The differencing IS the column
   (§L1).
3. **The warm-up is 37 bars = the two windows ADDED**, not 33. The signal
   averages `AO`, not the price (§C1).
4. **It amplifies the last bits**: a 1e-16 move in a price is up to
   1.812e-10 in the column (§D2).
5. **It is unbounded**; the seven frames span −0.1101 .. +0.1198 and a
   flat price reads exactly 0.0 (§C1).
6. **One guard, on the divisor.** A bad close empties its own bar; a bad
   high/low empties the 38 bars its windows reach and moves nothing
   earlier, with an `inf` behaving exactly like a NaN; a cross-scale frame
   overflows and is not guarded (§G1, §G3, §G5).
7. **Gate E is PENDING** (§E). Until the row is recorded, `dev` carries an
   unmeasured column, which is what `GATE_E_PENDING_OK=1` is for.

## Decisions this session made, and why

Nine, all recorded as ASSUMPTIONs in
`docs/reviews/auto-2026-11-14-j-acosc/00-manifest.md` because
`AskUserQuestion` is unavailable in a headless run and the rule is to take
the smaller scope:

1. **One column**, `J_ACOSC_5_34_5`. The issue quotes a single series and
   `ind_screen.py`'s `j_acosc` returns one. A sign/colour state column
   would be `np.sign` of this one and is the wider scope.
2. **No parameter surface.** 5, 34 and 5 are the source's constants, as
   `JAW`/`TEETH`/`LIPS` are in `j_gator`.
3. **SMA read as `rolling(n).mean()` at pandas' default
   `min_periods=n`**, on the issue's wording and the prototype and NOT on
   jesse's unread source. §A4 prices all three alternatives; (a) is the one
   that is uncomfortably near.
4. **`_sma` spelled in the module, not imported from
   `pandas_ta.overlap.sma`.** §A3 asserts them bit-equal, so this costs
   nothing arithmetically and avoids a rename plus a second
   `verify_series` pass on each of its three calls.
5. **Category `momentum`**, where `ao` lives.
6. **`WARMUP` = `SLOW + SIGNAL - 2` as a module constant**, so the trap
   §A4(b) describes is named in the code rather than only in prose.
7. **One guard, on the divisor only** (§G1), with §G3 measuring that `mid`
   needs none — an `inf` empties like a NaN — and §G5 naming what is left
   unguarded.
8. **Gate A is a tolerance against the independent oracle and bit-equality
   against the prototype and the fork route** (§A1, §A2, §A3), with the
   ABSOLUTE bound as the tight one.
9. **An invented `fwma` proxy is included in §L1 and labelled as
   invented.** The engine's `FWMA_Slope_pct_Pctl` is the screen's top
   comparator and is unreadable here; a labelled guess is more useful than
   silence, and the label is what keeps it from becoming evidence.

## §SUITES suite output

```
$ python -m pytest tests/test_j_acosc.py -q
175 passed

$ python docs/measure_j_acosc_cpu.py
numpy 1.26.4
NPY_DISABLE_CPU_FEATURES = 'AVX512F AVX512_SKX AVX2 FMA3'
dispatchable features still enabled: ['SSSE3', 'SSE41', 'POPCNT', 'SSE42',
 'AVX', 'F16C', 'AVX512CD', 'AVX512_CLX', 'AVX512_CNL', 'AVX512_ICL']
175 passed

$ python -m pytest -q
FAILED tests/test_altrepo_talib_csv.py::test_regenerating_reproduces_the_committed_rows
FAILED tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one
FAILED tests/test_pine_coverage_csv.py::test_audited_rows_carry_their_evidence
3 failed, 9120 passed, 85 skipped in 233.91s
```

⚠ The module's test COUNT moved during review and the figures above are
the final run: round 1 left **175**, round 2's new
`test_the_fast_lead_mutant_reaches_eighteen_bars_not_two` made it **176**,
round 3's fix to `test_gate_d_scale_at_extreme_price_levels` folded three
parametrized cases into one loop (the three levels now have to be compared
WITH each other, which a parametrized test cannot do) giving **174**, and
round 4's new
`test_the_flat_frame_is_excluded_because_divisor_lead_cannot_be_caught_there`
brought it back to **175**. The review log records each step.

The three failures are `dev`'s own, not this port's:

* `test_regenerating_reproduces_the_committed_rows` needs the sibling
  `../AlternativeRepos` checkout and is deselected by name in CI;
* `test_audited_rows_carry_their_evidence` is the known break of
  `CLAUDE.md` § *Known breaks* (`8d8f705` untracked `docs/pine/`) and is
  also deselected in CI;
* `test_every_indicator_that_needs_a_row_has_one` is the OWED Gate E row,
  red by design here and a skip on a PR into `dev` (§E).

⚠ **A pre-existing ordering defect, recorded and not fixed** (outside this
issue's scope; already recorded by #100 … #105). `pandas_ta/core.py:453`
hands out the live `Category[name]` list and `core.py:692` removes names
from it, so a module that exercises `df.ta.strategy()` shrinks `Category`
for every module collected after it in the same process. Measured again
this session, on the modules this port touches:
`python -m pytest tests/test_ml_companions.py tests/test_wiring_accessors.py tests/test_readme_counts.py`
fails 3 tests, all of them in `test_readme_counts.py`
(`test_every_category_is_listed_with_the_right_count`,
`test_the_headline_states_the_category_count`,
`test_the_outside_category_paragraph_names_exactly_the_right_indicators`,
the first reporting `long_run` among 3 names missing from the live
`Category`); dropping `test_wiring_accessors.py` from that command gives
20 passed. Alphabetical collection in a full run puts the readme and
altport modules BEFORE `test_wiring_accessors.py`, which is why the full
suite above is green on them.
