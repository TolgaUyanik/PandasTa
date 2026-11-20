# Run summary — c22-ami2 (2026-11-20)

| Task | Status | Rounds | Files touched | Follow-ups |
|---|---|---|---|---|
| C22-AMI2 | **ESCALATED by the round cap, every finding applied** | 4 (cap) | `pandas_ta/statistics/c22_ami2.py` (new) · `pandas_ta/statistics/__init__.py` · `pandas_ta/__init__.py` · `pandas_ta/core.py` · `tests/test_c22_ami2.py` (new) · `tests/test_altport2_ports.py` · `docs/measure_c22_ami2.py` (new) · `docs/measure_c22_ami2_cpu.py` (new) · `docs/C22Ami2Measured.md` (new) · `docs/IndicatorDictionary.md` · `docs/MLCompanionContract.md` · `README.md` | Gate E, run by the launcher; the ledger row, recorded by a later receipt session; §E4's owed rule for issues #132 and #129 |

Task-file write-back: skipped. `docs/issues/` is a read-only, gitignored
mirror of the owner's tracker in this worktree and the GitHub issue is the
source of truth, so there is no local convention to write back to.

## What the four rounds were about

30 findings across four rounds: **3 CRITICAL, 10 MAJOR, 13 MINOR, 4 NIT**.
Not one was about the mathematics. Every round's reviewer re-ran the harness,
the opt-in GPL-3.0 battery, the test module under both CPU dispatches and the
full suite, and every round reproduced the measurements digit for digit —
including the two that decide the column (2,802 of 2,802 for the shipped
reading against the reference, 8,400 of 8,400 within 1e-12) and the kernel's
own algebra (the marginals' axes, the correction's sign, the occupied-cell
counts, the bounds as an enclosure).

All three CRITICALs and nine of the ten MAJORs were the same defect, the one
`CLAUDE.md` names as this repository's dominant one: **a sentence written past
its measurement.** "Twelve mutants" above a table of eleven. 397 files in a
tree of 398. A buffer measured on one frame, claimed on six. "Moves every
window" where 31 windows have an exactly-zero correction. A median from one
400-window sample spliced onto a negative share from another. §F1 promising to
list every dispatch-sensitive digit twice, and twice not having run the
sections it promised for.

The fixes were, wherever possible, **new measurements rather than re-worded
claims**: a twelfth mutant that makes the count true, the file count printed
by the harness, §A7 extended to six frames, §A5b's `moved` column, §A10b's
four lengths, §E4's two proxies, §G's two full no-floor sweeps, §D1's twelve
extra cells, and §F1 re-run over §B, §E and §G. Four of the round-4 fixes
could only be re-wordings, and one of them corrected an arithmetic slip the
round-3 reviewer introduced ("an eleventh" for 8.94) — which is the argument
for re-deriving every number a reviewer hands over, and is recorded in
`01-c22-ami2.md`.

## The one thing a later reader should know

This port's **first** reading of the definition was wrong, and the thing that
caught it was a measurement, not a review: the reference returns negative
values, a mutual information cannot, and a battery of 18 candidate formulas
fitted to it as a black box identified the two structural readings the
definition's own sentence leaves open — where the 0.1 buffer goes, and that
the estimator is Miller–Madow bias-corrected. The first reading reproduced the
reference on 15 of 2,802 windows; the shipped one on 2,802. `docs/C22Ami2Measured.md`
§P1c is that work, and it is the reason the 2026-10-24 screen's Gate E
expectation transfers to this column.
