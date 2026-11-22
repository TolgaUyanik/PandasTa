# Brutally Honest Review — ytd-ret (round 2)

**Date:** 2026-11-20
**Target:** docs/YtdRetMeasured.md, docs/measure_ytd_ret.py, docs/reviews/2026-11-20-ytd-ret-review.md (re-review of round 1's CRITICAL/MAJOR findings and of the files changed since)
**Type:** text (receipt) + code (measurement script)
**Verdict:** PASS

## Round-1 MAJOR — status

- **docs/YtdRetMeasured.md "Fork overlap" (unreproducible synthetic numbers, unattributed 0.85 line)** — RESOLVED. `docs/measure_ytd_ret.py` now has `overlap()`, and `python -W ignore -m docs.measure_ytd_ret` prints every quoted number. The 0.85 cutoff is attributed and kept separate from the issue's 0.90 line.

## Findings

### MINOR / NIT
- **MINOR — docs/YtdRetMeasured.md, "Synthetic only" paragraph** — The 0.85 cutoff is now attributed, but only to "the screening task's own rule". No file or issue in the repo records that task, so a reader can't check where the threshold came from. "Per-frame median |ρ|" can also be read as "every frame's |ρ| below 0.85". It actually means the median across the 12 frames. That matters here because one frame reaches 0.8582 against `MADISP_200_SMA`, above 0.85.
  - Fix: Either name where the 0.85 rule lives (file path or issue number), or cut it and judge the synthetic screen only against the issue's 0.90 line. Reword to "median across the 12 frames of per-frame |ρ| ≥ 0.85; one frame reaches 0.8582, the median is 0.7853".
- **NIT — docs/YtdRetMeasured.md:60 and pandas_ta/performance/ytd_ret.py:54** — The round-1 NIT about "(#205 asks for the quarter form)" was not addressed. `docs/MtdRetMeasured.md:92` already makes the same cross-reference, so this is consistent with the repo, but neither file gives #205's title.
  - Fix: Add #205's title (e.g. "#205, B3-QTD-RET") in both places, or leave it as is to match `MtdRetMeasured.md`.

## Summary

The round-1 MAJOR is fixed. `docs/measure_ytd_ret.py` now has an `overlap()` function: 12 seeded frames of 1,500 business days from 2015-01-01, prices rounded to 0.1, per-frame Spearman correlation. The reviewer ran `python -W ignore -m docs.measure_ytd_ret` from the repo root and it printed every number the receipt quotes. The Gate A–D figures match: 900/279/621, 0.332203/−0.281170/−0.037828, 899 offsets with leak counts 0/896/4, 260 NaN bars, bit-identical at ×8/×64, 2.22e-16 at ×10/×3.7. The overlap figures also match: `MADISP_200_SMA` and `MADISPSQ_200_SMA` both 0.7853 with range 0.6235–0.8582, `PCTRET` 126/189/252/63 at 0.7376/0.7039/0.6852/0.6420, `MTD_RET` 0.3391. The 0.85 line is now attributed to a source and kept apart from the issue's 0.90 line, though the source can't be checked from the repo. Two round-1 MINORs are also fixed: the issue's real fork-overlap result (0.7678 vs `MADISPSQ_200_SMA` on the prototype, per-frame median 0.7670) is restored with a note that the port itself has not been measured, and the Gate F row now gives the full command with `GATE_E_PENDING_OK=1` and explains the "Gate E owed" skip. `GATE_E_PENDING_OK` is `1` in this environment. No CRITICAL or MAJOR findings are left. The two items above are wording fixes, not blockers.

## Reviewer's caveats

- The reviewer did not re-run the Gate F pytest set or regenerate the dictionary. The module, tests and wiring are unchanged since round 1 and were not reviewed again.
