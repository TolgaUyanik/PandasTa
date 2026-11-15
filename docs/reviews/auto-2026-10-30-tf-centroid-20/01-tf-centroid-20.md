# Task — TF-CENTROID-20

**Status:** PASS (round 2) · **Rounds:** 2

## Implementation summary

Ported TSFEL's `calc_centroid` (BSD-3-Clause) as `pandas_ta.statistics.tf_centroid_20`:
`TFCENTROID_length = sum(t * ret^2) / sum(ret^2)` over the last `length` (default 20)
bars, `ret` = simple returns of `close`, `t = 0..length-1` rescaled to `0..1`. Wired all
five touch points (module, `statistics/__init__.py` export, `Category["statistics"]`,
`core.py` accessor, `tests/test_tf_centroid_20.py`), updated the three cross-checked
count documents (`README.md`, `docs/MLCompanionContract.md`,
`tests/test_altport2_ports.py::CATEGORY_TOTAL`), regenerated
`docs/IndicatorDictionary.md`, and wrote `docs/TfCentroid20Measured.md` with Gates A, B,
D measured and Gate C (synthetic only); Gate E marked PENDING per the overriding
instruction that the launcher runs it after this session.

A real bug was found and fixed during implementation, not during review: the first draft
used `close.pct_change()` with pandas' default `fill_method="pad"`, which forward-fills a
NaN close before differencing instead of propagating the gap — caught by
`test_warmup_and_nan_propagation` failing, fixed to
`close.pct_change(fill_method=None)`. Documented in `docs/TfCentroid20Measured.md`'s "A
bug Gate D's own environment caught" section.

Full local test suite: 3,272 passed, 83 skipped, 3 failed — 2 pre-existing and unrelated
(`test_altrepo_talib_csv.py`, `test_pine_coverage_csv.py`, both documented in `CLAUDE.md`
"Known breaks") and 1 new, expected, by-design (`test_gate_e_ledger.py`'s "no row yet"
check, since Gate E is deferred).

## Round 1

Dispatched a Fletcher reviewer (`Explore` subagent, read-only) against the 10-file
touch-point set. Verdict: **REVISE**.

```
VERDICT: REVISE
FINDINGS:
  - severity: MAJOR
    location: docs/TfCentroid20Measured.md:3-6, 86
    problem:  The headline status line and the Gate F table row both claim all 3 test failures on this branch are "the pre-existing, pre-this-change known breaks." One of the three, `test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`, is not pre-existing: it is a direct, new consequence of this PR. Before this change every `Category` indicator has a ledger row or a grandfathered exemption (confirmed by reading `tests/test_gate_e_ledger.py`'s `_needs_a_row()` logic), so that test is green on a clean checkout. This PR puts `tf_centroid_20` into `Category` with no ledger row — correctly, since Gate E is deferred — and that is exactly what flips `missing` non-empty and fails the test. Labeling a self-caused failure "pre-existing, pre-this-change" in the one document whose entire job is to stop exactly this kind of overclaim is the dominant historical defect this repo's own CLAUDE.md calls out, reproduced inside the receipt meant to prevent it.
    fix:      Rewrite the Gate F line to state plainly: "2 pre-existing known breaks (unrelated) + 1 new, expected failure caused by this port (`test_gate_e_ledger.py`, no ledger row yet because Gate E is deferred)." Do not fold the self-caused failure into "pre-existing."
  - severity: MINOR
    location: docs/TfCentroid20Measured.md:83
    problem:  Gate C quotes precise point statistics on the synthetic walk — range `0.2270 .. 0.7640`, mean `0.5007`, median `0.5015`, and "1,180 distinct values" — none of which are asserted anywhere in `tests/test_tf_centroid_20.py`. The only related assertion, `test_column_is_not_constant`, checks `fires == 1180` and `nunique() > 1000`, a much looser bound. A regression that quietly changed the actual distribution (while staying inside `[0,1]`, keeping `fires == 1180`, and keeping `nunique` above 1000) would pass the suite untouched while these quoted numbers silently went stale.
    fix:      Either add explicit assertions in the test file pinning these exact figures (min/max/mean/median/`nunique() == 1180`), or soften the doc's wording to "measured once, not pinned by a test" so the Gate C row does not read as more verifiable than it is.
SUMMARY: The math, causality proof, and scale-free proof are all solid — the TSFEL formula is reproduced faithfully, the `t` rescaling to `[0,1]` is disclosed prominently in three places rather than buried, the mutant genuinely proves a one-bar look-ahead would be caught, and all five wiring touch points plus every cross-document count (README/MLCompanionContract/test_altport2_ports/IndicatorDictionary) line up correctly. But the receipt document — the one artifact whose entire purpose is to stop unmeasured claims from shipping — itself ships one: it calls a brand-new, self-inflicted test failure "pre-existing, pre-this-change" instead of naming it as what it is. That is not a nitpick in a repo whose own CLAUDE.md says the dominant historical defect is a claim written before it was measured; it is that defect, recurring inside the exact document meant to prevent it. Fix the mislabel and tighten Gate C's unpinned statistics before this ships.
```

