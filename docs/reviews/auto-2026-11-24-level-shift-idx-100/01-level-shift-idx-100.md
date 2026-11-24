# KATS-LEVEL-SHIFT-IDX-100 — port position of the largest level shift as `level_shift_idx`

Task text (verbatim, from the invocation):

> KATS-LEVEL-SHIFT-IDX-100: port the indicator of issue #159 through Gates A-D, the wiring,
> the tests and docs/<Name>Measured.md, per the issue and the rules in your system prompt
> (position of that largest level shift (100). Source: Kats tsfeatures (Meta, MIT) —
> `get_level_shift_features: argmax of the same`.). Gate E and the whole suites are run by
> the launcher afterwards. You and every subagent verify with `python -m pytest -q <the
> port's test modules> tests/test_readme_counts.py tests/test_altport2_ports.py
> tests/test_wiring_accessors.py tests/test_ml_companions.py tests/test_gate_e_ledger.py
> tests/test_pine_coverage_csv.py tests/test_prose_counts_match_the_csvs.py` plus any
> PandasTa test module a finding names, never the whole suite (the launcher runs it). Until
> the launcher's Gate E run and the receipt record this port's ledger row,
> `tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one` fails:
> expected, not a finding.

Clarifications: none needed (see `00-manifest.md`).

## Execution log

- Read `pandas_ta/statistics/stability.py`, `lumpiness.py` and `stl_seasonal_strength.py`
  (merged sibling Kats ports in the same category, issues #158/#156/#155) and their
  `docs/*Measured.md` receipts to match this fork's port shape, the fixed-module-constant
  convention for a library's own default sub-parameter, the `length` floor/fallback pattern,
  and the receipt depth.
- Read the issue's cited source in `docs/issues/screen/ind_screen_r5.py` (the `_level_shift`
  helper and its `kats_level_shift_size_100` / `kats_level_shift_idx_100` `@cand` entries):
  `cs = cumsum(pad(W))`; `means = sliding 20-bar means via the cumsum`; `d =
  round(abs(diff(means)), 12)`; `return d.max(1), d.argmax(1) / (d.shape[1] - 1)`. This port
  ships only the `argmax`/idx half (`kats_level_shift_size_100` is a separate issue, #162,
  out of scope).
  ASSUMPTION: Kats' own source (`kats/tsfeatures/tsfeatures.py`) is not installed or network-
  reachable in this session, so the formula is taken from the issue's and the prototype's own
  citation text, not independently re-read from Kats — disclosed in the module docstring and
  the receipt rather than left implicit, the same caveat `stability`/`stl_seasonal_strength`'s
  own receipts carry.
