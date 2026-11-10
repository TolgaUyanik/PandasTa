# g191_043 — measured (issue #69)

> **Status: Gates A-D cleared, wired, this repo's suite green except the pre-existing breaks
> below. Gate E: pending, run by issue-solver after this session.**

6-day signed volume (OBV slope): Guotai Junan's (2017, "GTJA191", internal quant report, read
via the HKUDS/Vibe-Trading copy, MIT) alpha `#43`, per issue #69's own instruction. Module
`pandas_ta/volume/g191_043.py`, column `G191_043_6`. Tests: `tests/test_g191_043.py` (21, all
passing). Numbers below: `python docs/measure_g191_043.py`. Environment: this worktree's pinned
pandas/numpy. Measured 2026-11-10.

## Gate A: derivation from the published formula, not the prototype

Issue #69 states GTJA191 alpha `#43`:

    #43: SUM(C>C1 ? V : (C<C1 ? -V : 0), 6)

and its own scale-free conversion, `/SUM(V,6)`.

**What this session could NOT do, disclosed up front:** `docs/pine/` and web access are both
unavailable in this worktree, so the issue's own named copy -- HKUDS/Vibe-Trading (MIT) -- was
never read. Everything below is derived from the issue's own stated formula string, per the
issue's own instruction ("Gate A starts from the source formula, not the prototype"), then
cross-checked against the issue's own prototype (`docs/issues/screen/ind_screen.py:357-359`):

    @cand("g191_043", "6-day signed volume (OBV slope)", G,
          "#43: SUM(C>C1 ? V : (C<C1 ? -V : 0), 6)", "/SUM(V,6)")
    def _(o, h, l, c, v): return sdiv(tsum(np.sign(delta(c, 1)) * v, 6), tsum(v, 6))

using the prototype's own unambiguous spellings `delay(x, n) = x.shift(n)` and
`delta(x, n) = x - x.shift(n)` (`ind_screen.py:45-46`) and `tsum(x, n) = x.rolling(n).sum()`
(`ind_screen.py:49`) -- no disclosed ASSUMPTION needed. `np.sign(delta(c, 1))` returns exactly
`+1`/`-1`/`0` for the three ternary branches (up/down/flat day), matching the issue's own string
at every bar, including the `C==C1` boundary (`delta==0` yields `0` under either formulation).

    G191_043 = SUM(SIGN(C-C1)*V, 6) / SUM(V, 6)

This fork's own `pandas_ta.utils.signed_series(close)` -- already used by this fork's `obv`
(`pandas_ta/volume/obv.py`) -- computes the identical thing without `numpy`: `close.diff(1)`
mapped to `+1`/`-1`/`0`, with bar 0 left `NaN` (its `initial` parameter defaults to `None`),
matching `np.sign(NaN) == NaN`. Measured on a 1,500-bar synthetic walk
(`python docs/measure_g191_043.py`): `signed_series(close)` and an explicit
`np.sign(close.diff(1))` ternary agree bit-for-bit (`signed_series-vs-ternary agree=True`), NaN
masks matching. That walk has zero exactly-flat bars (`zero-delta-bars=0`, a continuous-float
random walk essentially never lands on `delta == 0` exactly -- disclosed, not glossed over); the
`delta == 0` boundary itself is pinned separately on a dedicated 9-bar hand-derived frame below
and in `tests/test_g191_043.py::test_hand_derived_nine_bars` / `test_signed_series_matches_an_explicit_sign_ternary_at_the_zero_boundary`.

## Gates

