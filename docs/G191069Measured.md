# g191_069 — measured (issue #70)

> **Status: Gates A-E cleared, wired, this repo's suite green except the pre-existing breaks
> below. Gate E: DISCLOSE (max |rho| 0.7621, under the 0.90 STRUCK line) -- ship.**

Open-based directional balance (DTM/DBM, 20): Guotai Junan's (2017, "GTJA191", internal quant
report, read via the HKUDS/Vibe-Trading copy, MIT) alpha `#69`, per issue #70's own instruction.
Module `pandas_ta/trend/g191_069.py`, column `G191_069_20`. Tests: `tests/test_g191_069.py` (16,
all passing). Numbers below: `python docs/measure_g191_069.py`. Environment: this worktree's
pinned pandas/numpy. Measured 2026-11-10.

## Gate A: derivation from the published formula, not the prototype

Issue #70 states GTJA191 alpha `#69`:

    #69: SUM(DTM,20) vs SUM(DBM,20) normalised by the larger; DTM = O<=O1 ? 0 : MAX(H-O, O-O1)

**What this session could NOT do, disclosed up front:** `docs/pine/` and web access are both
unavailable in this worktree, so the issue's own named copy -- HKUDS/Vibe-Trading (MIT) -- was
never read. Everything below is derived from the issue's own stated formula string, per the
issue's own instruction ("Gate A starts from the source formula, not the prototype"), then
cross-checked against the issue's own prototype (`docs/issues/screen/ind_screen.py:408-416`):

    @cand("g191_069", "open-based directional balance (DTM/DBM, 20)", G,
          "#69: SUM(DTM,20) vs SUM(DBM,20) normalised by the larger; DTM = O<=O1 ? 0 : MAX(H-O, O-O1)")
    def _(o, h, l, c, v):
        o1 = delay(o, 1)
        dtm = pd.Series(np.where(o <= o1, 0.0, np.maximum(h - o, o - o1)), index=c.index).where(o1.notna())
        dbm = pd.Series(np.where(o >= o1, 0.0, np.maximum(o - l, o - o1)), index=c.index).where(o1.notna())
        sd, sb = tsum(dtm, 20), tsum(dbm, 20)
        return pd.Series(np.where(sd > sb, sdiv(sd - sb, sd), np.where(sd < sb, sdiv(sd - sb, sb), 0.0)),
                         index=c.index).where(sd.notna() & sb.notna())

**One disclosed interpretation choice.** The issue's own stated text spells out `DTM` in full but
names `DBM` only by its mirror role ("vs SUM(DBM,20)"), so the prototype's own `dbm` line is this
port's source for `DBM`'s exact shape: `O >= O1 ? 0 : MAX(open-low, open-O1)`. It is the textbook
mirror of `DTM` (swap the gate direction and the `H`/`L` term, keep `open-O1` in both second
terms) and the only reading under which `DBM >= 0` always (matching `DTM >= 0`, needed for the
division-by-zero argument below). No other prototype term was needed; the issue's own string and
the prototype's `dtm`/`sd`/`sb`/final-ternary lines already agree exactly.

    G191_069 = SD > SB ? (SD-SB)/SD : (SD < SB ? (SD-SB)/SB : 0)
        where SD = SUM(DTM, 20), SB = SUM(DBM, 20)

## Gates