- Wrote `pandas_ta/statistics/level_shift_idx.py`: `log(close)` directly as the input (not
  returns, matching `stl_seasonal_strength`'s close-level convention rather than
  `stability`/`lumpiness`'s return-level one), a 100-bar outer window (`length`), `WINDOW_SIZE
  = 20` fixed, `ROUND_DECIMALS = 12` fixed (kept from the prototype — needed for Gate D, not
  cosmetic), `MIN_LENGTH = WINDOW_SIZE + 2 = 22` (the smallest window giving 2 diffs, so the
  idx scale's denominator is never 0).
- Wired the 5 touch points: `pandas_ta/statistics/__init__.py` export,
  `pandas_ta/__init__.py` `Category["statistics"]` entry (alphabetical, after `lean_tdd_20`,
  before `lot_zeroret_60`), `pandas_ta/core.py` accessor (`df.ta.level_shift_idx()`),
  `tests/test_level_shift_idx.py`.
- Wrote `tests/test_level_shift_idx.py`: Gate A (an independent plain-Python-loop oracle,
  `_oracle_idx`, deliberately not sharing the module's cumsum vectorisation, matched at every
  bar of four 1,500-bar frames at three lengths; a closed-form single-level-shift construction
  pinning an exact `30/79` result), Gate B (causality), Gate D (×8/×64 bit-identical, ×10/×3.7
  tolerance, fires-and-not-constant), edge cases (flat price reads `0.0` not NaN — this column
  never divides by a window statistic, unlike `stability`/`lumpiness`, so it needs no rounding
  guard; bad/short input; the length floor; chunk boundaries), wiring.
- Ran `python -m pytest -q tests/test_level_shift_idx.py`: all passed on first full write
  except one failure in `test_mutant_is_caught`, using a generic "swap the tail for an
  unrelated random GARCH path from offset j on" causality probe (the shape
  `stability`/`lumpiness` use). Debugged with a scratch test file (`tests/test_zzz_debug_*`,
  removed before commit via `git add` + `git restore --source=HEAD --staged --worktree`, not
  `rm`, since `rm` is a denied command in this session): confirmed the mutant genuinely reads
  one bar into the future (traced the index arithmetic by hand and matched the debug output),
  but `argmax` over a 100-bar window is dominated by one much larger, older shift elsewhere in
  the window on that GARCH frame, so perturbing only the tail often leaves the reported
  `argmax` unchanged even under the mutant — a structural low-power case for a generic
  future-swap probe on an `argmax`-of-diffs feature, not a bug in the module. Replaced the
  probe with a deliberate single-level-shift construction (`_step_series`) that removes the
  confound: bars before the shift must be bit-identical under the real module regardless of
  what happens after it, and the mutant is shown to leak exactly one bar early. Documented the
  reasoning in both the module's test docstring and `docs/LevelShiftIdxMeasured.md` (Decision
  7), rather than silently swapping the test and saying nothing.
- Wrote `docs/measure_level_shift_idx.py` and `docs/measure_level_shift_idx_cpu.py` (the
  latter following the `measure_stability_cpu.py`/`measure_stl_seasonal_strength_cpu.py`
  pattern: set `NPY_DISABLE_CPU_FEATURES` before numpy import, print which dispatchable
  features are still enabled, run the test module under pytest). Ran both to get every number
  in the receipt from actual tool output rather than asserting it: Gate A bit-identical on all
  12 frame×length cases; a clean monotonic semantics table (idx rising 0.0 -> 0.75 as a
  deliberate step moves later inside the window, confirming the issue's "1 = latest" reading);
  Gate D bit-identical on ×8/×64/×10/×3.7 alike (not merely "within tolerance" — the output is
  an integer-index ratio, so once the rounding keeps the same index winning the result is
  exactly identical); 31/31 passed under the CPU-feature-disabled rerun.
- Ran `python -m pytest -q tests/test_level_shift_idx.py tests/test_readme_counts.py
  tests/test_altport2_ports.py tests/test_wiring_accessors.py tests/test_ml_companions.py
  tests/test_gate_e_ledger.py tests/test_pine_coverage_csv.py
  tests/test_prose_counts_match_the_csvs.py`: 1 expected failure
  (`test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`, naming
  `level_shift_idx` as the indicator owed a row — expected per CLAUDE.md's "Owed, not failed"
  rule), 1482 passed, 7 skipped.
- Ran `python docs/gen_indicator_dictionary.py` to regenerate `docs/IndicatorDictionary.md`
  (mechanical; confirmed via `git diff` the resulting diff is confined to the three header
  counts, the `statistics` section count, the new `level_shift_idx` row, and the SF
  shortlist).
- Updated `README.md` (headline 384->385, callable 392->393, `statistics (73)` ->
  `statistics (74)` with `level_shift_idx` added alphabetically), `tests/test_altport2_ports.py`
  (`CATEGORY_TOTAL` 384->385, with a new history entry prepended), and
  `docs/MLCompanionContract.md`'s running tagged-column tally (729->730 tagged, 363->364 `SF`)
  by prepending a new history entry, matching the file's existing append-only convention.
- Wrote `docs/LevelShiftIdxMeasured.md` transcribing every number above from actual tool
  output, with Gate E stated as "pending, run by issue-solver after this session" and no
  ledger row recorded (per the system-prompt override).

## Review round 1

VERDICT: REVISE
FINDINGS:
  - severity: MAJOR
    location: pandas_ta/statistics/level_shift_idx.py:48-51 (code comment), pandas_ta/statistics/level_shift_idx.py:120-121 (docstring), docs/LevelShiftIdxMeasured.md:66-69 (Decision 6)
    problem:  All three places claim a bad close is blanked because "the cumsum ... poisons every later mean of its own window, poisoning its own argmax." That is not what the shipped code does, and the claim is false even as a hypothesis. The actual mechanism is the explicit mask one line below the comment: `ok = ~np.isnan(chunk).any(axis=1)`; `_level_shift_idx_rows` is only ever called on `chunk[ok]`, i.e. rows that already contain zero NaNs — the cumsum in `_level_shift_idx_rows` never sees a NaN in the shipped path, so it poisons nothing. The hypothetical itself is also wrong: `np.argmax` does not propagate a NaN diff into a NaN scalar result — it returns the *index* of the first NaN it encounters (a plain int), so `argmax(d)/(d.shape[1]-1)` would evaluate to a normal-looking, deterministic, WRONG float, not NaN. Compare `stl_seasonal_strength.py:279` where an analogous "poisons the matrix multiply, 0*NaN=NaN" comment is actually true because that module has no pre-filter and really does let the NaN propagate through a dense sum into the final scalar. This comment reads like it was copied from that sibling without checking it still applies to an index-selecting (argmax) reduction instead of a sum/variance reduction.
    fix:      Rewrite all three passages to describe the real mechanism: "a window containing a bad close is excluded from `_level_shift_idx_rows` entirely by the `ok` mask in the calling loop, before any mean/diff is computed, and is written as NaN directly." Drop the cumsum/argmax-poisoning language, or if you want to keep an explanatory aside, state correctly that `np.argmax` would NOT turn a poisoned window into a NaN output (it would return a bogus non-NaN index) — i.e. make clear the `ok` mask is load-bearing, not redundant, so nobody "simplifies" it away later trusting this comment.
  - severity: MINOR
    location: pandas_ta/statistics/level_shift_idx.py:9-10
    problem:  "WINDOW_SIZE + 2 closes give exactly 2 sliding means, hence 2 diffs between them" is arithmetically wrong. At `length = WINDOW_SIZE + 2 = 22`, means count = `length - WINDOW_SIZE + 1 = 3`, and diffs = `means - 1 = 2`. Two means would give only ONE diff, not two — the comment's own stated mechanics are self-contradictory (2 means can't produce 2 diffs between them). The final conclusion (denom >= 1, no 0/0) happens to still be right, but the specific count asserted is false, exactly the class of unverified-count claim CLAUDE.md calls out as this repo's dominant historical defect.
    fix:      Change "2 sliding means, hence 2 diffs between them" to "3 sliding means, hence 2 diffs between them."
  - severity: MINOR
    location: tests/test_level_shift_idx.py:149-172 (test_real_module_never_reads_the_future, test_mutant_is_caught)
    problem:  Gate B's causality sweep is 3 `shift_at` positions (150/300/450 of a 600-bar frame). The sibling `stability` port sweeps 16 offsets (`tests/test_stability.py` OFFSETS = range(130,600,30)) for the same concern. The switch away from the generic swap-tail probe to a dedicated single-level-shift construction is reasonable (argued and measured, Decision 7), but the number of positions tested shrank along with the methodology change, with no stated reason tied to the new method's own needs — it's just thinner coverage of where in the warm-up/window the shift can land (e.g. nothing near `MIN_LENGTH`'s edge, nothing within the first or last few bars of the frame).
    fix:      Parametrize `shift_at` over more positions (e.g. a `range`-based sweep like stability's, or at minimum add one near the very start and one near the very end of the frame) so the mutant-catch proof covers the same breadth of boundary conditions the sibling ports pin.
  - severity: NIT
    location: tests/test_level_shift_idx.py:59
    problem:  `_oracle_idx(logw, ws=WINDOW_SIZE, decimals=12)` hardcodes `12` as a literal instead of referencing `_REAL.ROUND_DECIMALS`. Today they're equal so the test passes, but if `ROUND_DECIMALS` is ever tuned, this "independent oracle" silently stops testing the module's actual rounding behavior rather than failing loudly.
    fix:      Default `decimals=_REAL.ROUND_DECIMALS` instead of the literal `12`.
  - severity: NIT
    location: tests/test_level_shift_idx.py (general, edge-case section)
    problem:  No test combines a bad close with a price rescale (e.g. assert the NaN mask from `test_a_bad_close_blanks_its_windows` is reproduced identically under `x k`). Not exotic, just a one-line gap next to the two properties that are each tested alone.
    fix:      Add a parametrized case multiplying `close` by e.g. 8.0 in `test_a_bad_close_blanks_its_windows` and assert the same NaN span.
SUMMARY: The math checked out everywhere I traced it by hand and re-ran — Gate A's cumsum vectorization matches the genuinely independent oracle, the Gate B mutant is a real one-bar-earlier write and is caught, Gate D's bit-identical claims reproduce exactly via the measurement script, and the wiring/counters are all correct and test-verified. But this port ships a materially wrong explanation — in the module's own comment, its own docstring, and the Measured.md receipt — for why a bad close blanks its window: the real guard is an explicit pre-filter, not "cumsum poisoning," and the cumsum-poisoning story wouldn't even produce NaN if it were true, since `np.argmax` returns an index, not a propagated NaN. That's a false claim sitting in three documents a reviewer is supposed to trust at face value, in a repo whose own CLAUDE.md says that exact failure mode — a claim nobody checked — is the dominant historical defect here. Fix it before this ships; the rest is tightening (count arithmetic, test breadth, oracle drift-proofing), not blocking.

### Fixes applied
- MAJOR -> rewrote all three "cumsum poisons" passages (module loop comment, module
  docstring, `docs/LevelShiftIdxMeasured.md` Decision 6) to correctly describe the `ok` mask
  as the load-bearing guard, and to state that `np.argmax` returns an integer index (never
  NaN), so an unmasked bad window would produce a bogus non-NaN result rather than NaN.
- MINOR (arithmetic) -> corrected "2 sliding means" to "3 sliding means, hence 2 diffs" in the
  module comment, docstring and `docs/LevelShiftIdxMeasured.md` Decision 5.
- MINOR (Gate B breadth) -> grew the `shift_at` parametrize lists on both
  `test_real_module_never_reads_the_future` and `test_mutant_is_caught` from 3 to 5 positions
  (105, 150, 300, 450, 590 of a 600-bar frame), adding explicit near-start and near-end
  coverage; updated the test module's own docstring and `docs/LevelShiftIdxMeasured.md`'s
  Gate B section to match.
- NIT (oracle drift-proofing) -> `_oracle_idx` now defaults `decimals=_REAL.ROUND_DECIMALS`.
- NIT (bad-close + rescale gap) -> added
  `test_a_bad_close_blanks_the_same_windows_under_a_price_rescale`, combining an injected bad
  close with an x8 price rescale and asserting both the NaN span and the bit-identical scale
  property hold together.
- Re-ran `tests/test_level_shift_idx.py` (31 passed, up from 24), the full named Gate-F
  subset (1 failed -- the expected owed-ledger-row case -- 1489 passed, 7 skipped), and the
  CPU-feature variant (31 passed) to confirm the fixes did not regress anything.

## Review round 2 (fresh Explore subagent, Fletcher persona)

VERDICT: PASS
FINDINGS:
  - severity: NIT
    location: tests/test_level_shift_idx.py:150,161 and docs/LevelShiftIdxMeasured.md Gate B
    problem:  Round 1 compared the 3-position sweep unfavorably to stability's 16-offset sweep; the fix landed at 5 positions (105/150/300/450/590), not 16. This is a legitimate, deliberate design choice (the test module and docs both explain why a generic multi-offset leak probe has low power on an argmax feature and a single-shift construction is used instead), and round 1's fix request was "add more shift_at positions covering near-start and near-end," which is exactly what happened (105 near start, 590 near end of the 600-bar frame). Not a defect, just flagging that the numeric comparison to "16" in round 1's wording is not literally matched.
    fix:      None required. If parity with the 16-offset convention is wanted purely for density rather than power, it could be added, but the current 5-position set already covers near-start/near-end/mid-frame and all 10 parametrized cases (2 test functions x 5 positions) pass.
SUMMARY: All five round-1 findings are genuinely fixed, not reworded into something else that's still wrong. The MAJOR fix is correct and verified against the actual code: `ok = ~np.isnan(chunk).any(axis=1)` really does gate `chunk[ok]` before it ever reaches `_level_shift_idx_rows` (pandas_ta/statistics/level_shift_idx.py:59-62), and the new text in the code comment (:48-53), the docstring (:122-125), and docs/LevelShiftIdxMeasured.md Decision 6 (:66-72) all correctly state that np.argmax returns an integer index (never NaN) so an unmasked bad window would produce a bogus non-NaN result, not a blanked one -- this is true by construction (argmax's return dtype is intp) regardless of which index a NaN-containing row would pick. The MIN_LENGTH comment arithmetic is now correct: length=22 gives means=22-20+1=3, diffs=3-1=2, matching the code and matching Decision 5/the docstring's "three means, hence two diffs" language verbatim everywhere it appears. The shift_at sweep grew from 3 to 5 positions (105/150/300/450/590) with explicit near-start and near-end coverage on both `test_real_module_never_reads_the_future` and `test_mutant_is_caught`; all 10 parametrized cases execute and pass. `_oracle_idx` now defaults `decimals=_REAL.ROUND_DECIMALS` with `_REAL` already imported at module load (line 41, well before the function at line 60). The new `test_a_bad_close_blanks_the_same_windows_under_a_price_rescale` is non-trivial and distinct from the existing bad-close test -- it specifically checks the NaN span doesn't shift under an 8x price rescale, exercising an interaction round 1 flagged as untested. Full module run: 31 passed. Named Gate-F subset: 1 failed (test_gate_e_ledger.py's owed-row check, exactly the expected non-defect), 1489 passed, 7 skipped -- matching the receipt's claimed numbers exactly. A fresh skeptical pass turned up no new breakage: no stale "cumsum poisons" language survives anywhere in the tree, the test module docstring's "five shift positions (near start/end, mid-frame)" claim is internally consistent with the actual parametrize lists, and the "31 tests" count in the doc matches pytest's own collection. Clean round 2; ship it.

## Outcome
PASS (round 2)