| Gate | Result | Evidence |
|---|---|---|
| A Correctness | derived directly from the issue's own stated formula, using the prototype's own (unambiguous) `delay`/`delta`/`tsum` spellings, and matched against this fork's own `signed_series` helper (already used by `obv`) -- no disclosed ASSUMPTION needed | 9-bar hand-derived example at `length=3` (`tests/test_g191_043.py::test_hand_derived_nine_bars`), including a flat-day (`delta==0`) boundary bar: `result[3..8] = [-0.111111, 0.166667, -0.066667, 0.333333, -0.333333, 0.333333]`, matching the module's float64 output exactly (`python docs/measure_g191_043.py`: `hand-derived bars 0..8`). Matches an independent per-bar loop built from plain numpy slicing (not the module's own `.rolling()`/`signed_series` calls) at the shipped default (`length=6`), 3 spot-checked bars (300, 600, 899) on a 900-bar synthetic frame: `module=0.261465 loop=0.261465`, `module=0.626902 loop=0.626902`, `module=-0.192411 loop=-0.192411` |
| B Causality | pass | Future-perturbation sweep (close AND volume rewritten from `j` onward, another synthetic pair), 34 offsets past the 6-bar warm-up: real module **0 of 34** leaks (`python docs/measure_g191_043.py`). One mutant (`importlib` source read, `exec`'d in memory, the final write index shifted `length=6` bars into the future), shown live (differs from the real module) then caught at **34 of 34** |
| C Reachability | synthetic only (real-data reachability comes from Gate E's pooled count, not re-derived here) | 1,500-bar synthetic frame (seed 11 close, seed 97 volume, `docs/measure_g191_043.py:_walk`/`_volume`), shipped default: **1,494 of 1,500** bars non-NaN (99.60%) -- exactly `n - 6`, the `length = 6`-bar warm-up, no wider gap. **1,461 distinct values** observed on this frame (not a constant column), range `[-1.000000, 1.000000]` (bounded by construction), median `0.051569` |
| D Scale-free | pass | For ANY `k > 0`: scaling volume (`V -> k*V`) scales both the signed-volume sum and the volume sum linearly, so `k` cancels in the ratio exactly; scaling price (`C -> k*C`) changes nothing, since only `SIGN(C-C1)` is read, never its magnitude. Measured on the 1,500-bar frame: VOLUME x8/x64 **bit-identical, 0.0 max\|diff\|**; VOLUME x10/x3.7: max\|diff\| **1.11e-15**, float64 rounding from the scalar multiply itself, well under the test's 1e-9 tolerance. PRICE x8/x64/x10/x3.7 **ALL bit-identical, 0.0 max\|diff\|** (the sign ternary reads only the SIGN of a price difference, so even a non-power-of-two rescale is exact -- unlike the volume case). `0 < 1,494 fires < 1,500` and `1,461 > 1` distinct values rule out a constant column |
| E Attribution | **pending, run by issue-solver after this session** | not run in this session, per this session's rules |
| F Suites | this repo only; parent repo (`Backtesting`) is run by the launcher in clean worktrees | `python -m pytest -q` (this session): see run below |

## Wiring

`Category` **303 -> 304** (`volume` **38 -> 39**); `df.ta.<name>()` accessor count **311 ->
312**. Touch points: `pandas_ta/volume/g191_043.py` (module), `pandas_ta/volume/__init__.py`
(export), `pandas_ta/__init__.py` -> `Category["volume"]` (discovery), `pandas_ta/core.py` ->
`AnalysisIndicators.g191_043` (accessor), `tests/test_g191_043.py` (tests). README.md's headline
and `volume (39)` row, and `docs/IndicatorDictionary.md` (regenerated), both updated and checked
by `tests/test_readme_counts.py`. `docs/MLCompanionContract.md`'s running tag count updated
**648 -> 649 / 291 -> 292 `SF`** (`G191_043_6` probes cleanly at the dictionary's 600-bar
synthetic frame and takes many distinct values, so the generator tags it `SF`).
`tests/test_altport2_ports.py`'s `CATEGORY_TOTAL` updated to match (303 -> 304) and
`CATEGORY_BUCKETS["volume"]` (38 -> 39).

`g191_043`'s Gate E ledger row is owed, recorded by the receipt session after the launcher's
Gate E run.

## Suite run (this repo, this session)

`python -m pytest -q`, full suite, default collection order: **3 failed, 4945 passed, 83
skipped**. `g191_043`'s own tests (`tests/test_g191_043.py`): **21 passed**. Failures, all
pre-existing and unrelated to this port except the owed Gate E row (CLAUDE.md "Known breaks"
plus "Owed, not failed"):
`tests/test_altrepo_talib_csv.py::test_regenerating_reproduces_the_committed_rows` (needs the
sibling `../AlternativeRepos` checkout, absent in this worktree),
`tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one` (owed for
`['g191_043', 'mtd_ret']` -- `g191_043` is this port's own pending row, closed by the receipt
session after the launcher's Gate E run; `mtd_ret` pre-dates this session, per
`docs/G191167Measured.md`'s identical note) and
`tests/test_pine_coverage_csv.py::test_audited_rows_carry_their_evidence` (untracked
`docs/pine/` corpus, 8d8f705). No other test regresses.
