# Auto run — summary (TS-PERMENT-20, PandasTa issue #91)

Mode C, one task, 2026-11-12, branch `issue-91-ts-perment-20`.

| task | status | review rounds | files touched | follow-ups |
|---|---|---|---|---|
| `ts-perment-20` | **PASS** (round 4) | 4: REVISE, REVISE, PASS, PASS — every finding of all four applied, the round-4 four after the loop's last gate and therefore unreviewed | see below | Gate E and Gate C's real-data counts, owed to the launcher; the ledger row is a later receipt session's |

Full log, with every verdict quoted: `01-ts-perment-20.md`. Assumptions and
the execution map: `00-manifest.md`.

## Files

Added:

* `pandas_ta/statistics/ts_perment_20.py` — the indicator
* `tests/test_ts_perment_20.py` — 158 tests
* `docs/TsPerment20Measured.md` — the receipt
* `docs/measure_ts_perment_20.py` — the measurement script, 8 sections
* `docs/reviews/auto-2026-11-12-ts-perment-20/` — this run folder

Modified: `pandas_ta/statistics/__init__.py`, `pandas_ta/__init__.py`
(`Category["statistics"]`), `pandas_ta/core.py` (the accessor), `README.md`
(324 registered / 332 callable / `statistics (33)`),
`docs/IndicatorDictionary.md` (regenerated), `docs/MLCompanionContract.md`
(669 tagged / 312 `SF`), `tests/test_altport2_ports.py`
(`CATEGORY_TOTAL = 324`).

## Suites, as measured in this session

* `python -m pytest tests/test_ts_perment_20.py -q` → **158 passed**.
* `python -m pytest -q` → **3 failed, 6,085 passed, 83 skipped**.

The three failures are the two `CLAUDE.md` *Known breaks*
(`test_altrepo_talib_csv.py::test_regenerating_reproduces_the_committed_rows`,
which needs the sibling `../AlternativeRepos` checkout, and
`test_pine_coverage_csv.py::test_audited_rows_carry_their_evidence`, the
`supertrend` citation into the untracked `docs/pine/`) plus
`test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`, which
reports `['mtd_ret', 'ts_perment_20']` — this port's owed Gate E row and one
owed before this branch. That failure is expected while Gate E is owed; CI
into `dev` skips it under `GATE_E_PENDING_OK=1`.

## What the reviewer found, round by round

| round | verdict | CRITICAL | MAJOR | MINOR | NIT | all applied |
|---|---|---|---|---|---|---|
| 1 | REVISE | 0 | 2 | 7 | 2 | yes |
| 2 | REVISE | 0 | 1 | 4 | 2 | yes |
| 3 | PASS | 0 | 0 | 4 | 3 | yes |
| 4 | PASS | 0 | 0 | 3 | 1 | yes, **after the last gate, so unreviewed** |

The two round-1 MAJORs and the round-2 MAJOR were all the same species: a
number written in a document that did not come from the run it names, or a
claim scoped wider than what was measured. None of them touched the column —
and that is the point of the gate, since this repo's recorded failure mode is
exactly that.

## The one thing a later session must not get wrong

**This port is not the column issue #91 screened.** The screen prototype sums
over four of the six realisable ordinal patterns (it visits two impossible
codes and skips two real ones). The port is the six-pattern source form, which
`CLAUDE.md` requires, and it correlates 0.5487 / 0.4817 / −0.0296 with the
prototype on a walk / a tick-rounded walk / a coarse grid. The issue's Gate E
figures (max \|ρ\| 0.2046 vs `psl`, SHIP) were measured on the prototype and
are a prior, not a result. Gate E must be re-run on the committed module, and
its verdict could differ.
