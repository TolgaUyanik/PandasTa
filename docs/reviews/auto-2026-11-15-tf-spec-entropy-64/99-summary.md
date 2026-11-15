# Run summary — `/brutally-honest-review --auto` (Mode C), 2026-11-15

| task | status | rounds | files touched | follow-ups |
|---|---|---|---|---|
| `tf-spec-entropy-64` | **PASS** (round 4) | 4 (REVISE, REVISE, REVISE, PASS) | `pandas_ta/statistics/tf_spec_entropy_64.py`, `pandas_ta/statistics/__init__.py`, `pandas_ta/__init__.py`, `pandas_ta/core.py`, `tests/test_tf_spec_entropy_64.py`, `tests/test_altport2_ports.py`, `README.md`, `docs/IndicatorDictionary.md`, `docs/MLCompanionContract.md`, `docs/TfSpecEntropy64Measured.md`, `docs/measure_tf_spec_entropy_64.py`, `docs/measure_tf_spec_entropy_64_cpu.py`, this run folder | **Gate E**, run by the issue-solver launcher after this session; then a receipt session records the ledger row and replaces `test_the_gate_e_row_is_owed_and_not_yet_recorded` with one pinning the row's identity. **Gate C's real-data limb** comes from the same run. |

22 findings across four rounds — 4 MAJOR, 11 MINOR, 7 NIT, no CRITICAL — and
**all 22 were applied**, including the six that round 4's PASS did not
require. Every verdict is quoted verbatim in `01-tf-spec-entropy-64.md`.

## What the four rounds were about, and it was the same thing each time

**Not one finding in 22 was about the mathematics.** Every round's reviewer
re-ran the whole measurement script and reported each table reproducing to the
digit; round 4 re-ran all fifteen sections and the full suite and matched every
figure in three documents and two docstrings.

What they found, four times running, is the repo's named dominant defect in
one specific shape: **a fix corrects the cited line and leaves the same wrong
claim alive one document away.** The bin-8 sinusoid figure lived in five
places and round 1's fix reached four. The Gate-A oracle count lived in four
and reached three. The §A2 provenance lived in three and reached two. Round 3
then found the pattern one level up — the module docstring quoting a frame
size (1,500) that its own count (137 = 200 - 64 + 1) refuted.

Three things, measured, about what actually stopped it:

1. **Printing the number inside the script is the only repair that holds.**
   Round 4's one substantive finding was a count — "a 1.001 ramp fires on all
   1,436 bars" — that no committed run printed. Putting it in `section_A1`
   did not just verify it; it **falsified the sentence around it**. At
   `step = 1.0000000001` only 1,294 of 1,436 windows fire, because
   consecutive ratios round to the same double. The rule is exact equality of
   the 64 returns, not whether the step is a power of two, and nobody would
   have found that by re-reading.
2. **A test that asserts a docstring's claim must touch the module.** Round 2
   caught one test that only exercised numpy; round 3 caught three more that
   only exercised a test-local copy of the arithmetic, which is the sole
   evidence for two ⚠ paragraphs of the SHIPPED docstring. The fix,
   `test_the_row_helper_is_the_modules_arithmetic`, pins the copy to the
   module bit for bit on seven frames — so a window function added to
   `_spectral_entropy` now breaks the tests that describe its absence.
3. **The audit trail is code and obeys the same guards.** Round 3's MAJOR was
   this run folder itself: quoting a reviewer's unspaced `460/438/.../769`
   verbatim tripped
   `tests/test_pine_coverage_csv.py::test_no_other_document_retypes_the_split`,
   which reads five or more slash-separated integers as a retyped PINEBI
   verdict split. A fourth suite failure, in neither CLAUDE.md's Known breaks
   nor CI's deselect list, i.e. a red PR. Fixed by re-spacing inside the quote
   with the edit disclosed above the block.

⚠ **Still true at the end, and worth the owner's eye:** writing
"3 failed / 9,980 passed" into the round-4 entry — four rounds after being
told, in the sentence summarising those four rounds — and catching it only by
running `python -m pytest -q` again. The log records the slip rather than
hiding it. The real figure is **3 failed / 9,977 passed / 85 skipped**.

## Suites, as run at the end of the loop

* `tests/test_tf_spec_entropy_64.py`: **257 passed**.
* The same **257** under `NPY_DISABLE_CPU_FEATURES="AVX512F AVX512_SKX AVX2
  FMA3"`, via `python docs/measure_tf_spec_entropy_64_cpu.py`, which refuses
  to run unless the dispatch took and prints the features still enabled.
* Full suite: **3 failed, 9,977 passed, 85 skipped** — the two CLAUDE.md
  clean-checkout breaks (`test_pine_coverage_csv.py::test_audited_rows_carry_their_evidence`,
  `test_altrepo_talib_csv.py::test_regenerating_reproduces_the_committed_rows`)
  and the owed Gate E row, which reports `['arch_lm', 'diff2_acf1', 'edge',
  'firstzero_ac', 'halflife', 'lumpiness', 'mtd_ret', 'tf_spec_entropy_64']`.

## Recorded, not fixed (pre-existing, outside this issue's scope)

`pandas_ta/core.py:453` hands out the live `Category[name]` list and
`core.py:692` removes names from it, so running
`tests/test_wiring_accessors.py` before `tests/test_altport2_ports.py` in one
process fails the pinned `CATEGORY_TOTAL`. Reproduced here; alphabetical
collection hides it in a full run. Already recorded by issues #100, #101,
#102, #103 and #118.
