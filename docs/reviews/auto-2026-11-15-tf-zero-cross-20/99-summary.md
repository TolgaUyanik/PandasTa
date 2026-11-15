# Run summary — tf-zero-cross-20

| Task | Status | Rounds | Files touched | Follow-ups |
|------|--------|--------|---------------|------------|
| TF-ZERO-CROSS-20 | PASS (round 4) | 4 | `pandas_ta/statistics/tf_zero_cross_20.py`, `pandas_ta/statistics/__init__.py`, `pandas_ta/__init__.py`, `pandas_ta/core.py`, `tests/test_tf_zero_cross_20.py`, `tests/test_altport2_ports.py`, `docs/measure_tf_zero_cross_20.py`, `docs/measure_tf_zero_cross_20_cpu.py`, `docs/TfZeroCross20Measured.md`, `docs/IndicatorDictionary.md`, `docs/MLCompanionContract.md`, `README.md`, this folder | Gate E (launcher), Gate C's real-data limb, and the OWED momersion overlap measurement with its revert rule |

Rounds: 1 REVISE (2 CRITICAL, 3 MAJOR, 3 MINOR, 1 NIT — all 9 applied),
2 PASS (4 MINOR, 3 NIT — all 7 applied anyway, so the PASS no longer
covered the tree), 3 PASS (2 MINOR, 2 NIT — all 4 applied), 4 PASS (1
MINOR, 3 NIT). Three of round 4's four were applied after it: the
`docs/MLCompanionContract.md` level-shift clause, which flattened a measured
caveat into an unconditional claim and is a false statement in a
consumer-facing document; the date attribution in the test docstring; and
the receipt's EXCEPT list. The fourth, reading the dictionary's truncation
limit out of the generator instead of retyping it, was applied too. No
fifth review ran: the session's cap is four rounds, and each of the four
edits is a correction quoting a figure round 4 had already verified.

The one finding across all four rounds that was argued rather than
applied is round 1's MAJOR on the `LEAN_MOMERSION_20` overlap. The
reviewer did not ask for a revert and said so ("I will not overturn
[the call]"); what it asked for, and what landed, is a trigger: the
Gate E section now carries an OWED item with a band and a revert
rule, mirrored in the module docstring and
`docs/MLCompanionContract.md` and pinned by
`test_the_overlap_measurement_is_still_owed_from_the_gate_e_run`.

Measured at the end of the run, after every fix:

* `python -m pytest tests/test_tf_zero_cross_20.py -q` → 336 passed.
* `python docs/measure_tf_zero_cross_20_cpu.py` (the same module with
  `AVX512F AVX512_SKX AVX2 FMA3` disabled) → 336 passed.
* `python docs/measure_tf_zero_cross_20.py` and
  `python docs/measure_tf_zero_cross_20_cpu.py --all` → the same
  `DIGEST A1,A2,A3,A4,A5,A6,A7,B,C,D,G,L,W
  108bc7c39deb6b45b9c9115d98df5bbf2e7716a5`.
* `python -m pytest -q` → 3 failed, 10,611 passed, 85 skipped. The three are
  `tests/test_pine_coverage_csv.py::test_audited_rows_carry_their_evidence`
  and
  `tests/test_altrepo_talib_csv.py::test_regenerating_reproduces_the_committed_rows`
  (the two `CLAUDE.md` clean-checkout breaks, both deselected by CI) and
  `tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
  (the owed Gate E row this commit ships with).

Task-file write-back: skipped. The project's tracker is `docs/issues/`,
which is gitignored and read-only in this worktree; issue #113 is closed by
the launcher's PR, not from here.
