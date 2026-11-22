# PREPUSH-R1 — fix the round-1 pre-push review's findings

Task (verbatim, from the invocation): "Fix every CRITICAL and MAJOR finding of the pre-push
review gate (round 1 of 3, HEAD 07813f6bff02) ... fix MINOR/NIT findings only when cheap and
safe." The gate's four findings (one MAJOR, two MINOR, one NIT) are quoted in full in the
invocation and are not repeated here; see the command history.

## Execution log

- Read `docs/QtdRetMeasured.md`, `docs/MLCompanionContract.md:25-40`,
  `tests/test_qtd_ret.py:1-15`, `tests/test_altport2_ports.py:186-197`,
  `docs/gate_e_ledger.csv` (qtd_ret row), `docs/MtdRetMeasured.md` (sibling shape to mirror),
  `tests/test_c22_ami2.py:1335-1358`, `tests/test_j_wae.py:1118-1138` (sibling guard-assertion
  pattern), `docs/measure_qtd_ret.py:1-8` (confirms the script's own docstring says
  `python -m docs.measure_qtd_ret`).
- MAJOR fix: replaced the stale "Gate E pending, run by issue-solver after this session" clause
  with the real DISCLOSE numbers (0.7975 vs `Dist_to_SMA_50_pct`) in all three named locations —
  `docs/MLCompanionContract.md`'s `qtd_ret` parenthetical, `tests/test_altport2_ports.py`'s
  `CATEGORY_TOTAL` comment, and `tests/test_qtd_ret.py`'s module docstring. Added a new guard
  test, `test_the_receipt_carries_the_measured_gate_e_numbers_and_not_the_pending_clause`, to
  `tests/test_qtd_ret.py`, mirroring `test_c22_ami2.py`/`test_j_wae.py`'s pattern: reads
  `docs/QtdRetMeasured.md` and asserts the ledger row's numbers are present and both "pending"
  phrasings are absent.
- MINOR fix (Gate F row): re-ran the exact eight-module subset
  (`python -m pytest -q tests/test_qtd_ret.py tests/test_readme_counts.py
  tests/test_altport2_ports.py tests/test_wiring_accessors.py tests/test_ml_companions.py
  tests/test_gate_e_ledger.py tests/test_pine_coverage_csv.py
  tests/test_prose_counts_match_the_csvs.py`) and got **1362 passed, 7 skipped**, confirming the
  commit message's number before touching anything. Replaced the stale "1 failed, 1354 passed"
  row with this. Re-ran again after adding the new guard test above: **1363 passed, 7 skipped**
  (one more test in the same subset) — recorded the +1 explicitly in the receipt rather than
  silently updating the number, so the arithmetic stays traceable.
- MINOR fix (measure-script invocation): changed `docs/QtdRetMeasured.md`'s "Numbers:" line from
  `python docs/measure_qtd_ret.py` to `python -m docs.measure_qtd_ret`, matching the script's own
  docstring and the sibling `docs/MtdRetMeasured.md`.
- NIT fix (Gate E cell): lifted the dense Gate E table cell into its own
  "## Gate E — measured: DISCLOSE" section (run id, pooled max, per-frame max median,
  reachability, DISCLOSE band reasoning), mirroring `docs/MtdRetMeasured.md:17-57`. Left a
  one-line pointer in the Gate table's E row. Dropped a first draft of a "why this comparator"
  paragraph that speculated about window-length similarity between a quarter and a 50-bar SMA —
  unmeasured and not read from any source, so it would have been exactly the kind of
  claim-before-measurement defect this repo's CLAUDE.md calls out; removed before committing.
- ASSUMPTION: none needed — all four findings named exact locations and fixes in the invocation.

## Review round 1 (this fix round's own first gate)

