# Trend Detection Index (Pee; 20, multiple 2) — measured (`tdi`)

M. H. Pee's Trend Detection Index, the scale-free form. Issue #148. Catalog candidate
`ttr_tdi_20` in `docs/issues/screen/ind_screen_r5.py`, which cites R TTR's `TDI.R`
(GPL-2.0) as the library the candidate was found in; per the issue, the port is written
from the formula stated in the issue, never from `TDI.R`, and never from the prototype
script (the prototype's `mom.fillna(0)` is a screening-harness convenience, not part of
the published formula, and is NOT reproduced here).

**Status: Gates A-F cleared (SHIP). Round 5 below records the launcher's re-run Gate E at HEAD.**
`tdi` is in `Category`, so any `df.ta.strategy()` sweep in the parent repo picks it up.

Shipped: `pandas_ta/trend/tdi.py`, one column `TDI_<length>_<multiple>` (default
`TDI_20_2`). Tests: `tests/test_tdi.py` (116). Numbers: `python docs/measure_tdi.py`.
CPU-kernel check: `python docs/measure_tdi_cpu.py disable pytest`. Environment: pandas
2.3.3, numpy 1.26.4, Python 3.11, this machine's own CPU features (measured 2026-11-23).

## What the published algorithm is

The issue's own distillation of `TDI.R`:

    mom[T]     = price[T] - price[T - length]
    TDI_n_m[T] = (|sum_n mom| - (sum_2n |mom| - sum_n |mom|)) / price[T]

where n = length (20), 2n = multiple * length (40 at the default multiple = 2), and the
two rolling sums run over the n and 2n most recent values of `mom`. The `/price[T]`
divisor (scale-free form) is the issue's own specification, not an addition.

