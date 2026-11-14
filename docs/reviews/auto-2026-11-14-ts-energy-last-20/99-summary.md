# auto run 2026-11-14 — `ts-energy-last-20` — summary

| task | status | rounds | files touched | follow-ups |
|---|---|---|---|---|
| `ts-energy-last-20` | see the round table below | 4 returned, which is this review loop's cap | 12, plus this run folder's three — see the Files table in `01-ts-energy-last-20.md` | Gate E, run by the launcher; then a receipt session records the ledger row and replaces `test_the_gate_e_row_is_owed` |

## What shipped

`pandas_ta/statistics/ts_energy_last_20.py` — **`TS_ENERGY_LAST_20_4`**,
the share of a 20-return window's squared-return energy that sits in its
newest 5 bars. tsfresh's
`energy_ratio_by_chunks(num_segments=4, segment_focus=3)` over 20 simple
returns, which is PandasTa issue #102's own formula.

Gates A–D are in `docs/TsEnergyLast20Measured.md`, with
`docs/measure_ts_energy_last_20.py` as the evidence generator and
`docs/measure_ts_energy_last_20_cpu.py` as the reduced-CPU-feature run
(tests, or any named section).

## The two things worth remembering from this run

1. **Gate A is bit-equality, and that decided the implementation.**
   `sliding_window_view` gives each row a stride of one double, so
   `ew.sum(axis=1)` is the same pairwise reduction `np.sum` runs on the
   source's own array: 1,480 of 1,480 bars on each of ten frames and at
   six lengths, masks included, and it survives
   `NPY_DISABLE_CPU_FEATURES="AVX512F AVX512_SKX AVX2 FMA3"`. The
   left-to-right accumulation the first draft used is 3 to 4 ulps away
   and farther from an exact rational oracle on 10 of 10 frames.
2. **The reduced-CPU run is not a formality.** It broke one draft claim
   — the §G4 locality count pinned at exactly 0 bars, now pinned as
   `kept < n`. (§Z's milliseconds were falsified separately, by plain
   full-kernel re-runs of `python docs/measure_ts_energy_last_20.py Z` in
   review rounds 1–3; that script is the only one that times anything.)

## The disclosure the owner has to decide

The fork now ships THREE readings of "where in the last 20 returns was
the volatility": `TFCENTROID_20` (#116, the energy-weighted mean
position), `TS_IMQ_20` (#99, the absolute-mass median position) and this
one (the share in the last quarter). Synthetic Spearman:

* **0.8466** imq/centroid, pooled by #99 over NINE frames —
  **DISCLOSE_GAP** under `r3-perframe-0.90` (0.80 ≤ ρ < 0.90), which is
  what `docs/TsImq20Measured.md` §O says of it (per-frame median 0.8545,
  0 of 9 frames reaching 0.90);
* **0.7493** this/centroid and **0.6093** this/imq, both pooled over this
  receipt's TEN frames, and both **SHIP** (< 0.76).

Gate E cannot see any of the three — its 687 comparators are the
engine's and hold no pandas_ta port.
`docs/TsEnergyLast20Measured.md` §O1 is the receipt.
⚠ An earlier draft of this paragraph called all three SHIP and attributed
all three to ten frames. Review round 4 caught it; it was the only
mislabel left after round 1 corrected the same thing in four other files,
and it was in the one paragraph written for the owner's decision.

## Review rounds

| round | verdict | findings | where |
|---|---|---|---|
| 1 | REVISE | 1 CRITICAL, 4 MAJOR, 5 MINOR | `01-ts-energy-last-20.md` |
| 2 | PASS | 3 MINOR, 3 NIT (all applied) | `01-ts-energy-last-20.md` |
| 3 | PASS | 3 MINOR, 2 NIT (all applied) | `01-ts-energy-last-20.md` |
| 4 | **REVISE** | 1 MAJOR, 2 MINOR, 2 NIT (all applied, and NOT re-reviewed — 4 is the cap) | `01-ts-energy-last-20.md` |

Round 1's CRITICAL is the one to learn from: the receipt quoted a
full-suite count from before its own fix, and the sentence announcing
that fix re-broke the guard it had fixed by quoting the offending string.
Rounds 3 and 4 exist because fixes landed after a PASS, and each of them
found something: round 3 falsified round 2's own replacement claim about
the timing by re-running the section four times, and found a guard test
that excluded the single bar it exists to protect; round 4 then found
that THIS file — written as round 2's fix #6 and never reviewed — told
the owner that 0.8466 was SHIP when it is DISCLOSE_GAP, and that round
3's replacement ratio was above five of the seven runs that measure it.
⚠ **Round 4's five fixes are the only changes in this port that no
reviewer has seen**, because four rounds is this loop's cap. Each is a
sentence, each is listed in `01-ts-energy-last-20.md`, and all five are
checkable against a committed command or a committed file: the band
against `CLAUDE.md`'s Gate E row and `docs/TsImq20Measured.md` §O, the
ratio against `python docs/measure_ts_energy_last_20.py Z`, and the two
remaining ones against `docs/TsEnergyLast20Measured.md` §F and the two
siblings' own source lines. Nothing in the module, the tests' assertions
or the receipt's tables changed in round 4.

## Runs at the end of the run

* `python -m pytest tests/test_ts_energy_last_20.py -q` → 226 passed.
* `python docs/measure_ts_energy_last_20_cpu.py` → the same 226 with
  AVX-512/AVX2/FMA3 disabled.
* `python -m pytest -q` → 3 failed, 8,359 passed, 85 skipped: the
  CLAUDE.md *Known break*, the `../AlternativeRepos`-only test CI
  deselects by name, and the owed Gate E row, which names
  `ts_energy_last_20`.