| Gate | Result | Evidence |
|---|---|---|
| A Correctness | derived directly from the issue's own stated formula, with one disclosed interpretation choice for `DBM`'s exact shape (the textbook mirror of `DTM`, matching the prototype), using the prototype's own (unambiguous) `delay`/`tsum` spellings -- see the Gate A section above | 7-bar hand-derived example at `length=3` (`tests/test_g191_069.py::test_hand_derived_seven_bars`), including a flat-open (`open==open1`) boundary bar: `result[3..6] = [0.400000, 0.400000, 0.400000, 0.850000]`, matching the module's float64 output exactly (`python docs/measure_g191_069.py`: `hand-derived bars 0..6`). Matches an independent per-bar loop built from plain numpy slicing (not the module's own `.rolling()`/`np.where` calls) at the shipped default (`length=20`), 3 spot-checked bars (300, 600, 899) on a 900-bar synthetic frame: `module=0.828761 loop=0.828761`, `module=0.408492 loop=0.408492`, `module=0.405019 loop=0.405019` |
| B Causality | pass | Future-perturbation sweep (open, high, low AND close all rewritten from `j` onward, another synthetic frame), 34 offsets past the 20-bar warm-up: real module **0 of 34** leaks (`python docs/measure_g191_069.py`). One mutant (`importlib` source read, `exec`'d in memory, the final write index shifted `length=20` bars into the future), shown live (differs from the real module) then caught at **34 of 34** |
| C Reachability | synthetic only (real-data reachability comes from Gate E's pooled count, not re-derived here) | 1,500-bar synthetic frame (seed 23 OHLC, `docs/measure_g191_069.py:_ohlc`), shipped default: **1,480 of 1,500** bars non-NaN (98.67%) -- exactly `n - 20`, the `length = 20`-bar warm-up, no wider gap. **1,480 distinct values** observed on this frame (not a constant column), range `[-0.717688, 0.963483]`, median `0.435050` |
| D Scale-free | pass | For ANY `k > 0`: a uniform price rescale (`open,high,low,close -> k*(...)`) leaves every gate comparison and the final `SD > SB` branch unchanged (scaling preserves the sign of a difference, hence an ordering), and scales `DTM`, `DBM`, `SD`, `SB` all by exactly `k`, so the final ratio is invariant algebraically. Measured on the 1,500-bar frame: PRICE x8/x64 **bit-identical, 0.0 max\|diff\|**; PRICE x10/x3.7: max\|diff\| **8.69e-15** / **4.26e-15**, float64 rounding from the scalar multiply itself, well under the test's 1e-9 tolerance. `0 < 1,480 fires < 1,500` and `1,480 > 1` distinct values rule out a constant column |
| E Attribution | DISCLOSE (ship, disclosed) | `G191_069_20`: max \|rho\| **0.7621** vs `Ret_21d_vol_adj` (manifest comparator, n = 396,980), per-frame max median \|rho\| **0.7889** (also `Ret_21d_vol_adj`, 89 frames, 0% of frames >= 0.90). Both under the 0.90 STRUCK line (pooled and per-frame-median), so not struck; 0.76 <= 0.7621 < 0.80 puts it in the DISCLOSE band (CLAUDE.md Gate E row, `r3-perframe-0.90`). Run by the launcher: `gate_e_overlap.py run --module pandas_ta.trend.g191_069`, 89 ALTPORT-1 frames, 398,849 bars, 687 comparators (329 compute_all + 358 manifest), canary bit-equal (AKBNK.IS, BIENY.IS, AGHOL.IS, SASA.IS). Recorded in `docs/gate_e_ledger.csv` (`docs/gate_e_ledger.py record`, measured 2026-11-10) |
| F Suites | this repo only; parent repo (`Backtesting`) is run by the launcher in clean worktrees | `python -m pytest -q` (this session): see run below |

## Wiring

`Category` **304 -> 305** (`trend` **61 -> 62**); `df.ta.<name>()` accessor count **312 -> 313**.
Touch points: `pandas_ta/trend/g191_069.py` (module), `pandas_ta/trend/__init__.py` (export),
`pandas_ta/__init__.py` -> `Category["trend"]` (discovery), `pandas_ta/core.py` ->
`AnalysisIndicators.g191_069` (accessor), `tests/test_g191_069.py` (tests). README.md's headline
and `trend (62)` row, and `docs/IndicatorDictionary.md` (regenerated), both updated and checked by
`tests/test_readme_counts.py`. `docs/MLCompanionContract.md`'s running tag count updated
**649 -> 650 / 292 -> 293 `SF`** (`G191_069_20` probes cleanly at the dictionary's 600-bar
synthetic frame and takes many distinct values, so the generator tags it `SF`), confirmed by
`tests/test_ml_companions.py::test_the_contract_quotes_the_dictionarys_actual_ml_form_counts`.
`tests/test_altport2_ports.py`'s `CATEGORY_TOTAL` updated to match (304 -> 305) and
`CATEGORY_BUCKETS["trend"]` (61 -> 62).

`g191_069`'s Gate E ledger row is recorded (`docs/gate_e_ledger.csv`), DISCLOSE verdict, measured
2026-11-10.

## Suite run (this repo, this session)

`python -m pytest -q`, full suite, default collection order: **3 failed, 4969 passed, 83
skipped**. `g191_069`'s own tests (`tests/test_g191_069.py`): **16 passed**. Failures, all
pre-existing and unrelated to this port except the owed Gate E row (CLAUDE.md "Known breaks"
plus "Owed, not failed"):
`tests/test_altrepo_talib_csv.py::test_regenerating_reproduces_the_committed_rows` (needs the
sibling `../AlternativeRepos` checkout, absent in this worktree),
`tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one` (owed for
`['g191_069', 'mtd_ret']` -- `mtd_ret` pre-dates this session, per `docs/G191167Measured.md`'s
identical note; `g191_069` is owed by this port, per this file's own Gate E row above) and
`tests/test_pine_coverage_csv.py::test_audited_rows_carry_their_evidence` (untracked
`docs/pine/` corpus, 8d8f705). No other test regresses.
