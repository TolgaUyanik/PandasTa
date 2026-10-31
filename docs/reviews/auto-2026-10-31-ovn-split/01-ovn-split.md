# Task: ovn_split (issue #14, OVN)

## Implementation summary

Ported the issue's "rolling sums of the close->open (overnight) and open->close (intraday)
returns, as two columns; optionally their difference" as `pandas_ta/momentum/ovn_split.py`,
emitting `OVNSUM_{length}`, `INTSUM_{length}`, `OVNINTDIFF_{length}` (default length 21). Wired
through all five touch points (module, `momentum/__init__.py`, `Category`, `core.py` accessor,
`tests/test_ovn_split.py`). Gates A/B/D cleared with measured numbers; Gate C synthetic only
(no real BIST data in this headless worktree); Gate E and both repos' suites deferred to the
launcher per this session's rules. Full writeup, every ASSUMPTION, and the issue's own
"risk, check first" gap (not measurable here -- no network/data access) are in
`docs/OvnSplitMeasured.md`. Doc-count touch-ups: README.md, docs/IndicatorDictionary.md
(regenerated), docs/MLCompanionContract.md, tests/test_altport2_ports.py (CATEGORY_TOTAL
248 -> 249).

## Review round 1

Dispatched a Fletcher `Explore` reviewer (read-only) against the full file list, with the
original ask verbatim and explicit review instructions covering: math correctness, the Gate B
mutant harness, Gate D tolerances, every measured number in `docs/OvnSplitMeasured.md`
(reproduced live via `python docs/measure_ovn_split_proxy.py`), wiring completeness, doc-count
arithmetic, and honesty about what was deferred/not measured.

```
VERDICT: REVISE
FINDINGS:
  - severity: MAJOR
    location: docs/OvnSplitMeasured.md:95 (Gate A row)
    problem:  The documented Gate A max|diff| for OVNSUM at length=21 is given as `4.16e-17`,
      but running the reproduction command actually prints `1.388e-17` for OVNSUM at
      length=21 (the `4.16e-17` figure is in fact INTSUM's value, duplicated into OVNSUM's
      slot) -- exactly the "typed, not computed" failure mode the measured-doc discipline
      exists to prevent.
    fix:      Re-run the script, copy the printed value verbatim, correct the OVNSUM triple.
  - severity: MINOR
    location: docs/OvnSplitMeasured.md:95 (Gate A row)
    problem:  The row says "on a 400-bar overnight/intraday walk" but the quoted n-counts
      (1,179/1,191/1,198) only arise from the script's actual 1,200-bar default walk.
    fix:      Change "400-bar" to "1,200-bar" to match the n-counts already in the sentence.
SUMMARY: The engineering is sound -- math, bar-0 alignment, the Gate B mutant harness, Gate D
  tolerances, all five wiring touch points, and the honesty about the unmeasured
  yfinance/BIST risk and deferred Gate E all check out and reproduce exactly -- but a wrong
  number sat in the one document whose entire reason for existing is that every number in it
  is computed, not typed.
```

## Fixes applied

Corrected the OVNSUM triple in `docs/OvnSplitMeasured.md`'s Gate A row to
`1.39e-17 / 2.08e-17 / 8.67e-18` (matching the script's actual printed output) and changed
"400-bar" to "1,200-bar" to match the quoted n-counts.

## Review round 2

Re-dispatched a Fletcher `Explore` reviewer scoped to verifying the specific fix (re-run the
script, diff every number in the Gate A row against its actual output) plus a spot check of
the rest of the file.

```
VERDICT: PASS
FINDINGS: (none)
SUMMARY: Both round-1 defects are genuinely fixed, not just reworded -- the Gate A OVNSUM/INTSUM
  triples now match the script's actual digit-for-digit output (within correct 3-sig-fig
  rounding), and the "1,200-bar" walk description is now arithmetically consistent with the
  quoted n-counts. A full re-run of docs/measure_ovn_split_proxy.py and a spot check of the rest
  of the table (Gate C ranges, Gate D tolerance, pre-screen Spearman values) against the doc
  turned up nothing newly broken; this row is clean.
```

**Status: PASS at round 2 of 3.**
