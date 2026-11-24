# stl_spikiness — pre-push review gate, round 2 of 3

Input: the gate's verbatim contract (VERDICT: REVISE, HEAD e47d2a5f170d) with one MAJOR,
two MINOR and two NIT findings.

## Fixes applied

- **MAJOR** (`docs/StlSpikinessMeasured.md` Decision 1): the Hyndman/shipped algebraic
  relationship was stated backwards (claimed "Hyndman = shipped x n(n-2)^2/(n-1)^3"; the
  correct direction is "shipped = Hyndman x n(n-2)^2/(n-1)^3", equivalently
  "Hyndman = shipped x (n-1)^3/(n(n-2)^2)"). Flipped the subject, kept the same numeric
  factor (0.98980 at n=100) per the gate's own suggested fix (option 2). Checked against
  the gate's own numeric example (r=[0,0,0,4], n=4: shipped=192/81=2.3704, Hyndman=4.0,
  shipped/Hyndman=16/27=0.5926=n(n-2)^2/(n-1)^3 at n=4) before committing to the edit.
- **MINOR** (ddof attribution): re-scoped the `ddof=1`-on-both-legs pairing to Hyndman's R
  `tsfeatures` only (R's `var()` default), explicitly flagged the Kats Python
  transcription's own `ddof` as not independently re-confirmed this session (no network
  access), and added the ddof=0-both-legs alternative factor
  (`(n-1)^4/(n^2(n-2)^2)`) to show the rank-identity argument survives either choice.
- **MINOR** (Gate F count mismatch, 1544 vs 174): re-ran the named subset fresh this round
  — `1544 passed, 7 skipped` — matching the receipt, not the round-1 task log's "174". Did
  not edit `docs/reviews/auto-2026-11-24-kats-stl-spike-100/01-stl-spikiness.md` (this
  session's file-scope rules make `docs/reviews/**` new-files-only); instead added a note
  in `docs/StlSpikinessMeasured.md`'s Gate F section naming the round-1 task log's "174" as
  a transcription error and pointing at this round's fresh 1544/7 re-run as the correct
  figure.
- **NIT** (`tests/test_stl_spikiness.py::test_matches_statsmodels_stl` docstring): changed
  "EVERY window ... (301 fits, ~0.15s)" to "300-351 fits depending on `length`", since the
  test is parametrized over lengths 50/100/101 (351/301/300 fits respectively), not just
  the length-100 case.
- **NIT** (`docs/StlSpikinessMeasured.md`, tests paragraph): changed "Two test functions
  (four parametrized cases)" to "Two test functions (four cases in total)" — only one
  function is actually parametrized (3 cases); the other is a plain test (1 case).

## Re-review

Dispatched a fresh read-only `Explore` reviewer against the same 5 points, with
instructions to independently re-derive the Decision 1 algebra (not trust this session's
framing) and to actually run the named test subset rather than trust the stated count.

Verdict returned: **PASS**, with one NIT — a redundant trailing sentence in Decision 1
restating the "not re-confirmed against Kats" caveat a second time two sentences later.
Fixed: deleted the redundant sentence (the caveat is stated once, where the ddof
alternative is discussed).

Re-ran the required subset after that last edit: `1544 passed, 7 skipped` (repo root):

```
python -m pytest -q tests/test_stl_spikiness.py tests/test_readme_counts.py \
    tests/test_altport2_ports.py tests/test_wiring_accessors.py \
    tests/test_ml_companions.py tests/test_gate_e_ledger.py \
    tests/test_pine_coverage_csv.py tests/test_prose_counts_match_the_csvs.py
```

`tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one` passes (the
launcher's Gate E run and the receipt already recorded this port's ledger row in an earlier
session); this is expected, not a finding, per this session's rules.

## Status: PASS (round 2)

No further REVISE round needed — the re-review's only finding was a NIT, already fixed and
re-verified green.
