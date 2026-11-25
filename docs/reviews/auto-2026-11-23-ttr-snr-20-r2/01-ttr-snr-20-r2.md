# Task log — TTR-SNR-20-R2

## Round 1 (given, not re-run) — pre-push review gate, HEAD `7f3a2cfe6481`

```
VERDICT: REVISE
FINDINGS:
  - severity: MAJOR
    location: docs/MLCompanionContract.md:27 (`#149`'s `ttr_snr_20` clause)
    problem:  The ML contract of record says "Gate E pending, run by issue-solver after this session" for `TTR_SNR_20`, in the same commit tree whose `docs/gate_e_ledger.csv` carries a live SHIP row and whose `docs/TtrSnr20Measured.md` says "Gates A-F cleared". The contract that downstream readers consult therefore declares this column unmeasured when `gatee/is149-ttr_snr_20-608253f6` measured it. Every sibling clause in the same sentence (#146, #145, #144) states its verdict, comparator, run id and date -- this one is the only one lying.
    fix:      Replace "Gate E pending, run by issue-solver after this session" with the measured verdict in the sibling clauses' exact shape: "Gate E SHIP, 0.5640 vs `BB_BWidth_Pctl` (per-frame max median 0.5654), run is149-ttr_snr_20-608253f6, measured 2026-11-23". Leave the rest of the clause alone.
  - severity: MAJOR
    location: tests/test_altport2_ports.py:196 (`CATEGORY_TOTAL = 380` rationale comment)
    problem:  The pinned-count rationale reads "+1 on issue #149's ttr_snr_20 port (volatility; signal-to-noise ratio, |20-bar move| / ATR(20); Gate E pending, run by issue-solver after this session; see docs/TtrSnr20Measured.md)". This comment exists so an accidental `Category` edit fails loudly with a readable history; a history entry that misreports Gate E state is the thing the pin was built to prevent. Same stale string, same tree, live SHIP row.
    fix:      Rewrite the #149 clause to "Gate E SHIP, 0.5640 vs `BB_BWidth_Pctl` (per-frame max median 0.5654), run is149-ttr_snr_20-608253f6, measured 2026-11-23; see docs/TtrSnr20Measured.md", matching the #146/#145/#144 clauses beside it.
  - severity: MAJOR
    location: tests/test_ttr_snr_20.py:27-28 (module docstring, "Wiring" bullet)
    problem:  The port's own test module ends its docstring with "Gate E is owed: the launcher runs it after this session." The launcher has run it; the verdict is SHIP and the ledger row is committed in this very tree. The test file is the first thing a maintainer reads when this column breaks, and it tells them a gate is outstanding that is closed.
    fix:      Replace that sentence with the measured verdict, e.g. "Gate E: SHIP, max |rho| 0.5640 vs `BB_BWidth_Pctl` (per-frame max median 0.5654), run is149-ttr_snr_20-608253f6, measured 2026-11-23; see docs/TtrSnr20Measured.md." -- the same correction #146 applied to `tests/test_msw_sine.py`.
  - severity: NIT
    location: docs/measure_ttr_snr_20.py:224-233 and :304-314
    problem:  `walk()` here omits the `+ 1e-6` wick floor that `tests/test_ttr_snr_20.py:_ohlc_walk()` applies, so the doc's Gate A/C/D numbers come from a generator that is not quite the one the suite pins (both happen to land on 1,180 fires, so nothing is contradicted). In the frozen-after-volatile probe, `n = 60` is dead, and the freeze level is hard-coded `np.full(30, 100.0)` instead of the test's `lead[-1]`, putting a price jump at the join that the test deliberately does not have.
    fix:      Import or duplicate the test's exact `_ohlc_walk` (wick floor included), drop the unused `n = 60`, and freeze at `lead[-1]` so the script probes the same series the test asserts on.
SUMMARY: [...] Fix the three strings to the SHIP you actually measured and this ships; until then the repository contradicts itself about whether the gate it just cleared is open.
```

## Fixes applied (main thread, commit `853f1ea`)

- `docs/MLCompanionContract.md`: #149's `ttr_snr_20` clause rewritten from "Gate E pending, run
  by issue-solver after this session" to "Gate E SHIP, 0.5640 vs `BB_BWidth_Pctl` (per-frame max
  median 0.5654), run is149-ttr_snr_20-608253f6, measured 2026-11-23" -- exact fix text supplied
  by the gate.
- `tests/test_altport2_ports.py`: `CATEGORY_TOTAL`'s #149 clause rewritten the same way.
- `tests/test_ttr_snr_20.py`: docstring's "Wiring" bullet no longer carries the Gate E sentence;
  a new standalone bullet states "Gate E: SHIP, max |rho| 0.5640 vs `BB_BWidth_Pctl` (per-frame
  max median 0.5654), run is149-ttr_snr_20-608253f6, measured 2026-11-23".
- `docs/measure_ttr_snr_20.py` (NIT, cheap+safe so fixed too): `walk()`'s `hi_wick`/`lo_wick` now
  add the same `+ 1e-6` floor as the test's `_ohlc_walk()`; the frozen-after-volatile probe drops
  the dead `n = 60` and freezes at `np.full(30, lead[-1])` instead of a hard-coded `100.0`, so
  there is no artificial price jump at the join that the test does not have.

Targeted suite run after the fix:
```
python -m pytest -q tests/test_ttr_snr_20.py tests/test_readme_counts.py \
  tests/test_altport2_ports.py tests/test_wiring_accessors.py tests/test_ml_companions.py \
  tests/test_gate_e_ledger.py tests/test_pine_coverage_csv.py tests/test_prose_counts_match_the_csvs.py
-> 1447 passed, 7 skipped
```
CPU-restricted rerun (`NPY_DISABLE_CPU_FEATURES='AVX512F AVX512_SKX AVX2 FMA3'` via
`docs/measure_ttr_snr_20_cpu.py`, this machine's AVX512F/AVX512_SKX/AVX2/FMA3 set):
```
python docs/measure_ttr_snr_20_cpu.py -> 21 passed
```

## Round 2 — gate re-run (fresh `Explore` subagent, read-only, Fletcher persona)

```
VERDICT: PASS
FINDINGS:
  - severity: NIT
    location: tests/test_ttr_snr_20.py:28-30 (vs. tests/test_msw_sine.py:3-7, tests/test_msw_lead.py module docstring)
    problem:  The round-1 fix turned the stale "Wiring bullet ends with Gate E is owed" text into a standalone "* Gate E: SHIP, ..." bullet inside the "What these tests pin" list. The two directly adjacent sibling ports (#146 msw_sine, #145 msw_lead) instead state their Gate E verdict in the docstring's lead-in paragraph, before the "What these tests pin" list even starts, and do not give Gate E its own bullet in that list at all. The fix is internally correct and not factually wrong, but it diverges from the house style of the two nearest siblings it's supposed to match "the shape of."
    fix:      Either leave it as is (harmless), or for consistency move the "Gate E: SHIP, ..." sentence up into the docstring's lead-in paragraph (next to the "Measurements in docs/TtrSnr20Measured.md" sentence on line 5-6) the way test_msw_sine.py and test_msw_lead.py do, and drop the separate bullet.
SUMMARY: The round-1 fix is exactly what it claims to be, and nothing about it is invented. docs/MLCompanionContract.md's #149 clause, tests/test_altport2_ports.py's CATEGORY_TOTAL rationale, and tests/test_ttr_snr_20.py's docstring all now say "Gate E SHIP, 0.5640 vs BB_BWidth_Pctl (per-frame max median 0.5654), run is149-ttr_snr_20-608253f6, measured 2026-11-23" verbatim, and those figures reconcile exactly against docs/gate_e_ledger.csv's ttr_snr_20 row (0.5639743099556117 / 0.5653972212054249, run id and date match) and docs/TtrSnr20Measured.md (same numbers, same run id, Gate table and "Closed" section agree). docs/measure_ttr_snr_20.py's walk() now applies the same `+ 1e-6` floor to both hi_wick and lo_wick as tests/test_ttr_snr_20.py's `_ohlc_walk()`, the dead `n = 60` is gone, and the frozen-after-volatile probe freezes at `np.full(30, lead[-1])` with no leftover hard-coded jump or unused variable -- a repo-wide grep for #149/ttr_snr_20/TTR_SNR_20 combined with "pending"/"owed"/"run by issue-solver after this session" turns up nothing live outside the frozen historical review transcript (which correctly describes the pre-fix state as of its own timestamp, not the current tree). Full targeted test run (test_ttr_snr_20.py, test_altport2_ports.py, test_ml_companions.py, test_gate_e_ledger.py) passes 1336/1336 with 0 failures. The repository now states exactly one true thing about this port's Gate E status everywhere it is mentioned; the only loose thread is a cosmetic docstring-placement inconsistency against the two nearest sibling ports, not worth blocking on.
```

Round 2 is PASS. Stop per the review-loop rule ("stop early on PASS"). The NIT (docstring
placement vs. sibling ports) is left as-is -- cosmetic, not worth a third round.
