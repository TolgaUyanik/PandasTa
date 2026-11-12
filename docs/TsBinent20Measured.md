# `ts_binent_20` — measured

Issue #89 (TS-BINENT-20), ported 2026-11-12 on branch `issue-89-ts-binent-20`.
Column: **`TS_BINENT_20_5`**, `pandas_ta/statistics/ts_binent_20.py`.
**Status: Gates A–D cleared, Gate E owed.** Gate E and both repos' suites are
run by issue-solver after this session; a later receipt session records the
`docs/gate_e_ledger.csv` row and fills in Gate C's real-data counts.

Every number here is printed by `python docs/measure_ts_binent_20.py` (its
sections can be run one at a time, e.g. `… gate_b`) on pandas 2.3.3 / numpy
1.26.4, or by `python -m pytest tests/test_ts_binent_20.py -q`. Nothing in
this file was typed from expectation; where a number is *not* measured, the
line says so.

## What it is

    r[t]    = close[t] / close[t-1] - 1
    lo, hi  = min, max of r over the trailing `length` returns
    width   = hi - lo        (NaN where width <= 9.09e-13)
    k[i]    = min(floor((r[i] - lo) / width * bins), bins - 1)
    p[b]    = (count of k == b) / length
    column  = -sum(p * log p) over the occupied bins

At the defaults (`length=20`, `bins=5`): five equal-width bins laid across a
20-return window's own [min, max], Shannon entropy of the bin shares in nats.
The window reads 21 closes.

Because the bins are anchored on the window's own extremes, the column reads
**how evenly the returns fill their own range** — low when one large move
stretches the range and collapses the rest into one bin, high when the returns
are spread. It is a concentration / outlier-dominance reading, and it is
invariant to the location and the amplitude of the returns (see *Invariances*),
so it is **not** a volatility or a trend feature.

## Source, and what "tsfresh (MIT)" does and does not mean here

The issue names tsfresh's `feature_calculators` (MIT) and states the formula:

> `binned_entropy(max_bins=5) on 20 returns`

with the screen prototype (`docs/issues/screen/ind_screen.py`, candidate
`ts_binent_20`) spelling it as

    roll(ret(c), 20, w_binned_entropy)

    def w_binned_entropy(W, bins=5):
        lo = W.min(1, keepdims=True); hi = W.max(1, keepdims=True)
        rng = np.where(hi - lo == 0, np.nan, hi - lo)
        k = np.clip(np.floor((W - lo) / rng * bins), 0, bins - 1)
        h = np.zeros(len(W))
        for b in range(bins):
            p = (k == b).mean(1)
            h -= np.where(p > 0, p * np.log(np.where(p > 0, p, 1)), 0)
        return np.where(np.isnan(rng[:, 0]), np.nan, h)

