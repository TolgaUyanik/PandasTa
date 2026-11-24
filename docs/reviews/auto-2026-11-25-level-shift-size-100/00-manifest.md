# Manifest — KATS-LEVEL-SHIFT-SIZE-100 (issue #163)

Mode: C (batch task execution), single free-form task — the issue-solver port task given
as the invocation's argument text, not a TODO-tag lookup.

## Task

Port `level_shift_size` (issue #163): Kats tsfeatures' `get_level_shift_features`'s `max`
column — `max |mean(w) - mean(w+1)|` over sliding 20-bar windows of log close, 100-bar
outer window — through Gates A-D, wiring, tests and `docs/LevelShiftSizeMeasured.md`.
Gate E and the whole suites are explicitly out of scope this session (run later by the
launcher); the owed `test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
failure is expected.

## Clarification (Phase 2)

No AskUserQuestion available in this session (headless issue-solver run); per the
session's own override rule, ambiguities are resolved by the most conservative reading
and logged as ASSUMPTION rather than asked.

ASSUMPTIONS made:
- Module/column naming: `level_shift_size` / `LEVELSHIFTSIZE_{length}`, following the
  already-shipped sibling `level_shift_idx` / `LEVELSHIFTIDX_{length}`'s naming
  convention exactly (the issue's own candidate name `kats_level_shift_size_100` is a
  screen-prototype label, not a module name — same relationship the sibling's issue #159
  already established, where the prototype candidate was `kats_level_shift_idx_100`).
- Category: `statistics`, matching the sibling and every other Kats tsfeatures port in
  this repo.
- Scale-free implementation device: feed the window `log(close / its own first close)`
  rather than plain `log(close)`, to get bit-exact (not merely rounded-tie-stable)
  invariance under a power-of-two price rescale, since this column's output is a
  continuous value rather than `level_shift_idx`'s discrete index. See Decision 3 in
  `docs/LevelShiftSizeMeasured.md`.
- `MIN_LENGTH = WINDOW_SIZE + 1` (21), one less than the sibling's 22, since this column's
  own arithmetic needs only one diff (no index-scale denominator to divide by zero).

## Execution map (Phase 3)

Single task, sequential, main thread (no parallel lanes needed — one indicator, one
dependency chain: module before tests before docs before wiring/counters before gate).

## Gate (Phase 4)

One Fletcher reviewer dispatch (`Explore`, read-only), against all new + modified files.
Round 1: **PASS**, no findings. No REVISE rounds needed.
