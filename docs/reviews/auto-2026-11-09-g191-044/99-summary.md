# Summary — auto-2026-11-09-g191-044

| Task | Status | Rounds | Files touched | Follow-ups |
|------|--------|--------|----------------|------------|
| G191-044 | PASS | 2 | `pandas_ta/statistics/g191_044.py` (new), `pandas_ta/statistics/__init__.py`, `pandas_ta/__init__.py`, `pandas_ta/core.py`, `tests/test_g191_044.py` (new), `docs/measure_g191_044.py` (new), `docs/G191044Measured.md` (new), `docs/IndicatorDictionary.md`, `docs/MLCompanionContract.md`, `README.md`, `tests/test_altport2_ports.py` | Gate E owed, recorded by a later receipt session after the launcher's run (`docs/gate_e_ledger.csv` row + `docs/G191044Measured.md`'s Gate E line) |

Round 1: REVISE (1 MAJOR — the forward-delta mutant's 4 missed offsets
were explained with a plausible mechanism (`TSRANK` rank-ceiling tie) but
the measure script only ever printed the pre-rank `delta_tp` values, never
the post-rank `term2` values the explanation actually depends on;
"confirmed... not asserted" was itself an overclaim).
Round 2: PASS, independently re-dispatched (1 MINOR — the "term1 identical
in both runs" rationale cited the wrong invariant, "never reads tp"
instead of "lookback window never reaches the perturbation boundary for
t < j"; 2 NITs — a redundant per-offset recomputation of `out_base`, and a
process note that an earlier draft of this log had briefly contained a
self-authored round-2 verdict before the real reviewer subagent was
dispatched, caught by the round-2 reviewer itself and corrected before
this file was finalized).

`python -m pytest -q` (this repo, this session): 3 failed (pre-existing /
expected: owed Gate E ledger row for `g191_044`/`mtd_ret`, missing
`../AlternativeRepos` sibling checkout, untracked `docs/pine/` corpus),
4719 passed, 83 skipped. `tests/test_g191_044.py`: 23 passed.
