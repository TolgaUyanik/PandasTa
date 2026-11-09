# g191_093 — measured (issue #62)

> **Status: Gates A-D cleared, F (this repo) green. Gate E pending.**

20-day sum of open-down moves (DBM): Guotai Junan's (2017, "GTJA191",
internal quant report, read via the HKUDS/Vibe-Trading copy, MIT) alpha
`#93`, per issue #62's own instruction. Module
`pandas_ta/momentum/g191_093.py`, column `G191_093_20`. Tests:
`tests/test_g191_093.py` (16, all passing). Numbers below:
`python docs/measure_g191_093.py`. Environment: this worktree's pinned
pandas/numpy. Measured 2026-11-09.

## Gate A: derivation from the published formula, not the prototype

Issue #62 states GTJA191 alpha `#93`:

    SUM(O>=O1 ? 0 : MAX(O-L, O-O1), 20)

with the issue's own stated scale-free form: "`/close`".

**What this session could NOT do, disclosed up front:** `docs/pine/` and
web access are both unavailable in this worktree, so the issue's own
named copy -- HKUDS/Vibe-Trading (MIT) -- was never read. Everything
below is derived from the issue's own stated formula string plus its own
scale-free instruction, per the issue's own rule ("Gate A starts from the
source formula, not the prototype"), then cross-checked against the
issue's own prototype (`docs/issues/screen/ind_screen.py:438-442`):

    @cand("g191_093", "20-day sum of open-down moves (DBM)", G,
          "#93: SUM(O>=O1 ? 0 : MAX(O-L, O-O1), 20)", "/close")
    def _(o, h, l, c, v):
        o1 = delay(o, 1)
        return tsum(pd.Series(np.where(o >= o1, 0.0, np.maximum(o - l, o - o1)),
                               index=c.index).where(o1.notna()), 20) / c

No disclosed interpretation choice was needed -- the issue's own string
and the prototype agree exactly, including the window length and the
scale-free conversion. Operators, each read directly off the prototype's
own module source (`ind_screen.py:45` DELAY, `ind_screen.py:49` SUM):
`DELAY(X,n) = X.shift(n)`, `SUM(X,n) = X.rolling(n).sum()`, matching the
convention every other `g191_*` port in this fork already relies on.
`MAX(a,b)` is read as the POINTWISE `np.maximum`, not the rolling-window
`TSMAX` the same registry also defines -- the issue's own formula names
two plain series arguments, not a series and a window length.

### A measured structural fact: `MAX(O-L, O-O1)` always collapses to `O-L`

`mad.py`-style "two formulas with the same informal name" checks do not
apply here (no shipped indicator shares this name), but a genuinely
non-obvious structural property of the formula itself was found while
building the causality mutant and is worth recording: under ordinary
OHLC consistency (`low <= open` at every bar, true by construction of
any real or synthetic OHLC frame), the `O-O1` term inside the branch's
`MAX` can NEVER win. The branch only runs when `O < O1`; `O-O1` would
have to exceed `O-L` for it to be selected, which requires `O1 < L`; but
`L <= O < O1` already holds in this branch, so `O1 < L <= O < O1` is a
contradiction. Measured, not just argued: on a 1,500-bar synthetic OHLC
frame (`python docs/measure_g191_093.py`), **746 of 746** down-branch
bars select `O-L`, zero select `O-O1`. This means the `DELAY` in the
formula changes the OUTPUT only through the `open >= O1` branch GATE
(which days are 0 vs. `O-L`), never through the magnitude on a down day
-- a fact that drove the Gate B mutant design below.

### Warm-up: a disclosed necessary condition

`O1 = DELAY(O,1)` is undefined at bar 0 (no prior bar). `contribution`
(the per-bar ternary output) is therefore only meaningful from `t >= 1`,
masked to `NaN` at bar 0 rather than silently read as "no down move".
`DBM`, a trailing `length`-bar sum, needs `length` CONSECUTIVE
meaningful `contribution` values ending at `t`: true warm-up
`min_length = length + 1` -- **21** at the shipped default
(`length=20`), enforced by `verify_series`.

## Gates