⚠ **tsfresh is not installed in this worktree and web access is
unavailable.** Its own code was not read in this session. So the attribution
is an attribution, not an oracle: Gate A below is against the issue's stated
line, the prototype, and the standard DEFINITION of equal-width binning as
numpy's own `np.histogram` implements it. Anything tsfresh does that the line
does not say — what it returns for a series shorter than `max_bins`, whether
it drops NaNs rather than returning NaN — is **unverified here**. The
prototype (gitignored, local to the owner's machine) was read, and it is the
source for the NaN rule on a degenerate window, which the literal
`np.histogram` reading does not share (§Gate A, A6).

## Gate A — correctness

**A1. Four windows derived by hand, exact in closed form.** The first is at
the SHIPPED defaults, which is the one that matters:

`close` = eleven 1s, then five ×1.5 steps (1.5, 2.25, 3.375, 5.0625,
7.59375), then five ×2 steps (15.1875 … 243.0) — every close and every return
exactly representable in binary.

| quantity | value |
|---|---|
| the 20 returns | ten +0, five +1/2, five +1 |
| lo, hi, width | 0, 1, 1 — five bins of width 1/5 |
| `k = floor(r·5)` | 0 for +0, 2 for +1/2, 5 → clipped to 4 for +1 |
| counts | [10, 0, 5, 0, 5], `p = (1/2, 1/4, 1/4)` |
| column | (1/2)·log 2 + (1/4)·log 4 + (1/4)·log 4 = **1.5·log 2 = 1.0397207708399179** |

Module: `1.0397207708399179`, **|difference| = 0.0** — exact to the last bit;
bars 0..19 NaN. The other three:

| case | counts | exact | module |
|---|---|---|---|
| `[1,1,1,1,2]`, length 4, bins 4 → returns [0,0,0,+1] | [3,0,0,1] | `-(3/4·log¾ + 1/4·log¼)` = 0.56233514461880829 | **0.0 away** |
| `[1,1,2,6,24]`, length 4, bins 4 → returns [0,+1,+2,+3] | [1,1,1,1] | `log 4` = 1.3862943611198906 | **0.0 away** |
| `[1,2,1,2,1]`, length 4, bins 2 → returns [+1,−½,+1,−½] | [2,2] | `log 2` = 0.69314718055994529 | **0.0 away** |

**A2. Against the screen prototype**, 1,500-bar walk, 1,480 fired bars:

| compared against | max \|diff\| | bit-equal | Spearman | NaN masks |
|---|---|---|---|---|
| the prototype retyped in the test module | 0.000000e+00 | **1480/1480** | 1.000000 | equal |
| **the screen's own registry candidate, imported from `docs/issues/screen/ind_screen.py`** | 0.000000e+00 | **1480/1480** | 1.000000 | equal |

The imported row is the real candidate, not a retype: the measurement script
loads `REG["ts_binent_20"]["fn"]` out of that file when the worktree has it,
and says so when it does not (a clone does not — `docs/issues/` is
gitignored). Bit-equality is the point: the module keeps the prototype's
arithmetic and its bin-by-bin order of accumulation, and on a continuous walk
no window reaches the noise floor the prototype lacks.

**A3. Against the DEFINITION, spelled with numpy's own `np.histogram`**, window
by window — bin shares, zeros replaced by 1 so an empty bin contributes
nothing, Shannon entropy in nats. It shares no window machinery and no bin
arithmetic with the module:

| frame | n | max \|diff\| | bit-equal | NaN masks |
|---|---|---|---|---|
| gaussian walk | 1,480 | 0.000000e+00 | **1480/1480** | equal |
| tick-rounded walk (returns repeat, samples sit on edges) | 1,480 | 0.000000e+00 | **1480/1480** | equal |

The tick-rounded row is the one that tests the edge convention: the top edge
is inclusive (the window's maximum gives `floor(…·bins) = bins`, folded into
the last bin by the clip), which is what `np.histogram` does too.

**A4. Against an independent per-window loop in plain Python scalars** (no
numpy, no sliding window, every count written out), 400 bars / 380 fired:
max \|diff\| **2.220446e-16**, bit-equal 339/380, **0 bars differing by more
than 1e-12**, NaN masks equal. Spearman is **0.999831** rather than 1.000000,
and that is a property of the column rather than a disagreement: it takes only
93 distinct values over those 380 bars, so a last-bit difference reorders tied
bars. No distinct value disagrees.

**A5. Four of the five readings the wording leaves open** — the fifth, NaN or
0 on a degenerate window, is A6. Each decided, and each priced against the
port on the same 1,500-bar walk rather than dismissed (`bins=5` is one
reading priced at two rejected settings, so the table has five rows):

| reading, and what this port does | max \|diff\| | bit-equal | Spearman |
|---|---|---|---|
| bins are **equal-width**, the prototype's and `np.histogram`'s. Rejected: equal-FREQUENCY (quantile) bins | 6.832822e-01 | 3/1480 | **undefined — the variant is CONSTANT** |
| **`bins=5`**, the issue's. Rejected: 3 bins | 6.876385e-01 | 0/1480 | 0.651029 |
| **`bins=5`**. Rejected: 10 bins | 6.931472e-01 | 0/1480 | 0.724187 |
| entropy in **nats, unnormalised**. Rejected: dividing by `log(bins)` | 6.094379e-01 | 0/1480 | **1.000000** |
| returns are **simple** (`close/close.shift(1) - 1`). Rejected: log returns | 2.502012e-01 | 831/1480 | 0.944970 |

Four things worth keeping from that table:

* **The equal-frequency reading is not a different column, it is no column at
  all.** 5 bins of 4 samples each give `p = 1/5` on every bar, so it reads
  exactly `log 5` on **1,480 of 1,480** bars — 1 distinct value. That is why
  equal-width binning is the reading, and it is pinned by a test rather than
  stated in a sentence.
* **The bin count is a real choice.** 3 bins is Spearman 0.651029 against the
  default and 10 bins 0.724187. 5 is the issue's number, and the number its
  Gate E screen was run with.
* **Normalising is a strict rescaling.** `port / log(5)` reproduces the
  normalised variant **exactly** (max \|diff\| 0.0), Spearman 1.000000, so
  nothing that ranks the column could tell them apart. The unnormalised nats
  are kept because that is the standard `binned_entropy` form.
* **Log returns matter more here than they would for a moment-based column.**
  A monotone but non-affine transform of the returns moves samples across bin
  edges: 831 of 1,480 bars are still bit-equal (no sample crossed an edge
  there) and the rest move, up to 0.2502.

**A6. The degenerate window: NaN (this port) or 0 (the literal reading).**
The widening is numpy's, and it is run rather than described:

    np.histogram(np.zeros(20), bins=5) -> counts [0, 0, 20, 0, 0],
                                          edges [-0.5 .. 0.5]

so a window whose returns are all equal lands entirely in the MIDDLE bin and
the literal reading is `-1·log(1)` = exactly 0. This port says NaN — the
prototype's reading, this fork's habit (`ts_c3_20`, `lean_hurst_100`), and the
reading issue #89's Gate E numbers were screened with. The "literal reading"
column below is the real `np.histogram` path (A3's oracle, which does not skip
a zero-width window), not a hand-written 0.0; the hand-written variant used
elsewhere in the script was checked against it and agrees on every bar of both
frames:

| frame | this port fires | literal `np.histogram` reading fires | of those, exactly 0.0 |
|---|---|---|---|
| flat 300 closes | **0/300** | 280/300 | **280** |
| 21 identical closes planted in a 400-bar walk | 379/400 | 380/400 | **1** |
| 1,500-bar walk | 1,480/1,500 | 1,480/1,500 | 0 — the two readings are bit-equal on all 1,480 bars |

So the choice costs nothing except on a window with no range at all, and there
it is a deliberate NaN rather than a 0 that a tree would read as "minimum
entropy".

## Gate B — causality, by mutant

Future-perturbation sweep over **37 J values** (J = 40..1480 step 40) on
1,500-bar frames: replace every bar from J onward with a different path, assert
nothing strictly before J moves. Three frame pairs — a random walk, a
**tick-rounded** walk (prices on a 0.01 grid, as quotes are) and a
**student-t(2)** path, whose windows are outlier-dominated, which is the regime
this column reads lowest.

| | walk | tick-rounded | heavy-tailed |
|---|---|---|---|
| **real module** | **0/37** | **0/37** | **0/37** |
| mutant: column back-dated by 2 bars | 37/37 | 37/37 | 37/37 |
| mutant: column back-dated by `length − 1` | 37/37 | 37/37 | 37/37 |
| mutant: the return stamped one bar early (`r[:-1] = …`) | 37/37 | **36/37** | 37/37 |
| mutant: window rolled `length // 2` bars into the future | 37/37 | 37/37 | 37/37 |
| mutant: the bin's lower edge taken from the window `length` bars ahead | 37/37 | 37/37 | 37/37 |

Every mutant is live on every frame (its output differs from the real module's
before the sweep runs), so none of the 15 cells is a mutation that did nothing.
Mutants are `importlib`-read from the module source and `exec`'d in memory.

**Non-default parameters, on the walk.** `length` and `bins` are both
user-reachable; all five mutants are re-run at three further settings:

| setting | real module | back-date 2 | back-date `length−1` | forward return | rolled window | forward edge |
|---|---|---|---|---|---|---|
| `length=20, bins=5` (default) | **0/37** | 37/37 | 37/37 | 37/37 | 37/37 | 37/37 |
| `length=20, bins=10` | **0/37** | 37/37 | 37/37 | 37/37 | 37/37 | 37/37 |
| `length=60, bins=5` | **0/37** | **36/37** | 37/37 | **36/37** | **36/37** | **36/37** |
| `length=5, bins=5` | **0/37** | 37/37 | 37/37 | **34/37** | 37/37 | 37/37 |

**The real module leaks 0 of 37 in all 6 configurations run** — the three
frames at the defaults, plus `(20, 10)`, `(60, 5)` and `(5, 5)` on the walk.
The settings are not re-run on the other two frames, so this is 6
configurations and not a 3 × 4 cross product. Of the **30** mutant cells
(5 mutants × 3 frames, plus 5 × 3 further settings) **24 are 37/37**; the six
that are not come under two explanations, and both are printed by the script
and asserted by the tests rather than argued:

* The four **36/37** cells at `length=60` miss only J = 40, the one sweep
  offset below a 60-bar warm-up. Measured on that frame: the prefix `[0:40]` is
  entirely NaN under both the real module and the mutant
  (`prefix [0:40] all-NaN real=True mutant=True`), so there was nothing for the
  perturbation to move.
* The **36/37 on the tick-rounded frame and the 34/37 at `length=5`** are the
  discrete column absorbing the change, and the mechanism is measured, not
  asserted. The forward-return mutant stamps each return one bar early, so at
  offset J the only prefix bar that can move is J−1, whose window ends at the
  perturbed return:

| frame | J | perturbed return | bin counts of bar J−1's window | same multiset |
|---|---|---|---|---|
| tick-rounded | 120 | 3.591114e-03 → 1.352931e-02 | [1,6,5,6,2] → [1,6,5,6,2] | yes (identical) |
| walk, `length=5` | 200 | 8.187723e-03 → −1.886901e-01 | [2,0,0,2,1] → [1,0,0,2,2] | **yes (a permutation)** |
| walk, `length=5` | 400 | 5.608538e-03 → −4.435843e-01 | [4,0,0,0,1] → [1,0,0,0,4] | **yes (a permutation)** |
| walk, `length=5` | 1000 | 1.858490e-03 → −5.198820e-01 | [4,0,0,0,1] → [1,0,0,0,4] | **yes (a permutation)** |

The entropy is a symmetric function of the bin counts, so a permutation of them
is bit-identical. That is a property of a count statistic, and it is why this
column's Gate B is asserted over three frames and three further settings rather
than over one.

**How sensitive the sweep is, measured.** A *one-bar* edge leak (the lower edge
taken from the NEXT window rather than a whole window ahead) is far harder to
see:

| frame | one-bar edge leak caught | consecutive windows sharing their minimum |
|---|---|---|
| walk | 37/37 | 1346/1480 |
| heavy-tailed | 35/37 | 1350/1480 |
| **tick-rounded** | **5/37** | 1339/1480 |

On coarse prices the mutation usually has no effect to detect. This is stated
as a limit of the test, not as a property of the module: what the module's own
0/37 is asserted on is all three frames and all three further settings.

`offset` is the caller-reachable look-ahead and is pinned, not assumed:
`offset=2` is exactly the default shifted two bars later, `offset=-2` exactly
two bars earlier. The sweep covers the default `offset=0`, which is what
`Category` uses.

## The rounding-noise floor

`max − min != 0` — all the prototype's zero-range test catches — is not enough.
The returns of an exactly geometric path are mathematically constant, so there
is no range to bin; but in float64 they vary at rounding level, and an
unguarded reading then bins **that rounding noise** into a value that looks
ordinary. Measured on 300-bar frames, guarded (the module) against unguarded:

| frame | guarded fires | unguarded fires | unguarded range | of those, inside a real walk's live range [0.9262, 1.6094] |
|---|---|---|---|---|
| geometric, 1% a bar | **0/300** | 280/300 | [0.6474, 1.5114] | **114** |
| geometric by exact ratio, ×1.5 a bar | **0/300** | 280/300 | [0.3944, 1.0805] | **94** |
| exactly flat | 0/300 | 0/300 | — (the range is exactly 0) | — |
| gaussian random walk | 280/300 | 280/300 | identical, 0 bars differ | — |
| tick-rounded walk, 2 decimals | 280/300 | 280/300 | identical, 0 bars differ | — |

**This is the opposite failure mode from `ts_c3_20`'s, and the worse one.**
That port's unguarded ladders reached 7.96e+41 — obviously wrong to anything
looking. Here the unguarded values sit *inside* the range a real walk produces:
114 of 280 on the 1% ladder are between 0.9262 and 1.6094, the live min and max
of this column on a 1,500-bar walk. Nothing downstream could have spotted them.
A halted or exactly-geometric window would have shipped a plausible number.

The floor is **absolute** — `NOISE_ULPS = 4096` machine epsilons, 9.095e-13 —
rather than a rolling scale, because what it floors is the range of
*dimensionless* price ratios, so it needs no window of its own whose causality
would have to be pinned. Where the crossover sits, on a 1%-a-bar ladder whose
steps jitter by a known relative amount (real variation, but tiny):

| jitter | guarded fires | unguarded fires |
|---|---|---|
| ±1e-16 | 0/1500 | 1480/1500 |
| ±1e-14 | 0/1500 | 1480/1500 |
| ±1e-12 | 1480/1500 | 1480/1500 |
| ±1e-11 | 1480/1500 | 1480/1500 |
| ±1e-09 | 1480/1500 | 1480/1500 |

So the floor stops reading variation at about 1e-12 of relative return RANGE —
and range is the right word: it bounds `max(r) − min(r)`, not `|r|`. On a
monotone one-tick-per-bar path the returns are about `tick / price` but they
differ from *each other* only in the next digits:

| price | tick | \|r\| | max−min of the last 20 returns | fires |
|---|---|---|---|---|
| 50 | 0.01 | 1.888e-04 | 6.793e-07 | 280/300 |
| 1e6 | 0.001 | 1.000e-09 | 2.220e-16 | **0/300** |
| 1e6 | 0.01 | 1.000e-08 | 1.998e-15 | **0/300** |

The two emptied rows are the correct answer rather than a cost: a window whose
returns are constant to 1e-16 has no range to bin. What is measured about the
floor's safety is the two real-shaped frames above — a walk and a tick-rounded
walk, 280 of 300 bars each, identical to the unguarded form, 0 bars differing —
and not a generalisation beyond them.

## The attainable set — a count statistic

The value is a function of the window's bin COUNT VECTOR and of nothing else,
so the entropy FUNCTION's range is a finite set, enumerated rather than
estimated:

| quantity | value |
|---|---|
| count vectors over 5 bins summing to 20 with the first and last bin occupied | **7,315** |
| distinct entropy values among them, **rounded to 1e-12** | **182** |
| the same set enumerated over count MULTISETS (the entropy is symmetric in the counts) | 182, identical set |
| minimum (19/1 across two bins) | **0.198515** |
| maximum (the even split, four returns per bin) | **1.6094379124341005** |

⚠ That maximum is **one ulp ABOVE `math.log(5)`** = 1.6094379124341003,
because the five terms are accumulated one bin at a time. `value <= log(bins)`
is false by a last bit, and a 1,500-bar walk reaches the value exactly
(`test_the_top_of_the_range_is_one_ulp_above_log_bins`).

⚠ **The 182 is a count of ROUNDED values, and the module emits more than 182
distinct float64 values.** Same cause as the ulp above: the terms are
accumulated in bin order, so two count vectors that are permutations of each
other land on different last bits, which the multiset enumeration can never
produce. Both counts, per frame:

| frame | fired bars | distinct float64 values | distinct at 1e-12 | rounded values inside the attainable set | raw values inside it |
|---|---|---|---|---|---|
| gaussian walk | 1,480 | **154** | **104** | yes | **no** |
| tick-rounded walk | 1,480 | 136 | 85 | yes | **no** |
| student-t(2) | 1,480 | 193 | 137 | yes | **no** |

`tests/test_ts_binent_20.py::test_the_attainable_set_is_182_values_to_1e12`
asserts every cell of that table, so the rounded count and the raw count
cannot be quoted as each other again.

The practical consequence, stated here because it affects how Gate E's Spearman
should be read: **this column ties heavily by construction** — 1,480 bars over
136–193 distinct float64 values (104–137 of them distinct at 1e-12) — so a rank
correlation against it is computed on many tied ranks. That is a property of
the feature, not of the measurement.

## Invariances — what the column does NOT see

Every bin edge is a fraction of the window's own range, so the value depends on
the returns only through an affine map: `r → a·r + b` with `a > 0` leaves every
count unchanged. Measured on the 1,500-bar walk, 1,480 fired bars:

| transform | why it is affine on simple returns | result |
|---|---|---|
| +0.004 of log drift a bar | `r → e^d·r + (e^d − 1)` | **1480/1480 bit-identical**, NaN masks equal |
| the returns themselves scaled ×0.5 | `r → k·r` | **1480/1480 bit-identical** |
| the returns themselves scaled ×3 | `r → k·r` | **1480/1480 bit-identical** |

So it is **not** a volatility feature and **not** a trend feature: the same
shape at any amplitude, with or without drift, reads the same number. The
neighbouring returns statistic `ts_c3_20` is NOT drift-invariant (Spearman
0.8013 against the same drifted walk, `docs/TsC320Measured.md`); neither
property carries across.

## Gate C — reachability

**Real data: owed.** The pooled non-NaN and non-zero counts over the 89 frozen
ALTPORT-1 frames come from the launcher's Gate E run and are recorded by the
receipt session. The arithmetic floor on the NaN count is `89 × 20 = 1,780`
warm-up bars of 398,849 — that denominator is NOT measured here (this worktree
has no BIST frames); it is the pooled bar count every Gate E run on the 89
frozen ALTPORT-1 frames reports, e.g. `docs/TsC320Measured.md` §Gate E. **Five**
further causes can empty bars on real data — two bad-data causes and the three
ways a window can reach the floor — each measured on synthetic frames below: a close inside a frame that is NaN,
zero, negative or subnormal (**21 bars each** — one bad close spoils two
returns); a close PAIR whose ratio overflows (**20 bars** — one spoiled
return); 21 consecutive identical closes (a halted or limit-locked session);
an exactly geometric window, which reaches the same floor with 21 DISTINCT
closes; and a near-monotone fine-tick window at a high price, whose closes are
distinct and not geometric (*The rounding-noise floor* above: price 1e6,
tick 0.001, 0 of 300 bars). Nothing is predicted here.

The rest of this section is **synthetic**: 1,500-bar generated paths, 1,480
fired bars each. "distinct" counts RAW float64 values (see *The attainable
set* for what they are at 1e-12).

| path | distinct | min | p10 | median | p90 | max | spread (max−min) |
|---|---|---|---|---|---|---|---|
| uniform returns | 115 | 1.1648 | 1.4150 | **1.5260** | 1.5842 | 1.6094 | 4.446e-01 |
| gaussian walk | 154 | 0.9262 | 1.3047 | **1.4737** | 1.5672 | 1.6094 | 6.833e-01 |
| tick-rounded walk | 136 | 0.9958 | 1.3331 | **1.4708** | 1.5672 | 1.6094 | 6.136e-01 |
| laplace returns | 174 | 0.7083 | 1.1582 | **1.3748** | 1.5260 | 1.5968 | 8.885e-01 |
| student-t(2) returns | 193 | 0.1985 | 0.6129 | **1.2348** | 1.4786 | 1.5968 | 1.398e+00 |
| two-point returns (±σ) | 8 | 0.4227 | 0.6474 | **0.6881** | 0.6931 | 0.6931 | 2.704e-01 |

`0 < 1480 < 1500` fired on every one of the three frames Gate D uses, with 154
/ 136 / 193 distinct values and 1,480 of 1,480 fired bars non-zero, so Gate D's
non-constant requirement is met with room.

**What the column orders is concentration, not size.** The six paths above
differ in the SHAPE of their return distribution; the medians come out in that
order, and the return sd does not explain them:

| path | median | return sd | excess kurtosis |
|---|---|---|---|
| uniform | 1.5260 | 0.0116 | −1.17 |
| gaussian | 1.4737 | 0.0151 | 0.01 |
| laplace | 1.3748 | 0.0135 | 2.61 |
| student-t(2) | 1.2348 | 0.0357 | 97.17 |
| two-point (±σ) | 0.6881 | 0.0100 | −2.00 |

The two-point row is the exception that proves the mechanism rather than a
counter-example to it: when the returns take exactly two values, only the first
and last bin can be occupied, so the value is `H(count/20)` over two bins and
can never exceed `log 2` = 0.6931 — which is exactly the row's maximum.

**One outlier is enough to move it**, which is the behaviour to know before
reading a low value as "quiet":

| planted move at bar 200 of a 400-bar walk | the 20 windows that hold it | bars exactly at the 19/1 floor 0.198515 |
|---|---|---|
| +10 sigma | median **0.8557** (frame median 1.4989) | 0/20 |
| +50 sigma | median **0.198515** | **20/20** |

**Where an ordinary gaussian window sits.** Over **2,000 independent 20-return
iid-gaussian windows**: mean 1.4633, median **1.4786**, sd 0.0943, p10
**1.3349**, p90 **1.5672**, finite on all 2,000, 105 distinct values. So the
column is high and tight on ordinary data, and a reading near 0.9 is already
in the tail — the opposite shape from `ts_c3_20`, whose iid deciles straddle
zero.

## Gate D — scale-free

1,500-bar frames, 1,480 fired bars each:

| frame | ×8 | ×64 | ×10 | ×3.7 |
|---|---|---|---|---|
| walk | **1480/1480 bit-identical** | **1480/1480** | **1480/1480 bit-identical**, max \|diff\| 0.0 | **1480/1480**, 0.0 |
| tick-rounded | **1480/1480** | **1480/1480** | **1480/1480**, 0.0 | **1480/1480**, 0.0 |
| heavy-tailed | **1480/1480** | **1480/1480** | **1480/1480**, 0.0 | **1480/1480**, 0.0 |

At three non-default parameter settings, on the walk:

| setting | fired bars | ×8 | ×64 |
|---|---|---|---|
| `length=20, bins=10` | 1,480 | **1480/1480 bit-identical** | **1480/1480** |
| `length=60, bins=5` | 1,440 | **1440/1440** | **1440/1440** |
| `length=5, bins=5` | 1,495 | **1495/1495** | **1495/1495** |

NaN masks are equal on all twelve default cells and on these six. ×8 is
bit-identical rather than merely close because every input is a price *ratio*:
`8a / 8b` is the same double as `a / b`. The difference-of-logarithms spelling
of the return is **not** — at ×8 it is bit-equal on 821 of 1,499 bars where the
ratio spelling is bit-equal on all 1,499. That is why the module spells the
return `c[1:] / c[:-1] - 1.0` and not `log(c)` differences; it is not a
simplification to undo.

⚠ **×10 and ×3.7 come out bit-identical too, and the arithmetic does not
promise that.** Those rescales do *not* reproduce the returns bit-for-bit; the
column survives because it is a function of discrete bin counts, so a last-bit
change in a return moves the value only if it moves a sample across a bin edge,
and on these three frames none did. The test asserts a 1e-13 tolerance AND the
bit-equal count, so the day a frame crosses an edge the tolerance still holds
and the count fails loudly rather than silently.

`0 < fires < n` holds on all three frames (1,480 of 1,500), with 136–193
distinct float64 values (154 / 136 / 193 on the walk / tick-rounded /
student-t), so no constant column is passing this gate by accident.

## Gate E — attribution

**Gate E: pending, run by issue-solver after this session.** The harness
(`gate_e_overlap.py`) needs the private Backtesting engine, the 827 MB BIST
cache and the 89 frozen ALTPORT-1 frames, none of which are in this worktree;
this session is forbidden to run it or to read `../Backtesting`. A later
receipt session records the `docs/gate_e_ledger.csv` row, which is why
`tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
fails here until then.

What the issue reports for the PROTOTYPE (2026-10-24, run `screen_20261024`,
n = 33,594 — a prototype is not a port): max \|ρ\| **0.1353** vs `ZIGZAG`,
top-5 per-frame max median 0.1301 → SHIP; next comparators `Pct_Up_Days_63`
0.1328 and `LINREG_LOWER_2` 0.1179. The port is bit-equal to that prototype on
a 1,500-bar walk (§Gate A, A2), so the re-run is expected to land near those
numbers — expected, not measured, and the launcher's run is what decides.

**Nearest shipped columns on ONE 1,500-bar synthetic walk — NOT Gate E** (14
shipped columns, one frame; Gate E is 687 comparators over 89 frozen BIST
frames):

| \|ρ\| | column | n |
|---|---|---|
| 0.2050 | `ts_c3_20` | 1480 |
| 0.1867 | `entlz_20` | 1480 |
| 0.0976 | `lean_hurst_100` | 1401 |
| 0.0797 | `kpss_100` | 1401 |
| 0.0618 | `natr_14` | 1480 |
| 0.0527 | `entropy_20` | 1462 |
| 0.0306 | `rsi_14` | 1480 |
| 0.0296 | `tf_centroid_20` | 1480 |
| 0.0262 | `skew_30` | 1471 |
| 0.0247 | `osap_retskew_21` | 1479 |
| 0.0181 | `zscore_30` | 1471 |
| 0.0121 | `kurtosis_30` | 1471 |
| 0.0080 | `cusum_100` | 1400 |
| 0.0067 | `lean_momersion_20` | 1479 |

The two entropy columns already shipped are the ones a reader would worry
about, and on this frame they are the second and sixth rows: `entlz_20` (the
AFML Lempel–Ziv entropy of a binary return encoding, issue #11 — the related
issue the screen named) at 0.1867 and `entropy_20` (Shannon entropy of
normalised CLOSES, not returns) at 0.0527. One synthetic frame is not evidence
about the 89; the issue's own stage-2 fork overlap put the prototype's worst at
0.1219 vs `covariance:COV_30_1` over 12 frames.

## Gate F — suites

Porting session, in this worktree:

* `python -m pytest tests/test_ts_binent_20.py -q` → **126 passed** in 4.30 s.
* `python -m pytest -q` → **3 failed, 5,802 passed, 83 skipped** in 121.34 s.
  The three failures are the two `CLAUDE.md` *Known breaks* —
  `test_altrepo_talib_csv.py::test_regenerating_reproduces_the_committed_rows`,
  which needs the sibling `../AlternativeRepos` checkout and is deselected in
  CI, and `test_pine_coverage_csv.py::test_audited_rows_carry_their_evidence`,
  the `supertrend` citation into the untracked `docs/pine/` — plus
  `test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`, which
  reports `['mtd_ret', 'ts_binent_20']`: the row this port owes, and one owed
  before this branch. CI into `dev` skips that test under
  `GATE_E_PENDING_OK=1`. The same counts are summarised in
  `docs/reviews/auto-2026-11-12-ts-binent-20/99-summary.md`.

The launcher runs both repos' suites in clean worktrees.

## Cost

The module materialises one `(n − length + 1, length)` array of bin indices and
holds two same-shape float64 temporaries while computing it, so its memory is
O(n · length) rather than O(n). The index-array column is arithmetic from the
shape; the peak is measured with `tracemalloc`, which numpy's allocator reports
into:

| bars | time | index array (computed) | traced peak (measured) |
|---|---|---|---|
| 10,000 | 11 ms | 1.6 MB | 3.7 MB |
| 100,000 | 60 ms | 16.0 MB | 36.1 MB |
| 400,000 | 244 ms | 64.0 MB | **144.1 MB** |

The engine calls indicators per frame (the 89 ALTPORT-1 frames average ~4,500
bars), so this is disclosed rather than a problem; a caller handing it a
400,000-bar series should know the peak is about 144 MB, not the 64 MB of the
index array alone.

## Edge cases, measured

| case | behaviour |
|---|---|
| 20 bars | returns `None` (`verify_series` floor: a value needs `length + 1` closes) |
| exactly 21 bars | fires 1/21, at bar 20 |
| one NaN close at bar 200 | empties exactly 21 bars, 200..220; **0** bars before 200 move |
| one zero / negative / infinite / subnormal (1e-310) close | each empties exactly the same 21 bars, and nothing before 200 moves |
| a close PAIR whose ratio overflows (1e-300 at bar 200, 1e50 at 201) | one spoiled return rather than two, so it empties **20** bars, 201..220; nothing before 200 moves and no fired bar drops below the two-bin floor. Run unguarded, those same 20 windows all report **0.048729** — finite, plausible, and below the floor the column claims as its minimum |
| a flat run planted at bar 200 of a 400-bar walk | 20 identical closes empty **0** bars; 21 empty **1** (bar 220); 25 empty **5** (bars 220..224). In every case bar 219 reads exactly **0.198515** — 19 zero returns and one move, the two-bin floor |
| exactly flat frame | 0/300 fire |
| `length` = None / 0 / −5 / 2 / 0.5 / 2.9 | all fall back to `TS_BINENT_20_5` |
| `length=2` (refused) | would be the constant `log 2`: 1 distinct value over 398 windows, which is why `MIN_LENGTH` is 3 (`length=3` already takes 2 distinct values) |
| `bins` = None / 0 / 1 / −3 | all fall back to `bins=5` |
| `bins` = 2 / 3 / 10 / 20 / 21 / 50 at `length=20` | `TS_BINENT_20_2` / `_3` / `_10` / `_20` / `_20` / `_20` — clamped to `length`; 10 / 30 / 93 / 45 / 45 / 45 distinct values over 380 fired bars |
| the clamp is not a no-op | an unclamped `bins=100` is Spearman **0.263965** against the clamped column (max \|diff\| 0.8409); `bins=40` is 0.564612; `bins=20` agrees to 4.4e-16. More bins than samples reads mostly the number of exact ties, which is why the distinct-value count FALLS from 93 at `bins=10` to 45 at `bins=20` |
| `length=3, bins=50` | `TS_BINENT_3_3` |
| `length=50.9` | identical to `length=50` (int truncation) |
| `length=10` vs `length=60` | distinct names, Spearman −0.0307 — different columns |
| `fillna=-1.0` | fills exactly the 20 warm-up bars |

## Five-point wiring

| # | file | what landed |
|---|---|---|
| 1 | `pandas_ta/statistics/ts_binent_20.py` | the indicator |
| 2 | `pandas_ta/statistics/__init__.py` | `from .ts_binent_20 import ts_binent_20` |
| 3 | `pandas_ta/__init__.py` → `Category["statistics"]` | `"ts_binent_20"` |
| 4 | `pandas_ta/core.py` | `df.ta.ts_binent_20(length=None, bins=None, offset=None)` |
| 5 | `tests/test_ts_binent_20.py` | 126 tests |

Plus the documentation touch points: `README.md` (the three counts — 322 in
`Category`, 330 accessors, statistics 31 — and the statistics list),
`docs/IndicatorDictionary.md` (regenerated by
`python docs/gen_indicator_dictionary.py`, which probes the live package and
tags `TS_BINENT_20_5` **SF** with a 20-bar warm-up),
`docs/MLCompanionContract.md` (667 tagged columns / 310 `SF`) and
`tests/test_altport2_ports.py` (`CATEGORY_TOTAL` 322).
