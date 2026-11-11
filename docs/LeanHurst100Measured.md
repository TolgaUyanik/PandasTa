# `lean_hurst_100` — measured

Issue #85 (LEAN-HURST-100), ported 2026-11-11 on branch `issue-85-lean-hurst-100`.
Column: **`LEAN_HURST_100_20`**, `pandas_ta/statistics/lean_hurst_100.py`.

Every number here is printed by `python docs/measure_lean_hurst_100.py`
(pandas 2.3.3 / numpy 1.26.4) or by `python -m pytest tests/test_lean_hurst_100.py -q`.
Nothing in this file was typed from expectation; where a number is *not* measured,
the line says so.

## What it is

    k        = 2 .. 20
    d_k[t]   = log(close[t] / close[t - k])
    sd_k[t]  = population sd of d_k over the window's (100 - k) values
    column   = ordinary-least-squares slope of log(sd_k) on log(k)

How fast the spread of a log-price move grows with the horizon it is measured
over. A 100-close window; lag k contributes the 100 − k pairs whose both ends
lie inside it (98 at k = 2, 80 at k = 20).

## Source, and what "Apache-2.0 Lean" does and does not mean here

The issue names QuantConnect Lean's `HurstExponent` (Apache-2.0) and states the
formula:

> `HurstExponent(100, maxLag 20): slope of log std(x[t+k]-x[t]) on log k, k=2..20, x = log close`