| Gate | Result | Evidence |
|---|---|---|
| A Correctness | derived directly from the issue's own stated formula plus its own scale-free conversion, matching the issue's own prototype line-for-line | A hand-derived 6-bar example (`length=3`) matching the module to float precision (`6/103`, `4/104`, `5/105` at bars 3-5), plus an independent per-bar computation (plain numpy array slicing, not the module's own `.rolling()` calls) spot-checked at the shipped default on a 900-bar frame: `t=300 module=0.04060793898637337 independent=0.04060793898637337`, `t=600` and `t=899` identical to float precision (`python docs/measure_g191_093.py`) |
| B Causality | pass | Future-perturbation sweep (OHLC series jointly rewritten from `j` onward), 34 offsets past the 21-bar warm-up: real module **0 of 34** leaks. Write-shift mutant (final rolling-sum write index `length=20` bars into the future): caught **34 of 34**. Forward-DELAY mutant (`open_.shift(1)` to `open_.shift(-1)`) needed a DEDICATED deterministic construction rather than the same random sweep: because `MAX` always collapses to `O-L` (above), the DELAY only ever flips a binary branch gate, and the random sweep's own coincidental gate agreement hid the leak at **13 of 34** offsets (caught only 21 of 34) -- measured, which is why the committed test instead builds a strictly-increasing `open` series and perturbs only the suffix to force a deterministic gate flip at one bar, where the mutant visibly leaks (`base=0.03` vs. `pert=0.02`) and the real module does not (`base=0.0` vs. `pert=0.0`) |
| C Reachability | synthetic only (real-data reachability comes from Gate E's pooled count, not re-derived here) | 1,500-bar synthetic OHLC series (seed 11, see `docs/measure_g191_093.py:_ohlc`), shipped default: **1,480 of 1,500** bars non-NaN (98.67%), first valid at bar 20 (exactly the structural warm-up boundary, `min_length - 1`). **1,480 distinct values**. Range `[0.004019, 0.110608]`, median `0.038238` |
| D Scale-free | pass | `O1` is linear in `open` (a shift carries no arithmetic); the `open >= O1` comparison is unchanged by a positive rescale; `O-L` and `O-O1` each scale linearly, so their `MAX` scales by the same positive factor; `DBM`, a plain sum, scales linearly; dividing by `close` (scaled by the same factor) cancels it exactly. Measured on the 1,500-bar series: PRICE x8/x64 **bit-identical, 0.0 max\|diff\|** (power-of-two multiplication is exact in IEEE754); x10/x3.7 **within float64 rounding tolerance** (max\|diff\| 7.29e-16 / 6.59e-16). `0 < 1480 fires < 1500` and `1480 > 1` distinct values rule out a constant column |
| E Attribution | pending, run by issue-solver after this session | -- |
| F Suites | this repo only; parent repo (`Backtesting`) is run by the launcher in clean worktrees | `python -m pytest -q` (this session): see run below |

## Wiring

`Category` **296 -> 297** (`momentum` **72 -> 73**); `df.ta.<name>()`
accessor count **304 -> 305**. Touch points:
`pandas_ta/momentum/g191_093.py` (module),
`pandas_ta/momentum/__init__.py` (export), `pandas_ta/__init__.py` ->
`Category["momentum"]` (discovery), `pandas_ta/core.py` ->
`AnalysisIndicators.g191_093` (accessor), `tests/test_g191_093.py`
(tests). `README.md`'s headline and `momentum (73)` row, and
`docs/IndicatorDictionary.md` (regenerated, `298 -> 299` probed), both
updated and checked by `tests/test_readme_counts.py`.
`docs/MLCompanionContract.md`'s running tag count updated **641 -> 642 /
284 -> 285 `SF`** (`G191_093_20` probes cleanly at the dictionary's
600-bar synthetic frame and takes many distinct values, so the generator
tags it `SF`), checked by
`tests/test_ml_companions.py::test_the_contract_quotes_the_dictionarys_actual_ml_form_counts`.
`tests/test_altport2_ports.py`'s `CATEGORY_TOTAL` updated to match
(296 -> 297); no `CATEGORY_BUCKETS` entry needed (that dict only tracks
`trend`/`volatility`/`volume`, not `momentum`).

Gate E owed; run by the launcher (`gate_e_overlap.py`, Backtesting #107)
after this session, then recorded in `docs/gate_e_ledger.csv` by a later
receipt session.

## Suite run (this repo, this session)

`python -m pytest -q`, full suite, default collection order: **3 failed,
4771 passed, 83 skipped**. `g191_093`'s own tests (`tests/test_g191_093.py`):
**16 passed**. Pre-existing / expected failures, all unrelated to this
port's correctness (CLAUDE.md "Known breaks" plus this port's own owed
Gate E row):
`tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
(owed for `['g191_093', 'mtd_ret']` -- `g191_093`'s row is owed by design
per this session's override rules; `mtd_ret` pre-dates this session),
`tests/test_altrepo_talib_csv.py::test_regenerating_reproduces_the_committed_rows`
(needs the sibling `../AlternativeRepos` checkout, absent in this
worktree) and `tests/test_pine_coverage_csv.py::test_audited_rows_carry_their_evidence`
(untracked `docs/pine/` corpus). No other test regresses.
