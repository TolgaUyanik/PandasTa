# Task 01 — fix pre-push gate findings for C22-RS-RANGE

## What was wrong (round-1 gate verdict, HEAD `939de55741c7`)

- MAJOR: `docs/measure_c22_rs_range.py`'s bare invocation imported and called
  `pycatch22` (GPL-3.0, dev-only, not an `install_requires` dependency) with no
  `importlib.util.find_spec` guard, inverting the discipline
  `docs/measure_c22_ami2.py` / `docs/measure_c22_periodicity.py` already use.
- MAJOR: an "isolation" claim (that the DFA-sibling breakpoint search with a
  "trusted" `log_f_dfa` separates "wrong F(tau)" from "wrong extraction") was
  asserted in the harness's prints, the receipt's §A3/§E, and the prior commit
  message, while §A2 itself only ever sanity-checked `log_f_dfa`'s AR(1)
  ordering — never that it is the reference's own F(tau). The inference does
  not follow from the measurement.
- MAJOR: the receipt's §B said "there is no candidate formula that reproduces
  the named feature" — a universal claim — while only 10 structural hypotheses
  (2 F(tau) × 5 criteria) were tried, and the textbook Peng et al. DFA-2
  construction plus an obvious global-profile-range variant were never run
  against the rs_range reference at all.
- MINOR: `log_f_rs_classical` used `ddof=0` while the text credited it to
  `g191_165`, which uses `ddof=1`.
- MINOR: the "Spearman ρ" column was position-tie-broken (`argsort(argsort)`),
  not true midrank Spearman, overstating what was computed on a lattice where
  ties are frequent by construction.
- NIT ×4: a stray quote mark, an undercounted sample total (96 vs the true
  120 the section actually draws), a table caption describing the wrong unit
  of selection, and a self-contradicting "Gates B–F were not attempted" next
  to a section titled "Gate F — suites" reporting a run.

## What was done

1. `docs/measure_c22_rs_range.py`:
   - `DEFAULT = ["FSANITY"]`; `TAU` and `SEARCH` are opt-in, each gated by
     `importlib.util.find_spec("pycatch22") is None` → print ABSENT and
     return, before any `import pycatch22`. Module docstring updated to
     describe the opt-in invocation.
   - Removed the isolation/causal-inference language from `section_search`'s
     closing prints; replaced with a plain report plus an explicit caveat
     that the DFA-sibling run does not isolate F(tau) from the extraction
     step.
   - Added two new `F(tau)` variants to `f_variants`: `log_f_dfa` (the Peng
     et al. DFA-2 construction itself, previously built but never run
     against rs_range) and a new function `log_f_range_global` (same global
     polynomial-detrend machinery, per-box RANGE statistic instead of RMS —
     the literal "rsrangefit" reading). Re-ran SEARCH: now 4 × 5 × 4 = 80
     combinations; the ceiling is unchanged at Pearson ρ = 0.364
     (range-order-0, connected, min_side=12) — both new variants top out at
     |ρ| ≤ 0.156.
   - `log_f_rs_classical` now uses `ddof=1`, matching
     `pandas_ta/statistics/g191_165.py:134`.
   - Added `_midrank` (average rank within tied groups); `_spearman` now uses
     it instead of position-broken ranks.
2. `docs/C22RsRangeMeasured.md`: updated §0 to describe the opt-in harness
   discipline; §A2's table to the new `ddof=1` FSANITY numbers; §A3's table
   to the 16-row, 80-combination result (every cell re-verified against the
   harness's own printed output across two review rounds — two "connected"
   rows for the new DFA-family variants were wrong on the first pass and
   corrected to match the harness exactly); §A3/§E's isolation language
   removed and rescoped to what the runs actually support; §B's claim
   rescoped from "no candidate formula" to "no candidate among the 20
   hypotheses tried"; the four NIT text issues fixed.

## Verification

- `python -m pytest -q tests/test_readme_counts.py tests/test_altport2_ports.py tests/test_wiring_accessors.py tests/test_ml_companions.py tests/test_gate_e_ledger.py tests/test_pine_coverage_csv.py tests/test_prose_counts_match_the_csvs.py` → **1282 passed, 7 skipped** (unchanged — no module/wiring touched).
- `python docs/measure_c22_rs_range.py` (bare) → runs FSANITY only, no
  `pycatch22` import, numbers match the receipt's §A2 table.
- `python docs/measure_c22_rs_range.py TAU` and `... SEARCH` → numbers
  cross-checked against the receipt by two independent reviewer passes.

## Review rounds

- Round 1 (this fix round's own gate, not the pre-push round quoted in the
  invocation): REVISE — 2 MAJOR (two `§A3` table rows picked the wrong
  `min_side`, one self-contradicting the receipt's own narrative sentence).
  Fixed by recomputing both cells directly from the harness's printed
  output.
- Round 2: PASS.

## Files touched

`docs/measure_c22_rs_range.py`, `docs/C22RsRangeMeasured.md`. No module,
wiring, or test file added or changed — this issue remains a measured revert.
