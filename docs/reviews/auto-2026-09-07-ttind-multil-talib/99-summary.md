# Run summary — TTIND · MULTIL · TALIB (2026-09-07/08)

**3 review rounds run, the cap. Two groups PASS-worthy on their own artifacts;
the batch as a whole is ESCALATED — round 3 found the recurring defect had
migrated into the one scanner nobody hardened.**

| task | status | rounds | artifacts | outstanding |
|---|---|---|---|---|
| TTIND-0 | ✅ done | 3 | `gen_altrepo_tti.py`, `altrepo_tti.csv`, `test_altrepo_tti_csv.py` (11) | — |
| TTIND-1 | ✅ done | 3 | same CSV; signal layer recorded per row | — |
| TALIB-0 | ✅ closed, superseded | — | — | — |
| TALIB-2 | ⚠ ESCALATED | 3 | `gen_altrepo_talib.py`, `altrepo_talib.csv`, `test_altrepo_talib_csv.py` (8) | `CORREL` unmeasured; one guard cannot fail |
| TALIB-1 | ⚠ NOT EXECUTED | — | shortlist of 8 named in `00-manifest.md` | needs Gate E (a `../Backtesting/` measurement, out of scope this batch) |
| MULTIL-0 | ✅ done | 3 | `multil_length_grid.csv`, `multil_kept_set.csv`, `multil_universe.csv`, `test_multil_length_grid.py` (13) | — |
| MULTIL-1/-2 | moved | — | now in `Backtesting/TODO.md` | owner deferred (Q1) |
| PTCLASSIC (collateral) | ⚠ ESCALATED | — | `altrepo_pandas_ta_classic.csv` | see below |

Suite at close: **1318 passed / 22 skipped**.

---

## The one defect this run kept producing

**A false gap entry: an indicator published as absent while the fork ships it.**
Eight separate occurrences across three rounds, every one the same root cause —
the probe harness called fork functions in exactly one narrow way (default
kwargs, close-only inputs, default windows), so anything reachable another way
looked absent.

| round | artifact | false absences |
|---|---|---|
| 1 | tti | `ad` `adosc` `mom` `roc` `pvt` `massi` `donchian` `pvo` |
| 1 | ta-lib | `CORREL` |
| 2 | tti | `TimeSeriesForecast` `VolumeRateOfChange` |
| 2 | ta-lib | `LINEARREG_ANGLE` `LINEARREG_SLOPE` |
| 3 | pandas-ta-classic | `linregslope` `linregangle` `correl` |

Round 3's are the instructive ones: rounds 1–2 hardened the tti and TA-Lib
scanners and **left the pandas-ta-classic scanner untouched** — the largest of
the three, 224 rows. The defect simply moved there, and the two shipped CSVs
began contradicting each other about the same fork function (`LINEARREG_SLOPE`
`have` in one, `linregslope` `port` in the other).

Measured against the fork, 260 bars:

```
linregslope  vs linreg(slope=True)               1.829e-14
linregangle  vs linreg(angle=True, degrees=True) 1.035e-12
correl       vs correlation                      0.000e+00
talib.CORREL vs correlation                      7.836e-12
```

## What was fixed after round 3

- **The classic scanner gained kwargs variants and a two-series channel.** Its
  gap fell 38 → 33; the whole `linreg` family left the gap.
- **The gap note stopped lying.** All 38 rows carried "no counterpart on the
  fork's Category, df.ta or module surface" — false for **15 of 38**, since
  `linreg`, `correlation`, `dm`, `roc`, `eom`, `decay`, `adx` and `stoch` are
  all on that surface. It now states what was actually searched.
- **`Backtesting/TODO.md`'s kept set was drifted and is now bound.** It
  published `rsi` keep `7 28` under "this is the list MULTIL-1 wires, and
  nothing else" while the CSV said `7 50` — the write-back predated a tie-break
  fix and nothing tested it.
  `test_the_backtesting_writeback_matches_the_kept_set` now fails if they
  diverge.

## OUTSTANDING — what a fourth round would fix

1. **`correl` / `CORREL` are still not measured.** Both CSVs carry
   `unknown - not comparable`; the true answer is `have` (0.0 and 7.8e-12). The
   two-series probe landed in the classic scanner but the classify path does not
   reach it.
2. **The classic scanner still has no pinned-window retry**, so the four
   `linreg` rows read `port - alternate impl` when at a matched window they are
   `have` (1.8e-14). They are no longer false *absences*, but they are still the
   wrong verdict.
3. **`test_a_mapped_name_is_never_reported_as_absent` cannot fail.** It looks
   for `port` rows with a non-empty equivalent; the only code path emitting
   `port` hard-codes an empty one. The guard written to stop the CORREL defect
   is structurally incapable of catching it.
4. **The gap guards are backward-looking allowlists.** They pin names already
   caught by a reviewer. They cannot catch occurrence nine.
5. **`_tail_diff` promotes to `have` on a tail agreement with no degeneracy
   check**, and `ravel()`s multi-column frames into a meaningless interleaving.
   Three rows ride that path today and all three are genuine.
6. **Only `IndicatorList.md` is generated and guarded.** Counts in the manifest
   and both `TODO.md` files are hand-typed and bound to nothing — which is
   exactly where the `rsi` drift happened.

## The honest read

The scanners are far better than they started: behavioural comparison instead of
name-diffing, column-aware matching, degeneracy and identity guards, environment
stamping, and 40 guard tests that did not exist. Three of the four measurement
methods were wrong on their first attempt and were caught by measurement, not by
argument.

But **the count published as "the gap" has been wrong in every single round**,
including this one, and the guards protecting it are allowlists of yesterday's
mistakes. Until a `port` verdict is derived by re-running the resolver inside
the test — the fix named in finding 4 — the next false absence will ship green
too.
