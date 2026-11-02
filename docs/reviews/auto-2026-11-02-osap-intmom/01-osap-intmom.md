# Task: osap_intmom port (issue #40)

## Implementation summary

Ported `osap_intmom` — intermediate momentum, OSAP SignalDoc `IntMom` (Novy-Marx 2012,
OSAP t 5.79), formation window months t-12..t-7 — into
`pandas_ta/momentum/osap_intmom.py`. Formula: `INTMOM = close.shift(126) /
close.shift(252) - 1`, near_length=126 ("t-7" boundary, 6*21 trading days), far_length=252
("t-12" boundary, 12*21 trading days) — the identical arithmetic
`docs/issues/screen/ind_screen.py`'s `osap_intmom` candidate row states
(`delay(c,126)/delay(c,252)`), and the identical arithmetic `osap_mrrev` #37's own module
docstring had already independently derived as cross-candidate corroboration before this
port existed. Same telescoping-return identity `osap_mrrev` relies on (a cumulative return
over a price window reduces to the ratio of its endpoints).

Five touch points: module, `pandas_ta/momentum/__init__.py` (export),
`pandas_ta/__init__.py` → `Category["momentum"]` (alphabetically before `osap_mrrev`),
`pandas_ta/core.py` → `AnalysisIndicators.osap_intmom` accessor, `tests/test_osap_intmom.py`
(14 tests: 2 correctness, 4 warm-up/offset/fillna, 2 causality, 3 scale-free, 1 wiring,
plus the hand-derived and independent-loop checks folded into "correctness").

Gates A-D cleared this session (all measured, not asserted — see
`docs/OsapIntmomMeasured.md`): Gate A rests on the telescoping identity plus the issue's
own 126/252 conversion, cross-checked against `osap_mrrev`'s prior independent derivation
of the identical arithmetic (disclosed as corroboration, not proof — the primary OSAP
SignalDoc remains unreachable in this worktree). Gate B: 33-offset future-perturbation
sweep past the 252-bar warm-up, real module 0/33 leaks, an 8-bar look-ahead mutant
(`close.shift(near_length - 134)` instead of `close.shift(near_length)`) caught 33/33.
Gate D: bit-identical under close x8/x64, within 2.22e-16 under x10/x3.7 (well inside the
asserted 1e-9 tolerance), 648 of 900 synthetic bars fire (72.00%), 648 distinct values.
Gate E is pending — the launcher runs it after this session, per the overriding rules in
this session's system prompt; the issue's own prototype-level Gate E number (DISCLOSE, max
|ρ| 0.7610 vs `Mom_12_1_pct`) is recorded in `docs/OsapIntmomMeasured.md` as context, with
an explicit note that it measures the *prototype*, not this port's module, and must not be
quoted as this port's result.

Updated: README.md (headline 272→273, accessor count 280→281, `momentum (62)`→`momentum
(63)` row), `docs/IndicatorDictionary.md` (regenerated), `docs/MLCompanionContract.md`
(618→619 tagged columns, 262→263 `SF`, chain entry appended), `tests/test_altport2_ports.py`
(`CATEGORY_TOTAL` 272→273).

Files touched: exactly the 7 allowed-to-modify paths plus 4 new files (module, test,
`docs/OsapIntmomMeasured.md`, `docs/measure_osap_intmom.py`) — within the one-new-module
cap and the stated file scope.

## Review round 1

Dispatched Fletcher reviewer (`Explore` subagent, read-only, bash + file access) against:
the 4 new files, the 7 modified files' diffs, and the `osap_mrrev` precedent (module,
test, Measured.md) plus `CLAUDE.md`'s Gate table. Instructed to independently re-run
`docs/measure_osap_intmom.py` and the targeted test suites and cross-check every number in
`docs/OsapIntmomMeasured.md` against actual output, not just read and guess.

**VERDICT: PASS**

FINDINGS:
- severity: NIT
  location: docs/issues/screen/candidates.csv:96
  problem: The candidates.csv row for osap_intmom carries trailing fields "new,issue 039,039" — a stale/mismatched issue tag (039 instead of 040) in a file outside this session's edit scope.
  fix: Not this session's defect and not in the allowed file-scope list; flag it for whoever next touches ind_screen.py/candidates.csv so the tag gets corrected to 040 — do not fix it here since candidates.csv isn't in this port's touch-list.
- severity: NIT
  location: pandas_ta/momentum/osap_intmom.py:16-22 / docs/OsapIntmomMeasured.md Gate A section
  problem: The docstring's Gate A disclosure is near-verbatim boilerplate lifted from osap_mrrev's docstring (same identity paragraph, same ASSUMPTION paragraph, same hedge sentence), which is defensible given the issue explicitly wants the identical derivation chain reused, but it does make the two modules read as copy-paste twins rather than independently-reasoned ports.
  fix: No action required for this port — the reuse is correct and disclosed (it explicitly cites osap_mrrev #37 as the prior derivation) — but a future session auditing "claim written before it was measured" should be aware the two docstrings are intentionally duplicated, not two independent derivations.

SUMMARY: This port is clean. The arithmetic (near_length=126/far_length=252, 6*21/12*21)
traces exactly to the issue's own restatement and the prototype's
`delay(c,126)/delay(c,252)` row, with the identity/assumption split correctly disclosed as
non-circular. The Gate B mutant string appears exactly once in the module, the mutant's
shift(126-134)=shift(-8) is a genuine 8-bar look-ahead, and OFFSETS=range(400,1225,25) is
verifiably 33 elements, all past the 252-bar warm-up. Every number quoted in
`docs/OsapIntmomMeasured.md` was confirmed to match the actual script output bit-for-bit.
Wiring is complete and consistently alphabetized across all touch points, and the
CATEGORY_TOTAL/MLCompanionContract arithmetic chain is internally consistent and
test-verified. Full suite: 4173 passed, 83 skipped, exactly the same 3 pre-existing
failures documented in CLAUDE.md, none caused by this port. File scope respected exactly.

**Both NITs not actioned** (consistent with this repo's prior review rounds, e.g.
`lot_zeroret_60` #39's round 3: a NIT is recorded, not acted on, unless it changes a
shipped claim).

## Round count

1 round (PASS on round 1).