One choice NOT taken: the prototype (`ind_screen_r5.py`) computes `mom =
(close - close.shift(20)).fillna(0)` before the rolling sums, which shortens the
warm-up by treating the undefined leading `mom` values as zero. The issue's formula has
no `fillna` term, so the port leaves `mom` NaN until `close.shift(length)` has real
history, same as any other `price - price[n]` momentum term in this fork (e.g. `mom`
itself, `roc`). This makes the module's warm-up longer than the prototype's
(`length + multiple * length - 1` = 59 bars vs. the prototype's 39), and is the
one place Gate A deliberately disagrees with the prototype rather than matching it.

## Gates

| Gate | Result | Evidence |
|---|---|---|
| A Correctness | pass | matches an independent Python-loop re-derivation of the issue's formula (not the module's vectorized rolling form, and with no `fillna`): NaN masks match on all eight frames, max\|diff\| 3.109e-15 (measured, `python docs/measure_tdi.py A1`) |
| B Causality | pass | blind future-perturbation sweep, 1,499 offsets per frame: real module **0 leaks on every one of the eight frames** (`python docs/measure_tdi.py B`). Five look-ahead mutants read off the shipped source, `exec`'d in memory: proven LIVE on all eight frames, then caught on **36 of 36 tail offsets of every frame, including `flat`** — dividing by `close` (never by a high/low range) means there is no degenerate branch for a mutant to hide behind on a flat price, unlike `tao`'s partially-caught `hh-lead` mutant (`python docs/measure_tdi.py B1`) |
| C Reachability | synthetic only | warm-up is a CONSTANT 59 bars on every one of the eight frames, including `flat`: 1,441 of 1,500 bars fire everywhere. On `flat`, `mom` is identically 0 (never NaN, since it is a plain close-minus-lagged-close difference, not a divide by a range), so the column fires at a constant 0.0 rather than going all-NaN (measured, `python docs/measure_tdi.py C`) |
| D Scale-free | pass | x8/x64/2^-20/2^300 bit-identical on all eight frames; x10/x3.7/x0.1 within 1e-9 (measured at most 4.066e-15), identical NaN masks; `0 < fires < n` on the seven firing frames. A level shift does **NOT** cancel — measured 3.801e-02 / 9.231e-01 / 2.256 points at shift +1 / +50 / +1e6 on `walk` (column range roughly [-2, 2]) — because `mom` and both rolling sums cancel an additive constant exactly, but the `/close` divisor does not; this is the reason the issue specifies `/close` rather than a shift-invariant form, not a defect (`python docs/measure_tdi.py D`, which loops over the seven firing frames; the eighth, `flat`, is covered instead by `tests/test_tdi.py::test_scale_an_exact_binary_factor_is_bit_identical`, parametrized over all eight) |
| E Attribution | pass (SHIP) | run `is148-tdi-b1bb91c6` (Round 5 below, the launcher's re-run on HEAD after the squash merge), against the shipped module text (`candidate_source_sha1` still `78fb84d9`, unchanged since Round 4): `TDI_20_2` max \|rho\| **0.4924** vs `mad_pct_Pctl` (manifest, n = 391,017 of 687 comparators = 329 `compute_all` + 358 manifest), per-frame max median \|rho\| **0.4915** over 89 ALTPORT-1 frames, 0.0% of frames at or above 0.90 -> **SHIP**, matching the issue's prototype measurement almost exactly. Canary bit-equal (AKBNK.IS, BIENY.IS, AGHOL.IS, SASA.IS). Recorded in `docs/gate_e_ledger.csv`. |
| F Suites | this repo, targeted only | `python -m pytest -q tests/test_tdi.py tests/test_readme_counts.py tests/test_altport2_ports.py tests/test_wiring_accessors.py tests/test_ml_companions.py tests/test_gate_e_ledger.py tests/test_pine_coverage_csv.py tests/test_prose_counts_match_the_csvs.py` after the ledger record (Round 5, below). Same command's `test_tdi.py` subset under `python docs/measure_tdi_cpu.py disable pytest` (CPU kernels without AVX-512F/AVX512_SKX/AVX2/FMA3): 116 of 116 pass (measured 2026-11-23, Round 3). Whole suites: run by issue-solver in clean worktrees (see the PR body). |

### Round 2 (review fix) -- attribution

A pre-push review (round 2) found a MAJOR attribution defect: the shipped docstring
(`pandas_ta/trend/tdi.py:43`) opened "Blough's Trend Detection Index", but the index is
M. H. Pee's -- R TTR's own documentation, the issue's title, and this file's own heading
all say so. Fixed to "M. H. Pee's Trend Detection Index" in the module docstring, this
file's opening line, and `docs/MLCompanionContract.md`'s #148 clause; the generated
`docs/IndicatorDictionary.md` row follows from re-running
`python docs/gen_indicator_dictionary.py`. Also named the prototype's warm-up bar (39,
with its `fillna(0)`) instead of leaving it as "the prototype's shorter one" (NIT, three
locations).

### Round 3 (launcher finding) -- stale ledger row removed

Editing the module in Round 2 changed its bytes, so its LF-normalised sha1 no longer
matched `d519532bfbf2207f6350d216290b64350252eac0`, the sha1 the earlier
`is148-tdi-c25dda7f` run had measured against. `docs/gate_e_ledger.py`'s own design has
no carve-out for a comment-only edit: a reviewer cannot tell "docstring-only" from
"secretly behaviour-changing" without re-running the measurement, so that run's row no
longer described the shipped module and `tests/test_gate_e_ledger.py::test_row_still_describes_its_module[tdi:TDI_20_2]`
failed outright (not a skip: this worktree does not set `GATE_E_PENDING_OK=1`). Leaving
a stale row in `docs/gate_e_ledger.csv` is not a valid state for an edited module --
the row is deleted outright, same as any other indicator whose Gate E is owed, rather
than kept as a "historical receipt": `test_row_still_describes_its_module` only runs
against rows that exist, so a deleted row cannot fail it, and `tdi` now falls under
`test_every_indicator_that_needs_a_row_has_one` instead -- the same owed-row path a
brand-new indicator takes, a skip under CI's `GATE_E_PENDING_OK=1` and a hard failure
toward `main` or on any bare local run, per `CLAUDE.md`'s "Owed, not failed, on the way
to dev". Gate E (0.4924 vs `mad_pct_Pctl`, measured 2026-11-23 on the pre-Round-2 text)
is no longer a valid receipt for the current module and is not restated above; the
measurement is re-run and re-recorded by issue-solver after this session, against the
current module text. (Done: Round 4 below, run `is148-tdi-a3774479`.)

