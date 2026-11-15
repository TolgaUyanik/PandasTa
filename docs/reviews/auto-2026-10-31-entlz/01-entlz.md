# Task: ENTLZ (issue #11)

Port the entropy-of-sign-encoded-returns indicator through Gates A-D, the wiring, the
tests and `docs/EntlzMeasured.md`. Gate E and both repos' suites are the launcher's job.

## Implementation summary

- `pandas_ta/statistics/entlz.py`: `entlz(close, length=20, base=2, offset=0)` — plug-in
  Shannon entropy of `np.sign(close.diff())` over a trailing `length`-bar window, 3-symbol
  alphabet `{-1, 0, +1}`. Column `ENTLZ_{length}`.
- Wiring: `pandas_ta/statistics/__init__.py` (export), `pandas_ta/__init__.py`
  (`Category["statistics"]`), `pandas_ta/core.py` (`.entlz()` accessor).
- Tests: `tests/test_entlz.py`, 22 tests (correctness vs. an independent reference loop and
  3 hand-computed closed forms; causality via a deterministic single-bar sign-flip mutant
  test, 2 look-ahead mutants caught 32/32; scale-free at x8/x64/x10/x3.7 all bit-identical;
  bounded; reachability; edges; wiring).
- Measurement script: `docs/measure_entlz_proxy.py` (Gate A/C/D numbers + an informal,
  explicitly-NOT-Gate-E pre-screen against in-package candidates).
- Receipt: `docs/EntlzMeasured.md` — Gates A, B, D PASS; C synthetic only; E PENDING (the
  launcher's job); logs the 4 open design decisions (sign vs. quantile encoding, plug-in
  vs. LZ estimator, window length, 3- vs. 2-symbol alphabet) as ASSUMPTIONs, since
  AskUserQuestion was unavailable in this headless session.
- Counter bumps: `README.md`, `docs/IndicatorDictionary.md` (regenerated),
  `docs/MLCompanionContract.md`, `tests/test_altport2_ports.py` (`CATEGORY_TOTAL`
  248 -> 249).

## Assumptions (logged per issue-solver's "no AskUserQuestion" override)

1. Encoding: sign, not k quantile bins (no causality-fit surface needed).
2. Estimator: plug-in, not Lempel-Ziv/Kontoyiannis (issue says plug-in is simplest).
3. Window: `length=20` (matches this fork's short-lookback defaults; untuned).
4. Alphabet: 3 symbols from `np.sign` (`{-1,0,+1}`), not a 2-symbol tie-broken version.

All four are the smaller-scope reading in each case, and are recorded in
`docs/EntlzMeasured.md`'s "Decisions the issue left open" section, not silently assumed.

## Review rounds (Fletcher / Explore, verbatim)

### Round 1 — REVISE

```
VERDICT: REVISE
FINDINGS:
  - severity: MAJOR
    location: docs/EntlzMeasured.md:56 (Gate B row)
    problem: The sentence "a pilot run of this test showed: 29/32 and 29/32 caught, not
    32/32, using the whole-tail-replacement convention pfe/cusum use" is a specific,
    quantified empirical claim with no backing artifact anywhere in the repo. [...]
    fix: Either delete the specific "29/32" figures [...] or actually re-run the pilot,
    commit the throwaway script (or keep it as a commented-out variant in the test file)
    so the exact count is reproducible, and only then restate the number.
  - severity: NIT
    location: pandas_ta/statistics/entlz.py:33-43
    problem: three separate O(n) rolling passes, one per symbol.
    fix: not required; fine as-is at this n and length.
  - severity: NIT
    location: tests/test_entlz.py
    problem: no test exercises a non-default base.
    fix: add one assertion at base=10.
SUMMARY: [...] you buried one invented-sounding number in the one gate that exists
specifically to prove causality [...] Fix that one line [...] and this ships.
```

**Fix applied:** added `_leaks_random_future` + `test_the_random_future_convention_ties_on_this_alphabet`
(parametrized over both mutants, pins 29/32 reproducibly) and
`test_matches_the_reference_loop_at_a_non_default_base` to `tests/test_entlz.py`; reworded
`docs/EntlzMeasured.md`'s Gate B row to cite the test by name instead of asserting a bare
number.

### Round 2 — REVISE

```
VERDICT: REVISE
FINDINGS:
  - severity: MAJOR
    location: docs/EntlzMeasured.md:51, docs/EntlzMeasured.md:60
    problem: The round-1 fix added three tests [...] raising it from 19 to 22 [...] Nobody
    re-ran the suite to update the doc's own counts: line 51 still reads "tests/test_entlz.py:
    19 of 19 passing" and the Gate F row still reads "1 failed, 3,520 passed, [...]." I ran
    both: pytest tests/test_entlz.py -q -> 22 passed; the full suite [...] -> 1 failed, 3523
    passed, 83 skipped, 2 deselected. Both doc numbers are now flatly wrong [...]
    fix: Re-run both suites, then update line 51 to "22 of 22 passing" and the Gate F row to
    "1 failed, 3,523 passed, 83 skipped, 2 deselected." Consider also updating [...] the
    manifest's matching lines [...].
SUMMARY: [...] you fixed one lie and let two smaller ones grow back in the same document
[...] Fix the two numbers, rerun the suites one more time before you call it closed [...]
```

**Fix applied:** re-ran `tests/test_entlz.py` (22 passed) and the full suite with CI's two
deselects (1 failed, 3,523 passed, 83 skipped, 2 deselected); updated both numbers in
`docs/EntlzMeasured.md` and in `00-manifest.md`.

### Round 3 — PASS

```
VERDICT: PASS
FINDINGS: (none)
SUMMARY: The number finally holds [...] every digit in docs/measure_entlz_proxy.py's output
[...] reproduces the doc to the decimal. The manifest no longer contradicts the receipt doc,
the review-rounds log is honest about both prior screwups, and the wiring [...] is clean
[...] Ship it.
```

## Outcome

PASS at round 3 (of the 3-round cap). Status: DONE as a ship-pending-Gate-E — not blocked.
`docs/EntlzMeasured.md` is the receipt; `tests/test_gate_e_ledger.py`'s one failure for
`entlz` is expected and clears once the launcher's Gate E run is recorded by a later
session.