### Fixes applied

1. **MAJOR** — rewrote `docs/TfCentroid20Measured.md`'s status line and Gate F row to
   split the 3 failures explicitly: 2 pre-existing/unrelated, 1 new/expected/caused-by-
   this-port (not a regression).
2. **MINOR** — `tests/test_tf_centroid_20.py::test_column_is_not_constant` now asserts
   the exact min/max/mean/median (via `pytest.approx`) and `nunique() == 1180`, pinning
   every number the Gate C row quotes. Re-ran the test file to confirm the pinned values
   are exactly what the module produces: 14 passed.

## Round 2

Re-dispatched a fresh Fletcher reviewer against the fixed files, with both round-1
findings and their claimed fixes stated for verification, plus instruction to
re-examine the full file set for anything missed. Verdict: **PASS**.

```
VERDICT: PASS
FINDINGS:
  - severity: NIT
    location: pandas_ta/statistics/tf_centroid_20.py:73
    problem: `np.where(den > 0.0, num / np.where(den > 0.0, den, 1.0), np.nan)` computes `den > 0.0` twice and wraps the divisor in its own `np.where` purely to dodge a `0/0` warning that `errstate(invalid="ignore")` already suppresses two lines up.
    fix: Collapse to `centroid = np.where(den > 0.0, num / den, np.nan)` — the `errstate` context already makes the extra guard dead weight.
  - severity: NIT
    location: pandas_ta/statistics/tf_centroid_20.py:55
    problem: The length guard is `length and length > 1 else 20`, diverging from every sibling statistics indicator's `length > 0` idiom (see `stdev.py:9`, `mad.py:8`) without a comment explaining why `length=1` is excluded (division by `length-1` in the `t` axis would be `0/0`).
    fix: Add a one-line comment at that guard noting `length=1` is rejected because `t = arange(length)/(length-1)` is undefined at `length=1`, so a future editor doesn't "fix" it back to the fork's usual `> 0` threshold and reintroduce a divide-by-zero.
SUMMARY: Both round-1 findings are genuinely closed, not cosmetic. The Gate F status line and table row now correctly split the three failures into two pre-existing/documented breaks (both independently confirmed in `CLAUDE.md`) and one new, expected, by-design failure caused by this port's deliberate deferral of its Gate E ledger row — an honest statement, not a dodge. The Gate C point statistics are no longer unaccountable prose: `test_column_is_not_constant` now pins the exact min (0.22703367476493705), max (0.7639855682057195), mean (0.5007277309366513), median (0.5015225423847335) and `nunique() == 1180`, and every one of those numbers matches what the doc quotes to four decimal places — they will go red the day the doc goes stale instead of rotting silently. A second pass over the full file set (module, test, both `__init__.py`s, `core.py`, `test_altport2_ports.py`, `README.md`, `MLCompanionContract.md`, `IndicatorDictionary.md`) turned up nothing beyond two style nits. That was acceptable. Barely.
```

### NIT fixes applied (not required for PASS, applied anyway)

1. Collapsed the redundant double `np.where`/`den > 0.0` check in
   `pandas_ta/statistics/tf_centroid_20.py` to `num / den` under the existing
   `errstate` context.
2. Added a one-line comment on the `length > 1` guard explaining why `length=1` is
   rejected (the `t` axis divides by `length - 1`).

Re-ran `tests/test_tf_centroid_20.py` (14 passed) and the full suite (3,272 passed, 83
skipped, same 3 expected failures) after applying the NIT fixes.