### Round 4 (receipt session) -- Gate E re-run, ledger recorded, revert not needed

The launcher ran Gate E on `pandas_ta/trend/tdi.py` at HEAD (post-Round-2 attribution
fix): run `is148-tdi-a3774479`, `candidate_source_sha1` `78fb84d91c8948c93390fe89f809d9c0bddd67af`,
89 ALTPORT-1 frames, 398,849 pooled bars, 687 comparators (329 `compute_all` + 358
manifest), canary bit-equal on AKBNK.IS / BIENY.IS / AGHOL.IS / SASA.IS. `TDI_20_2`: max
\|rho\| 0.4924 vs `mad_pct_Pctl` (manifest, n = 391,017), per-frame max median \|rho\|
0.4915, 0.0% of the 89 frames at or above 0.90 -> **SHIP** under `r3-perframe-0.90`
(well under the 0.76 ship line, matching the issue's own prototype measurement of
0.4924 / 0.4915 almost exactly). Recorded with `python docs/gate_e_ledger.py record
/home/tolga/.issue-solver/runs/20261123-150046-148/gatee/is148-tdi-a3774479 --measured
2026-11-23`, which accepted the run (a non-default run, a universe other than 89
frames, or a non-bit-equal canary would have been refused). No column is STRUCK, so
nothing is reverted; the port ships as-is.

`python -m pytest -q tests/test_tdi.py tests/test_readme_counts.py
tests/test_altport2_ports.py tests/test_wiring_accessors.py tests/test_ml_companions.py
tests/test_gate_e_ledger.py tests/test_pine_coverage_csv.py
tests/test_prose_counts_match_the_csvs.py`: 1,542 passed, 7 skipped, 0 failed (measured
2026-11-23, after the ledger record -- the `test_every_indicator_that_needs_a_row_has_one`
failure from Round 3 is gone now that `tdi:TDI_20_2` has a current row). Whole suites:
run by issue-solver in clean worktrees (see the PR body).

### Round 5 (receipt session) -- launcher's Gate E re-run at HEAD, ledger recorded, no revert

The launcher ran Gate E on `pandas_ta/trend/tdi.py` at the squash-merged HEAD (`9fcbe4c`):
run `is148-tdi-b1bb91c6`, `candidate_source_sha1` `78fb84d91c8948c93390fe89f809d9c0bddd67af`
-- unchanged from Round 4's run, since the module's own text has not moved since the
attribution fix -- 89 ALTPORT-1 frames, 398,849 pooled bars, 687 comparators (329
`compute_all` + 358 manifest), canary bit-equal on AKBNK.IS / BIENY.IS / AGHOL.IS /
SASA.IS. `TDI_20_2`: max \|rho\| 0.4924 vs `mad_pct_Pctl` (manifest, n = 391,017),
per-frame max median \|rho\| 0.4915, 0.0% of the 89 frames at or above 0.90 ->
**SHIP** under `r3-perframe-0.90`, identical to Round 4's numbers (the pandas_ta source
feeding the engine did not change). Recorded with `python docs/gate_e_ledger.py record
/home/tolga/.issue-solver/runs/20261124-120630-148/gatee/is148-tdi-b1bb91c6 --measured
2026-11-24`, which accepted the run and replaced the ledger's `pandas_ta_src_sha1` (the
squash merge changed the tree hash even though `tdi.py` itself did not) and run id/date.
No column is STRUCK, so nothing is reverted; the port ships as-is.

