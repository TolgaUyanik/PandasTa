# Brutally Honest Review — pfe closure fixes #1–3

**Date:** 2026-10-22
**Target:** `docs/MLCompanionContract.md`, `tests/test_pfe.py`, `docs/PfeMeasured.md`, `docs/reviews/2026-10-22-pfe-task-closure-review.md`
**Type:** code + text
**Verdict:** PASS

## Findings

### MINOR / NIT
- **MINOR docs/PfeMeasured.md:69 (Gate F row)** — The row says the failures are "the same 42 failures and error as the pre-port baseline (42 / 3,070)". That was never measured. The 3,070 baseline is only consistent with the arithmetic (3,087 − 17 pfe tests). The port also edited non-pfe files, so which tests fail could have changed.
  - Fix: measure the baseline in a throwaway `git worktree add <dir> HEAD`, or reword it to "baseline 42 / 3,070 inferred (3,087 − 17 new pfe tests; no failure names pfe), not re-measured."
- **MINOR docs/reviews/2026-10-22-pfe-task-closure-review.md** — The review still lists #1, #2 and the vacuous `< n` test as open, and still says "43 failed". It doesn't mention that those were later fixed.
  - Fix: add a "Resolution (2026-10-22)" section. It should say #1, #2 and MINOR-1 are fixed, that the suite is now 42 / 3,087 / 85 / 1, and that the CRITICAL and the Hannula-source MAJOR are still open.
- **NIT docs/PfeMeasured.md:69** — The Gate F row has grown into a changelog.
  - Fix: shorten it to "42 failed / 3,087 passed / 85 skipped / 1 error (2026-10-22, after fixing the MLCompanionContract SF count the port had broken)."
- **NIT docs/MLCompanionContract.md:22** — The parenthetical gives no task ID, unlike its neighbours, and doesn't say it should be undone on a revert.
  - Fix: "(565 -> 566 / 212 -> 213 `SF` on <task-id> pfe: `PFE_10_5`; revert with the port.)"

## Summary

All three fixes do what they claim:
1. **Contract count:** it now reads 566 / 213 SF, `test_ml_companions` passes, and the other counts in that sentence match the dictionary.
2. **Gate F row:** the full suite measures 42 failed / 3,087 passed / 85 skipped / 1 error. No failure names pfe. The strategy-sweep failures are pandas 3 dtype errors (`KeyError: 0`, int64 setitem).
3. **Non-constancy test:** it can now fail, because a constant column has nunique 1. The reviewer re-measured the pinned counts: 1,190 values, 1,190 unique, 612 positive, 578 negative.

Two issues remain. "Same as the pre-port baseline" is an inference, not a measurement. And the closure-review report is now stale. The task itself is still open, because Gate E, Gate C on real data and the parent-repo suite are still owed. PfeMeasured.md's status line says so honestly.
