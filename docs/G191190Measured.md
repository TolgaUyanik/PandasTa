# g191_190 — measured (issue #59)

> **Status: Gates A-D cleared. Gate E: pending, run by issue-solver after**
> **this session. Gate F: this repo's suite green modulo pre-existing/**
> **expected failures (below).**

Above/below geometric-mean return dispersion (20): Guotai Junan's (2017,
"GTJA191", internal quant report, read via the HKUDS/Vibe-Trading copy,
MIT) alpha `#190`, per issue #59's own instruction. Module
`pandas_ta/statistics/g191_190.py`, column `G191_190_20`. Tests:
`tests/test_g191_190.py` (16, all passing). Numbers below:
`python docs/measure_g191_190.py`. Environment: this worktree's pinned
pandas/numpy. Measured 2026-11-09.

## Gate A: derivation from the published formula, not the prototype

Issue #59 states GTJA191 alpha `#190`:

    LOG((COUNT(r>g,20)-1)*SUMIF((r-g)^2, r<g, 20) / (COUNT(r<g,20)*SUMIF((r-g)^2, r>g, 20))),
    g = (C/C19)^(1/20)-1

**What this session could NOT do, disclosed up front:** `docs/pine/` and
web access are both unavailable in this worktree, so the issue's own named
copy -- HKUDS/Vibe-Trading (MIT) -- was never read. Everything below is
derived from the issue's own stated formula string plus its own
prototype's unambiguous operator definitions, per the issue's own rule
("Gate A starts from the source formula, not the prototype").

