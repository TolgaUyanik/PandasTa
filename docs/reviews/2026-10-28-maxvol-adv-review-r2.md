# Brutally Honest Review — maxvol_adv (round 2)

**Date:** 2026-10-28
**Target:** uncommitted change on `B2-MAXVOL14-ADV50`: `pandas_ta/volume/maxvol_adv.py`, `tests/test_maxvol_adv.py`, `docs/MaxvolAdvMeasured.md`, `docs/EquivalentStrategies.md`, wiring in `pandas_ta/volume/__init__.py`, `pandas_ta/__init__.py`, `pandas_ta/core.py`, count edits in `tests/test_altport2_ports.py`, `tests/test_ml_companions.py`, `README.md`, `docs/IndicatorDictionary.md`, `docs/MLCompanionContract.md`
**Type:** code
**Verdict:** REVISE
**Previous round:** `docs/reviews/2026-10-28-maxvol-adv-review.md`

## Main-thread test run (2026-10-28)

`pytest tests/test_maxvol_adv.py tests/test_ml_companions.py tests/test_altport2_ports.py tests/test_wiring_accessors.py tests/test_readme_counts.py`

| venv | clean `d7fd91d` (temp worktree) | with this change |
|---|---|---|
| `.venv-pd2` (pandas 2.3.3) | 3 failed, 103 passed, 3 skipped | 3 failed, 117 passed, 3 skipped |
| `.venv` (pandas 3.0.6) | 9 failed, 97 passed, 3 skipped | 9 failed, 111 passed, 3 skipped |

- The failing tests are the same in both columns. The change adds no failures.
- `tests/test_maxvol_adv.py` passes in both venvs.
- The 3 failures in `test_readme_counts` depend on test order. That file passes when run alone, which fits the known bug where `strategy()` mutates `Category`.

## Round-1 status

| Finding | Status |
|---|---|
| CRITICAL contract counts (568 / 49 ORD) | FIXED: now 570 / 50 ORD. The reviewer re-counted with the guard's regex and got the same. The guard now checks all seven tags and the total. |
| MAJOR Gates C/E/F not met | PARTIAL: the doc is now honest ("NOT DONE. Do not merge"), but no gate has been run |
| MAJOR no clean Gate F baseline | FIXED: clean `d7fd91d` column added; the failing-ID lists diff empty; +14 passes = 14 items |
| MINOR tolerance figures disagreed | FIXED: both now say 2.2e-16 / 3.9e-16; the reviewer measured 2.2167e-16 / 3.9249e-16 |
| MINOR "rescaling cancels" unqualified | FIXED |
| MINOR source details second-hand | FIXED |
| MINOR short > long test proved nothing / no negative-ADV case | FIXED |
| MINOR "already shipped? No" unscoped | FIXED |
| MINOR NaN behaviour with min_periods undocumented | FIXED |
| NIT dictionary row provenance | FIXED |
| NIT `EquivalentStrategies.md` mixed in | NOT FIXED: the Measured doc now also links to it |

## Findings

### MAJOR
- **docs/MaxvolAdvMeasured.md, status banner and Gates C/E/F** — The issue's done condition is still not met:
  - Gate C has no real data.
  - Gate E was not run on the port. Only the prototype's 0.7003 is quoted.
  - Gate F is red on both venvs (failures that already existed).
  - Even so, `Category` and every count already say 237 indicators, 24 in volume.
  - Fix: on the machine that has `../Backtesting`:
    1. Run `gate_e_overlap.py run --module pandas_ta.volume.maxvol_adv --name maxvol_adv`, with `build --rebuild` first if the cache is stale.
    2. Record the pooled max |ρ| with its n, and the top-5 per-frame medians.
    3. Report Gate C NaN and value counts on the 89 BIST frames.
    4. Run the Backtesting suite.
    5. If Gate E strikes the column, revert the wiring and the count edits, and keep the Measured doc as the receipt.
    6. Until then, commit to the branch only.

### MINOR / NIT
- **docs/MLCompanionContract.md:27** (MINOR) — The "(with the `pfe` and `kalman_trend` rows hand-patched)" clause is stale. The dictionary header now lists five hand-patched rows: pfe, kalman_trend, range_compress_run, dpo and maxvol_adv.
  - Fix: write "(generated, some rows hand-patched; see its header)".
- **docs/MaxvolAdvMeasured.md, "Is it already shipped?"** (MINOR) — It claims "every rolling max and rolling mean of volume", but the list leaves some out:
  - `vfi.py:38` (`vave`) and `fvg_sweep_magnet.py:209/326` (an internal volume/SMA20 ratio) are not mentioned.
  - The max in `pocket_pivot` is over `sell_volume`, not raw volume.
  - Fix: name these and say why neither is this column, or drop "every".
- **tests/test_maxvol_adv.py, `test_volume_scale_within_tolerance`** (MINOR) — The test asserts rtol=1e-14, which is 25–45× looser than the "within 4e-16" quoted in three places.
  - Fix: assert the relative error is at most 4e-16, or quote 1e-14 as the guarantee.
- **docs/MaxvolAdvMeasured.md, Gate D row** (NIT) — The row doesn't say that `0 < fires < n` was replaced with a different check.
  - Fix: add "continuous column, so `0 < fires < n` is replaced by nunique = 1,151 of 1,151 non-NaN bars."
- **docs/EquivalentStrategies.md** (NIT) — This file belongs to issues #192/#193, not this one.
  - Fix: commit it first as its own `docs:` commit, so the link from the Measured doc resolves.

## Summary

Round 2 fixed nearly everything that mattered on paper:
- The contract counts are correct, and their guard now checks all seven tags and the total.
- Gate F has a real clean baseline.
- The tolerance figures match a fresh run.
- The docstring no longer claims the post defined the windows.

The code is a correct four-line ratio. It is causal (both look-ahead mutants are caught), invariant to volume scale, and wired at all five touch points. `Category` holds 237 indicators, 24 of them in volume, matching the live package.

Two kinds of gap are left. First, the issue is not done: Gate E on the port, Gate C on real data and both green suites are owed, and none can be run on this machine. Second, three places where the text says more than the runs show: the stale hand-patch clause, the unbacked "every", and a test 25× looser than the tolerance the docs quote. Fix the MINORs, commit to the branch, and do not merge until C/E/F are measured.

**Not checked:** full suites in either venv (Gate F's 2/42 figures come from the doc); the Reddit post, the prototype and `candidates_r8.csv`, none of which are on this machine; anything in Backtesting.
