# Run summary — DEMAND (issue #33)

| task | status | rounds | files touched | follow-ups |
|---|---|---|---|---|
| demand (issue #33): port Gates A-D, wiring, tests, docs/DemandMeasured.md | PASS | 2 | `pandas_ta/volume/demand.py` (new), `pandas_ta/volume/__init__.py`, `pandas_ta/__init__.py`, `pandas_ta/core.py`, `tests/test_demand.py` (new, 16 tests), `README.md`, `docs/IndicatorDictionary.md`, `docs/MLCompanionContract.md`, `tests/test_altport2_ports.py`, `docs/DemandMeasured.md` (new), `docs/measure_demand.py` (new) | Gate E is pending — the launcher runs `gate_e_overlap.py` after this session; a later receipt session records the ledger row in `docs/gate_e_ledger.csv` and finalizes ship/revert per `docs/DemandMeasured.md`'s "What happens next" section |

## Round 1 — REVISE

CRITICAL: the ΔC-near-zero flat-bar guard masked output on `pct_chg.notna()` only, not on
whether `k` (the volatility scale) had itself warmed up — a flat bar landing in the gap
between `avg_vol`'s and `k`'s warm-ups (real whenever `vol_length <= length`, including the
shipped default `10/10`) read a fabricated `0.0` instead of `NaN`. MINOR: a Gate C claim in
`docs/DemandMeasured.md` was true only by seed luck given the bug.

Fix applied: `raw.where(pct_chg.notna())` → `raw.where(pct_chg.notna() & k.notna())`; two
regression tests added (default-params 1-row gap at index 9; asymmetric-params 46-row gap
probed at index 20); `docs/DemandMeasured.md` updated with a "Round 1 review fix" section
and the new numbers (test count 14→16, suite 4061→4063 passed, all else unchanged).

## Round 2 — PASS

Fletcher hand-traced the warm-up arithmetic independently (confirmed the 1-row and 46-row
gaps are real, not test-author assertions), confirmed the rising/falling branches were
already NaN-safe through `k` so the added mask term is a provable no-op there, confirmed
both new tests land their engineered flat bar genuinely inside the claimed gap rather than
tripping an unrelated `verify_series` rejection, and confirmed none of the original 14
tests' pinned values moved. No findings. PASS.

## Final state

- `python -m pytest tests/test_demand.py -q`: 16 passed.
- `python -m pytest -q` (full repo): 3 failed, 4063 passed, 83 skipped. All three failures
  are pre-existing or expected for this exact reason (named in `docs/DemandMeasured.md`
  Gate F and in this repo's `CLAUDE.md` "Known breaks"): `test_pine_coverage_csv` (known
  break, `docs/pine/` untracked), `test_altrepo_talib_csv` (needs the sibling
  `../AlternativeRepos` checkout), `test_gate_e_ledger` (Gate E owed, expected per the
  issue-solver rules until the launcher's run is recorded).
- Receipt: `docs/DemandMeasured.md`.
