# `ts_c3_20` — measured

Issue #88 (TS-C3-20), ported 2026-11-12 on branch `issue-88-ts-c3-20`.
Column: **`TS_C3_20_1`**, `pandas_ta/statistics/ts_c3_20.py`.
**Status: SHIPPED through Gates A–F.** Gate E ran on the committed code
(issue-solver, 2026-11-12): `TS_C3_20_1` max \|ρ\| **0.0806** vs
`kama_vs_SMA_20_pct`, per-frame max median 0.0940 over 89 frames →
**SHIP**, recorded in `docs/gate_e_ledger.csv`. Gate C's real-data counts
come from that same run and are now measured.

Every number here is printed by `python docs/measure_ts_c3_20.py`
(pandas 2.3.3 / numpy 1.26.4), by `python -m pytest tests/test_ts_c3_20.py -q`,
or — for Gates C and E on real data — by the launcher's Gate E run
(`overlap_max.csv` and `meta.json` of run `is88-ts_c3_20-853aeed4`,
2026-11-12). Nothing in this file was typed from expectation; where a number
is *not* measured, the line says so.

## What it is

    r[t]     = close[t] / close[t-1] - 1
    p[t]     = r[t] * r[t-lag] * r[t-2*lag]
    num[t]   = mean of p over the trailing (length - 2*lag) triples
    sd[t]    = sample standard deviation (ddof=1) of r over the trailing
               `length` returns, NaN where sd <= 9.09e-13
    column   = num / sd^3

At the defaults (`length=20`, `lag=1`): 18 triples inside a window of 20
returns, which reads 21 closes. A third-order autocorrelation, standardised
by volatility so it is dimensionless in return units — zero in expectation
for any sign-symmetric independent series, non-zero when the size of a move
is predicted by the product of the two before it.

## Source, and what "tsfresh (MIT)" does and does not mean here

The issue names tsfresh's `feature_calculators` (MIT) and states the formula:

> `c3(x, lag=1) = mean(x[t]*x[t-1]*x[t-2]) on 20 returns`

with the scale-free form of the screen prototype
(`docs/issues/screen/ind_screen.py`, candidate `ts_c3_20`): *divided by
`std(r,20)^3`*, spelled there as

    sdiv(mean(r * delay(r, 1) * delay(r, 2), 18), std(r, 20) ** 3)

