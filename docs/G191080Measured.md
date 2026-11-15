# g191_080 — measured (issue #64)

> **Status: shipped through Gates A-F. Gate E SHIP (max \|rho\| 0.6913 vs
> `Volume_Ratio_20_Pctl`). This repo's suite green except the pre-existing breaks below.**

5-day volume change: Guotai Junan's (2017, "GTJA191", internal quant report, read via the
HKUDS/Vibe-Trading copy, MIT) alpha `#80`, per issue #64's own instruction. Module
`pandas_ta/volume/g191_080.py`, column `G191_080_5`. Tests: `tests/test_g191_080.py` (15, all
passing). Numbers below: `python docs/measure_g191_080.py`. Environment: this worktree's
pinned pandas/numpy. Measured 2026-11-09.

## Gate A: derivation from the published formula, not the prototype

Issue #64 states GTJA191 alpha `#80`:

    (V-V5)/V5*100

**What this session could NOT do, disclosed up front:** `docs/pine/` and web access are both
unavailable in this worktree, so the issue's own named copy -- HKUDS/Vibe-Trading (MIT) -- was
never read. Everything below is derived from the issue's own stated formula string, per the
issue's own instruction ("Gate A starts from the source formula, not the prototype").

`V5` is GTJA191's own delayed-volume notation -- the same spelling the report uses for `C5`
(`g191_018`: `CLOSE/DELAY(CLOSE,5)`) and `C6`/`C20` elsewhere -- so `V5 = DELAY(VOLUME, 5)`,
volume 5 bars ago, **not** a 5-bar moving average. Confirmed against the issue's own prototype
(`docs/issues/screen/ind_screen.py:426-427`, `cand("g191_080", ...)`):

    def _(o, h, l, c, v): return 100 * sdiv(v - delay(v, 5), delay(v, 5))

using the prototype's own unambiguous spellings `delay(x, n) = x.shift(n)` (`ind_screen.py:45`)
and `sdiv(a, b) = (a / b).replace([inf, -inf], nan)` (`ind_screen.py:41-42`) -- no disclosed
ASSUMPTION needed. The `sdiv` guard is reused for the identical reason as `g191_076`/`g191_191`:
a zero-volume bar 5 bars back would otherwise make the ratio `+-inf` rather than a defined
number.

    G191_080 = sdiv(V - DELAY(V,5), DELAY(V,5)) * 100

## Gates

