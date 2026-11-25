# Manifest — C22-MODE-5 (issue #134)

**Mode:** C (batch task execution), single task.

## Phase 1 — Select

Task (verbatim from the invocation): port the indicator of issue #134
through Gates A-D, the wiring, the tests and `docs/<Name>Measured.md`, per
the issue and the rules in the issue-solver system prompt. catch22 mode of
the z-scored 5-bin return histogram (100). Source: catch22 (Lubba et al.
2019, DMKD 33:1821; reference code pycatch22 1.0.2, GPL-3.0 — port from the
definitions) — `DN_HistogramMode_5` on the last 100 daily returns. Gate E
and the whole suites are run by the launcher afterwards.

Run folder: `docs/reviews/auto-2026-11-22-c22-mode-5/`.

## Phase 2 — Clarify

AskUserQuestion is unavailable in this issue-solver session (system prompt
rule). Gaps found and resolved by the most conservative (smallest-scope)
reading, logged as ASSUMPTIONS rather than asked:

- **ASSUMPTION (bin count and tie rule).** hctsa's `DN_HistogramMode(y,
  numBins)` is published as: equal-width histogram over `[min(y), max(y)]`,
  mode = mean of the bin centre(s) tied for the highest count. Chose the
  AVERAGE-ALL-TIES reading (not "pick one tied bin") as the literal,
  smallest-surprise reading of hctsa's own public pseudocode — never read
  from the GPL-3.0 reference's source. Pinned by a designed 4-way-tie test
  (`tests/test_c22_mode_5.py::test_a_designed_window_exercises_a_four_way_tie`)
  and confirmed against the actual black-box reference in
  `docs/measure_c22_mode_5.py` §P (0 of 8,400 windows disagree beyond 1e-5).
- **ASSUMPTION (z-score ddof).** `ZSCORE_DDOF = 1` — MATLAB `zscore`'s
  default, since hctsa is MATLAB — the same convention this fork's sibling
  `c22_entropy_pairs` already uses and discloses for the identical reason.
- **ASSUMPTION (MIN_LENGTH).** Set to `NUM_BINS = 5` — fewer returns than
  bins would leave several bins unable to hold more than one observation
  by pigeonhole alone, before the data's own shape is read at all. A
  module choice, disclosed as not from the source, following this fork's
  existing habit of a structural (not arbitrary) length floor.
- **ASSUMPTION (blanking floor).** Reused `NOISE_ULPS = 4096` /
  `NOISE_FLOOR = NOISE_ULPS * eps` verbatim, this fork's stated existing
  habit for a return-shape quantity (cited in five other modules).
- No destructive or irreversible steps were in scope for this task; none
  were skipped.

## Phase 3 — Plan execution

Single task, no parallel lanes. Executed on the main thread (porting a
financial-feature indicator needs continuous judgment — picking the
definition reading, deriving the Gate A oracle, interpreting measured
numbers — that does not decompose into independent subagent-sized pieces
without duplicating context).

## Phase 4 — Execute + gate

Implementation: `pandas_ta/statistics/c22_mode_5.py`,
`tests/test_c22_mode_5.py` (111 tests), `docs/measure_c22_mode_5.py`,
`docs/measure_c22_mode_5_cpu.py`, `docs/C22Mode5Measured.md`, wiring in
`pandas_ta/__init__.py` / `pandas_ta/core.py` /
`pandas_ta/statistics/__init__.py`, count updates in `README.md` /
`docs/MLCompanionContract.md` / `tests/test_altport2_ports.py`,
regenerated `docs/IndicatorDictionary.md`.

Verification commands run (all green except the expected pending-Gate-E
failure):
`python -m pytest -q tests/test_c22_mode_5.py tests/test_readme_counts.py tests/test_altport2_ports.py tests/test_wiring_accessors.py tests/test_ml_companions.py tests/test_gate_e_ledger.py tests/test_pine_coverage_csv.py tests/test_prose_counts_match_the_csvs.py`
→ 255 passed, 7 skipped, 1 failed
(`test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`,
expected per the issue-solver rules).
`python docs/measure_c22_mode_5_cpu.py` (AVX512F/AVX512_SKX/AVX2/FMA3
disabled) → 111 passed.

Gate review: see `01-c22-mode-5.md`.