`r` is the ordinary one-bar simple return (`C/DELAY(C,1)-1`) and `g` is a
20-bar GEOMETRIC-MEAN daily return: the issue's own literal `(C/C19)^(1/20)
-1` -- a 19-bar backward ratio (20 closes wide) raised to the `1/20` power.
The `19`/`20` asymmetry is the issue's own formula, not a typo this port
silently "corrects". `up = r>g` / `dn = r<g` split each bar into "beat the
window's own geometric mean" / "fell short of it"; `SUMIF(e2, cond, 20)`
sums `e2 = (r-g)^2` only over the bars in the trailing 20-bar window where
`cond` holds. The numerator is "how many above-average days there were
(less one) times how much the below-average days dispersed"; the
denominator mirrors it. `DELAY(X,n) = X.shift(n)`, `COUNT(cond,n) =
cond.astype(float).rolling(n).sum()` -- each read directly off the issue's
own named prototype's unambiguous module docstring
(`docs/issues/screen/ind_screen.py:45,49,54,108`), the same operator
family `g191_098` (issue #58) and `g191_144` (issue #57) relied on.
`SUMIF` has no single named prototype operator; it is built, as the
prototype itself builds it, from `SUM` (`ind_screen.py:49`) applied to a
series zeroed wherever the condition is false.

The issue's own prototype (`docs/issues/screen/ind_screen.py:570-579`,
candidate `g191_190`) spells out the identical formula directly:

    r = ret(c)                                    # ret(c) = c/c.shift(1)-1, ind_screen.py:108
    g = (c / delay(c, 19)) ** (1 / 20) - 1
    up, dn = r > g, r < g
    e2 = (r - g) ** 2
    num = (count(up, 20) - 1) * tsum(e2.where(dn, 0.0), 20)
    den = count(dn, 20) * tsum(e2.where(up, 0.0), 20)
    return _fin(np.log(sdiv(num, den).where(lambda x: x > 0)))

No disclosed interpretation choice was needed for the formula itself -- the
issue's own string and the prototype agree exactly, including the `19`/`20`
asymmetry. One disclosed guard WAS made, matching the prototype's own:
`LOG`'s argument is undefined for `<= 0`; the prototype itself masks this
with `.where(lambda x: x > 0)` before `np.log` (`ind_screen.py:579`). This
port applies the SAME guard, down to the same masking point -- not a
generic inf-safety net bolted on afterward.

### Warm-up: a disclosed necessary condition

`r[t]` needs `C[t-1]`, valid from `t>=1`. `g[t]` needs `C[t-19]`, valid
from `t>=19` -- the binding constraint. `up`/`dn`/`e2` are therefore only
MEANINGFUL from `t>=19` (a `NaN` `g[t]` makes a `>`/`<` comparison plain
`False` in pandas, not `NaN` -- a trap this port avoids by masking `up`/
`dn` to `NaN` wherever `g` itself is `NaN`, then rolling `COUNT`/`SUM` with
`min_periods=length` so a window touching even one pre-warm-up bar comes
out `NaN`). Measured, not theoretical: on the 1,500-bar synthetic frame,
the NAIVE (unmasked) reading produces a non-NaN -- and wrong -- value at
**16 of the 19 bars** in `[19,37]`, where this port's masked version is
`NaN` at all 19 by construction (`python docs/measure_g191_190.py`).
`COUNT`/`SUM` over a trailing 20-bar window ending at `t` need
every bar in `[t-19,t]` to be meaningful, i.e. `t>=38`. So the whole column
is `NaN` for strictly fewer than 39 bars of history; `min_length =
2*length-1 = 39` at defaults, enforced by `verify_series`. Measured: on
the 1,500-bar synthetic frame, first valid bar is exactly index 38 (the
structural boundary, no extension beyond it observed).

## Gates

| Gate | Result | Evidence |
|---|---|---|
| A Correctness | derived directly from the issue's own stated formula, matching the issue's own prototype line-for-line, including the `19`/`20` lookback/exponent asymmetry | Hand-derived example at `length=4` (`tests/test_g191_190.py::test_hand_derived_small_example`), tracing `r`, `g`, `up`, `dn`, `e2`, `num`, `den` independently: `result[6..9] = [-1.9614115435729524, -1.7372163903125624, 0.3923198260950293, 0.14500033504486046]`, bars 0-5 NaN (the 6-bar warm-up at `length=4`), matching the module's float64 output exactly (`python docs/measure_g191_190.py`). Matches an independent per-bar loop (plain python, summing `up`/`dn`/`e2` bar-by-bar over the trailing window, not the module's own vectorised `.rolling()` calls) at the shipped default (`length=20`), 3 spot-checked bars (300, 600, 899) on a 900-bar synthetic frame, relative difference 6.4e-12 / 1.4e-14 / 8.7e-14 (float64 rounding between the two independent implementations, not a disagreement) |
| B Causality | pass | Future-perturbation sweep (close series rewritten from `j` onward, another synthetic series), 34 offsets past the 39-bar warm-up: real module **0 of 34** leaks (`python docs/measure_g191_190.py`). Two independent mutants (`importlib` source read, `exec`'d in memory, each shown live-different from the real module): shifting the final write index `length=20` bars into the future, and replacing `g`'s backward `DELAY(close,19)` with a FORWARD shift (`close.shift(-19)`) -- both caught at **34 of 34** |
| C Reachability | synthetic only (real-data reachability comes from Gate E's pooled count, not re-derived here) | 1,500-bar synthetic close series (seed 11, see `docs/measure_g191_190.py:_close`), shipped default: **1,462 of 1,500** bars non-NaN (97.47%), first valid at bar 38 (exactly the structural warm-up boundary). **1,462 distinct values** observed (every fired bar distinct -- not a constant column), range `[-1.966201, 2.336908]`, median `-0.055001`. The remaining 38 bars are the warm-up, not the `LOG` domain guard -- on this synthetic frame the ratio inside `LOG` is positive at every warmed-up bar |
| D Scale-free | pass | `r` and `g` are both return RATIOS, each exactly invariant under a positive price rescale by any `k>0` (the `k` cancels inside the ratio before any other arithmetic runs) -- not a special case of power-of-two multiplication. Every downstream term is built only from `r` and `g`, so the whole column is scale-free BY CONSTRUCTION. Measured on the 1,500-bar series: PRICE x8/x64 **bit-identical, 0.0 max\|diff\|** (power-of-two multiplication is exact in IEEE754, so the already-exact algebraic invariance carries through exactly in float64); PRICE x10/x3.7: max\|diff\| **2.80e-14 / 2.15e-14** -- float64 rounding from the scalar multiply itself, far under the test's 1e-9 tolerance, not a scale dependency. `0 < 1,462 fires < 1,500` and `1,462 > 1` distinct values rule out a constant column |
| E Attribution | **pending** | Run by the launcher (`gate_e_overlap.py run --module pandas_ta.statistics.g191_190`) after this session. This file will be updated with the measured numbers once that run lands |
| F Suites | this repo only; parent repo (`Backtesting`) is run by the launcher in clean worktrees | `python -m pytest -q` (this session): see run below |

## Wiring

`Category` **293 -> 294** (`statistics` **25 -> 26**); `df.ta.<name>()`
accessor count **301 -> 302**. Touch points:
`pandas_ta/statistics/g191_190.py` (module),
`pandas_ta/statistics/__init__.py` (export), `pandas_ta/__init__.py` ->
`Category["statistics"]` (discovery), `pandas_ta/core.py` ->
`AnalysisIndicators.g191_190` (accessor), `tests/test_g191_190.py`
(tests). `README.md`'s headline and `statistics (26)` row, and
`docs/IndicatorDictionary.md` (regenerated), both updated and checked by
`tests/test_readme_counts.py`. `docs/MLCompanionContract.md`'s running tag
count updated **638 -> 639 / 281 -> 282 `SF`** (`G191_190_20` probes
cleanly at the dictionary's 600-bar synthetic frame and takes many
distinct values, so the generator tags it `SF`); `tests/test_ml_companions.py`
re-derives these from the live dictionary and passes.
`tests/test_altport2_ports.py`'s `CATEGORY_TOTAL` updated to match
(293 -> 294); no `CATEGORY_BUCKETS` entry needed (that dict only tracks
`trend`/`volatility`/`volume`, not `statistics`).

Gate E ledger row: NOT yet recorded -- owed, per the rules governing this
session (Gate E is run by the launcher after this session; a later receipt
session records `docs/gate_e_ledger.csv` once that run lands).
`tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
is expected to fail on `g191_190` until then (CLAUDE.md, "Owed, not
failed").

## Suite run (this session)

`python -m pytest -q`, full suite, default collection order: **3 failed,
4688 passed, 83 skipped**. `g191_190`'s own tests (`tests/test_g191_190.py`):
**16 passed**. The 3 failures are pre-existing / expected, all unrelated to
this port's correctness (CLAUDE.md "Known breaks"):
`tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
(fails with `no Gate E ledger row for ['g191_190', 'mtd_ret']` --
`g191_190` is this port's own owed row, by design per this session's
rules; `mtd_ret` pre-dates this session, per `docs/G191026Measured.md`'s
identical note), `tests/test_altrepo_talib_csv.py::test_regenerating_reproduces_the_committed_rows`
(needs the sibling `../AlternativeRepos` checkout, absent in this
worktree) and `tests/test_pine_coverage_csv.py::test_audited_rows_carry_their_evidence`
(untracked `docs/pine/` corpus, CLAUDE.md "Known breaks"). No other test
regresses.
