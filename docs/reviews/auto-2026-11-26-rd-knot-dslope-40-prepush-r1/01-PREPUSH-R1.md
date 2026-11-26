# PREPUSH-R1 — fix the round-1 pre-push review's findings

Task (verbatim, from the invocation): "Fix every CRITICAL and MAJOR finding of the pre-push
review gate (round 1 of 3, HEAD 767ad83806fa) ... fix MINOR/NIT findings only when cheap and
safe." The gate's five findings (two MAJOR, two MINOR, one NIT) are quoted in full in the
invocation and are not repeated here; see the command history.

## Execution log

- Read `pandas_ta/statistics/rd_knot_dslope_40.py`, `docs/RdKnotDslope40Measured.md`,
  `pandas_ta/statistics/level_shift_size.py` (the Decision-3 ratio device cited by the finding),
  `tests/test_rd_knot_dslope_40.py`, `docs/measure_rd_knot_dslope_40.py`,
  `docs/MLCompanionContract.md` and `tests/test_altport2_ports.py`'s `#175` clauses,
  `tests/test_gate_e_ledger.py` (to understand exactly how a module-sha1 change interacts with
  a recorded ledger row), `docs/gate_e_ledger.csv` (the `rd_knot_dslope_40` row).
- MAJOR-1 fix (Gate D): changed `rd_knot_dslope_40.py` to fit the hinge on
  `log(raw_windows / raw_windows[:, :1])` instead of `log(close)` directly — the
  `level_shift_size` ratio-to-first-bar device. Verified the IEEE-754 argument empirically, not
  just algebraically: re-ran `docs/measure_rd_knot_dslope_40.py`, x8/x64 now measure **0.0** max
  abs/rel diff (was ~1.2–1.8e-15), x10/x3.7 tightened too (~6e-17 vs ~1.3e-15 before, since the
  ratio form carries less rounding even off the exact-rescale path). Split
  `test_scale_stays_within_a_tiny_tolerance` into `test_price_scale_is_bit_identical` (x8/x64,
  real `==`, not `np.isclose`) and a narrower tolerance test (x10/x3.7 only). Re-ran Gate A's
  oracle and hand-derived tests — both still pass (max |diff| vs the independent `lstsq` loop
  moved from 3.662e-15 to 2.661e-15, expected since the oracle still fits on raw `log(close)`
  while the module now fits on the ratio; both are the same `c_best` up to float noise, which is
  exactly what Gate A's job is to confirm). Rewrote Decision 6, the Gate D section, the module
  docstring's SCALE-FREE paragraph, and the test module's docstring to the measured result.
- MAJOR-2 (the two "Gate E: pending" fossils): the literal fix the finding asked for — replace
  both clauses with the recorded SHIP numbers — turned out to be the wrong move once MAJOR-1
  landed. The recorded ledger row (`is175-rd_knot_dslope_40-eef638c4`, SHIP 0.7012) measured the
  module at sha1 `de923cbcbbd6e0a32213680d8adde855750765dd`; MAJOR-1's fix moved the module to
  sha1 `f48afaf88e993671fa92390428b7bee35b8b6406`. Writing the SHIP text into those two fossils
  would have been exactly the defect CLAUDE.md calls out repeatedly — a claim that no longer
  matches the tree it's attached to. Instead: deleted the stale row from
  `docs/gate_e_ledger.csv` (a deleted row "counts as owed too", per CLAUDE.md), left the two
  "Gate E: pending, run by issue-solver after this session" clauses as-is (now true again, not
  stale), and updated only their math description (bit-identical x8/x64, not "~1.8e-15,
  transcendental, not claimed bit-identical") in `docs/MLCompanionContract.md`. Confirmed
  `tests/test_altport2_ports.py`'s `#175` clause already said "pending" (never got rewritten to
  SHIP in the receipt commit, so no edit needed there) — rechecked it still matches the new math
  claim implicitly (it doesn't restate the Gate D numbers, so nothing to update).
  `docs/RdKnotDslope40Measured.md`'s own Gate E section was rewritten from a SHIP table to an
  explicit "pending again" narrative naming both sha1s, the prior run's numbers (kept for audit,
  not reused as current truth), and the reason (CLAUDE.md's ledger-row rule), so the reasoning
  is on disk, not just implied by an edit.
- MINOR fix (range cell): `-0.0186..0.0192` → `-0.0186..0.0198`, matching Gate C's own ten-seed
  measurement (max 0.019822) — which is also what the re-measured Decision-6 run reproduced
  exactly (same NaN masks, same seed ranges, since OLS's own invariance holds up to float
  noise).
- MINOR fix (Gate C real-data counts): added them, but with the caveat the MAJOR-2 resolution
  forces — those counts (`non_nan` 395,378, `non_zero` 395,378 of 398,849) were measured against
  the PRE-Decision-6 module, not the one this file now describes, so they are stated as
  "expected to carry over, not re-claimed until the re-run confirms it" rather than flat fact.
- NIT fix (Status line): not the literal "Gates A–F measured, SHIP" the finding asked for
  (Gate E is owed again after MAJOR-1/2), but the true current state: "Gates A, B, C, D, F
  measured, SHIP; Gate E owed again" with a pointer to Decision 6 for why.
- Also fixed, not separately asked for but necessary for internal consistency once Gate E
  reverted to pending: Gate F's pass count (1,622 passed/0 failed → **1,614 passed, 1 failed, 7
  skipped**, the 1 failure being `test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`,
  called out explicitly as expected per CLAUDE.md's "Gate E owed, not failed" rule rather than
  left as an unexplained red), the "Counters touched" section's stale SF-tag description, and a
  markdown line-wrap bug that split a sha1 across two lines inside a backtick span.
- Regenerated `docs/IndicatorDictionary.md` after the arithmetic change — empty diff, confirming
  the column's tag/warm-up/range classification is unaffected by a same-value float-noise
  change, and recorded that (not "nothing changed, trust me") in the Measured.md.
- Ran `python docs/measure_rd_knot_dslope_40_cpu.py` (AVX512F/AVX512_SKX/AVX2/FMA3 disabled) —
  still 20 passed, confirming the new bit-identical test isn't an artifact of this machine's
  dispatched kernels.
- ASSUMPTION: the MAJOR-2 resolution above (revert to "pending" rather than write SHIP) is the
  one judgment call this round required without a way to ask the owner; most conservative
  reading taken (never assert a measurement against a tree it no longer describes).

## Review round 1 (this fix round's own first gate)

```
VERDICT: PASS
FINDINGS:
SUMMARY: Decision 6 does what the MAJOR finding actually demanded -- fits the hinge on `log(raw_windows / raw_windows[:, :1])`, the exact `level_shift_size` ratio device, and I confirmed it independently: `test_price_scale_is_bit_identical` uses real `==`, not `np.isclose`, measured 0.0 abs diff on 1,561 cells, sha1 checked at both ends (`de923cb...` pre-fix, `f48afaf8...` post-fix, matching the ledger row and the docstring exactly), and the IEEE-754 argument for why a power-of-two rescale survives division bit-for-bit is correct and holds up against the fork's own prior art. The second MAJOR did not get patched with a cosmetic string replace -- the session correctly recognized that changing the module's arithmetic moved its sha1, which by this repo's own `test_gate_e_ledger.py` and CLAUDE.md's "owed, not failed" rule makes the recorded Gate E run describe a tree that no longer exists; deleting that row and reverting both "pending" fossils back to true is the only non-fraudulent move available, and it's written down auditably in the Gate E section with both sha1s, not just asserted. I ran the full gate list myself: 1,614 passed, 7 skipped, exactly the one named `test_gate_e_ledger.py` failure, with the fail message naming `rd_knot_dslope_40` and pointing at the re-run command -- not a silent or unexplained red. Both MINOR fixes landed (`-0.0186..0.0198`, Gate C counts with an honest "pre-Decision-6 module" caveat) and the NIT was upgraded rather than cargo-culted -- "Gates A,B,C,D,F measured; Gate E owed again" is the true statement, not the literal text the round-1 reviewer asked for before the rework made it stale. Nothing here is theater. That was acceptable. Barely.
```

## Outcome

PASS (round 1 of this fix cycle; round 2 of the overall pre-push loop counting the original
gate as round 1).
