# `c22_stretch_high` — measured and reverted

PandasTa issue **#135** (C22-STRETCH-HIGH), attempted 2026-11-22 on branch
`issue-135-c22-stretch-high`. **No `pandas_ta` module, test or wiring entry
was added.** The candidate is a restatement of an already-shipped column, so
nothing ships; this file is the receipt.

| | |
|---|---|
| candidate | catch22 (Lubba et al. 2019, *Data Min. Knowl. Disc.* 33:1821), feature `SB_BinaryStats_mean_longstretch1` — the hctsa operation `SB_BinaryStats(y, 'mean')` read-out `longstretch1`: binarize `y[i] > mean(y)` over a trailing window, report the longest run of consecutive 1s — proposed on the last 100 daily simple returns |
| harness | `docs/measure_c22_stretch_high.py` (sections A, Z, R by default; P and D are opt-in — P is the only part of this repository that runs the reference implementation, present in this worktree, and D diagnoses P's one gap) |
| Gate A | on six real-shaped frames, the candidate's own definition agrees with this fork's ALREADY SHIPPED `ts_strike_20(close, length=100)` on 0/8,400 windows disagreeing (§2) against an independent plain-Python oracle, and on 1,199/1,200 windows against the real GPL-3.0 `pycatch22` reference -- the one gap a float64/float32 last-bit residual in the mean of the Z-SCORED window, not a tie-rule convention difference (§4). On a SEVENTH, deliberately degenerate frame (a monotone one-tick ladder at a price level where the return span sits below `ts_strike_20`'s own `NOISE_FLOOR`), the unguarded oracle disagrees with the shipped column on 1,353/1,400 windows and the real reference disagrees with it on 193/200 sampled windows -- both exactly where the floor zeroes a rounding-noise window that the raw catch22 definition does not floor (§2) |
| Non-redundant | **FAILED by inspection and by measurement.** `ts_strike_20` (PandasTa issue #90, tsfresh's `longest_strike_above_mean`) is the SAME statistic, already parameterized by `length`; `ts_strike_20(close, length=100)` / `df.ta.ts_strike_20(length=100)` already gives this column on every non-degenerate window measured, differing from the raw catch22 definition only on rounding-noise windows that the module's own `NOISE_FLOOR` deliberately zeroes (§2) |
| Gate B/C/D | not attempted beyond §2/§3/§4 — no new module exists to test, and the formula is already covered by `ts_strike_20`'s own Gates (its receipt, `docs/TsStrike20Measured.md`) |
| Gate E | not applicable — nothing new ships |
| Gate F | required subset green on the unmodified tree — see §5 |
| outcome | **measured revert** per issue #135: "a measured revert closes this exactly as well as a ship" |

Every number below is `python docs/measure_c22_stretch_high.py`'s own output
on this machine (numpy 1.26.4, pandas 2.3.3, Python 3.11, `pycatch22`
present in this worktree).

---

## 0. What was tried, and why it stopped here

The issue's own text already flags the overlap: the catch22 feature tuple
for `stretch_high` names its related issue as **"#90 TS-STRIKE-20"**. That
issue ported `ts_strike_20` from tsfresh's `longest_strike_above_mean` —
"longest run of consecutive (r[i] > mean(r))" over a trailing window of
simple returns — and shipped it already parameterized by `length` (default
20, but callable at any window). `SB_BinaryStats_mean_longstretch1` reads,
per hctsa's own published operation description: binarize a series by
`y[i] > mean(y)` and report the longest run of consecutive 1s. These are
the same two sentences describing the same statistic under two different
library names (hctsa/catch22 and tsfresh), and `ts_strike_20`'s own module
explicitly documents this: "INVARIANT to any affine map of the returns,
not just to the price level" (a z-score, which catch22's own pipeline
applies before every feature, is one such affine map — see §3).

Rather than write a second module that would be, by construction, the same
~100 lines of code as `pandas_ta/statistics/ts_strike_20.py` (277 lines
total, docstring included) with `length=100` baked in and a different
output name, this session MEASURED the equivalence before deciding, per
this repository's own rule that a claim must come from a run, not from
reading two docstrings and assuming they match.

### 0a. Why this does not contradict the issue's own stage-2 number

`docs/issues/134-c22-stretch-high.md` already ran a fork-overlap check and
recorded: "Fork overlap (stage 2, not Gate E: scale-free `Category` outputs
at defaults, 12 frames): max \|ρ\| 0.1593 vs `equal_highs_lows:EQH_DIST_5_5`
... → not a restatement at the 0.90 line." That looks like it contradicts
this receipt's claim that the candidate restates `ts_strike_20` under a
new name — it does not, because it never tested this comparison. That
stage-2 sweep is
`docs/issues/screen/fork_overlap.py`'s `fork_columns()`, which calls every
`Category` indicator with `getattr(df.ta, name)()` — **no `length` kwarg**
(line 55) — so it measured `ts_strike_20` at its DEFAULT `length=20`, a
20-return window, never at the `length=100` this issue's candidate and
`ts_strike_20(close, length=100)` both use. `TS_STRIKE_20` and
`TS_STRIKE_100` are different columns (different windows read different
history) and are not expected to correlate highly — §2/§4 below are the
apples-to-apples comparison, matched at `length=100` on both sides, which
that stage-2 run never performed.

## 1. Fire counts and value spread at both lengths (§R)

Before anything else, a shape check: `ts_strike_20(close, length=100)`
against the same function at its own default `length=20`, on the six
real-shaped synthetic frames plus the seventh, deliberately degenerate
frame §2 uses:

| frame | `TS_STRIKE_100` fires | distinct values | `TS_STRIKE_20` fires |
|---|---|---|---|
| walk | 1,400 | 14 | 1,480 |
| tick-rounded | 1,400 | 7 | 1,480 |
| penny | 1,400 | 12 | 1,480 |
| ar1 | 1,400 | 12 | 1,480 |
| cosine | 1,400 | 3 | 1,480 |
| student-t | 1,400 | 10 | 1,480 |
| flat-tick | 1,400 | 1 | 1,480 |

(`TS_STRIKE_20` fires on more bars because its shorter window needs fewer
warm-up closes — 21 vs 101 — not because the two columns disagree on
anything; `TS_STRIKE_100` and `TS_STRIKE_20` are never compared to EACH
OTHER here, only each to the independent oracle. This is a fire-count and
value-spread table, not an overlap statistic — it reports no agreement
number between the two columns.) The real question — whether the catch22
DEFINITION, read independently of this fork's code, produces the
`TS_STRIKE_100` column — is answered in §2.

## 2. Gate A — the formula, read independently

`docs/measure_c22_stretch_high.py` §A implements `SB_BinaryStats(y,
'mean')`'s `longstretch1` from the published description, in plain Python
(`itertools.groupby` over a `y[i] > mean(y)` boolean list — no array
machinery shared with `ts_strike_20`, and no `NOISE_FLOOR`), and compares
it to this fork's SHIPPED `ts_strike_20(close, length=100)` on six
synthetic frames (a walk, a tick-rounded walk, a 2-lira/1-kurus penny
stock, an AR(1) path, a 20-bar cosine, and a Student-t(3) path — the same
six-frame set this fork's other catch22 ports use), 1,400 windows each:

| frame | n | disagree | worst \|diff\| |
|---|---|---|---|
| walk | 1,400 | 0 | 0.0 |
| tick-rounded | 1,400 | 0 | 0.0 |
| penny | 1,400 | 0 | 0.0 |
| ar1 | 1,400 | 0 | 0.0 |
| cosine | 1,400 | 0 | 0.0 |
| student-t | 1,400 | 0 | 0.0 |

**0 of 8,400 windows disagree on these six.** But these six frames all
have a return span many orders of magnitude above `ts_strike_20`'s own
`NOISE_FLOOR` (`pandas_ta/statistics/ts_strike_20.py:26`, `4096 * eps` =
9.09e-13): a window whose returns vary only at rounding level reads 0
under the shipped column regardless of what the unguarded formula reads,
and none of these six windows are that degenerate, so the floor NEVER
fires in them and the "0 disagree" table is silent on it by construction.
A SEVENTH frame, `flat-tick` — a monotone one-tick-per-bar ladder at
price 1e6 with a 0.001 tick, the same price/tick pair
`docs/TsStrike20Measured.md` already measures as floor-triggering
(mathematically constant returns, return span 2.2e-16, below the floor) —
makes the divergence happen on purpose:

| frame | n | disagree | worst \|diff\| |
|---|---|---|---|
| flat-tick | 1,400 | 1,353 | 99.0 |

**1,353 of 1,400 windows disagree, by up to 99.** The unguarded oracle
reads a run length off float64 rounding noise (the formula has no floor
to stop it); the shipped column reads the constant **0** its own
`NOISE_FLOOR` reserves for exactly this case. This is NOT a formula gap —
it is `ts_strike_20`'s own documented, deliberate choice
(`docs/TsStrike20Measured.md`, *The rounding-noise floor*: "a window whose
returns vary only at rounding level has no strike to read ... reported as
0"). Restated precisely: the candidate's raw definition and the shipped
column are the SAME statistic on every non-degenerate window measured
(0/8,400), and differ ONLY on windows degenerate enough to trip the
floor, where the shipped column's choice to read 0 rather than rounding
noise is the reason to revert rather than against it — porting the
unguarded definition under a new name would ship a column that reads
float64 noise on flat-close or limit-locked BIST bars.

## 3. Z-scoring (catch22's own preprocessing) is inert here, measured not assumed

catch22's published pipeline z-scores the input series before every one of
its 22 features. `ts_strike_20` does not z-score. §Z checks this cannot
matter for THIS feature: a run of `y[i] > mean(y)` is unchanged by any
positive affine map `y -> k*y + d` (k > 0), because `k*y[i] + d >
k*mean(y) + d` iff `y[i] > mean(y)`. Measured on a 100-sample synthetic
window at four (k, d) pairs including a z-score itself:

| k | d | raw | affine (k·y+d) | z-scored | match |
|---|---|---|---|---|---|
| 1.0 | 0.0 | 6 | 6 | 6 | True |
| 3.0 | 0.002 | 6 | 6 | 6 | True |
| 0.37 | -0.001 | 6 | 6 | 6 | True |
| 8.0 | 0.0 | 6 | 6 | 6 | True |

All four read **6**, including after a genuine z-score (`(y - mean) /
std(ddof=1)`) — this holds in EXACT arithmetic, where `k*y[i] + d >
k*mean(y) + d` iff `y[i] > mean(y)` for `k > 0`, and this measurement
confirms it is not merely a hand-derived identity. It is inert EXCEPT at
an exact tie with the window mean: a sample sitting exactly on the raw
mean becomes exactly 0 in z-space, and the mean of the z-scored series is
then a fresh floating-point summation whose last-bit residual (generically
nonzero) decides whether that sample reads "above" its OWN z-scored
mean — the strict `>` rule is unchanged, but the comparison target has
moved by a rounding error no longer tied to the raw window. §4 hits
exactly this case.

## 4. The GPL-3.0 reference as a black box (opt-in)

`python docs/measure_c22_stretch_high.py P`. Not run by a bare invocation;
the reference package is imported only inside this section.

Every 7th window of the same six 1,500-bar frames (200 windows per frame,
1,200 total) PLUS the seventh, `flat-tick` frame §2 adds (200 more
windows, 1,400 total), `pycatch22.catch22_all(w, short_names=True)`'s own
`stretch_high` output (the package's own short name for this feature)
against `ts_strike_20(close, length=100)`:

| frames | disagreements (> 1e-9) | total windows |
|---|---|---|
| six real-shaped frames | 1 | 1,200 |
| `flat-tick` (degenerate, §2) | 193 | 200 |

**On the six real-shaped frames, 1,199 of 1,200 windows agree exactly** —
unchanged by adding `flat-tick`, since it is a separate frame. The one gap
(`cosine`, t=653: reference 11.0, `ts_strike_20(100)` 10.0) was diagnosed
in §D of the harness. The first hypothesis tried (a last-bit rounding
difference in the RAW window's mean) does NOT hold up: the window's own
mean is numerically 0 under both `numpy.float64.mean` and a full-precision
`math.fsum` average, the two methods classify every sample identically (0
flips), and even recomputing the RAW window's mean in `float32` still
gives mean 0 and the same run of 10 — none of these reproduce the
reference's 11. **On `flat-tick`, 193 of 200 sampled windows disagree** —
this is the SAME floor divergence §2 measures directly against the
unguarded oracle, now confirmed against the real GPL-3.0 reference too
(e.g. t=100: reference 2.0, `ts_strike_20(100)` 0.0): the reference has no
`NOISE_FLOOR`, so it reads whatever float64 rounding noise the window
happens to contain, while the shipped column reads the 0 its floor
reserves for a degenerate window. This is the deliberate divergence §2
explains, not a new finding about the `cosine` case.

What reproduces the `cosine` t=653 gap: §D's diagnosis in §Z already
established that z-scoring is inert EXCEPT at an exact tie with the raw
mean, where the mean of the Z-SCORED series (a fresh floating-point sum)
decides the comparison by its own last-bit residual — and this window has
**4 of its 100 samples sitting EXACTLY at the raw mean** (0.0, printed by
the harness), so it is exactly that case. Z-scoring the window the way the
reference does (`z = (w - w.mean()) / w.std(ddof=0)`) and recomputing the
mean of `z`: **negative** in both float64 (`-1.110e-18`) and float32
(`-1.788e-09`), and the longest strict `>` run under either z-scored mean
is **11** — an EXACT match to the reference, obtained with the SAME
strict `>` rule `ts_strike_20` uses, not an inclusive `>=`. An inclusive
tie rule on the RAW mean also gives 11 on this window, but does not
discriminate between the two explanations; the z-scored-mean residual is
the one that was actually tested against the window the reference itself
would compute, and it reproduces 11 under the fork's own comparison
operator. The one disagreement is therefore consistent with a
**floating-point residual in the mean of the z-scored window** — the
SAME mechanism `docs/C22Mode5Measured.md` §P infers for that reference's
own gap — not a tie-rule convention difference: hctsa's rule and
`ts_strike_20`'s rule are the same strict `>`, and they land on different
integers here only because catch22's z-scoring pipeline moves an exact
tie by a last-bit rounding error before the comparison happens. This is
demonstrated for THIS window only, not asserted as hctsa's general rule,
since only one window was diagnosed this deeply. A sample sitting exactly
on the mean reading as NOT extending a run is `ts_strike_20`'s own
documented, deliberate choice (comment at
`pandas_ta/statistics/ts_strike_20.py:68-69`: "a sample sitting exactly ON
the mean does not extend a strike"; its receipt, `docs/TsStrike20Measured.md`
line 166-167, states the same decision as "**Strict `>`**, which is what the
issue's line (\"above their mean\") and the prototype's `W > W.mean(1,
keepdims=True)` give" — the issue's own screen prototype and tsfresh's
convention, same as `ts_strike_20`'s). How often does an exact raw-mean
tie arise in practice? Measured, not assumed: counting samples exactly
equal to their own window's mean across the same 1,400 sampled windows §P
now evaluates — **0** such ties on walk, tick-rounded, penny, ar1 and
student-t (1,000 windows total), **20** ties on `cosine` alone (its 200
windows), and **700** ties on `flat-tick` alone (its 200 windows) —
confirming the distinction is reachable only on a frame engineered to be
exactly symmetric or degenerate, like `cosine` or `flat-tick`, not on
anything resembling real, continuously-valued BIST returns. On the six
real-shaped frames, a 99.92% exact match against the live GPL-3.0
reference, with the sole miss explained by a floating-point residual in
the mean of the z-scored window this fork's existing `ts_strike_20`'s
strict-`>` convention shares with the reference — not a convention the
fork got wrong — confirms the candidate IS hctsa's
`SB_BinaryStats_mean_longstretch1`, and that it is the same column as
`ts_strike_20(close, length=100)` on every window measured that is not
degenerate enough to trip the shipped column's own `NOISE_FLOOR` (§2).

## 5. Gate F — suites (unmodified tree)

| run | result |
|---|---|
| `python -m pytest -q tests/test_readme_counts.py tests/test_altport2_ports.py tests/test_wiring_accessors.py tests/test_ml_companions.py tests/test_gate_e_ledger.py tests/test_pine_coverage_csv.py tests/test_prose_counts_match_the_csvs.py tests/test_ts_strike_20.py` | **1458 passed, 7 skipped** |

No `Category`, `core.py`, `__init__.py` or README entry changed, so
`test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
passes outright here (nothing new needs a row) — unlike a shipped port,
where that test is expected to fail until the launcher's Gate E run.

The launcher's own base-vs-HEAD comparison (`gate-1/tests.md`) records one
failing PandasTa test at BOTH base `1d8f4618c72a` and HEAD `d786d7effd37`
(13,962 passed, 1 failed, 93 skipped at each — 0 regressions):
`tests/test_altrepo_talib_csv.py::test_regenerating_reproduces_the_committed_rows`,
which needs the sibling `../AlternativeRepos` checkout
(`CLAUDE.md`'s CI section names it as the one test CI deselects for the
same reason). That node is outside the eight files the subset run above
covers, so it is not a regression from this change and the subset run
above is clean on everything it touches.

Whole suites: run by issue-solver in clean worktrees (see the PR body).

## 6. Conclusion

`SB_BinaryStats_mean_longstretch1` at 100 returns is, by measurement, the
same statistic this fork already ships as `ts_strike_20` at `length=100` —
already reachable via `ta.ts_strike_20(close, length=100)`,
`df.ta.ts_strike_20(length=100)`, or `df.ta.strategy()` with that
parameter — on every window measured that is not degenerate enough to
trip the shipped column's own `NOISE_FLOOR` (§2); on a window that is,
the shipped column deliberately reads 0 rather than the raw formula's
rounding noise, a difference documented in `docs/TsStrike20Measured.md`
and argued there to be the reason to revert rather than against it, since
porting the unguarded catch22 definition under a new name would ship a
column that reads float64 noise on flat-close or limit-locked BIST bars.
Shipping a second module would, on every non-degenerate bar, restate the
same signal under a second column name, which `CLAUDE.md`'s ML feature
contract rules out ("A column that restates a shipped column double-weights
one signal in the miner"). Per issue #135's own closing rule, this measured
revert closes the issue exactly as well as a ship would have.