```
VERDICT: REVISE
FINDINGS:
  - severity: MINOR
    location: tests/test_qtd_ret.py:13
    problem:  The implementer fixed the "run it as a path, not a module" defect in docs/QtdRetMeasured.md:9 (now `python -m docs.measure_qtd_ret`) but left the identical stale command, `python docs/measure_qtd_ret.py`, sitting one paragraph below the edited docstring line (tests/test_qtd_ret.py:13). It's the same bug round 1 flagged, in a sibling location round 1 didn't name but which exists in this same file -- so the "fix" closed the letter of the finding (one file) without closing its substance (the actual wrong command, which still appears in the repo and will mislead a reader who hits this docstring instead of the receipt).
    fix:      Change `the numbers in this docstring are \`python docs/measure_qtd_ret.py\`'s output` to `` the numbers in this docstring are `python -m docs.measure_qtd_ret`'s output `` at tests/test_qtd_ret.py:13, matching docs/QtdRetMeasured.md:9 and the script's own docstring.

SUMMARY: Three of round 1's four findings land cleanly and substantively: the "Gate E pending" MAJOR is gone everywhere I could find it (MLCompanionContract.md, test_altport2_ports.py's CATEGORY_TOTAL comment, and test_qtd_ret.py's header all now quote the real DISCLOSE numbers, and a new guard test mirrors the sibling pattern from test_c22_ami2.py/test_j_wae.py, genuinely runs, and genuinely fails on the old wording per its own asserted sentinels); the Gate F MINOR is fixed with traceable arithmetic (I ran the exact pytest subset myself: 1363 passed, 7 skipped, matching the doc, and the "1362 before this round" claim matches 07813f6's own commit message verbatim -- not a fudge); and the Gate E NIT got its own "## Gate E — measured: DISCLOSE" section in the same shape as the MtdRetMeasured.md sibling, with every number (0.7975080912149055, 0.802193974881588, Dist_to_SMA_50_pct, n=394488, reachability counts, run id is205-qtd_ret-ddf9146b) matching the actual gate_e_ledger.csv row field-for-field -- nothing fabricated. The one loose end is a leftover instance of the exact invocation-path bug round 1 diagnosed, just in a file round 1 didn't name (tests/test_qtd_ret.py's own docstring), left stale while the sibling line in docs/QtdRetMeasured.md got fixed -- cosmetic, but it's a second-round review's whole job to catch a fix that closes the letter of a finding in one place while the same defect survives two lines away in its source file. Fix that one line and this is a clean PASS.
```

### Fixes applied
- `tests/test_qtd_ret.py:13` — changed `python docs/measure_qtd_ret.py` to
  `python -m docs.measure_qtd_ret`, matching `docs/QtdRetMeasured.md:9` and the script's own
  docstring. Re-ran the eight-module subset: 1363 passed, 7 skipped, unchanged.

## Review round 2

```
VERDICT: PASS
FINDINGS:
SUMMARY: The implementing session did exactly what was asked and nothing more: tests/test_qtd_ret.py:13 now reads "python -m docs.measure_qtd_ret", matching docs/QtdRetMeasured.md:9, and that is the only content change in this diff beyond what round 2 already passed. A repo-wide sweep for the stale path-form "python docs/measure_qtd_ret.py" turns up nothing live -- the only remaining hit is a frozen session log (docs/reviews/auto-2026-11-22-b3-qtd-ret/01-B3-QTD-RET.md:28, committed at 96471b4 before this review cycle), which the repo's own established convention treats as immutable history rather than a bug, exactly like measure_qtd_ret_cpu.py. No "Gate E pending, run by issue-solver" text remains anywhere tied to qtd_ret/QTD_RET, every other hit in the repo belongs to unrelated indicators. Every number quoted in docs/QtdRetMeasured.md and tests/test_qtd_ret.py (0.7975080912149055 vs Dist_to_SMA_50_pct n=394,488; 0.802193974881588 per-frame max median; 89 frames; 329+358=687 comparators; 398,849/398,849 non-NaN, 393,683 fires, 0 degenerate; canary tickers; module sha1) matches the docs/gate_e_ledger.csv qtd_ret row and the raw Gate E run artifacts (meta.json, overlap_max.csv, top25.csv, degenerate.csv) bit-for-bit, and the full 25-test suite passes live. Clean.
```

## Outcome

PASS (round 2 of this fix cycle; round 3 of the overall pre-push loop counting the original
gate as round 1).
