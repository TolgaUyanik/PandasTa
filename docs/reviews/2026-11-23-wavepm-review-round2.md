# Brutally Honest Review — wavepm port (issue #261), round 2

**Date:** 2026-11-23
**Target:** docs/MLCompanionContract.md, tests/test_altport2_ports.py, docs/WavepmMeasured.md, pandas_ta/volatility/wavepm.py, tests/test_wavepm.py, docs/reviews/2026-11-23-wavepm-review.md
**Type:** code (plus a text receipt)
**Verdict:** PASS

Scope: (1) check that every round-1 CRITICAL/MAJOR is resolved; (2) look for new problems in the
files changed since round 1.

## Findings

### MINOR / NIT
- **MINOR — tests/test_wavepm.py:22-24 (module docstring, item 1)** — The round-1 fix added a new "Gate A is OWED" warning at lines 9-12, but the old caveat inside item 1 was left in place. It still ends "so Gate A is against the issue's transcription of finta, not against finta's line numbers; the issue's definition is the contract here." That sentence says Gate A was met, with the issue text as the contract. It contradicts the OWED warning a dozen lines above it, and it is the exact wording round-1 MAJOR (a) objected to.
  - Fix: Delete the "⚠ finta's source itself was not readable ... the issue's definition is the contract here." sentence from item 1. Lines 9-12 already state the gap correctly.
- **NIT — docs/WavepmMeasured.md §G, last sentence ("A mask was written, measured as a no-op, and deleted.")** — This history claim has nothing behind it. The script has no mask variant, the round-1 report does not mention one, and the sentence cannot be checked from this tree. The table proves the real point without it: ±inf is bit-identical to a NaN plant with no mask, and `measure_wavepm.py` G prints that. So the sentence is an unverifiable extra on a receipt that says "Every figure below is printed by that script".
  - Fix: Delete the sentence. "There is no mask: pandas' rolling windows already return NaN over an infinity" already says everything that matters, and it is measured.
- **NIT — docs/WavepmMeasured.md §W / Z ("two runs printed 8–10 ms and 33–35 ms")** — The parenthetical gives exact digits for past runs. The reviewer's run of section Z printed "9 .. 9 ms" and "36 .. 37 ms", and 36-37 falls outside the quoted 33–35. The round-1 NIT asked for less false precision, and the fix added a new exact-digit claim that a rerun already contradicts.
  - Fix: Drop the parenthetical and keep "about 10 ms / about 35 ms on this machine, varying from run to run". Or quote it as a band that covers the runs seen so far (8–10 ms, 33–37 ms).
- **NIT — pandas_ta/volatility/wavepm.py:55** — The docstring line inserted for the Gate A note is 87 characters, while every other docstring line wraps at 79 or fewer.
  - Fix: Re-wrap the paragraph so line 55 ends at "cited here." and "The ProRealCode port, which" starts the next line.

## Summary

Both round-1 MAJORs are resolved. (a) Gate A is now marked "owed (source unread)" in all four places that were asked for: the CATEGORY_TOTAL comment, the MLCompanionContract #261 clause, the receipt's title block and "does NOT establish" list, and the test docstring. The module docstring also says so, and the receipt says outright that issue #261 stays open and the port is NOT cleared through A–F. (b) "0.5502", "14 frames" and "pre-port" appear nowhere in the receipt, test, module or script. The round-1 MINOR is fixed: the `mean-lead`-on-`flat` reason now correctly says sigma = 0 before the split, so r = rms = 0. The NIT is half-fixed: the timing digits are softened, but a new exact-range parenthetical came with them. Every number in docs/WavepmMeasured.md was checked against a fresh run of A1 A4 B C D F G L M W Z, and all reproduce digit for digit except the machine-dependent timings. The targeted suite passes (130 passed, 3 skipped). What remains is cleanup: a leftover sentence in the test docstring still calls the issue text "the contract", which undercuts the OWED label the fix added; there is an unverifiable mask-history line in §G, a stale timing range and one over-long docstring line. None of these blocks the port, but fix the test-docstring contradiction before merging. It is the same false impression the round-1 MAJOR was about.

Not checked by the reviewer: the full repo suite and the Backtesting suite (Gate F), and finta's source. Gate A against finta is still owed, so issue #261 must stay open (use "Refs", not "Closes").
