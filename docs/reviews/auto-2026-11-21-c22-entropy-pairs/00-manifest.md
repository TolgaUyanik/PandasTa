# Manifest — C22-ENTROPY-PAIRS (issue #133)

**Mode:** C (batch task execution), single task.

## Phase 1 — Select

Task (verbatim from the invocation): port the indicator of issue #133
through Gates A-D, the wiring, the tests and `docs/<Name>Measured.md`, per
the issue and the issue-solver system prompt. catch22 entropy of 2-letter
words in a 3-quantile return alphabet (100). Source: catch22 (Lubba et al.
2019, DMKD 33:1821; reference code pycatch22 1.0.2, GPL-3.0 — port from the
definitions). Gate E and the whole suites are run by the launcher
afterwards.

Run folder: `docs/reviews/auto-2026-11-21-c22-entropy-pairs/`.

## Phase 2 — Clarify

AskUserQuestion is unavailable in this issue-solver session (system prompt
rule). Gaps found and resolved by the most conservative (smallest-scope)
reading, logged as ASSUMPTIONS rather than asked:

- **ASSUMPTION (quantile interpolation convention).** "Quantile" names the
  binning rule but not the finite-sample estimator. Chose linear
  interpolation between bracketing order statistics (`numpy.quantile`'s
  default) — the most literal reading of "the 1/3 and 2/3 empirical
  quantiles" and the smallest-footprint choice (no extra parameter).
  Disclosed in the module docstring and tested against six candidate
  conventions in `docs/measure_c22_entropy_pairs.py` §P1; none reproduces
  the GPL-3.0 reference bit-for-bit, and the shipped convention ties for
  the best median fit.
- **ASSUMPTION (word definition: overlapping vs non-overlapping pairs).**
  Chose OVERLAPPING consecutive-letter pairs (`length - 1` words), the
  conventional reading of a "motif" statistic and the one catch22's own
  `h`/`hh`/`hhh`/`hhhh` naming implies (word length encoded by repeated
  letters, not by a stride parameter). Measured in §P2 against pycatch22 as
  the best-fitting of four structural candidates tried (overlapping beats
  non-overlapping, log2, and type-normalized readings by a wide margin).
- **ASSUMPTION (MIN_LENGTH).** Set to `NUM_LETTERS ** WORD_LENGTH + 1 = 10`
  — as many 2-letter words as the alphabet has word types — following this
  fork's existing convention for other catch22 ports (`c22_ami2`'s
  `NUM_BINS**2 + TAU`).
- **ASSUMPTION (blanking floor).** Reused `NOISE_ULPS = 4096` /
  `NOISE_FLOOR = NOISE_ULPS * eps` verbatim, this fork's stated existing
  habit for a return-shape quantity (cited in five other modules).
- No destructive or irreversible steps were in scope for this task; none
  were skipped.

## Phase 3 — Plan execution

Single task, no parallel lanes. Executed on the main thread (porting a
financial-feature indicator needs continuous judgment — picking the
definition reading, deriving Gate A oracles, interpreting measured
numbers — that does not decompose into independent subagent-sized pieces
without duplicating context).

## Phase 4 — Execute + gate

Implementation: `pandas_ta/statistics/c22_entropy_pairs.py`,
`tests/test_c22_entropy_pairs.py` (92 tests), `docs/measure_c22_entropy_pairs.py`,
`docs/measure_c22_entropy_pairs_cpu.py`, `docs/C22EntropyPairsMeasured.md`,
wiring in `pandas_ta/__init__.py` / `pandas_ta/core.py` /
`pandas_ta/statistics/__init__.py`, count updates in `README.md` /
`docs/MLCompanionContract.md` / `tests/test_altport2_ports.py`, regenerated
`docs/IndicatorDictionary.md`. Committed as `b985c6c`.

Verification commands run (all green except the expected pending-Gate-E
failure):
`python -m pytest -q tests/test_c22_entropy_pairs.py tests/test_readme_counts.py tests/test_altport2_ports.py tests/test_wiring_accessors.py tests/test_ml_companions.py tests/test_gate_e_ledger.py tests/test_pine_coverage_csv.py tests/test_prose_counts_match_the_csvs.py`
→ 1390 passed, 7 skipped, 1 failed (`test_every_indicator_that_needs_a_row_has_one`,
expected per the issue-solver rules).
`python docs/measure_c22_entropy_pairs_cpu.py` (AVX512F/AVX512_SKX/AVX2/FMA3
disabled) → 92 passed.

Gate review: see `01-c22-entropy-pairs.md`.