⚠ **Lean's C# source is not in this worktree and web access is unavailable.** It
was not read in this session. So the attribution is an attribution, not an
oracle: Gate A below is against the issue's stated line, and anything Lean does
that the line does not say — its own warm-up, its standard-deviation
convention, whether it subtracts the mean, what it emits before the window
fills — is **unverified here**. The prototype
(`docs/issues/screen/ind_screen.py`, candidate `lean_hurst_100`, gitignored and
local to the owner's machine) was read and is used as a second implementation,
not as the source.

## Gate A — correctness

**A1. A window whose slope is exactly 1/2, derived by hand.** `close = [1, 2, 8, 4, 32]`
at `length=5, max_lag=3`, where only lags 2 and 3 exist and the fit is an exact
difference quotient. With x = log close = [0, L, 3L, 2L, 5L] and L = log 2:

| lag | differences | mean | population sd |
|---|---|---|---|
| 2 | 3L, L, 2L | 2L | L·sqrt(2/3) |
| 3 | 2L, 4L | 3L | L |

slope = (log L − log(L·sqrt(2/3))) / (log 3 − log 2) = 0.5·log(1.5)/log(1.5) = **1/2**.

Module: `0.50000000000000011`, i.e. **|value − 0.5| = 1.11e-16**; bars 0..3 NaN.

**A2. Against the screen prototype**, 1,500-bar walk, 1,401 fired bars:

| compared against | max \|diff\| | bit-equal | Spearman | NaN masks |
|---|---|---|---|---|
| the prototype retyped here (`w_hurst_lagdiff` + `roll`) | 1.776357e-15 | 60/1401 | 1.000000 | equal |
| **the screen's own registry candidate, imported from `docs/issues/screen/ind_screen.py`** | 1.776357e-15 | 60/1401 | 1.000000 | equal |

The imported row is the real candidate, not a retype: the measurement script
loads `REG["lean_hurst_100"]["fn"]` out of that file when the worktree has it,
and says so when it does not (a clone does not — `docs/issues/` is gitignored).

**A3. Against an independent per-window loop in plain Python scalars** (no numpy,
no pandas rolling, every sum written out), 400 bars / 301 fired:

| the loop's spelling of x[t+k] − x[t] | max \|diff\| | bit-equal | Spearman |
|---|---|---|---|
| `log(c[t] / c[t-k])` — the module's | 6.661338e-16 | 21/301 | 1.000000 |
| `log(c[t]) - log(c[t-k])` — the prototype's | 2.164935e-15 | 5/301 | 1.000000 |

**A4. Five readings the wording leaves open.** Each decided, and each priced
against the port on the same 1,500-bar walk rather than dismissed:

| reading, and what this port does | max \|diff\| | bit-equal | Spearman |
|---|---|---|---|
| `std` = population (`ddof=0`, numpy's default, the prototype's). Rejected: `ddof=1` | 5.164568e-04 | 0/1401 | **1.000000** |
| the mean IS subtracted. Rejected: root mean square, mean kept | 3.009660e-01 | 0/1401 | 0.931847 |
| k runs 2..20, as the issue says. Rejected: k from 1 | 1.005629e-01 | 0/1401 | 0.989560 |
| only pairs inside the window (100 − k per lag). Rejected: 100 differences per lag, reaching past it | 3.012974e-01 | 0/1381 | 0.888384 |
| differences as `log(close/close.shift(k))`. "Rejected": the difference of two logarithms | 1.776357e-15 | 60/1401 | 1.000000 |

Three things worth keeping from that table:

* **`ddof=1` is rank-identical on this frame** (Spearman 1.000000) even though no
  bar is bit-equal. The convention changes the per-lag divisor, so the fit tilts;
  but anything mining ranks would not see it. The choice is made because it is
  the prototype's and numpy's, not because it was shown to matter.
* The crossing-window reading is **not** just a different value: it needs 20
  closes of extra history, first firing at bar 119 against the port's bar 99.
* The last row is a *spelling*, not a reading: the two are the same quantity, and
  the module takes one logarithm of a ratio because that is what makes Gate D
  bit-exact (below). It is not a simplification to undo.

## Gate B — causality, by mutant

Future-perturbation sweep over **34 J values** (J = 150..1470 step 40) on a
1,500-bar frame: replace every bar from J onward with a different path, assert
nothing strictly before J moves. Three frame pairs, because the module has a
NaN decision that only one of them exercises — a random walk, a **tick-rounded**
walk (prices on a 0.01 grid, as quotes are), and a **geometric ladder with one
real move in it**, where the rounding-noise floor decides which windows fire.

| | walk | geometric+jump | tick-rounded |
|---|---|---|---|
| **real module** | **0/34** | **0/34** | **0/34** |
| mutant: column back-dated by `length` | 34/34 | 34/34 | 34/34 |
| mutant: `px.shift(lag)` → `px.shift(-lag)` | 34/34 | 34/34 | 34/34 |
| mutant: `center=True` on the rolling sd | 34/34 | 34/34 | 34/34 |
| mutant: the log-sd row read one bar late | 34/34 | 34/34 | 34/34 |

Every mutant is live on every frame (its output differs from the real module's
before the sweep runs), so none of the 12 cells is a mutant that did nothing.
Mutants are `importlib`-read from the module source and `exec`'d in memory.

`offset` is the caller-reachable look-ahead and is pinned, not assumed:
`offset=2` is exactly the default shifted two bars later, `offset=-2` exactly
two bars earlier. The sweep covers the default `offset=0`, which is what
`Category` uses.

## The rounding-noise floor

`sd == 0` — the prototype's guard — is not enough. The lagged differences of an
exactly geometric path are mathematically constant, so there is no slope; but in
float64 they vary at rounding level, and an unguarded fit reports a number from
that noise. Measured on 300-bar frames, guarded (the module) against unguarded
(`sd > 0` only):

| frame | guarded fires | unguarded fires | unguarded range |
|---|---|---|---|
| geometric, 1% a bar | 0/300 | 201/300 | [−0.0100, 0.1100] |
| geometric by exact ratio, ×1.5 a bar | 0/300 | 85/300 | [0.2723, 0.5359] |
| exactly flat | 0/300 | 0/300 | — |
| tick-rounded walk, 2 decimals | 201/300 | 201/300 | identical, 0 bars differ |
| gaussian random walk | 201/300 | 201/300 | identical, 0 bars differ |

The ×1.5 row is the reason the guard exists: 0.2723..0.5359 is exactly the range
a reader would accept as "a random walk", produced by nothing at all.

The floor is **absolute** — `NOISE_ULPS = 4096` machine epsilons, 9.095e-13 —
rather than a rolling scale, because what it floors is a *dimensionless* log
price ratio. That is a deliberate simplification with a Gate B consequence: the
module has exactly **one** `.rolling(` call, so one window whose causality needs
pinning, instead of two. (An earlier revision of this port used
`4096 · eps · |rolling mean|`; its second aggregation could not be shown to leak
on any frame tried, which is a reason to not have it rather than a reason to
trust it.) `tests/test_lean_hurst_100.py::test_the_noise_floor_is_an_absolute_constant_not_a_window`
pins the single rolling call.

Where the crossover sits, on a geometric ladder whose steps jitter by a known
relative amount (real variation, but tiny):

| jitter | guarded fires | unguarded fires |
|---|---|---|
| ±1e-16 | 0/1500 | 352/1500 |
| ±1e-14 | 0/1500 | 1401/1500 |
| ±1e-12 | 118/1500 | 1401/1500 |
| ±1e-11 | 1401/1500 | 1401/1500 |
| ±1e-09 | 1401/1500 | 1401/1500 |

So the floor stops reading variation at about 1e-12 in log terms. The smallest
variation real quotes can show is one tick over the price — 1e-9 even at a price
of 1e6 with a 0.001 tick — three orders above that, and the tick-rounded walk
row above loses no bars to it. (The 1e-9 bound is arithmetic, not a measurement
of any instrument.)

## Gate C — reachability

⚠ **Synthetic only.** This worktree has no BIST frames; the real-data counts are
owed to Gate E's run and belong in this file when the receipt session fills it in.

1,500-bar paths, 1,401 fired bars each, 1,401 distinct values each:

| path | min | p10 | median | p90 | max | share > 0.5 |
|---|---|---|---|---|---|---|
| AR(1) returns, φ = +0.8 (persistent) | 0.267932 | 0.517998 | **0.723194** | 0.848689 | 0.922070 | 0.9215 |
| AR(1) returns, φ = +0.4 | 0.086738 | 0.363386 | **0.509264** | 0.683469 | 0.818191 | 0.5460 |
| gaussian walk, iid returns | 0.094626 | 0.241568 | **0.430069** | 0.573666 | 0.668410 | 0.2505 |
| AR(1) returns, φ = −0.4 | 0.175784 | 0.235704 | **0.383550** | 0.498739 | 0.587404 | 0.0992 |
| AR(1) returns, φ = −0.8 | 0.067506 | 0.173826 | **0.264444** | 0.398489 | 0.489593 | 0.0000 |
| hard alternating log returns | 0.127927 | 0.229165 | **0.328217** | 0.411718 | 0.473016 | 0.0000 |

`0 < 1401 < 1500` fired on the walk, 1,401 distinct values, so Gate D's
non-constant requirement is met with room.

**The ordering is the claim; the LEVEL is biased low.** For iid returns the
population slope is exactly 0.5 (the sd of a k-bar difference is sqrt(k)·σ), but
each lag has only 100 − k *overlapping* differences. Over **2,000 independent
100-bar iid-return windows**: mean 0.4132, median **0.4199**, sd 0.1251,
p10 0.2473, p90 0.5681, above 0.5 on **25.65%**. Do not read 0.5 as the
random-walk line on a 100-bar window.

**Drift-invariance**, which follows from the formula and is measured rather than
asserted: adding a constant to every log return moves lag k's differences by
k·drift and leaves their sd alone. Walk vs the same walk at +0.004 of log drift
a bar: max \|diff\| **2.373102e-15**, Spearman 1.000000, NaN masks equal.

## Gate D — scale-free

1,500-bar walk, 1,401 fired bars:

| rescale | NaN masks | bit-identical | max \|diff\| |
|---|---|---|---|
| ×8 | equal | **1401/1401** | 0.000000e+00 |
| ×64 | equal | **1401/1401** | 0.000000e+00 |
| ×10 | equal | 97/1401 | 1.415534e-15 |
| ×3.7 | equal | 111/1401 | 2.720046e-15 |

×8 is bit-identical rather than merely close because every input is a price
*ratio*: `8a / 8b` is the same double as `a / b`. The literal
difference-of-logarithms spelling is **not** — its lag-2 differences come out
bit-equal on 790 of 1,498 bars at ×8 and 594 of 1,498 at ×64 (max \|diff\|
8.88e-16 and 1.78e-15), and the slope inherits that. This is the whole reason
the module takes one logarithm of a ratio.

## Gate E — attribution

**Gate E: pending, run by issue-solver after this session.**

`tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
fails locally until the row exists; CI into `dev` sets `GATE_E_PENDING_OK=1` and
skips it with a reason starting "Gate E owed". The receipt session records the
ledger row and writes the measured numbers here.

What the issue reports for the **prototype** (2026-10-24; a prototype is not a
port, and these are NOT this column's numbers): pooled max \|ρ\| 0.2491 vs
`mad_pct`, n = 390,038, top-5 per-frame max median 0.2241 → SHIP; next
comparators `ADX` 0.1958 and `Cloud_Thickness_pct` 0.1947; fork overlap (stage 2,
12 frames) 0.3140 vs `ht_dcperiod:HT_DCPERIOD`.

**Nearest neighbours on one 1,500-bar synthetic walk — NOT Gate E** (13 shipped
columns, one frame; Gate E is 687 comparators over 89 frozen BIST frames):

| \|ρ\| | column |
|---|---|
| 0.5214 | `kpss_100` |
| 0.4589 | `ht_dcperiod` |
| 0.4579 | `mad_100 / close` |
| 0.1878 | `adx_14` |
| 0.1302 | `natr_14` |
| 0.1065 | `zscore_30` |
| 0.0976 | `rsi_14` |
| 0.0964 | `kurtosis_30` |
| 0.0947 | `entropy_20` |
| 0.0758 | `cusum_100` |
| 0.0746 | sd of 100 log returns |
| 0.0632 | `skew_30` |
| 0.0037 | `cfo_9` |

`kpss` and `ht_dcperiod` leading is the smell test's signal: all three are "how
does this window's path behave over longer horizons" questions. Neither is
near the 0.90 line on this frame, and the frame is not evidence about the 89.

## Gate F — suites

Run in this worktree:

* `python -m pytest tests/test_lean_hurst_100.py -q` → **65 passed** in 7.91 s.
* `python -m pytest -q` → **3 failed, 5450 passed, 83 skipped** in 115 s. The
  three failures are the two `CLAUDE.md` "Known breaks"
  (`test_altrepo_talib_csv.py::test_regenerating_reproduces_the_committed_rows`,
  which needs the sibling `../AlternativeRepos` checkout and is deselected in
  CI, and `test_pine_coverage_csv.py::test_audited_rows_carry_their_evidence`,
  the `supertrend` citation into the untracked `docs/pine/`) plus
  `test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`, which
  reports `['lean_hurst_100', 'mtd_ret']`: the Gate E row this port owes, and
  one owed before it. CI into `dev` skips that one under
  `GATE_E_PENDING_OK=1`.

The launcher runs both repos' suites in clean worktrees.

## Edge cases, measured

| case | behaviour |
|---|---|
| 99 bars | returns `None` (`verify_series` floor) |
| exactly 100 bars | fires 1/100, at bar 99 |
| one NaN close at bar 200 | empties exactly 100 bars, 200..299; **0** bars before 200 move; 79 bars after it (300..399) move by at most 4.44e-16 |
| one zero / negative / infinite / subnormal (1e-310) close | each empties exactly the same 100 bars |
| exactly flat frame | 0/300 fire |

The 79 moved bars after the hole are not a causality leak and not a correctness
defect: pandas' rolling standard deviation is an online accumulation, so a NaN
in the middle changes the arithmetic *path* of later windows. Nothing before the
hole moves (measured: 0 bars), and Gate B's sweep is what tests for back-dating.

**Parameter guards** (400-bar frame, so 301 fired bars at the defaults):

| input | effective column | fires |
|---|---|---|
| `length` = None / 0 / −5 / 4 / 0.5 / 2.9 | `LEAN_HURST_100_20` | 301 |
| `length=5` | `LEAN_HURST_5_3` (max_lag clamped) | 396 |
| `length=50` | `LEAN_HURST_50_20` | 351 |
| `max_lag` = None / 0 / 2 | `LEAN_HURST_100_20` | 301 |
| `max_lag=3` | `LEAN_HURST_100_3` | 301 |
| `max_lag` = 98 / 99 / 200 | `LEAN_HURST_100_98` (clamped to `length − 2`) | 301 |

Both guards fall back rather than raise, which is this fork's convention, and
the **effective** value is the one in the column name — so a caller who asked
for `max_lag=200` can see in `LEAN_HURST_100_98` what they got.

## Wiring

| # | touch point | state |
|---|---|---|
| 1 | `pandas_ta/statistics/lean_hurst_100.py` | added |
| 2 | `pandas_ta/statistics/__init__.py` | exported |
| 3 | `Category["statistics"]` in `pandas_ta/__init__.py` | registered; `CATEGORY_TOTAL` 318 → 319 in `tests/test_altport2_ports.py` |
| 4 | `pandas_ta/core.py` | `df.ta.lean_hurst_100(length, max_lag, offset)` |
| 5 | `tests/test_lean_hurst_100.py` | 65 tests, Gate B `mutant` and Gate D `scale` among them |

Counters, each re-read from the generated dictionary rather than incremented by
hand: README 319 `Category` / 327 accessors / statistics (29);
`docs/IndicatorDictionary.md` regenerated (321 probed, the column tagged `SF`,
warm-up 99); `docs/MLCompanionContract.md` 663 → 664 tagged and 306 → 307 `SF`.

## Recommendation

**Ship it, pending Gate E.** Nothing measured here argues against the column:

* it is the formula the issue states, agreeing with the screen's own candidate
  to 1.8e-15 with identical NaN masks and a hand-derived closed-form window hit
  to 1.1e-16;
* it is causal (0/34 leaks on three frames, four live mutants caught 34/34 each)
  and exactly scale-free (1401/1401 bit-identical at ×8 and ×64);
* it asks a question the shipped set does not obviously already ask — its
  nearest synthetic neighbour is `kpss` at 0.52 — and the prototype's own Gate E
  was 0.2491, far under the 0.76 ship line. (How that compares with the other
  candidates of the 2026-10-24 screen was not checked in this session; the one
  comparison that matters is this column's own run, which is owed.)

Two caveats a reader should carry, both measured and neither disqualifying:

1. **The level is biased low** (median 0.4199 where the population value is 0.5),
   so a rule written as "above 0.5 means trending" is wrong on this column at
   `length=100`. Its usable content is the ordering.
2. **Lean's code was not read.** If the owner later compares against Lean's own
   `HurstExponent` output and it differs, the difference will be in one of A4's
   five readings — they are enumerated with their sizes precisely so that
   comparison is cheap.
