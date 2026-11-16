# auto run 2026-11-16 — J-SAFEZONE-DIST — summary

| task | status | rounds | files touched | follow-ups |
|---|---|---|---|---|
| `J-SAFEZONE-DIST` (issue [#121](https://github.com/TolgaUyanik/PandasTa/issues/121)) | **done, no post-fix PASS** — four review rounds, 25 findings, all 25 applied; the loop's round cap was reached on round 4, so no reviewer has seen the final state | 4 (REVISE, REVISE, REVISE, REVISE) | 6 added, 7 modified (below) | Gate E (launcher), Gate C's real-data limb, the parent repo's suite |

## What shipped

`j_safezone_dist` in `pandas_ta/trend/`, one column
`J_SAFEZONE_DIST_22_2.5_3`: the distance from the close down to Elder's
SafeZone long stop, as a fraction of the close.

```
pen[T]  = max(low[T-1] - low[T], 0)
avg[T]  = sum(pen, 22) / count(pen > 0, 22)      the mean over bars that HAD one
raw[T]  = low[T-1] - 2.5 * avg[T-1]
stop[T] = max(raw[T-2], raw[T-1], raw[T])
out[T]  = (close[T] - stop[T]) / close[T]
```

**Added**

| file | what |
|---|---|
| `pandas_ta/trend/j_safezone_dist.py` | the indicator (touch point 1) |
| `tests/test_j_safezone_dist.py` | 203 tests (touch point 5) |
| `docs/measure_j_safezone_dist.py` | 13 sections; the only place a figure in the receipt, the module docstring or the test module comes from |
| `docs/measure_j_safezone_dist_cpu.py` | the same under `NPY_DISABLE_CPU_FEATURES="AVX512F AVX512_SKX AVX2 FMA3"`; refuses to run if the environment edit did not take |
| `docs/JSafezoneDistMeasured.md` | the receipt issue #121 asks for |
| `docs/reviews/auto-2026-11-16-j-safezone-dist/` | this run: manifest, task log with all four reviews verbatim, this summary |

**Modified**

`pandas_ta/trend/__init__.py` (touch point 2) · `pandas_ta/__init__.py`
→ `Category["trend"]` (3) · `pandas_ta/core.py` → the `df.ta` accessor
(4) · `README.md` (355→356 registered, 363→364 callable, `trend
(62)`→`(63)` and the name in its list) · `docs/IndicatorDictionary.md`
(regenerated; the probe tags the column `SF`, warm-up 25) ·
`docs/MLCompanionContract.md` (700→701 tagged, 338→339 `SF`) ·
`tests/test_altport2_ports.py` (`CATEGORY_TOTAL` 355→356,
`CATEGORY_BUCKETS["trend"]` 62→63).

## Gates

| gate | verdict |
|---|---|
| **A** | **pass** — bit-equal to an independent bar-by-bar oracle on 1,475 of 1,475 fired bars of each of six frames (asserted at 1e-12, measured 0.0), and bit-equal to the screen prototype on all eight |
| **B** | **pass** — module caught 0 of 36 on every frame; six look-ahead mutants live and caught 3 .. 36 of 36; and the sweep's blind spot measured, with five more mutants the ORACLE catches |
| **C** | **pass on synthetic** — 1,475 of 1,500 on six frames, 1,471 .. 1,475 distinct values, 0 exactly 0.0. **Real-data counts OWED** with Gate E |
| **D** | **pass** — ×8/×64 bit-identical on six frames and at price levels 1e-6/1e+6/1e+100, with the DBL_MAX headroom printed (factor 2.800e+206); ×10/×3.7/×0.1/×1.0000001 within 4.091e-11 (6.546e-11 under reduced dispatch), asserted 1e-9; `0 < fires < n`; a level shift moves every fired bar |
| **E** | **pending — the launcher runs it.** No ledger row, and `test_the_gate_e_row_is_owed_and_not_yet_recorded` asserts there is none. The screen measured the PROTOTYPE at SHIP (0.7059 vs `Dist_to_hma_pct`, per-frame max median 0.7249) |
| **F** | PandasTa: 2 failed, 11,845 passed, 86 skipped — the `AlternativeRepos` talib CSV test CI deselects, and the owed Gate E row, which reports `['j_safezone_dist']` and nothing else. The module's 203 tests also pass with AVX-512/AVX2/FMA3 off. The parent repo's suite is the launcher's |

## The three things worth carrying out of this run

1. **The missingness is informative** (§C3). `avg` is undefined when the
   last 22 bars hold no down-penetration, so the column is blank exactly
   where a long has had an easy ride — 0 of 1,500 bars on a flat frame
   AND 0 of 1,500 on a strictly-rising-lows frame, where every bar moves.
   How a consumer fills it is a decision about trend, not about missing
   data.
2. **A future-perturbation sweep was not enough on its own** (§B2). The
   stop carries two `shift(1)`s, so five wrong versions of this module
   read bar T's own low without reading any later bar and are invisible
   to the sweep. Gate B here is the sweep AND Gate A's oracle, and the
   look-ahead mutants lead by two bars wherever the chain allows.
3. **Every reviewer-forced measurement arrived with a typed caption.**
   Round 2 forced §D3's x64 cells; round 3 found their margin written as
   "four orders" when it is 2.800e+206. Round 3 forced the printed
   margin; round 4 found it quoted over six cells when three had been
   walked. Round 2 forced §G3's overflow probes; round 4 found their NaN
   counts read without subtracting `min_periods`' 21-window warm-up —
   and the re-measurement then refuted the claim the block existed to
   support (two DBL_MAX summands DO produce one infinite window, so the
   compensated `rolling.sum` is not a guarantee and the final mask
   stays). The lesson is mechanical: make the script print the number,
   including the margins that look obviously safe.

## Review rounds

| round | verdict | findings | applied |
|---|---|---|---|
| 1 | REVISE | 2 MAJOR, 3 MINOR, 2 NIT | 7 of 7 |
| 2 | REVISE | 1 MAJOR, 3 MINOR, 2 NIT | 6 of 6 |
| 3 | REVISE | 1 MAJOR, 3 MINOR, 2 NIT | 6 of 6 |
| 4 | REVISE | 1 MAJOR, 3 MINOR, 2 NIT | 6 of 6 |

All four reports are quoted verbatim in `01-j-safezone-dist.md`.

⚠ **Not one of the 25 findings was about the mathematics.** Every
reviewer re-ran the measurement script, on both numpy dispatches, and
reported the tables reproducing cell for cell; round 3 was explicitly
invited to refute round 2's conclusion with a run and could not. What
failed, 25 times, was the sentence written after the number was read —
the repo's named dominant defect.

⚠ **No post-fix PASS.** The session's review rule caps the loop at round 1
plus three re-runs. Round 4's six findings are applied and the suite is
green, but no reviewer has seen that state. There are no open findings and
there is also no PASS; this file says so rather than implying one.

## Follow-ups, all owed to the launcher or the receipt session

* **Gate E**, run by issue-solver after this session. The receipt session
  records the ledger row with
  `python docs/gate_e_ledger.py record <run dir> --measured YYYY-MM-DD`,
  which replaces `test_the_gate_e_row_is_owed_and_not_yet_recorded`.
  If the run is STRUCK, the column is reverted or waived before the
  release.
* **Gate C's real-data limb** (§C2), from the same run.
* **The parent repo's suite** (Gate F's other half), which is not on this
  machine.