| Gate | Result | Evidence |
|---|---|---|
| A Correctness | derived directly from the issue's own stated formula, using the prototype's own (unambiguous) `delay`/`sdiv` spellings -- no disclosed ASSUMPTION needed | 7-bar hand-derived example at `length=3` (`tests/test_g191_080.py::test_hand_derived_seven_bars`): `result[3..6] = [200.0, -55.0, 300.0, -80.0]`, matching the module's float64 output exactly. Matches an independent per-bar loop built from plain numpy slicing (not the module's own `.shift()`) at the shipped default (`length=5`), 3 spot-checked bars (300, 600, 899) on a 900-bar synthetic volume series |
| B Causality | pass | Future-perturbation sweep (volume rewritten from `j` onward, another synthetic series), 29 offsets past the 5-bar warm-up: real module **0 of 29** leaks (`python docs/measure_g191_080.py`). One mutant (`importlib` source read, `exec`'d in memory, the final write index shifted `length=5` bars into the future), shown live (differs from the real module) then caught at **29 of 29** |
| C Reachability | synthetic only (real-data reachability comes from Gate E's pooled count, not re-derived here) | 1,600-bar synthetic volume series (seed 11, uniform 1e4-1e6, see `docs/measure_g191_080.py:_walk`), shipped default: **1,595 of 1,600** bars non-NaN (99.69%) -- exactly `n - 5`, the `length = 5`-bar warm-up, no wider gap. **1,595 distinct values** observed on this frame (every fired bar distinct -- not a constant column), range `[-97.905416, 6200.430258]`, median `-0.431888` |
| D Scale-free | pass | For ANY `k > 0`: `100*(k*V-k*V5)/(k*V5) = 100*(V-V5)/V5` algebraically -- the `k` cancels inside the division itself, not merely for a power-of-two multiplier. The column reads no price input at all, so a close/high/low/open rescale cannot reach it (no price-scale test applies, same as `osap_voltrend_60`). Measured on the 1,600-bar series: VOLUME x8/x64 **bit-identical, 0.0 max\|diff\|** (power-of-two multiplication is exact in IEEE754, so the algebraic cancellation is also exact in float64). VOLUME x10/x3.7: max\|diff\| **9.09e-13** both -- float64 rounding from the scalar multiply itself, well under the test's 1e-9 tolerance, not a scale dependency. `0 < 1,595 fires < 1,600` and `1,595 > 1` distinct values rule out a constant column |
| E Attribution | **SHIP** -- `G191_080_5` max \|rho\| **0.6913** vs `Volume_Ratio_20_Pctl` (manifest comparator, n = 391,774), per-frame max median **0.6957** (89 frames, 0.0% >= 0.90) -- under the 0.76 SHIP line | `gate_e_overlap.py run --module pandas_ta.volume.g191_080`, run `is64-g191_080-0f4c3a01`, 89 ALTPORT-1 frames, 398,849 pooled bars, 329 + 358 = 687 comparators, canary bit-equal (AKBNK.IS, BIENY.IS, AGHOL.IS, SASA.IS). Ledger row recorded `docs/gate_e_ledger.csv` (measured 2026-11-09) |
| F Suites | this repo only; parent repo (`Backtesting`) is run by the launcher in clean worktrees | `python -m pytest -q` (this session): see run below |

## Wiring

`Category` **298 -> 299** (`volume` **37 -> 38**); `df.ta.<name>()` accessor count **306 ->
307**. Touch points: `pandas_ta/volume/g191_080.py` (module), `pandas_ta/volume/__init__.py`
(export), `pandas_ta/__init__.py` -> `Category["volume"]` (discovery), `pandas_ta/core.py` ->
`AnalysisIndicators.g191_080` (accessor), `tests/test_g191_080.py` (tests). README.md's headline
and `volume (38)` row, and `docs/IndicatorDictionary.md` (regenerated), both updated and checked
by `tests/test_readme_counts.py`. `docs/MLCompanionContract.md`'s running tag count updated
**643 -> 644 / 286 -> 287 `SF`** (`G191_080_5` probes cleanly at the dictionary's 600-bar
synthetic frame and takes many distinct values, so the generator tags it `SF`).
`tests/test_altport2_ports.py`'s `CATEGORY_TOTAL` updated to match (298 -> 299) and
`CATEGORY_BUCKETS["volume"]` (37 -> 38).

`g191_080`'s Gate E ledger row is now recorded (`docs/gate_e_ledger.csv`, measured 2026-11-09,
SHIP). `mtd_ret` remains owed in the same assertion, pre-existing and unrelated to this port
(carried over from issue #206, per `docs/G191146Measured.md`'s identical note).

## Suite run (this repo, this session)

`python -m pytest -q`, full suite, default collection order: **3 failed, 4818 passed, 83
skipped**. `g191_080`'s own tests (`tests/test_g191_080.py`): **15 passed**. Pre-existing
failures, all unrelated to this port (CLAUDE.md "Known breaks" plus the owed Gate E rows):
`tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one` (owed for
`['g191_080', 'mtd_ret']` -- `g191_080` is this port's own pending row, closed by the receipt
session after the launcher's Gate E run; `mtd_ret` pre-dates this session),
`tests/test_altrepo_talib_csv.py::test_regenerating_reproduces_the_committed_rows` (needs the
sibling `../AlternativeRepos` checkout, absent in this worktree) and
`tests/test_pine_coverage_csv.py::test_audited_rows_carry_their_evidence` (untracked
`docs/pine/` corpus). No other test regresses.