`python -m pytest -q tests/test_tdi.py tests/test_readme_counts.py
tests/test_altport2_ports.py tests/test_wiring_accessors.py tests/test_ml_companions.py
tests/test_gate_e_ledger.py tests/test_pine_coverage_csv.py
tests/test_prose_counts_match_the_csvs.py`: 1,598 passed, 7 skipped, 0 failed (measured
2026-11-24, after this round's ledger record). Whole suites: run by issue-solver in
clean worktrees (see the PR body).

## CPU-kernel check (NPY_DISABLE_CPU_FEATURES)

`python docs/measure_tdi_cpu.py disable pytest` (this machine's own features: all 116
tests of `tests/test_tdi.py` pass under `NPY_DISABLE_CPU_FEATURES="AVX512F AVX512_SKX
AVX2 FMA3"` as well as under the native kernel set, measured 2026-11-23). `tdi` is pure
rolling-sum / abs / divide arithmetic with no branch whose CONDITION is a float
comparison (unlike `msw_sine`'s `|real| > eps` guard), so there is no comparison for a
kernel-dependent last-bit move to flip.

## Non-redundancy, synthetic (NOT Gate E)

Spearman rho of `TDI_20_2` against this fork's own columns, on the same eight 1,500-bar
synthetic frames (`python docs/measure_tdi.py F`):

| frame | VHF_28 | CFO_9 | ROC_10 | ROC_20 |
|---|---|---|---|---|
| walk | 0.5063 | -0.0018 | -0.0760 | -0.1361 |
| trend | 0.6139 | -0.0715 | 0.1606 | 0.5537 |
| range-bound | 0.2080 | -0.0208 | 0.1051 | 0.0678 |
| grid | 0.5852 | -0.0134 | -0.0135 | 0.0910 |
| heavy-tailed | 0.4124 | 0.0004 | -0.0132 | -0.1290 |
| jump | 0.4516 | 0.0169 | -0.0328 | -0.0107 |
| coarse | 0.4674 | -0.0087 | -0.0750 | -0.1354 |

`VHF_28` (Vertical Horizontal Filter, also a trend-vs-chop ratio over an absolute-move
sum) is the strongest synthetic comparator at up to 0.61, consistent with the issue's own
fork-overlap screen: its stage-2 measurement already found max |rho| 0.4883 vs
`vhf:VHF_28` on the prototype (12 real-data frames). `CFO_9` and `ROC_*` stay low, which
is expected: `tdi` is built from the trend/choppiness RATIO of absolute moves, not a
simple directional momentum term.

## §W Wiring — the five touch points

1 module `pandas_ta/trend/tdi.py` · 2 `ta.trend.tdi` True · 3 `Category["trend"]` True
(trend has 66, `Category` total 380) · 4 `df.ta.tdi` True, bit-equal to the function · 5
`tests/test_tdi.py`. Column `TDI_20_2`. `docs/IndicatorDictionary.md` tags `TDI_20_2`
`SF`. The census moves 724 -> 725 tagged columns and 358 -> 359 `SF`.

## §Z Cost

Vectorised throughout, no Python loop: one `shift`, three rolling sums, `abs` and
arithmetic.

| bars | traced peak MB | ms | ms (2nd) |
|---|---|---|---|
| 100,000 | 6.4 | 6.2 | 5.9 |
| 400,000 | 25.6 | 22.7 | 22.7 |

The wall clock is this machine's and this run's.

## Open

None. Gates A-F cleared (Round 5 above): the launcher's Gate E re-run at HEAD recorded in
`docs/gate_e_ledger.csv` (SHIP, 0.4924 vs `mad_pct_Pctl`, unchanged from Round 4). Both
repos' whole suites are run by issue-solver in clean worktrees per the PR body.
