# Run summary — auto-2026-11-11-g191-055

| task | status | rounds | files touched | follow-ups |
|---|---|---|---|---|
| `g191-055` (issue #80) | PASS rounds 1–3, REVISE round 4 with its fix applied after the cap | 4 | `pandas_ta/momentum/g191_055.py` (new), `tests/test_g191_055.py` (new), `docs/measure_g191_055.py` (new), `docs/G191055Measured.md` (new), `docs/reviews/auto-2026-11-11-g191-055/*` (new), `pandas_ta/momentum/__init__.py`, `pandas_ta/__init__.py`, `pandas_ta/core.py`, `tests/test_altport2_ports.py`, `README.md`, `docs/IndicatorDictionary.md`, `docs/MLCompanionContract.md` | Gate E (launcher's), then the ledger row; revert the column if Gate E strikes it |

## Findings across the four rounds

**13 findings: 1 CRITICAL, 0 MAJOR, 10 MINOR, 2 NIT.** Not one was a
mathematics error. Every single one was prose running ahead of the
measurement — and the CRITICAL was a round-3 fix invalidating its own
self-referential count by one.

| round | verdict | CRITICAL | MAJOR | MINOR | NIT |
|---|---|---|---|---|---|
| 1 | PASS | 0 | 0 | 4 | 1 |
| 2 | PASS | 0 | 0 | 3 | 1 |
| 3 | PASS | 0 | 0 | 3 | 0 |
| 4 | REVISE | 1 | 0 | 0 | 0 |

## What the gate actually caught

* An unattributed `+27` the session called a guess when it was one command.
* A recalled fact about Wilder's `R` filed under "evidence inside this worktree".
* A Gate F table cell disowning the owed Gate E row the bullet below it owned.
* A numerator with no provenance in a derivation that cited `R`'s to the line.
* A "relative" tolerance fix that was a strictly weaker no-op under the absolute
  assert it sat beneath — the one fix a round had to reject outright.
* "The other open-anchored directional GTJA191 port" when the fork ships three,
  two of which were missing from the comparator table.
* A float caveat guaranteeing `k*a > k*b`, which the code never computes.
* A code comment and a script comment each claiming a float64 difference their
  own stdout measured as `0.0`.
* A self-counting `swing` occurrence total that the fix to its own paragraph
  moved by one.

## Open items

* **The round-4 CRITICAL's fix was not re-reviewed** — the 4-round cap was spent
  when it landed. It is prose only (the 349-line count over the other 30 files,
  re-measured twice), the full suite was re-run after it, and
  `docs/G191055Measured.md` carries the same disclosure.
* **Gate E is owed**, by the rules of this session: the launcher runs
  `gate_e_overlap.py run --module pandas_ta.momentum.g191_055`, a later receipt
  session records the `docs/gate_e_ledger.csv` row and fills the Gate E section.
  Until then `tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
  fails naming `['g191_055', 'mtd_ret']`.
* **The three-branch `R` rests partly on recall** (no copy of the GTJA191 report
  was readable here). If the owner's copy carries the two-branch form, the fix is
  one line — already written as `TWO_BRANCH_MUTANT` in the test file — and the
  divergence is measured (ρ 0.967451, max |diff| 2.3181, 962 of 1,499 bars on the
  third branch).

## Suite

`python -m pytest -q`: **3 failed, 5255 passed, 83 skipped**, run twice (before
and after the review edits), identical both times. The three failures are the
two CLAUDE.md "Known breaks" plus this port's own owed Gate E ledger row.
