# osap_voltrend_60 — measured (issue #38)

> **Status: SHIP. Gates A-F cleared.**
> Gate F (both repos' suites) is run by the launcher in clean worktrees; `python -m
> pytest -q` in this worktree is reported below for the record.

Volume trend, as asked for by issue #38: the issue names it `VolumeTrend` in the Open
Source Asset Pricing (OSAP) SignalDoc (Chen & Zimmermann) catalogue (Haugen-Baker 1996,
t-stat 3.0), "monthly 60 -> daily 60" — the issue's own stated window, with no
trading-days-per-month conversion needed this time (unlike `osap_mrrev` #37, where "18
months" had to be turned into a bar count). Module
`pandas_ta/volume/osap_voltrend_60.py`, column `VOLTREND_60`. Tests:
`tests/test_osap_voltrend_60.py` (13, all passing). Numbers below:
`python docs/measure_osap_voltrend_60.py`. Environment: this worktree's pinned
pandas/numpy. Measured 2026-11-02.

## Gate A: the primary SignalDoc text and the OSAP code are NOT consulted — read this before trusting the column

Per the issue's own instruction, OSAP's replication code is GPL-2.0 and must never be the
source of a port; this is ported from the catalogue's own description, not from OSAP's
code. This session also could not reach the OSAP SignalDoc PDF/CSV itself (`docs/pine/`
and web access are unavailable), so the port rests on the issue's own plain-language
description, implemented literally:

1. **"slope of volume on time"** — the ordinary-least-squares slope of the trailing
   `length` volume bars regressed against a time index. This is an exact formula, not a
   judgment call: `slope = sum(t_i * y_i) / sum(t_i^2)` for a centered time index `t`
   (mean-zero), which is the standard closed form for a single-regressor OLS slope.
   Centering `t` on zero is **an identity, not an assumption** — the slope of `y` on `x`
   does not depend on where `x`'s origin sits, because shifting `x` by a constant leaves
   `cov(x, y)` and `var(x)` unchanged. The existing `pandas_ta.overlap.linreg` (`slope=True`)
   uses `x = 1..length` (uncentered) for the identical reason, and gets the identical
   slope value by the same identity — this port centers purely to keep the intermediate
   sums near zero, not because the uncentered form would be wrong.
2. **"over its mean"** — divided by the trailing `length`-bar mean of the same volume
   series, the scale-free form the issue states explicitly
   (`docs/issues/screen/candidates.csv`, candidate `osap_voltrend_60`: "slope /
   mean(V,60)"). The prototype (`docs/issues/screen/ind_screen.py:800-802`,
   `sdiv(regbeta_seq(v, 60), mean(v, 60))`) was read for one thing only — the centered-time
   convention `regbeta_seq` uses (`t = arange(n) - (n-1)/2`, weight `t / sum(t**2)`,
   identical to this module's `t`/`w`) — confirming the conversion, not supplying the
   formula itself (per the issue's own instruction, "Gate A starts from the source
   formula, not the prototype"). This remains unconfirmed against the primary SignalDoc
   text itself, which this worktree cannot reach.

If a future session gets access to the OSAP SignalDoc PDF/CSV, treat "slope of volume on
time over its mean (60)" as unverified against the primary source until re-checked (it is
currently verified only against the issue's own restatement of it).

## Gates

| Gate | Result | Evidence |
|---|---|---|
| A Correctness | primary SignalDoc unavailable — see above. Self-consistent against the issue's own stated formula and the OLS-slope-origin-invariance identity | Hand-derived 4-bar example at `length=3` (volume `[100, 150, 170, 300]`, every sum done by hand): bars read exactly NaN, NaN, 0.25, 45/124 = 0.362903. Matches an independent per-bar loop (written from the formula, not from the module) at 4 spot-checked bars (100, 300, 500, 899) on a 900-bar synthetic uniform-volume series at the shipped default (`length=60`), rel. tolerance 1e-9 |
| B Causality | pass | Future-perturbation sweep, 28 offsets past the 60-bar warm-up: real module **0 of 28** leaks. One look-ahead mutant (`importlib` source read, the slope's rolling window switched from trailing to `center=True` — reads future bars — `exec`'d in memory) is shown live (differs from the real module), then caught at **28 of 28** |
| C Reachability | synthetic only (real-data reachability comes from Gate E's pooled count, not re-derived here) | 1,600-bar synthetic uniform-volume series (seed 11, range [1e4, 1e6]), shipped default (`length=60`): **1,541 of 1,600** bars non-NaN (96.31%) — exactly `n - (length - 1)`, i.e. only the 59-bar warm-up is excluded. 1,541 distinct values among the 1,541 (every fired bar distinct). Range [-0.015995, 0.012922], median 0.000074 |
| D Scale-free | pass | x8/x64 volume: **bit-identical, 0.0 max\|diff\|** (a ratio of two identically-scaled linear forms of volume). x10/x3.7 volume: max\|diff\| 1.30e-17 — both far under the 1e-9 tolerance the test asserts, with matching NaN masks. The column reads no price, so a price rescaling cannot reach it (no price-axis test is applicable). `0 < 1,541 fires < 1,600` and 1,541 distinct values rule out a constant column |
| E Attribution | **SHIP** | `gate_e_overlap.py run --module pandas_ta.volume.osap_voltrend_60`, run `is38-osap_voltrend_60-d374bdb9`, 89 ALTPORT-1 frames, 398,849 pooled bars, 329 + 358 = 687 comparators, canary bit-equal (AKBNK.IS, BIENY.IS, AGHOL.IS, SASA.IS). `VOLTREND_60`: max \|ρ\| **0.6478** vs `pvo_PVOs_12_26_9` (`compute_all`, n=393,598), per-frame max median \|ρ\| **0.6532** (also `pvo_PVOs_12_26_9`), 0.0% of frames ≥ 0.90. 0.6478 < 0.76 SHIP line → **SHIP**, matches the prototype's own measurement above |
| F Suites | this repo only; parent repo (`Backtesting`) and Gate E are run by the launcher in clean worktrees | `python -m pytest -q` (this session, pre-ledger-record): **3 failed, 4127 passed, 83 skipped** — the three failures are the known break (`test_pine_coverage_csv.py`, untracked `docs/pine/` corpus), the sibling-repo dependency (`test_altrepo_talib_csv.py`, needs `../AlternativeRepos`), and `test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one` (resolved by a future receipt session's ledger record); all three are documented pre-existing/expected failures per `CLAUDE.md`, none caused by this port |

## Wiring

`Category` **270 → 271** (`volume` **29 → 30**); `df.ta.<name>()` accessor count **278 →
279**. Touch points: `pandas_ta/volume/osap_voltrend_60.py` (module),
`pandas_ta/volume/__init__.py` (export), `pandas_ta/__init__.py` → `Category["volume"]`
(discovery), `pandas_ta/core.py` → `AnalysisIndicators.osap_voltrend_60` (accessor),
`tests/test_osap_voltrend_60.py` (tests). `README.md`'s headline and `volume (30)` row, and
`docs/IndicatorDictionary.md` (regenerated; `osap_voltrend_60` probes cleanly, column
`VOLTREND_60` tagged `SF`, no disclosed-side-effect gap since `length=60` is well inside
the generator's 600-bar probe frame), both updated and checked by
`tests/test_readme_counts.py`. `docs/MLCompanionContract.md`'s running tagged-column count
updated **616 → 617** (`SF` **261 → 262**) and checked by
`tests/test_ml_companions.py::test_the_contract_quotes_the_dictionarys_actual_ml_form_counts`.
`tests/test_altport2_ports.py`'s `CATEGORY_TOTAL` and `CATEGORY_BUCKETS["volume"]` updated
to match.

## Receipt

Gate E measured 2026-11-02 by the launcher (run `is38-osap_voltrend_60-d374bdb9`), recorded
in `docs/gate_e_ledger.csv` by this session. `VOLTREND_60` max \|ρ\| 0.6478 is under the
0.76 SHIP line, matching the prototype's own pre-port measurement (0.6478 against the same
comparator) — verdict **SHIP**. Column ships as-is. Issue #38 closed by ship, not revert.
