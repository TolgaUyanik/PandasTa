# osap_retskew_21 — measured (issue #36)

> **Status: Gates A-E cleared, SHIP.** Gate E measured 2026-11-02 by the launcher
> (`gate_e_overlap.py run`, 89 ALTPORT-1 frames, 398,849 bars, canary bit-equal). Gate F: this
> repo's own suite run below; the parent repo (`Backtesting`) suite is the launcher's job.

Skewness of daily returns (21), per issue #36: Open Source Asset Pricing (Chen & Zimmermann)
SignalDoc's `ReturnSkew` (Bali-Engle-Murray 2016, OSAP t 4.01) — US monthly cross-sectional
evidence, not single-ticker BIST evidence; GTJA191 Alpha #166 is the same statistic over 20
days. Module `pandas_ta/statistics/osap_retskew_21.py`, column `OSAP_RETSKEW_21`. Tests:
`tests/test_osap_retskew_21.py` (13, all passing). Numbers below: `python
docs/measure_osap_retskew_21.py`. Environment: this worktree's pinned pandas/numpy (pandas
2.3.3). Measured 2026-11-02.

## Gate A: ported from the textbook formula, not from OSAP's code

The issue is explicit: "OSAP's code is GPL-2.0: port from the paper's definition, never from
that code." `docs/pine/` and web access are unavailable in this session, so the paper itself
(Bali-Engle-Murray 2016) could not be read either — the formula implemented here is the
**standard sample-skewness statistic** (the Fisher-Pearson bias-corrected coefficient, `g1`
with the small-sample correction), the same one this repo's own `pandas_ta/statistics/skew.py`
already ships for *price* (`close.rolling(length).skew()`); this port applies the identical
operator to *daily simple returns* instead. That operator is common-knowledge statistics (every
stats text, and `pandas.Series.skew()`'s own definition), not a transcription of OSAP's R/SAS
code — so the GPL constraint is honoured by construction, not merely by avoiding a specific
file.

ASSUMPTION (disclosed, not verified against the primary source): the window is fixed at 21
trading days, matching the issue's title and GTJA191's 20-day analogue rather than OSAP's own
monthly-update cadence, since this fork only has daily bars.

```
OSAP_RETSKEW_21 = close.pct_change().rolling(21).skew()
```

3-bar example (`length=3`, the smallest window skew is defined on): closes
`[100, 103, 101, 108]` → returns `[0.03, -0.019417, 0.069307]`, mean = 0.0266298,
sample std (ddof=1) = 0.0444581, and `n/((n-1)(n-2)) * sum((r-mean)^3) / s^3` = **-0.339166**,
matching the module to 1e-6 — printed by `docs/measure_osap_retskew_21.py`, not hand-typed
(round 1 review caught a hand-typed version of this paragraph that had the wrong sign and
roughly 3x the magnitude; it is now read off the script's own output). Matched against an
independent per-window loop built from the same formula over a 1,200-bar synthetic walk (seed
23): `rtol=1e-9` at every non-NaN bar. Matched directly against
`pandas.Series.rolling(length).skew()` applied to the same return series, `assert_series_equal`.

## Gates

| Gate | Result | Evidence |
|---|---|---|
| A Correctness | pass (textbook formula, GPL code not consulted — see above) | 3-bar example (-0.339166, printed by the measure script, matches the module to 1e-6); independent per-window loop over 1,200 bars, rtol 1e-9; direct match to `pandas.Series.rolling(21).skew()` |
| B Causality | pass | Future-perturbation sweep, 31 offsets on a 1,200-bar seed-23 walk: real module **0 of 31** leaks. One look-ahead mutant (`ret = close.pct_change().shift(-1)`, `importlib` source read, `exec`'d in memory) shown live (differs from the real module), then caught at **31 of 31** |
| C Reachability | 1,179 of 1,200 bars non-NaN (98.25%), the exact 21-bar warm-up and nothing wider; 1,178 distinct values. Range [-1.456562, 1.750310], median -0.062604, median\|value\| 0.348199 | `python docs/measure_osap_retskew_21.py` |
| D Scale-free | pass | `close.pct_change()` is a ratio of two closes, cancels exactly under a uniform price rescale. x8/x64: **bit-identical, 0.0 max\|diff\|**. x10/x3.7: max\|diff\| 1.83e-14 / 2.51e-14 — both far under the 1e-9 tolerance the test asserts, with matching NaN masks. `0 < 1,179 fires < 1,200` and 1,178 distinct values rule out a constant column |
| E Attribution | **SHIP**. `OSAP_RETSKEW_21` max \|ρ\| 0.411882 vs `PVT_Slope_norm` (manifest, n=396,970); per-frame max median \|ρ\| 0.394638 (89 frames, 0% ≥ 0.90); 0.411882 < 0.76 ship line | `gate_e_overlap.py run --module pandas_ta.statistics.osap_retskew_21`, launcher run `is36-osap_retskew_21-f46bdcaa`, 89 frames, 398,849 bars, 329+358 comparators, canary bit-equal; recorded `docs/gate_e_ledger.csv` |
| F Suites | this repo only; parent repo (`Backtesting`) is run by the launcher in a clean worktree | `python -m pytest -q` (this session, after the ledger row was recorded): **2 failed, 4,092 passed, 83 skipped** |

Gate F note, both failures named, neither caused by this change nor by this issue:
`tests/test_pine_coverage_csv.py::test_audited_rows_carry_their_evidence` is the
pre-existing known break (CLAUDE.md "Known breaks" — untracked `docs/pine/` corpus).
`tests/test_altrepo_talib_csv.py::test_regenerating_reproduces_the_committed_rows` is the
pre-existing failure that needs the sibling `../AlternativeRepos` checkout (CLAUDE.md,
deselected by name in CI for this reason) — absent in this worktree, so it fails on a clean
checkout regardless of this change. `tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
now passes: the ledger row for `osap_retskew_21` is recorded in `docs/gate_e_ledger.csv`.

## Wiring

`Category` statistics list gains `osap_retskew_21`; `df.ta.osap_retskew_21()` accessor added.
Touch points: `pandas_ta/statistics/osap_retskew_21.py` (module), `pandas_ta/statistics/__init__.py`
(export), `pandas_ta/__init__.py` (`Category`), `pandas_ta/core.py` (accessor),
`tests/test_osap_retskew_21.py` (suite).

## Fork overlap (stage 2, prototype-era, not Gate E)

The issue's own prototype measurement (2026-10-24, `docs/issues/screen/`, not re-run here):
Gate E on the prototype (`PVT_Slope_norm`, max |ρ| 0.4119, n=396,970) → SHIP; fork overlap
against this repo's own `Category` outputs at defaults (12 frames) → max |ρ| 0.2624 vs
`supertrend:SUPERTd_7_3.0`, not a restatement at the 0.90 line. Both are prototype-era numbers,
kept here for context; the port's own Gate E run (pending, above) is the number that governs
ship/revert.
