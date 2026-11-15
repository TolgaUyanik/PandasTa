# Fletcher review — trend_scan (round 1)

VERDICT: PASS

FINDINGS:
  - severity: MINOR
    location: docs/measure_trend_scan_proxy.py:154 ("anchor choice" block, `local_ref = window - window[0]`)
    problem: The block claimed to measure whether a window-local P_ref (the issue's literal wording) gives the identical (slope, t) as the shipped series-wide anchor, but computed `window - window[0]` (subtracting two already-logged values) instead of a fresh `log(raw_window / raw_window[0])` ratio — a different floating-point pathway than the ratio-then-log device Gate D is built around. The reported |diff| (1.332e-15) was an artifact of that shortcut, not evidence about a genuine per-window recompute.
    fix: Recompute `local_ref` as a fresh ratio of raw prices per window. Applied; see commit.
    outcome: fixed
  - severity: MINOR
    location: docs/reviews/auto-2026-10-31-trendscan-20/00-manifest.md (Phase 2 — Clarify)
    problem: Phase 2 said "No other gaps" and called the Gate D ratio-anchor fix "unambiguous," but the port deliberately overrides the issue's literal "P_ref taken inside the window" instruction with one series-wide anchor. That override was disclosed in the module docstring and the Measured doc, but not logged in the one document whose job is to enumerate every place the issue's literal text was not followed.
    fix: Add a second Phase 2 bullet naming the anchor-locality override as an ASSUMPTION/reasoned deviation. Applied; see commit.
    outcome: fixed

SUMMARY: Math, causality, and the Gate B forward mutant all verified by hand and by running the suite — correct. The `measure_trend_scan_proxy.py` numbers reproduced to the last digit against the module docstring and Measured doc at review time. Wiring, scope, and disclosure (horizon-set assumption, SLOPE_40 proxy ceiling) all clean. Two MINOR findings — a proxy measurement computing the wrong floating-point pathway, and a manifest omission — both fixed in place; re-measured numbers (max |diff| 2.1e-14, still exact-arithmetic-equivalent) now back the claim they always should have.
