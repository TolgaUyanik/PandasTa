# g191_144 — measured (issue #57)

> **Status: Gates A-D cleared (this session). Gate E pending, run by**
> **issue-solver after this session. Gate F: this repo's suite green**
> **modulo pre-existing/expected failures (below).**

Down-day illiquidity share: Guotai Junan's (2017, "GTJA191", internal quant
report, read via the HKUDS/Vibe-Trading copy, MIT) alpha `#144`, per issue
#57's own instruction. Module `pandas_ta/volume/g191_144.py`, column
`G191_144_20`. Tests: `tests/test_g191_144.py` (23, all passing). Numbers
below: `python docs/measure_g191_144.py`. Environment: this worktree's
pinned pandas/numpy. Measured 2026-11-09.

## Gate A: derivation from the published formula, not the prototype

Issue #57 states GTJA191 alpha `#144`:

    SUMIF(|C/C1-1|/AMOUNT, C<C1, 20) / COUNT(C<C1, 20)

with the issue's own parenthetical: "divided by the all-day mean of
|r|/AMOUNT over 20 bars; AMOUNT -> TP*V".

**What this session could NOT do, disclosed up front:** `docs/pine/` and web
access are both unavailable in this worktree, so the issue's own named copy
-- HKUDS/Vibe-Trading (MIT) -- was never read. Everything below is derived
from the issue's own stated formula string plus its own parenthetical
instruction, per the issue's own rule ("Gate A starts from the source
formula, not the prototype").

`C1` is GTJA notation for `DELAY(C,1)`, the previous close -- confirmed by
every other alpha in the issue's own screening registry that defines `C1`
the same way (e.g. `#53: COUNT(C>C1,12)/12*100`). `AMOUNT` is a daily
traded-VALUE field with no equivalent in daily OHLCV, so the issue's own
parenthetical states the proxy: `AMOUNT = TP*V` (typical price times
volume). The raw formula's left side is the average illiquidity
(`x = |C/C1-1| / AMOUNT`) on DOWN days only, over the trailing 20 bars; this
carries units of `1 / (price * volume)` and is NOT scale-free on its own.
The issue's own parenthetical states the conversion applied before Gate E
ever ran: divide by `MEAN(x, 20)` (the all-day average, same units), which
cancels them in the ratio:

    G191_144 = [SUMIF(x, C<C1, 20) / COUNT(C<C1, 20)] / MEAN(x, 20)
    where x = |C/C1 - 1| / (TP * V),  TP = (H+L+C)/3

matching the issue's own prototype (`docs/issues/screen/ind_screen.py:485`):
`sdiv(sdiv(tsum(x.where(dn, 0.0), 20), count(dn, 20)), mean(x, 20))` with
`x = sdiv(ret(c).abs(), tp(h, l, c) * v)`, `dn = c < delay(c, 1)`. No
disclosed interpretation choice was needed for the formula itself -- the
issue's own parenthetical states the conversion directly. One disclosed
decision WAS needed for the warm-up (see "Warm-up" below), which the
screening prototype does not address.

### Warm-up: a decision this port made that the screening prototype did not

Bar 0 has no `C1` (`DELAY(C,1)` is undefined there), so whether bar 0 is a
"down day" is itself undefined, not merely false. Coding
`close < close.shift(1)` naively reads `False` there (pandas/numpy compare
`NaN` as `False`, not as `NaN`), which would silently treat an undefined bar
as a known "not a down day" and let a contaminated 0 enter the very first
rolling window. This port masks bar 0 out of BOTH `SUMIF` and `COUNT`
explicitly, so the structural minimum for a valid output is `length + 1`
bars of input (`min_length`, enforced by `verify_series`) -- but this is
NECESSARY, not SUFFICIENT: if that first `length`-bar window happens to
contain zero down days, `down_avg` is `0/0` and the output stays NaN longer.
Measured: at `length=3` on the 6-bar hand-derived frame below, this extends
the warm-up by one bar (first valid at bar 4, not bar 3); at the shipped
default (`length=20`) on the 1500-bar synthetic frame, it does not (first
valid exactly at bar 20).

## Gates