⚠ **tsfresh is not installed in this worktree and web access is
unavailable.** Its own code was not read in this session. So the attribution
is an attribution, not an oracle: Gate A below is against the issue's stated
line, and anything tsfresh does that the line does not say — what it returns
when the series is shorter than `2*lag`, how it handles NaNs, whether its
`c3` demeans (the stated form does not) — is **unverified here**. The
prototype (gitignored, local to the owner's machine) was read, and it is the
source for the divisor, which is not part of tsfresh's `c3` at all.

## Gate A — correctness

**A1. A window whose value is exactly `-1/(3·sqrt(3))`, derived by hand.**
`close = [1, 2, 1, 2, 1]` at `length=4, lag=1`, so the window holds the four
returns `[+1, -1/2, +1, -1/2]` and exactly two triples:

| quantity | value |
|---|---|
| `r3·r2·r1` | (+1)(−1/2)(+1) = −1/2 |
| `r4·r3·r2` | (−1/2)(+1)(−1/2) = +1/4 |
| numerator | −1/8 |
| sd (ddof=1) | mean 1/4, sum sq dev 9/4, var 3/4, sd sqrt(3)/2 |
| column | (−1/8) / (3/4)^1.5 = **−1/(3·sqrt(3)) = −sqrt(3)/9** |

Module: `-0.19245008972987529` against the exact `-0.19245008972987526`, i.e.
**|value − exact| = 2.78e-17**; bars 0..3 NaN.

**A2. Against the screen prototype**, 1,500-bar walk, 1,480 fired bars:

| compared against | max \|diff\| | bit-equal | Spearman | NaN masks |
|---|---|---|---|---|
| the prototype retyped here | 0.000000e+00 | **1480/1480** | 1.000000 | equal |
| **the screen's own registry candidate, imported from `docs/issues/screen/ind_screen.py`** | 0.000000e+00 | **1480/1480** | 1.000000 | equal |

The imported row is the real candidate, not a retype: the measurement script
loads `REG["ts_c3_20"]["fn"]` out of that file when the worktree has it, and
says so when it does not (a clone does not — `docs/issues/` is gitignored).
Bit-equality, not closeness, is expected here and is the point: the module
spells the numerator and the divisor in the prototype's own order, and on a
continuous walk no window reaches the noise floor the prototype lacks.

**A3. Against the issue's line applied window by window** with
`sliding_window_view` — the triples formed inside each window, no pandas
rolling anywhere, so it shares no window machinery with the module:
max \|diff\| **4.496403e-15**, bit-equal 22/1480, Spearman 1.000000, NaN
masks equal.

**A4. Against an independent per-window loop in plain Python scalars** (no
numpy, no pandas rolling, every sum written out), 400 bars / 380 fired:
max \|diff\| **6.661338e-15**, bit-equal 7/380, Spearman 1.000000.

**A5. Four readings the wording leaves open.** Each decided, and each priced
against the port on the same 1,500-bar walk rather than dismissed:

| reading, and what this port does | max \|diff\| | bit-equal | Spearman |
|---|---|---|---|
| divisor = **sample** sd (`ddof=1`, pandas' default, the prototype's). Rejected: `ddof=0` | 6.161969e-02 | 0/1480 | **1.000000** |
| numerator over the **18 triples inside the window**. Rejected: a full 20-wide mean of the triple series, reaching 2 bars further back | 9.936851e-01 | 0/1478 | 0.920085 |
| returns are **simple** (`close/close.shift(1) - 1`), the prototype's `ret`. Rejected: log returns | 1.808741e-02 | 0/1480 | 0.999842 |
| divisor over the **same 20 returns** as the numerator's window. Rejected: the 18 returns the triples span | 6.252242e-01 | 0/1480 | 0.994954 |

Three things worth keeping from that table:

* **`ddof=0` is a strict rescaling, not a different shape.**
  `sd(ddof=0) = sd(ddof=1)·sqrt((n−1)/n)`, so dividing by its cube multiplies
  the column by `((n−1)/n)^-1.5` = **1.079977** at length 20. Measured:
  `port · 1.079977` reproduces the `ddof=0` variant to **5.55e-16**, every
  bar moves (0 bit-equal) and no rank does (Spearman 1.000000). The choice is
  made because it is the prototype's and pandas' default, not because it was
  shown to matter to a rank miner.
* The full-window numerator reading is **not** just a different value: it
  needs 2 closes of extra history, first firing at bar 22 against the port's
  bar 20, and its NaN mask therefore differs.
* Log returns are the closest of the four (Spearman 0.999842) and still not
  the same column; the simple return is the prototype's and is what the
  numbers in issue #88 were measured on.

A fifth decision — the NaN rule for a window with no volatility to divide by
— is priced in *The rounding-noise floor* below, on 300-bar geometric
ladders rather than on this walk, because a walk never reaches it.

## Gate B — causality, by mutant

Future-perturbation sweep over **37 J values** (J = 40..1480 step 40) on
1,500-bar frames: replace every bar from J onward with a different path,
assert nothing strictly before J moves. Three frame pairs — a random walk, a
**tick-rounded** walk (prices on a 0.01 grid, as quotes are) and a
**nonlinear** path built to have a non-zero third moment.

| | walk | tick-rounded | nonlinear |
|---|---|---|---|
| **real module** | **0/37** | **0/37** | **0/37** |
| mutant: column back-dated by `length` | 37/37 | 37/37 | 37/37 |
| mutant: `r.shift(lag)`, `r.shift(2*lag)` → `shift(-lag)`, `shift(-2*lag)` | 37/37 | 37/37 | 37/37 |
| mutant: the return read one bar ahead (`px.shift(-1) / px - 1`) | 37/37 | 37/37 | 37/37 |
| mutant: `center=True` on the numerator's rolling mean | 37/37 | 37/37 | 37/37 |
| mutant: `center=True` on the divisor's rolling sd | 37/37 | 37/37 | 37/37 |

Every mutant is live on every frame (its output differs from the real
module's before the sweep runs), so none of the 15 cells is a mutant that did
nothing. Mutants are `importlib`-read from the module source and `exec`'d in
memory. The module has exactly **two** `.rolling(` calls, the numerator's and
the divisor's, and the last two mutants are one per call.

**Non-default parameters, on the walk.** `lag` is user-reachable up to
`(length - 2) // 2` = 9 at length 20, and `length` is free. All three
mutants whose behaviour depends on a parameter — the forward triple (on
`lag`), the centred numerator mean (on its width `length - 2·lag`) and the
back-dated column (on `length`) — are re-run at three settings:

| setting | triples | real module | forward triple | centred mean | back-dated |
|---|---|---|---|---|---|
| `length=20, lag=1` (default) | 18 | **0/37** | 37/37 | 37/37 | 37/37 |
| `length=20, lag=9` | 2 | **0/37** | 37/37 | **0/37** (a no-op, below) | 37/37 |
| `length=60, lag=1` | 58 | **0/37** | 36/37 | 36/37 | 37/37 |

Three of the nine cells are not 37/37, under two explanations, and both
explanations are printed by the script rather than argued:

* The two **36/37** cells (forward triple and centred mean, both at
  `length=60`) miss at J = 40, the only sweep offset below a 60-bar
  warm-up. Measured on that frame: the prefix `[0:40]` is entirely NaN under
  both the real module and the mutant (`prefix [0:40] all-NaN real=True
  mutant=True`), so there is nothing for the perturbation to move. A
  property of the offset grid, not of the mutant.
* The one **0/37** cell is a mutation that does nothing at that setting, and the
  test asserts exactly that: at `lag=9` the numerator's window is 2 wide, and
  pandas centres a window by `(window - 1) // 2` bars, which is **0** for
  width 2 — so `center=True` is identical to `center=False` there. Measured:
  the mutant's output `equals()` the real module's at (20, 9) and differs
  from it at (20, 1) and (60, 1). It is also the useful half of the finding:
  a centring bug in the numerator introduces NO look-ahead when the
  numerator window is 2.

`offset` is the caller-reachable look-ahead and is pinned, not assumed:
`offset=2` is exactly the default shifted two bars later, `offset=-2` exactly
two bars earlier. The sweep covers the default `offset=0`, which is what
`Category` uses.

## The rounding-noise floor

`sd != 0` — all the prototype's `sdiv` catches — is not enough. The returns of
an exactly geometric path are mathematically constant, so there is no
standardised third moment; but in float64 they vary at rounding level, and an
unguarded division then reports the ratio of two roundings. Measured on
300-bar frames, guarded (the module) against unguarded:

| frame | guarded fires | unguarded fires | max \|unguarded\| |
|---|---|---|---|
| geometric, 1% a bar | **0/300** | 280/300 | 7.958e+41 |
| geometric by exact ratio, ×1.5 a bar | **0/300** | 280/300 | 3.343e+47 |
| exactly flat | 0/300 | 0/300 | — (sd is exactly 0) |
| gaussian random walk | 280/300 | 280/300 | identical, 0 bars differ |
| tick-rounded walk, 2 decimals | 280/300 | 280/300 | identical, 0 bars differ |

Unlike `lean_hurst_100`'s version of this failure, the unguarded values here
are **wild rather than plausible**: they reach 7.96e+41, where that port's
unguarded ladders stay inside [−0.0100, 0.1100] and [0.2723, 0.5359]
(`docs/LeanHurst100Measured.md`, its noise-floor table). The division here
is by a cube, so the rounding is amplified three times over. They are still
finite,
so `sdiv` keeps them, and a feature column of 1e+41 is worse than NaN for
anything that scales or splits on it.

The floor is **absolute** — `NOISE_ULPS = 4096` machine epsilons, 9.095e-13 —
rather than a rolling scale, because what it floors is the standard deviation
of *dimensionless* price ratios, so it needs no window of its own whose
causality would have to be pinned.

Where the crossover sits, on a 1%-a-bar ladder whose steps jitter by a known
relative amount (real variation, but tiny):

| jitter | guarded fires | unguarded fires |
|---|---|---|
| ±1e-16 | 0/1500 | 1480/1500 |
| ±1e-14 | 0/1500 | 1480/1500 |
| ±1e-12 | 1035/1500 | 1480/1500 |
| ±1e-11 | 1480/1500 | 1480/1500 |
| ±1e-09 | 1480/1500 | 1480/1500 |

So the floor stops reading variation at about 1e-12 of relative return
**dispersion**, and dispersion is the right word: the floor bounds `sd(r)`,
not `|r|`. A tick grid quantises the return LEVEL at `tick / price` but the
dispersion of consecutive returns at about `(tick / price)²`, so the
familiar "one tick over the price is 1e-9 even at a price of 1e6" is not a
comparison against this floor at all. What a monotone one-tick-per-bar path
actually does, measured:

| price | tick | \|r\| | sd(r) over 20 returns | fires |
|---|---|---|---|---|
| 50 | 0.01 | 1.888e-04 | 2.115e-07 | 280/300 |
| 1e6 | 0.001 | 1.000e-09 | 1.133e-16 | **0/300** |
| 1e6 | 0.01 | 1.000e-08 | 5.865e-16 | **0/300** |

The two emptied rows are the correct answer rather than a cost: a window
whose returns are constant to 1e-16 has no volatility to standardise by, so
there is no standardised third moment to report. What is measured about the
floor's safety is the two real-shaped frames in the table above — a walk and
a tick-rounded walk, 280 of 300 bars each, identical to the unguarded form,
0 bars differing — and not a generalisation beyond them.

## Gate C — reachability

**Real data: measured.** From the launcher's Gate E run of 2026-11-12
(`overlap_max.csv`), over the 89 frozen ALTPORT-1 frames and 398,849 pooled
bars:

| | bars | share of 398,849 |
|---|---|---|
| `TS_C3_20_1` non-NaN | **397,069** | 99.554% |
| of those, non-zero | **396,361** | 99.376% |
| NaN | 1,780 | 0.446% |

So the column fires on every bar that is not a warm-up bar and on no others:
`398,849 − 89 × 20 = 397,069` exactly, the arithmetic floor on the NaN count,
reached with nothing lost beyond it. Three other things could have emptied
bars and on these frames none did — a close inside a frame that is NaN, zero,
negative, infinite or subnormal (21 bars each, see *Edge cases* below), a
window whose 20 returns have `sd <= 9.09e-13`, which in real data means **21**
consecutive identical closes (a halted or limit-locked session, or an illiquid
name), and an exactly geometric window, which reaches the same floor with 21
DISTINCT closes (*The rounding-noise floor* below). The neighbouring
`lean_momersion_20` lost 11 bars beyond its own warm-up on these same frames
(`docs/LeanMomersion20Measured.md`, 396,969 non-NaN), so a tight floor is a
measurement here, not the expected outcome.

The 708 non-NaN bars that are exactly 0.0 (397,069 − 396,361) are not
explained here; a numerator that is exactly zero needs a triple product that
cancels to a float zero, which a zero return gives (two consecutive identical
closes inside a window, far commoner than 21 of them). Whatever the cause,
`0 < 396,361 < 398,849` is what Gate D's non-constant requirement asks for,
and the prototype's own sample size on the same frames was the same 397,069
(issue #88, run `screen_20261024`).

The rest of this section is **synthetic**: 1,500-bar generated paths,
1,480 fired bars each.

| path | distinct | min | p10 | median | p90 | max | share > 0 | spread (max−min) |
|---|---|---|---|---|---|---|---|---|
| nonlinear, a = +0.5 | 1480 | −0.3846 | 0.0298 | **0.2442** | 0.5954 | 1.1793 | 0.9250 | 1.564e+00 |
| nonlinear, a = 0 | 1480 | −0.7929 | −0.2331 | **0.0077** | 0.2555 | 0.7575 | 0.5122 | 1.550e+00 |
| nonlinear, a = −0.5 | 1480 | −1.5108 | −0.6495 | **−0.2550** | 0.0090 | 0.3578 | 0.1047 | 1.869e+00 |
| gaussian walk, iid returns | 1480 | −0.7705 | −0.2565 | **0.0056** | 0.2602 | 0.6360 | 0.5095 | 1.406e+00 |
| tick-rounded walk | 1480 | −0.7614 | −0.2368 | **−0.0129** | 0.2494 | 0.5396 | 0.4770 | 1.301e+00 |
| alternating sizes (deterministic) | 748 | −0.2487 | −0.2487 | **−0.2487** | −0.2487 | −0.2487 | 0.0000 | **8.893e-14** |

`0 < 1480 < 1500` fired on every one of the three frames Gate D uses, with
1,480 distinct values and 1,480 of 1,480 fired bars non-zero, so Gate D's
non-constant requirement is met with room. The alternating-sizes row is the
exception that proves the column is reading what it claims to: a path of one
large up move and one small down move repeating has every triple holding two
moves of one sign and one of the other, so the value is the same constant
(−0.2487) on every bar — its whole spread is **8.893e-14** over 1,480 bars,
which is rounding of the rolling mean rather than variation, and is why it
still shows 748 distinct float values.

**The ordering is the claim; one reading is not.** The nonlinear path sets
its LOG returns to `rlog[t] = eps[t] + a·eps[t-1]·eps[t-2]/sigma`, whose
population third moment `E[rlog_t·rlog_{t-1}·rlog_{t-2}]` is `a·sigma^3`
and whose implied standardised value is therefore `a/(1+a²)^1.5` = **0.3578**
at a = +0.5 (arithmetic from the generator, not a measurement). The medians
come out in the order of `a` (0.2442 / 0.0077 / −0.2550 at a = +0.5 / 0 /
−0.5), shrunk toward zero at length 20. That the window length is what
shrinks them is measured, not asserted — on a 20,000-bar path at a = +0.5:

| window | median |
|---|---|
| `length=20` | 0.2748 |
| `length=60` | 0.3390 |
| `length=200` | 0.3755 |
| `length=1000` | 0.3977 |

so the level rises with the window and straddles the implied 0.3578 rather
than converging on it from below — the residual gap at long windows is not
attributed to a cause here (the column reads simple returns where the
generator sets log ones, which A5 prices at Spearman 0.999842 / max \|diff\|
0.0181 at length 20, far too small to explain a level gap of this size).
Hence the ordering, not the level, is what the tests pin. Over
**2,000 independent 20-return iid-return windows**, whose population value is
exactly 0: mean 0.0056, median **0.0035**, sd 0.2185, p10 **−0.2602**,
p90 **0.2725**, positive on 50.90%, finite on all 2,000. Centred, and ±0.26
at the deciles — a single reading of 0.2 is inside the iid distribution.

**NOT drift-invariant**, measured rather than assumed: the numerator is not
demeaned, so drift moves it. Walk vs the same walk at +0.004 of log drift a
bar: max \|diff\| **8.121379e-01**, Spearman **0.801318**, 0 of 1,480 bars
bit-equal, NaN masks equal. The neighbouring port `lean_hurst_100` *is*
drift-invariant (2.4e-15); do not carry that over to this column.

## Gate D — scale-free

1,500-bar frames, 1,480 fired bars each:

| frame | ×8 | ×64 | ×10 | ×3.7 |
|---|---|---|---|---|
| walk | **1480/1480 bit-identical** | **1480/1480** | max \|diff\| 1.588e-14 | 1.316e-14 |
| tick-rounded | **1480/1480** | **1480/1480** | 1.238e-14 | 8.715e-15 |
| nonlinear | **1480/1480** | **1480/1480** | 1.890e-14 | 1.360e-14 |

At the two non-default parameter settings, on the walk:

| setting | fired bars | ×8 | ×64 |
|---|---|---|---|
| `length=20, lag=9` | 1,480 | **1480/1480 bit-identical** | **1480/1480** |
| `length=60, lag=1` | 1,440 | **1440/1440** | **1440/1440** |

NaN masks are equal on all twelve default cells and on these four. ×8 is
bit-identical rather than
merely close because every input is a price *ratio*: `8a / 8b` is the same
double as `a / b`. The difference-of-logarithms spelling of the return is
**not** — at ×8 it is bit-equal on 821 of 1,499 bars where the ratio spelling
is bit-equal on all 1,499. That is why the module spells the return
`px / px.shift(1) - 1.0` and not `log(px) - log(px).shift(1)`; it is not a
simplification to undo.

`0 < fires < n` holds on all three frames (1,480 of 1,500), with 1,480
distinct values, so no constant column is passing this gate by accident.

## Gate E — attribution

**Measured on this port, 2026-11-12**, by issue-solver running
`../Backtesting/Backtesting/scripts/analysis/gate_e_overlap.py run --module
pandas_ta.statistics.ts_c3_20` at default parameters over the 89 frozen
ALTPORT-1 BIST frames (398,849 pooled bars) against the 687 comparators
(329 `compute_all` + 358 `ml_features` manifest `1d`), 1 of them degenerate.
Bands `r3-perframe-0.90`. Canary: AKBNK.IS, BIENY.IS, AGHOL.IS, SASA.IS
bit-equal. Recorded in `docs/gate_e_ledger.csv`
(`pandas_ta_src_sha1` 3defa70b1e34c01bb4cd6b960ec1bd1b61fee3b3, module sha1
2eaede6ac813c1952e239c1cca97eee2bb95c576).

| column | max \|ρ\| | against | set | n | per-frame max median | frames | frames with median ≥ 0.90 | verdict |
|---|---|---|---|---|---|---|---|---|
| `TS_C3_20_1` | **0.0806** | `kama_vs_SMA_20_pct` | manifest | 397,069 | **0.0940** | 89 | **0 (0.0%)** | **SHIP** |

Split by comparator set: against `compute_all` the max is **0.0428** vs
`skew` (n = 396,268); against the manifest **0.0806** vs
`kama_vs_SMA_20_pct` (n = 397,069). The per-frame worst comparator is the
same `kama_vs_SMA_20_pct`, at a median of 0.0940 — so pooled and per-frame
agree on both the comparator and the verdict, and 0.0940 is 0.806 below the
0.90 per-frame strike line and the pooled 0.0806 is 0.679 below the 0.76
DISCLOSE line. Nothing is struck, nothing is disclosed; the column ships as
wired, with no waiver needed.

This reproduces the issue's prototype numbers exactly: max \|ρ\| 0.0806 vs
`kama_vs_SMA_20_pct` at n = 397,069 (2026-10-24, run `screen_20261024`), the
same comparator and the same sample size, and the per-frame max median agrees
too — 0.09397 unrounded here, 0.0940 as the issue reports it. The
prototype is bit-equal to this port
on a 1,500-bar walk (Gate A, A2), which is why the agreement is expected
rather than a coincidence; it is now measured on the port.

**Nearest shipped columns on ONE 1,500-bar synthetic walk — NOT Gate E**
(12 shipped columns, one frame; Gate E is 687 comparators over 89 frozen BIST
frames):

| \|ρ\| | column | n |
|---|---|---|
| 0.0857 | `kpss_100` | 1401 |
| 0.0587 | `natr_14` | 1480 |
| 0.0504 | `lean_hurst_100` | 1401 |
| 0.0474 | `cusum_100` | 1400 |
| 0.0443 | `skew_30` | 1471 |
| 0.0352 | `rsi_14` | 1480 |
| 0.0326 | `tf_centroid_20` | 1480 |
| 0.0231 | `cfo_9` | 1480 |
| 0.0119 | `zscore_30` | 1471 |
| 0.0087 | `entropy_20` | 1462 |
| 0.0069 | `kurtosis_30` | 1471 |
| 0.0020 | `osap_retskew_21` | 1479 |

Nothing on this frame is within 0.8 of the 0.90 line, including the
window-shaped return statistics (`osap_retskew_21`, the 21-bar return skew,
is the lowest of the twelve at 0.0020 — a third-order *moment* of returns is
not the same quantity as a third-order *autocorrelation* of them). One
synthetic frame is not evidence about the 89.

## Gate F — suites

Porting session, in this worktree:

* `python -m pytest tests/test_ts_c3_20.py -q` → **98 passed** in 2.62 s.
* `python -m pytest -q` → **3 failed, 5668 passed, 83 skipped** in 117.99 s,
  the third failure being the Gate E row this port then owed.

Receipt session (2026-11-12), after the ledger row landed:

* `python -m pytest tests/test_ts_c3_20.py -q` → **98 passed** in 2.61 s.
* `python -m pytest tests/test_gate_e_ledger.py -q` → **1 failed, 802
  passed** in 3.40 s.
* `python -m pytest -q` → **3 failed, 5,675 passed, 83 skipped, 0 errors** of
  5,761 in 120.47 s (counts read from the run's own `--junitxml`; the
  terminal's progress counter says 5,740 collected items, and the difference
  of 21 is the `tests/config.py` module-level skips, which the XML counts as
  tests and the collector does not).

The three failures are the two `CLAUDE.md` "Known breaks"
(`test_altrepo_talib_csv.py::test_regenerating_reproduces_the_committed_rows`,
which needs the sibling `../AlternativeRepos` checkout and is deselected in
CI, and `test_pine_coverage_csv.py::test_audited_rows_carry_their_evidence`,
the `supertrend` citation into the untracked `docs/pine/`) plus
`test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`, which
now reports `['mtd_ret']` — **`ts_c3_20` is gone from that list**, and the one
name left is a row owed before this branch and not by it. CI into `dev` skips
that test under `GATE_E_PENDING_OK=1`.

The launcher runs both repos' suites in clean worktrees.

## Edge cases, measured

| case | behaviour |
|---|---|
| 20 bars | returns `None` (`verify_series` floor: a value needs `length + 1` closes) |
| exactly 21 bars | fires 1/21, at bar 20 |
| one NaN close at bar 200 | empties exactly 21 bars, 200..220; **0** bars before 200 move |
| one zero / negative / infinite / subnormal (1e-310) close | each empties exactly the same 21 bars, and nothing before 200 moves |
| a flat run planted at bar 200 of a 400-bar walk | 20 identical closes empty **0** bars; 21 empty **1** (bar 220); 25 empty **5** (bars 220..224) — 21 identical closes are enough to empty a bar and 20 are not (they are not the only way there: see the geometric ladder) |
| exactly flat frame | 0/300 fire |
| `length` = None / 0 / −5 / 3 / 0.5 / 2.9 | all fall back to `TS_C3_20_1` |
| `lag` = None / 0 / −1 | all fall back to `lag=1` |
| `lag` = 2 / 9 / 10 / 50 at `length=20` | `TS_C3_20_2` / `_9` / `_9` / `_9` — clamped to `(length−2)//2` = 9 so two triples fit |
| `length=4, lag=20` | `TS_C3_4_1`, 396 of 400 bars fire |
| `length=50.9` | identical to `length=50` (int truncation) |
| `length=10` vs `length=60` | distinct names, Spearman 0.2510 — different columns |
| `fillna=-1.0` | fills exactly the 20 warm-up bars |

## Five-point wiring

| # | file | what landed |
|---|---|---|
| 1 | `pandas_ta/statistics/ts_c3_20.py` | the indicator |
| 2 | `pandas_ta/statistics/__init__.py` | `from .ts_c3_20 import ts_c3_20` |
| 3 | `pandas_ta/__init__.py` → `Category["statistics"]` | `"ts_c3_20"` |
| 4 | `pandas_ta/core.py` | `df.ta.ts_c3_20(length=None, lag=None, offset=None)` |
| 5 | `tests/test_ts_c3_20.py` | 98 tests |

Plus the documentation touch points: `README.md` (the three counts, and the
statistics list), `docs/IndicatorDictionary.md` (regenerated by
`python docs/gen_indicator_dictionary.py`, which probes the live package and
tags `TS_C3_20_1` **SF** with a 20-bar warm-up),
`docs/MLCompanionContract.md` (the `SF` count) and
`tests/test_altport2_ports.py` (`CATEGORY_TOTAL`).
