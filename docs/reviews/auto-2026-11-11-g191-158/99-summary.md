# Run summary — auto-2026-11-11-g191-158

| task | status | rounds | files touched | follow-ups |
|---|---|---|---|---|
| G191-158 — port GTJA191 alpha #158 as `g191_158` (issue #81) | **DELIVERED, last round's fixes un-re-reviewed** | 4 (cap; verdicts REVISE ×4) | `pandas_ta/volatility/g191_158.py` (new), `pandas_ta/volatility/__init__.py`, `pandas_ta/__init__.py`, `pandas_ta/core.py`, `tests/test_g191_158.py` (new, 26 tests), `tests/test_altport2_ports.py`, `README.md`, `docs/IndicatorDictionary.md`, `docs/MLCompanionContract.md`, `docs/measure_g191_158.py` (new), `docs/G191158Measured.md` (new), this run folder | Gate E (launcher), then the ledger row; round 4's four fixes were applied after the cap and never reviewed |

## What shipped

`G191_158 = (high - low) / close` in `volatility`, scale-free, causal, no
parameters and no warm-up. GTJA191 #158's
`((H-SMA(C,15,2))-(L-SMA(C,15,2)))/C` reduces to it exactly — the source
states the reduction itself — and the port is bit-identical to the
prototype whose Gate E prior issue #81 quotes (`max|diff| = 0.0`, 1,500 of
1,500 bars, against the real candidate out of the gitignored screen's own
registry).

Gates A–D cleared and measured; every number is reproduced by
`python docs/measure_g191_158.py` and recorded in `docs/G191158Measured.md`.
Gate E is **pending, run by the launcher** — `docs/gate_e_ledger.csv` was
not touched, and
`tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
fails naming `['g191_158', 'mtd_ret']`, which is the expected "Owed, not
failed" state.

## The review loop

20 findings over 4 rounds: 1 CRITICAL, 6 MAJOR, 6 MINOR, 7 NIT. **None was a
mathematics error.** Every CRITICAL/MAJOR was the defect CLAUDE.md names as
this repo's dominant one — a claim written before it was measured:

| round | verdict | headline finding |
|---|---|---|
| 1 | REVISE (1C, 3M, 2m, 2N) | a false "unlike every ratio-form port" comparison; the design decision propped on a 14-bar warm-up that is this fork's convention, not the source's; `open == close` in the comparator frame (inflating `pdist/close` to 0.807473); `Returns` claiming "NaN only where an input is NaN" |
| 2 | REVISE (1M, 1m, 2N) | "four sibling GTJA-`SMA` ports" — a volatility count passed off as the fork's |
| 3 | REVISE (1M, 1m, 2N) | "seven" — wrong again; `g191_146` spells the operator inline, invisible to the grep that "counted" it |
| 4 | REVISE (1M, 2m, 1N) | a round-3 review response that reported `fork_overlap_r7.csv` as having no `bw_mfi` row when line 7 names `bw_mfi:MFI_BW_SF_20`; two surviving universals; a wrong description of `g191_109` |

Root cause, after three wrong censuses in three rounds: **this port now
states no fork-wide count at all.** It cites two read lines
(`g191_109.py:101`, `g191_146.py:106-111`) and says why the obvious grep
misleads. Round 4's four fixes landed with the cap spent and were not
re-reviewed; each is logged in `01-g191-158.md` with the read that verifies
it, and `docs/G191158Measured.md` discloses the same.

## Measured, in one place

* Gate A: hand table (6 bars), real screen candidate bit-equal 1,500/1,500,
  literal spelling in both `SMA` spellings (fork's `min_periods`: 1,486
  bit-equal + 14 leading NaNs; source's: 1,500 bit-equal, no warm-up),
  stress frame 50 of 1,486 bars differ at 5.54e-15 relative.
* Gate B: real module leaks 0 of 37 offsets; write-shift and future-range
  mutants each live and caught 37 of 37.
* Gate C: 1,500 of 1,500 non-NaN, first fire bar 0, 1,500 distinct, range
  `[0.000573, 0.044346]`; tick-rounded frame 107 zero-range bars, and the
  column is `0.0` on exactly those; one NaN in any input empties exactly
  that bar.
* Gate D: ×8/×64 bit-identical; ×10/×3.7 max |diff| 2.16e-16 / 1.87e-16;
  volume is not an argument. `fires == n`, so CLAUDE.md's `0 < fires < n`
  is vacuous in its upper half — disclosed, with `nunique > 1` carrying the
  non-degeneracy instead.
* Non-redundancy: `bw_mfi`'s `MFI_BW_SF_20` is this column divided by
  relative volume — bit-identical on constant volume (1,481/1,481), ρ 0.6922
  on varying volume, and bounded by the owner's real-frame 0.8252 (highest
  fork overlap, vs `har_park`).
* Gate F (this repo): 3 failed, 5257 passed, 83 skipped.

## Follow-ups for whoever picks this up

1. **Gate E**, the launcher's run, then
   `python docs/gate_e_ledger.py record <run dir> --measured YYYY-MM-DD`.
   The prototype prior is DISCLOSE_GAP (0.8834 vs `pdist_pct`); if the port's
   run is STRUCK the column is reverted and
   `docs/G191158Measured.md` stays as the receipt.
2. Round 4's four fixes have no reviewer behind them.
3. Two repo-level inconsistencies were found and deliberately NOT fixed here
   (out of scope, and `bw_mfi.py` may not be edited by this session):
   `pandas_ta/volume/bw_mfi.py:85` still prints the superseded Gate E figure
   0.536816 instead of 0.578897, and the comparator count behind that
   measurement is recorded as 492 in `docs/AltportPortsMeasured.md:17` and
   496 in `tests/test_altport2_ports.py:78,200`.