| Gate | Result | Evidence |
|---|---|---|
| A Correctness | derived directly from the issue's own stated formula plus its own parenthetical conversion, matching the issue's own prototype line-for-line | 6-bar hand-derived example at `length=3` (`tests/test_g191_144.py::test_hand_derived_six_bars`), high/low built as `close +- 1` so the typical price collapses to `close` exactly: `result[4..5] = [1.1121281464530892, 1.4159877800407332]`, bars 0-3 NaN (bar 3's window has zero down days -- `down_avg` is `0/0`), matching the module's float64 output exactly (`python docs/measure_g191_144.py`). Matches an independent per-bar loop (plain numpy array slicing, not the module's own `.rolling()` calls) at the shipped default (`length=20`), 3 spot-checked bars (300, 600, 899) on a 900-bar synthetic frame, relative difference 0.0 / 1.202e-16 / 1.805e-16 (float64 rounding, not a disagreement) |
| B Causality | pass | Future-perturbation sweep (OHLCV series rewritten from `j` onward, another synthetic frame), 34 offsets past the 21-bar warm-up: real module **0 of 34** leaks (`python docs/measure_g191_144.py`). Two independent mutants (`importlib` source read, `exec`'d in memory), each shown live (differs from the real module) then caught at **34 of 34**: shifting the final write index `length=20` bars into the future, and flipping the backward `DELAY` (`close.shift(1)`, i.e. `C1`) into a FORWARD shift (`close.shift(-1)`) -- turning the previous-close reference into a look-ahead at the NEXT close |
| C Reachability | synthetic only (real-data reachability comes from Gate E's pooled count, not re-derived here) | 1,500-bar synthetic OHLCV series (seed 11, see `docs/measure_g191_144.py:_ohlcv`), shipped default: **1,480 of 1,500** bars non-NaN (98.67%), first valid at bar 20 (exactly the structural `length`-bar warm-up boundary -- this seed's first 20-bar window has >= 1 down day, so the `0/0` extension described above did not trigger here). **1,480 distinct values** observed (every fired bar distinct -- not a constant column), range `[0.427618, 1.860677]`, median `1.021865` |
| D Scale-free | pass | `|C/C1-1|` is exactly invariant to a positive price rescale, and `AMOUNT = TP*V` scales by the product of any price-rescale and any volume-rescale, so `x`'s scale cancels identically between the down-day average (numerator) and the all-day average (denominator) -- algebraically exact for ANY positive `k` (price), `j` (volume), together or separately. Measured on the 1,500-bar series: PRICE x8/x64 **bit-identical, 0.0 max\|diff\|**; VOLUME x8/x64 **bit-identical, 0.0 max\|diff\|**; BOTH (price and volume together) x8/x64 **bit-identical, 0.0 max\|diff\|** (power-of-two multiplication is exact in IEEE754, so the algebraic cancellation is also exact in float64). PRICE x10/x3.7: max\|diff\| **7.11e-15 / 5.77e-15**; VOLUME x10/x3.7: **1.44e-15 / 1.11e-15**; BOTH x10/x3.7: **7.77e-15 / 5.77e-15** -- all float64 rounding from the scalar multiply itself, far under the test's 1e-9 tolerance. `0 < 1,480 fires < 1,500` and `1,480 > 1` distinct values rule out a constant column |
| E Attribution | **pending, run by issue-solver after this session** | not run in this session (CLAUDE.md, "Gate E: the launcher runs it") |
| F Suites | this repo only; parent repo (`Backtesting`) is run by the launcher in clean worktrees | `python -m pytest -q` (this session): see run below |

## Wiring

`Category` **291 -> 292** (`volume` **36 -> 37**); `df.ta.<name>()` accessor
count **299 -> 300**. Touch points: `pandas_ta/volume/g191_144.py` (module),
`pandas_ta/volume/__init__.py` (export), `pandas_ta/__init__.py` ->
`Category["volume"]` (discovery), `pandas_ta/core.py` ->
`AnalysisIndicators.g191_144` (accessor), `tests/test_g191_144.py` (tests).
`README.md`'s headline and `volume (37)` row, and
`docs/IndicatorDictionary.md` (regenerated), both updated and checked by
`tests/test_readme_counts.py`. `docs/MLCompanionContract.md`'s running tag
count updated **636 -> 637 / 279 -> 280 `SF`** (`G191_144_20` probes cleanly
at the dictionary's 600-bar synthetic frame and takes many distinct values,
so the generator tags it `SF`); `tests/test_ml_companions.py` re-derives
these from the live dictionary and passes. `tests/test_altport2_ports.py`'s
`CATEGORY_TOTAL` updated to match (291 -> 292) and `CATEGORY_BUCKETS["volume"]`
(36 -> 37).

Ledger row: **owed**, recorded by a later receipt session once the
launcher's Gate E run lands (CLAUDE.md, "Gate E ledger"). `mtd_ret` is still
owed in the same ledger-test assertion, pre-existing and unrelated to this
port (carried over from issue #206, per `docs/G191026Measured.md`'s
identical note).

## Suite run (this repo, this session)

`python -m pytest -q`, full suite, default collection order: **3 failed,
4639 passed, 83 skipped**. `g191_144`'s own tests (`tests/test_g191_144.py`):
**23 passed**. The 3 failures are pre-existing / expected, all unrelated to
this port's correctness (CLAUDE.md "Known breaks"):
`tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
(owed for `['g191_144', 'mtd_ret']` -- `g191_144` is this port's own owed row,
`mtd_ret` pre-dates this session, per `docs/G191026Measured.md`'s identical
note), `tests/test_altrepo_talib_csv.py::test_regenerating_reproduces_the_committed_rows`
(needs the sibling `../AlternativeRepos` checkout, absent in this worktree)
and `tests/test_pine_coverage_csv.py::test_audited_rows_carry_their_evidence`
(untracked `docs/pine/` corpus, CLAUDE.md "Known breaks"). No other test
regresses.
