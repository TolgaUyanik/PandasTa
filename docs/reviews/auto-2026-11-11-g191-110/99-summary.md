# auto run 2026-11-11 — g191-110 (summary)

| task | status | rounds | files touched | follow-ups |
|---|---|---|---|---|
| `g191-110` | **ESCALATED at the review cap** — delivered, but round 4 returned REVISE and its fixes were not re-reviewed | 4 (round 1 + 3 re-runs, the cap; **all four REVISE**) | added `pandas_ta/momentum/g191_110.py`, `tests/test_g191_110.py`, `docs/measure_g191_110.py`, `docs/G191110Measured.md`, this run folder; modified `pandas_ta/momentum/__init__.py`, `pandas_ta/__init__.py`, `pandas_ta/core.py`, `README.md`, `docs/IndicatorDictionary.md`, `docs/MLCompanionContract.md`, `tests/test_altport2_ports.py` | (1) **the owner's keep-or-skip ruling** — the receipt recommends SKIP; (2) Gate E, run by the issue-solver launcher; (3) the ledger row, recorded by the receipt session; (4) the comparator-dump grep for `brar_BR_` that would replace the receipt's one inference with a run; (5) round 4's fixes have never been reviewed |

## What the four rounds did and did not catch

Across 4 rounds the reviewer raised **35 findings — 14 MAJOR, 0 CRITICAL — and not one was a
mathematics error.** (Counted from the four verdict blocks in `01-g191-110.md`: 9 findings /
3 MAJOR in round 1, 10 / 4 in round 2, 7 / 3 in round 3, 9 / 4 in round 4.) Every round
independently re-ran `docs/measure_g191_110.py`, the module's
test file and the full suite, reproduced every number to the digit, and then failed the prose
around them. The repeating failure mode was the repo's documented one, and it reproduced
inside the fix loop itself: each round's REPLACEMENT text planted new unmeasured absolutes.

| round | verdict | MAJOR findings | the pattern |
|---|---|---|---|
| 1 | REVISE | 3 | the `brar` difference list closed with "only"; the comparator-set claim unmeasured; a section headed "The recommendation" with no recommendation in it |
| 2 | REVISE | 4 | all four were absolutes introduced by round 1's own fixes ("every other `g191_*` port", "the one user-reachable look-ahead in any indicator", "two committed files", "the only one of the three") |
| 3 | REVISE | 3 | all three introduced by round 2's fixes ("the MINORITY spelling", "every comparator NAME carries its default suffix", "changes the column's VALUES") |
| 4 | REVISE | 4 | all four introduced by round 3's fixes (a 3+3 count over a 7-item list, "change every value" beside "bit-equal on 927 of 1,480", an un-softened "the one place", and "Every number in this file comes from a run") |

Round 4's fixes landed with the cap spent and were **not re-reviewed**. `01-g191-110.md`'s
round-4 table lists every piece of text they changed; it is the prose a next reader should
check first. The user's standing rule is max 4 rounds, then report the open findings — which
is this file.

## Open findings at the cap

None of round 4's nine findings was left unfixed; the open item is that **the fixes themselves
are ungated**. The risk is confined to prose: round 4 changed only docstrings and documents,
and `pandas_ta/momentum/g191_110.py`'s executable body — the 25 lines from `length = int(...)`
to `return result` — has not changed since before round 1. Rounds 1 and 2 did add to the test
module (a fourth mutant, the `offset` pin) and to the measure script; round 4 added nothing
executable anywhere.

Two substantive things are owed from outside this session, neither of them a review finding:

1. **Gate E** — the launcher runs `gate_e_overlap.py` on the committed module; this session may
   not. The receipt's Gate E row says "pending" and the prototype's priors are labelled as
   priors.
2. **The keep-or-skip ruling** — `docs/G191110Measured.md` recommends SKIP as
   question-redundancy, with the revert list in it. The port is in the commit so Gate E can
   run, not because the column was judged to earn its place.

## Assumptions logged (no questions were asked)

`AskUserQuestion` is unavailable in a headless issue-solver session, so the three decisions
that would otherwise have been questions are logged in `00-manifest.md`: the category
(`momentum`), shipping-rather-than-reverting with a SKIP recommendation, and Gate C on real
data being owed with Gate E rather than claimed.

## Verification at the end of the run

* `python -m pytest tests/test_g191_110.py -q` → **37 passed**
* `python -m pytest -q` → **3 failed, 5377 passed, 83 skipped** (108.35s); the three failures are the
  two CLAUDE.md "Known breaks" (`test_pine_coverage_csv`, and `test_altrepo_talib_csv` which
  needs the absent `../AlternativeRepos`) plus the OWED Gate E ledger row for
  `['g191_110', 'mtd_ret']`
* `python docs/measure_g191_110.py` → every number quoted in `docs/G191110Measured.md` that is
  labelled as measured in this session

One extra guard fired while this folder was being written and is recorded because it is a trap
for the next port: `tests/test_pine_coverage_csv.py::test_no_other_document_retypes_the_split`
failed on `01-g191-110.md` because round 4's quoted SUMMARY contained five slash-joined
integers (this column's sign counts), which its `NAMELESS_SPLIT` regex
(`test_pine_coverage_csv.py:44`) reads as a retyped PINEBI verdict split. Spacing the slashes
fixed it; the numbers are unchanged. A review log that quotes a reviewer verbatim can trip that
guard without retyping anything.
