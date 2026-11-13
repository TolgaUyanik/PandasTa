# `ts_kurt_60` — measured

Issue #93 (TS-KURT-60), ported 2026-11-13 on branch `issue-93-ts-kurt-60`.
Column: **`TS_KURT_60`**, `pandas_ta/statistics/ts_kurt_60.py`.
**Status: Gates A–D measured here, Gate E owed.**
Gate E: pending, run by issue-solver after this session. Until that run is
recorded in `docs/gate_e_ledger.csv`,
`tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
fails locally for this column, and that failure is expected rather than a
defect. Gate C's real-data counts come from the same run and are **owed**;
what is here is synthetic.

Every number here is printed by `python docs/measure_ts_kurt_60.py` on
pandas 2.3.3 / numpy 1.26.4, or asserted by
`python -m pytest tests/test_ts_kurt_60.py -q`. Nothing in this file was
typed from expectation; where a number is *not* measured, the line says so.

## What it is

    r[t]       = close[t] / close[t-1] - 1
    m2, m4     = mean(d**2), mean(d**4)  with d = r - mean(r) over the window
    g2         = m4 / m2**2 - 3
    TS_KURT[T] = ((n + 1) * g2 + 6) * (n - 1) / ((n - 2) * (n - 3))
                 masked where max(r) - min(r) <= 9.09e-13 over the window

At the default `length=60`: the sample (bias-corrected) excess kurtosis — G2,
Fisher's — of the trailing 60 simple returns. The window reads 61 closes, and
the first value lands at bar 60.

The arithmetic is pandas' own `rolling(length).kurt()`; the module owns the
return construction and the NaN discipline around it. That is a deliberate
choice, measured in §Gate A rather than argued: it makes the port and the
screened prototype the same column to the last bit where both fire, it is not
materially less accurate than the four other spellings checked against an
exact oracle (§A4 — the `fsum` loop is the closest of the five on all three
frames and this one is within 1.31× of it), and it is 5–63× cheaper in memory
than the numpy form it was checked against (§Cost).

What the column reads is **how much of the window's squared dispersion sits
in its few largest moves** — not how large those moves are. It is scale-free
in the returns themselves, which is exactly what makes it not a volatility
feature (§Invariances).

## Source, and what "tsfresh (MIT)" does and does not mean here

The issue names tsfresh's `feature_calculators` (MIT) and states the formula:

> `kurtosis on 60 returns`

with the screen prototype (`docs/issues/screen/ind_screen.py`, candidate
`ts_kurt_60`) spelling it as

    @cand("ts_kurt_60", "excess kurtosis of returns (60)", TS,
          "kurtosis on 60 returns")
    def _(o, h, l, c, v): return ret(c).rolling(60).kurt()

⚠ **tsfresh is not installed in this worktree and web access is
unavailable.** Its own code was not read in this session. So the attribution
is an attribution, not an oracle: Gate A below is against the issue's stated
line, the prototype, the published DEFINITION of
`feature_calculators.kurtosis` (`pandas.Series.kurtosis`, i.e. the
bias-corrected G2) and four independent spellings of that definition.
Anything tsfresh does that the line does not say — what it returns for a
series shorter than four samples, whether it drops NaNs rather than returning
NaN — is **unverified here**. The prototype (gitignored, local to the owner's
machine) was read and imported.

## Gate A — correctness

### A1. The two windows with an exact closed form

Both bounds are derivable, which makes them the hand cases. For n samples
`1 <= m4/m2**2 <= (n**2 - 3n + 3)/(n - 1)`:

* the **ceiling** is the one-hot window, where
  `m4/m2**2 = (n**2 - 3n + 3)/(n - 1)`, and the sample correction collapses
  to exactly `n`:
  `[(n+1)(n**2-3n+3) - 3(n-1)**2] / ((n-2)(n-3)) = n(n-2)(n-3)/((n-2)(n-3))`;
* the **floor** is any window taking two values in equal counts, where
  `m4/m2**2 = 1`, so `g2 = -2` and `G2 = -2(n-1)/(n-3)`.

⚠ The bound on the BIASED ratio is `(n²−3n+3)/(n−1)` = **58.016949** at
n = 60, not `n`; `m4/m2² ≤ n` is true but slack, and no window attains it.
What the sample correction maps to exactly `n` is the sharp bound.

| window, at the shipped `length=60` | exact | module | \|difference\| |
|---|---|---|---|
| one-hot: 59 returns of 0 and one of +1 (the frame plants a +1 every 60 bars, so all 1,440 fired windows are one-hot; 24 of them have the spike as their newest return) | 60.0 | min = max = 59.999999999999986, **1 distinct value over all 1,440 bars**, 0 above the ceiling | 1.421e-14 |
| alternating ±0.5, so 30 of each (1,440 bars) | -2.070175438596491 | -2.070175438596491 … -2.070175438596492 | 4.441e-16, **bit-equal on 1,195 of 1,440** |

Neither is bit-exact at the ceiling: `m2 = (n-1)/n**2 = 59/3600` is not a
dyadic rational, so the one-hot window rounds. The floor is bit-exact on 83%
of its bars and one ulp away on the rest.

At `length=4`, the smallest window the estimator is defined on, the same two
constructions are exact:

| window | exact | module |
|---|---|---|
| closes `[1,1,1,1,2]` → returns [0,0,0,+1] | 4.0 | 4.000000000000000 |
| returns [+½,−½,+½,−½] | −6.0 | −6.000000000000000 |

The bounds are then checked per length against 2,000 student-t(1.5) windows
each — a draw heavy enough to approach the ceiling. ⚠ These rows evaluate the
FORMULA, not the module: the draws are never turned into a price path, so
read them as the algebra being right, not as the column being inside its
bounds. `tests/test_ts_kurt_60.py` carries both — a formula check at these
six lengths and a separate one that runs a 3,000-bar student-t(1.5) path
THROUGH the module at the same six lengths and asserts that the column's own
min and max are inside the bounds.

| length | floor | ceiling | 2,000 draws span | inside |
|---|---|---|---|---|
| 4 | −6.000000 | 4.0 | [−5.962628, 3.999771] | yes |
| 10 | −2.571429 | 10.0 | [−2.077293, 9.997757] | yes |
| 20 | −2.235294 | 20.0 | [−1.251578, 19.999428] | yes |
| 60 | −2.070175 | 60.0 | [−0.353760, 59.984412] | yes |
| 120 | −2.034188 | 120.0 | [0.422268, 119.999251] | yes |
| 250 | −2.016194 | 250.0 | [2.726169, 249.887268] | yes |

### A2. Against the screen prototype

1,500-bar frames, 1,440 fired bars each:

| frame | max \|diff\| | bit-equal | Spearman | NaN masks |
|---|---|---|---|---|
| gaussian walk, prototype **imported** from `docs/issues/screen/ind_screen.py` | 0.000000e+00 | **1440/1440** | 1.000000 | equal |
| tick-rounded walk, **imported** | 0.000000e+00 | **1440/1440** | 1.000000 | equal |
| student-t(2) path, **imported** | 0.000000e+00 | **1440/1440** | 1.000000 | equal |
| gaussian walk, prototype retyped in the measurement script | 0.000000e+00 | **1440/1440** | 1.000000 | equal |
| tick-rounded walk, retyped | 0.000000e+00 | **1440/1440** | 1.000000 | equal |
| student-t(2) path, retyped | 0.000000e+00 | **1440/1440** | 1.000000 | equal |

The imported row is the real candidate, not a retype: the script loads
`REG["ts_kurt_60"]["fn"]` out of that file when the worktree has it, and says
so when it does not (a clone does not — `docs/issues/` is gitignored).

⚠ Bit-equality on these frames does **not** make the port and the prototype
the same function. They differ wherever the prototype's own degenerate test
lets a window through:

| frame | port fires | prototype fires | bars the port empties and the prototype does not | what the prototype reads there |
|---|---|---|---|---|
| flat 300 closes | 0/300 | 240/300 | 240 | exactly −3.0 |
| a 70-bar flat run planted in a 400-bar walk | 330/400 | 340/400 | 10 | exactly −3.0 |
| 1%-a-bar geometric ladder, 300 closes | 0/300 | 0/300 | 0 | — |

−3.0 is **below this statistic's own floor** of −2.0702, so it is not a value
the column can otherwise take; a consumer could not have placed it as a
degenerate flag either. That is the whole value of the mask.

### A3. Against the definition, spelled four other ways

The first is the one the attribution chain names and the one it would have
been easy not to run: tsfresh's `kurtosis(x)` is `pandas.Series(x).kurtosis()`,
which inside pandas is `nanops.nankurt` — a **two-pass** centred-moment
function, a different implementation from the online `calc_kurt` that backs
`rolling.kurt`. It is applied here window by window
(`r.rolling(60).apply(lambda w: Series(w).kurtosis())`). The other three share
no arithmetic with `rolling.kurt` either: two passes over the centred moments
in numpy, the textbook `ddof=1` form
(`n(n+1)/((n-1)(n-2)(n-3)) · Σd⁴/s⁴ − 3(n-1)²/((n-2)(n-3))`), and plain Python
with `math.fsum` so its accumulation is exact.

| spelling | frame | n | max \|diff\| | bars > 1e-09 | Spearman | NaN masks |
|---|---|---|---|---|---|---|
| **`pandas.Series.kurtosis` (`nanops.nankurt`), the literal tsfresh spelling** | walk | 1,440 | 5.329071e-15 | 0 | 1.000000 | equal |
| **`pandas.Series.kurtosis`** | tick-rounded | 1,440 | 3.996803e-15 | 0 | 1.000000 | equal |
| **`pandas.Series.kurtosis`** | student-t(2) | 1,440 | 8.526513e-14 | 0 | 1.000000 | equal |
| numpy two-pass centred moments | walk | 1,440 | 5.329071e-15 | 0 | 1.000000 | equal |
| numpy two-pass centred moments | tick-rounded | 1,440 | 4.329870e-15 | 0 | 1.000000 | equal |
| numpy two-pass centred moments | student-t(2) | 1,440 | 9.947598e-14 | 0 | 1.000000 | equal |
| unbiased-variance (`ddof=1`) spelling | walk | 1,440 | 5.995204e-15 | 0 | 1.000000 | equal |
| plain-Python scalar loop, `math.fsum` | 400-bar walk | 340 | 2.768619e-15 | 0 | 1.000000 | equal |

### A4. Which spelling is accurate — an exact rational oracle

Every float64 close is a rational, so the whole statistic is: the oracle
computes it in `fractions.Fraction` and rounds once, at the end. That is the
true value *of these inputs*, so it decides the question the online
raw-moment form raises (pandas accumulates Σx, Σx², Σx³, Σx⁴ and subtracts
same-sized quantities).

260-bar frames, 200 fired bars. All five spellings, all three frames — no row
dropped:

| frame | spelling | max \|diff\| vs exact | max relative | bit-equal |
|---|---|---|---|---|
| walk | **this module (`rolling.kurt`)** | 6.994e-15 | 1.158e-13 | 4/200 |
| walk | `Series.kurtosis` (`nankurt`) | 6.717e-15 | 1.284e-13 | 5/200 |
| walk | numpy two-pass centred moments | 7.216e-15 | 1.468e-13 | 2/200 |
| walk | plain-Python `fsum` loop | **6.509e-15** | 2.299e-13 | 0/200 |
| walk | unbiased-variance spelling | 6.717e-15 | 1.400e-13 | 4/200 |
| tick-rounded | **this module** | 8.341e-15 | 2.987e-13 | 1/200 |
| tick-rounded | `Series.kurtosis` | 9.250e-15 | 2.330e-13 | 1/200 |
| tick-rounded | numpy two-pass | 9.277e-15 | 2.602e-13 | 1/200 |
| tick-rounded | `fsum` loop | **7.820e-15** | 2.602e-13 | 1/200 |
| tick-rounded | unbiased-variance spelling | 8.361e-15 | 2.934e-13 | 0/200 |
| student-t(2) | **this module** | 6.040e-14 | 6.013e-15 | 2/200 |
| student-t(2) | `Series.kurtosis` | 5.329e-14 | 6.382e-15 | 5/200 |
| student-t(2) | numpy two-pass | 5.329e-14 | 6.607e-15 | 4/200 |
| student-t(2) | `fsum` loop | **4.619e-14** | 5.995e-15 | 5/200 |
| student-t(2) | unbiased-variance spelling | 5.684e-14 | 5.995e-15 | 9/200 |

**The cancellation does not materialise on returns at these lengths.** All
five spellings sit within a factor of 1.5 of each other and of the exact
value. The `fsum` loop — whose accumulation is exact by construction — is the
closest on **all three** frames, and `rolling.kurt` is within **1.31×** of it
(6.994/6.509, 8.341/7.820, 6.040/4.619); on the student-t frame this module
is the worst of the five, by 1.31×. That is the measurement behind keeping
it: the simpler spelling is not *materially* less accurate here, not that it
is the most accurate. ⚠ And it is a measurement on RETURNS (|r| ≈ 1e-2,
mean ≈ 0); it says nothing about `rolling.kurt` on a price LEVEL, where the
same cancellation is a real hazard — one more reason this column is of
returns.

### A5. The readings the wording leaves open, priced

All on the same 1,500-bar gaussian walk, 1,440 fired bars, port against
variant:

| reading | max \|diff\| | Spearman | verdict |
|---|---|---|---|
| **log returns** instead of simple | 0.2526 | 0.998596 | rejected — the prototype's `ret` is simple. Close, but not a relabelling: the 10 bars of largest disagreement all sit above 1.8, i.e. where the column is interesting (port values 2.8643, 2.7268, 2.4409, 2.3214, 2.3155, 2.1244, 2.0946, 1.9643, 1.8600, 1.8337) |
| **biased g2**, no sample correction | 0.3315 | 1.000000 | rejected — tsfresh's `kurtosis` is `pandas.Series.kurtosis`, the corrected G2. Invisible to a rank miner (for fixed `length` it is an exact affine map: `((n+1)*g2 + 6)*(n-1)/((n-2)*(n-3))` rebuilds the column to 5.329e-15), visible to a threshold |
| **raw (Pearson) kurtosis**, no −3 | 3.000000 | 1.000000 | rejected — the issue says *excess*. The difference is exactly the constant 3 |
| **60 CLOSES** (59 returns) instead of 60 returns | 1.0212 | 0.992198 | rejected — the issue says 60 returns. Priced because it is the off-by-one a reader makes, and it is a near-copy rather than a different question |
| a degenerate window reads **0 or −3** instead of NaN | see the table below | — | rejected — and both alternatives are the answer of a real spelling of the source, not a straw man |

**The degenerate window, measured across the three spellings** — flat 300
closes:

| spelling | fires | reads |
|---|---|---|
| **this port** | 0/300 | — |
| `rolling.kurt` (the prototype) | 240/300 | exactly **−3.0**, which is below this column's floor of −2.0702 |
| `pandas.Series.kurtosis` (the literal tsfresh spelling) | 240/300 | exactly **0.0**, the value a gaussian would score |
| numpy two-pass with the floor removed | 0/300 | — (`m2 == 0`, so it is NaN by arithmetic) |

Two spellings of the same named source give two different answers on the same
degenerate window, and one of them (0.0) is indistinguishable from an
ordinary reading. That is the argument for the module deciding this rather
than inheriting it.

**It is not the fork's existing `kurtosis`.** That indicator takes the same
moment of the CLOSE. On the same walk:

| comparator | max \|diff\| | Spearman |
|---|---|---|
| `kurtosis(close, length=60)` | 3.7122 | **−0.0847** |
| `kurtosis(close)` → `KURT_30`, its default | 4.4750 | **−0.1090** |

Kurtosis of a price level reads the shape of a trend; kurtosis of returns
reads the shape of a return distribution. The sign is negative on this frame
and the magnitude is small either way, so the two are not each other's
restatement — Gate E decides this against the real comparator set, not this
line.

## Gate B — causality, by mutant

A future-perturbation sweep: every bar from J onward is replaced with a
different path, and the test is whether anything strictly **before** J moves.
36 offsets per cell, J = 80 … 1,480 step 40 (past the 60-bar warm-up). Prefix
truncation alone cannot see back-dating, which is why this is a perturbation
sweep.

Five mutants, each `importlib`-read from the shipped file and `exec`'d in
memory:

| id | mutation |
|---|---|
| `back_date_two` | the column `.shift(-2)` — the value stamped 2 bars early |
| `back_date_full` | the column `.shift(-(length - 1))` — stamped at the window's first bar |
| `forward_return` | `r = px.shift(-1) / px - 1` — tomorrow's return stamped today |
| `rolled_window` | the window taken from `r.shift(-(length // 2))` |
| `centered_window` | `rolling(..., center=True)` — the window straddles the bar |

| cell | real module leaks | mutant caught |
|---|---|---|
| walk | **0/36** | 36/36 for all five |
| tick-rounded walk | **0/36** | 36/36 for all five |
| student-t(2) path | **0/36** | 36/36 for all five |

All fifteen mutant cells are 36/36 and all three real-module cells are 0/36 —
no excuses owed. The column is continuous and every bar of the window enters
the mean, so there is no discrete absorption of the kind `ts_binent_20` and
`ts_peaks_20` had to measure around.

Non-default lengths, on the walk (the real module leaks 0/36 in every one):

| mutant | length 20 | length 120 | length 4 |
|---|---|---|---|
| `back_date_two` | 36/36 | 35/36, missed J=80 | 36/36 |
| `back_date_full` | 36/36 | 36/36 | 36/36 |
| `forward_return` | 36/36 | 35/36, missed J=80 | 36/36 |
| `rolled_window` | 36/36 | 34/36, missed J=80, 120 | 36/36 |
| `centered_window` | 36/36 | 36/36 | 36/36 |

The misses at `length=120` are the sweep's own limit, not the mutant's: at
J = 80 and J = 120 the prefix is inside or barely past a 120-bar warm-up, so
there is nothing before J for either version to have written. Every mutant is
still a different column from the real one at that length
(`mutant-equals-real=False` in all fifteen cells).

**The sixth mutant, and why it is reported separately.** The degeneracy guard
read one bar into the future —
`spread = (rolling.max() - rolling.min()).shift(-1)` — is a real look-ahead
and the sweep above **cannot see it**: on a walk, a tick-rounded walk and a
student-t path the guard empties **0** windows, so moving it changes nothing.

| frame | changes the column | caught | windows the guard empties |
|---|---|---|---|
| walk | yes | 0/36 | 0 |
| tick-rounded | yes | 0/36 | 0 |
| student-t(2) | yes | 0/36 | 0 |
| 70-bar flat run planted in a 400-bar walk, 16 offsets J = 80…380 step 20 | yes | **1/16** | 10 |

So the guard's causality rests on the planted frame, where it is caught, and
on the fact that `rolling.max()`/`rolling.min()` are trailing windows of the
same length as the value they mask. The real module leaks 0/16 on that frame
too. This is stated as a limit of the sweep rather than smoothed over.

`offset=2` equals `shift(2)` and `offset=-2` equals `shift(-2)` — both
measured, so the documented escape hatch is the only way to get a non-causal
column out of this module.

## Gate C — reachability

**Synthetic only; the real-data counts are owed with Gate E.**

| frame (1,500 bars) | fires | distinct values | non-zero among fired | range |
|---|---|---|---|---|
| gaussian walk | 1,440 | 1,440 | 1,440 | [−1.2434, 2.8643] |
| tick-rounded walk | 1,440 | 1,440 | 1,440 | [−1.0483, 2.6676] |
| student-t(2) path | 1,440 | 1,440 | 1,440 | [0.3265, 56.2111] |

`0 < fires < n` holds on all three, and the column is continuous — every
fired bar takes a distinct value, so no constant or near-constant column can
hide here. The 60 NaN bars are exactly the warm-up.

Distribution by the SHAPE of the returns, 1,500-bar paths, 1,440 fired bars:

| path | min | p10 | median | p90 | max | return sd |
|---|---|---|---|---|---|---|
| uniform | −1.6162 | −1.3654 | −1.1694 | −0.8712 | −0.3731 | 0.0116 |
| gaussian | −1.2434 | −0.7289 | −0.1283 | 1.0915 | 2.8643 | 0.0151 |
| tick-rounded gaussian | −1.0483 | −0.5966 | −0.0307 | 0.8166 | 2.6676 | 0.0153 |
| laplace | −0.6837 | 0.4174 | 1.9349 | 4.2497 | 9.8361 | 0.0135 |
| student-t(2) | 0.3265 | 1.6016 | 9.7454 | 48.2003 | 56.2111 | 0.0357 |
| two-point (±σ) | −2.0702 | −2.0702 | −2.0507 | −1.8887 | −1.6395 | 0.0100 |

The ordering is by tail shape and not by amplitude: the two-point path has
the *smallest* return sd and sits at the floor, the laplace path has a
smaller sd than the gaussian one and reads 2.1 higher at the median.

What "normal" looks like, over 2,000 **independent** iid gaussian 60-return
windows (no window overlap, so this is the sampling distribution rather than
a path): median −0.1071, mean −0.0076, sd 0.6029, p10 −0.6542, p90 0.7473,
and 5.9% above 1.0.

## Gate D — scale-freeness

Every input is a price ratio and `8a / 8b` is the same double as `a / b`, so
a ×2^k rescale cancels exactly:

| frame | ×8 | ×64 | ×10 | ×3.7 |
|---|---|---|---|---|
| gaussian walk (1,440 fired) | **bit-equal 1440/1440** | **1440/1440** | 46/1440, max \|diff\| 3.975e-14 | 44/1440, 2.798e-14 |
| tick-rounded walk (1,440) | **1440/1440** | **1440/1440** | 36/1440, 2.143e-14 | 51/1440, 2.198e-14 |
| student-t(2) path (1,440) | **1440/1440** | **1440/1440** | 122/1440, 1.217e-13 | 148/1440, 8.793e-14 |

NaN masks agree exactly in all twelve cells, and Spearman is 1.000000 in all
four ×10/×3.7 cells. ×10 and ×3.7 are **not** bit-identical, and the arithmetic
does not promise they would be: they perturb each return in its last bits and
a fourth moment amplifies that. 1.2e-13 against values of order 1 is the
tolerance reading Gate D asks for.

Non-default lengths, ×8 and ×64 on the walk:

| length | fires | ×8 | ×64 |
|---|---|---|---|
| 20 | 1,480 | bit-equal 1480/1480 | 1480/1480 |
| 120 | 1,380 | 1380/1380 | 1380/1380 |
| 250 | 1,250 | 1250/1250 | 1250/1250 |
| 4 | 1,496 | 1496/1496 | 1496/1496 |

**Why the return is spelled as a ratio, not a difference of logarithms.** On
the same walk at ×8: the ratio form is bit-equal on 1,499 of 1,499 returns,
`log(c).diff()` on only **821 of 1,499**. The ratio is what makes the ×8/×64
rows above bit-identical instead of merely close.

## Invariances — and what the column is therefore blind to

| transform of the input | max \|diff\| | Spearman | reading |
|---|---|---|---|
| returns × 0.5 | 8.482104e-14 | 1.000000 | the column standardises, so amplitude is invisible |
| returns × 2 | 5.395684e-14 | 1.000000 | " |
| returns × 3 | 3.308465e-14 | 1.000000 | " |
| +0.004 of log drift a bar | 9.303669e-14 | 1.000000 | a drift shifts the window mean, which the centred moments remove |

⚠ **So it is not a volatility feature and not a trend feature.** The same
shape of returns at any amplitude, with or without a drift, reads the same
number. Measured against the obvious alternatives on the walk:

| compared with | Spearman |
|---|---|
| `max|r - mean| / sd` of the same window | **0.8698** |
| the SECOND largest standardised deviation | 0.7753 |
| the window's own standard deviation | **0.0505** |

The first line is the warning: most of what this column orders is "how far
out is the single largest move", and a consumer who already has one
outlier-dominance feature should expect overlap. One planted return is enough
to move it:

| planted at bar 700 of a 1,500-bar walk | the 60 windows holding it: median | max | frame median | bars moved by > 1e-9 |
|---|---|---|---|---|
| +10 σ | 22.1696 | 24.0855 | −0.1283 | 60, bars 700…759 |
| +50 σ | 57.1866 | 57.4315 | −0.1283 | 60, bars 700…759 |

(Bars differing *at all* are 787 and 784: rebuilding the price path from the
planted returns changes later closes in their last bits. The 60 is the count
at a 1e-9 tolerance, which is the one that means anything.)

**It is a slow state, not an event flag**: lag-1 autocorrelation 0.9861 and
lag-60 0.3371 on the walk, because two consecutive windows share 59 of their
60 returns.

## The noise floor, and pandas' own degenerate test

`NOISE_ULPS = 4096`, `NOISE_FLOOR = 9.094947017729282e-13` — the same
4096 eps this fork already uses on a dimensionless quantity in
`statistics/ts_binent_20.py`, `statistics/ts_c3_20.py` and
`statistics/lean_hurst_100.py`.

Two guards act here, and they do not cover the same cases:

| frame | the port fires | the prototype (pandas' test alone) fires | who empties it |
|---|---|---|---|
| flat 300 closes | 0/300 | 240/300, all exactly −3.0 | **the floor** |
| 70-bar flat run in a 400-bar walk | 330/400 | 340/400, the 10 extra all −3.0 | **the floor** |
| 1%-a-bar geometric ladder | 0/300 | 0/300 | pandas' guard |
| exact ×1.5 ladder | 0/300 | 0/300 | pandas' guard |
| flat path with ±1e-16 … ±1e-9 jitter (five frames, 1,500 bars) | 0/1500 | 0/1500 | pandas' guard |
| monotone one tick a bar, price 50, tick 0.01 (return range 2.1e-06) | 240/300 | 240/300 | neither — it fires |
| monotone one tick a bar, price 1e6, tick 0.001 (return range 2.2e-16) | **0/300** | 47/300 | **the floor** |
| monotone one tick a bar, price 1e6, tick 0.01 (range 6.0e-15) | 0/300 | 0/300 | pandas' guard |

So on this column pandas' absolute test already covers most rounding-level
windows, and the floor is what catches the two cases it does not: identical
returns, and a fine-tick monotone path at a high price. On a walk and a
tick-rounded walk the floor changes nothing (240 of 300 bars fire, masks
agree).

⚠ **pandas' own degenerate test is ABSOLUTE, and that is inherited.** What
its threshold is cannot be read in this environment — `rolling.kurt` is
`pandas/_libs/window/aggregations`, and only the compiled `.so` is installed,
no `.pyx` — so what follows is the measured boundary, not a quoted constant.
(The sibling two-pass function IS readable, and it is absolute in the same
way: `pandas/core/nanops.py:1361-1370` passes `(n-2)(n-3)·Σd²` through
`_zero_out_fperr`, which zeroes any magnitude below 1e-14 at line 1581, and
then returns `0` for a zero denominator — which is exactly the 0.0 measured
above on a flat frame.) The boundary is a statement about the SIZE of the
returns and not about their shape, so a genuinely fine low-volatility path is
emptied:

| return σ | the port fires | the same path with its returns ×100 |
|---|---|---|
| 1e-02 | 240/300 | 0/300 — not a counter-example: at σ = 1e-2 the ×100 path has `min(1 + 100r) = −1.8826`, so its rebuilt closes are not all positive and the module refuses them (measured) |
| 1e-04 | 240/300 | 240/300 |
| 1e-06 | 240/300 | 240/300 |
| **1e-07** | **47/300** | **240/300** |
| **1e-08** | **0/300** | **240/300** |

The column is therefore scale-free in the returns down to about σ = 1e-6 and
not below. For BIST daily data (σ ≈ 1e-2) this is three to four orders of
magnitude away; it is recorded because it is a real limit of the shipped
spelling, and the measurement is what sets the boundary rather than a guess.

## Guards and edges

| input | behaviour |
|---|---|
| 60 closes (`length + 1` − 1) | `None` — `verify_series` refuses |
| 61 closes | fires 1 bar, the first at bar 60 |
| `length` = `None`, 0, −5, 3, 0.5, 3.9 | falls back to 60 (`TS_KURT_60`) |
| `length` = 4 | `TS_KURT_4` — the minimum the correction allows |
| `length` = 60.9 / 120.9 | truncated to 60 / 120; `length=120.9` equals `length=120` exactly |
| `fillna=-99.0` | fills exactly the 60 warm-up bars |
| `offset` | `offset=±2` equals `shift(±2)` |

A bad close empties the 61 windows it sits in, because it spoils two returns,
and **moves nothing before it** (measured on a 400-bar walk, bad close at bar
200):

| close[200] | bars emptied | bars before 200 that move |
|---|---|---|
| `nan` | 61, bars 200…260 | 0 |
| `0.0` | 61, bars 200…260 | 0 |
| `-5.0` | 61, bars 200…260 | 0 |
| `inf` | 61, bars 200…260 | 0 |
| `1e-310` (subnormal) | 61, bars 200…260 | 0 |

A close PAIR whose ratio overflows spoils one return, so 60 windows:
`close[200]=1e-300, close[201]=1e50` empties bars 201…260 and the prototype
reports on none of them (pandas' own guard also rejects an infinite sample).

### The fourth-power guard — why the NaN list above is window-local

⚠ **Without it, one bad return empties every later bar.** `rolling.kurt`
accumulates the raw power sums ONLINE, so an infinite Σr⁴ never leaves the
accumulator. Measured on a 400-bar walk by running the module with the guard
removed (the measurement script rewrites that one line in memory, the same
mechanism Gate B's mutants use):

| planted `close[201]` | biggest return | its r⁴ | `rolling.kurt` alone: ±inf / NaN bars | module WITHOUT the guard empties | WITH it |
|---|---|---|---|---|---|
| 1e-200 × 1e70 | 1.00e+132 | inf | 0 / 258 | **198 bars, 202…399** | 60 bars, 202…261 |
| 1e-200 × 1e73 | 1.00e+129 | inf | 0 / 258 | **198, 202…399** | 60, 202…261 |
| 1e-200 × 1e76 | 1.00e+126 | inf | 0 / 258 | **198, 202…399** | 60, 202…261 |
| 1e-200 × 1e77 | 1.00e+125 | inf | **1** / 258 | **199, 201…399** | 61, 201…261 |
| 1e-200 × 1e78 | 1.00e+124 | inf | 0 / 259 | **199, 201…399** | 61, 201…261 |
| 1e-200 × 1e80 | 1.00e+122 | inf | 0 / 259 | **199, 201…399** | 61, 201…261 |
| 1e-200 × 1e100 | 1.00e+102 | inf | 0 / 259 | **199, 201…399** | 61, 201…261 |

Seven magnitudes: the damage runs to the end of the frame in all seven
without the guard, and with it is 60 bars where one return is spoiled and 61
where the pair spoils two. The clean frame fires on 340 of 400 bars; the
guarded frames fire on 279–280.

**Why the guard bounds the window SUM and not just the single term.** The
test a reader writes first is `isfinite(fourth)`, and it is not enough: two
returns of 1.0e+77 planted 30 bars apart share a 60-return window, each
one's fourth power is **1.0e+308** — finite, below the float maximum
1.798e+308 — and their sum is not. Measured on that frame (closes 1e-200 /
1e-123 planted at bars 200/201 and 230/231 of the same 400-bar walk):

| guard | bars emptied | non-finite values emitted | fires |
|---|---|---|---|
| **the shipped guard, `fourth < max/(2·length)`** | **91, bars 201…291** (the union of two 61-bar spans) | 0 | 249/400 |
| a term-only `isfinite(fourth)` | 199, bars 201…399 | 0 | 141/400 |
| no guard at all | 199, bars 201…399 | 0 | 141/400 |

With `max/(2·length)` = 1.498e+306 as the per-term ceiling, a window of
`length` kept returns sums to under half the float maximum, so the locality
above is **structural** rather than measured on one shape. The factor two is
headroom, and it is there for two reasons: summing 60 terms accumulates its
own rounding, and pandas sums `val*val*val*val` (three roundings) where this
guard tests one `r**4`. The same ceiling caps `|r|` at 3.50e+76, which leaves
pandas' other accumulators 75+ orders of magnitude inside the float range —
`sum(r)` below 2.1e+78, `sum(r**2)` below 7.4e+154, `sum(|r|**3)` below
2.6e+231 — so Σr⁴ is the only sharp one.

⚠ What a market can produce is nowhere near this: the guard rejects only
`|r| >= 3.499e+76` (printed by the script), i.e. a close 76 orders of magnitude above the previous
one. On every ordinary frame measured here it changes nothing (bit-equality
to the prototype survives it, 1,440 of 1,440 on each of three frames, §A2).

**The output `isfinite` mask is a labelled backstop, not a witnessed one.**
With the sum bound in place no input swept here leaves a non-finite value for
it — the column emits 0 on every row whose `np.isinf` count this file prints:
fifteen rows over **fourteen** distinct frames (five bad closes, two
overflowing close pairs, the seven magnitudes above, the two-spike frame —
the `1e-200`/`1e-100` pair row and the `1e100` magnitude row are the same
frame). With a
term-only guard it would: at `close[201] = 1e-200 × 1e77` the `rolling.kurt`
of the kept returns is `+inf` on exactly 1 bar. The mask stays because it
costs one pass and `rolling.kurt` is a compiled extension whose other
accumulators this module does not bound. ⚠ Which step of pandas'
accumulation produces that `+inf` is not pinned here.

## Cost

`rolling.kurt` is one O(n) pass, and the two extrema and the fourth-power
guard are three more, so nothing grows with `length`:

| n | time (best of 3) | fires | traced peak (tracemalloc) |
|---|---|---|---|
| 10,000 | 2 ms | 9,940 | 0.6 MB |
| 100,000 | 9 ms | 99,940 | 6.4 MB |
| 400,000 | 43 ms | 399,940 | 25.6 MB |

| n = 400,000 | time | traced peak | the numpy two-pass oracle's peak |
|---|---|---|---|
| `length` 20 | 36 ms | 25.6 MB | 144.1 MB |
| `length` 60 | 36–37 ms | 25.6 MB | 400.0 MB |
| `length` 250 | 37–38 ms | 25.6 MB | 1,615.1 MB |

**What the fourth-power guard costs**, timed back to back with the same call
having that whole block rewritten out in memory — nine alternating reps each,
so neither gets the cold cache:

| n = 400,000 | best | worst | traced peak |
|---|---|---|---|
| with the guard (two squarings) | **36 ms** | 78 ms | 25.6 MB |
| without the guard | **34 ms** | 70 ms | 22.4 MB |
| with the guard spelled `r ** 4` | **55 ms** | 112 ms | 25.6 MB |

⚠ **Read the gaps, not the absolutes.** The worst column is twice the best on
every row — this machine is not quiet, and the same code measured 38 / 34 / 84
ms on an earlier run of this session. What reproduces across runs (and across
the reviewer's two independent runs, which printed 36 / 34 / 55 twice) is the
ordering and roughly the gaps:

* the guard costs **3.2 MB** — the fourth-power array, and that figure is
  stable — and about **2 ms on a 34 ms call**;
* spelling it `r ** 4` instead of two squarings costs about **19 ms more**
  (55 against 36 end to end), i.e. an order of magnitude more than the guard
  itself, because it is `n` libm `pow` calls against two vectorised
  multiplies. The two spellings give a bit-equal column on 1,940 of 1,940
  bars of a walk, so the cheaper one is free — measured, not assumed.

The oracle materialises a `(rows, length)` deviation array, which is why it
is in `docs/measure_ts_kurt_60.py` and not in the shipped module; the two
agree to 6.2e-15 over 1,940 bars. One machine, three runs, the best taken.

## Gate E — attribution

**Gate E: pending, run by issue-solver after this session.**

What the issue reports, measured on the PROTOTYPE on 2026-10-24 and
**indicative only** — a prototype is not a port, and those figures come from
a different harness run:

* max \|ρ\| **0.2501** vs `ZIGZAG` (compute_all, n = 33,246), top-5 per-frame
  max median 0.2335 → **SHIP**;
* next comparators `LINREG_LOWER_2` 0.2059, `LINREG_LOWER_1` 0.2057;
* fork overlap (stage 2, 12 frames): max \|ρ\| 0.1389 vs
  `covariance:COV_30_1`, per-frame max median 0.1576.

This port is bit-equal to that prototype on every clean frame measured
(§A2), which makes those numbers more transferable here than they were for
issue #91's `ts_perment_20` — but it does **not** make them a receipt. The
launcher's run on this module decides ship or revert, and
`docs/gate_e_ledger.csv` carries no `TS_KURT` row until then (asserted by
`tests/test_ts_kurt_60.py`).

A synthetic pre-check against 14 shipped columns on ONE 1,500-bar walk — not
Gate E, no BIST frames, no `compute_all`. The most recent port's pre-check of
this kind over-stated its real maximum by 0.049 and named a comparator
outside the run's top 25 (`docs/TsPeaks20Measured.md`), so read the ordering
below as a hint and nothing more:

| \|ρ\| | column |
|---|---|
| 0.3706 | `ts_binent_20` |
| 0.2478 | `ts_c3_20` |
| 0.1585 | `ts_perment_20` |
| 0.1465 | `natr_14` |
| 0.1090 | `kurtosis_30` (of CLOSE) |
| 0.0847 | `kurtosis_60` (of CLOSE) |
| 0.0821 | `osap_retskew_21` |
| 0.0659 | `entlz_20` |
| 0.0620 | `rsi_14` |
| 0.0537 | `zscore_30` |
| 0.0518 | `skew_30` |
| 0.0353 | `lean_tdd_20` |
| 0.0112 | `lean_hurst_100` |
| 0.0012 | `ts_peaks_20` |

`ts_binent_20` at 0.3706 is the one to watch: it is the fork's other
outlier-dominance reading of a 20-return window, and this column's strongest
synthetic neighbour.

## Gate F — suites

`python -m pytest tests/test_ts_kurt_60.py -q` here; both repositories' full
suites are run by the launcher in clean worktrees. The local full-suite
result at the time of the port is in the commit message, including the owed
Gate E ledger row, which fails locally by design until the launcher's run.

## Wiring — the five touch points

| # | file | state |
|---|---|---|
| 1 | `pandas_ta/statistics/ts_kurt_60.py` | the indicator |
| 2 | `pandas_ta/statistics/__init__.py` | exported |
| 3 | `pandas_ta/__init__.py` → `Category["statistics"]` | registered (measured: `'ts_kurt_60' in pandas_ta.Category['statistics']` is True) |
| 4 | `pandas_ta/core.py` | `df.ta.ts_kurt_60()` returns `TS_KURT_60`, and `df.ta.ts_kurt_60(length=20)` returns `TS_KURT_20` — the keyword is forwarded under the right name |
| 5 | `tests/test_ts_kurt_60.py` | this port's suite |

`README.md`, `docs/IndicatorDictionary.md`, `docs/MLCompanionContract.md` and
`tests/test_altport2_ports.py`'s pinned `Category` total are updated with it.
