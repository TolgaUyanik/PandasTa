# PandasTa Tolga Uyanik's Fork To-do's

Library-scoped work only. Engine-side work (mining, wiring, live book) lives in
`../Backtesting/TODO.md` — the pine-porting initiative **TVPTA** (TVPTA-0 … TVPTA-7b) is there, and
several sections below extend it rather than restarting it.

Port protocol every section here is bound by: `../Backtesting/docs/TVPTA6-Indicator-Porting-Process.md`
(Gates A–F; overlap ρ ≥ ~0.9 → revert, 0.76–0.80 → ship with disclosure, < 0.76 → ship).
Column inventory and ML form of everything currently shipped: `docs/IndicatorDictionary.md`.

---

# ═══ ACTIVE ═══

**One item is open: MLCOL-1, and it is open only because its acceptance criterion cannot be met
honestly.** Everything else in this file's history is finished; the full blocks — with the
measured evidence, the reverts and the traps — moved to **[`docs/CompletedWork.md`](docs/CompletedWork.md)**
on 2026-09-12. Read that before re-opening anything, because most of what it records is *why a
column is not here*.

Suite at that point: **3,166 passed / 0 failed / 23 skipped**. `Category` **233**.

## Open

See the MLCOL section below. Nothing else.

## Owner decisions outstanding — not tasks, and not mine to take

1. 🔴 **The 16 broken `INDICATOR_SPECS` arg lists** (INDREF-2 §5d). Sixteen of the 104 specs pass
   an argument list that does not match the pandas_ta signature, raise `TypeError` on every bar of
   every run, and are swallowed by a bare `except: continue` — so they have never emitted a
   column. The same 16 are broken in **all six copies** of the table, **four of which are inside
   `deploy/`**, where repairing them would make 16 indicators start emitting columns in the live
   container. That is a strategy-affecting change under the TRADING FREEZE.
2. 🔴 **2,211 `.pine` files are TRACKED in `Backtesting`** with 912 MPL-2.0 headers under hundreds
   of individual rightsholders, and that repo has **no `LICENSE` file**. Untracking them in
   `PandasTa` (2026-09-07) closed this for *this* repo only. Whether the other repo is public is
   unverified. Remediation means history rewriting and a force-push.
3. ⚠ **`dpo` ships `centered=True` as its DEFAULT**, so `ta.dpo(close)` silently returns a
   look-ahead column, and `dpo` is in `Category`, so `df.ta.strategy()` sweeps it. Documented
   upstream behaviour the fork inherited — left alone rather than changed unasked, but it is a
   live trap. (`ssf` was a third, undocumented look-ahead; that one was a bug and is fixed.)

# ═══ BACKLOG ═══

## PINEBI — TradingView built-ins ✅ CLOSED

Full record: [`docs/CompletedWork.md`](docs/CompletedWork.md). PINEBI-0, -0b, -1a…-1e and -2 are
all closed. **Zero `port` rows remain** in `docs/pine_builtin_coverage.csv`.

**Verdict split, generated — this is the table the -1b…-1e scopes are cut from.**
Produced by `docs/gen_pine_builtin_coverage.py` (PINEBI-0, done 2026-09-07).

| verdict | n |
|---|---|
| `have` | 73 |
| `port - primitive` (→ -1a) | 18 |
| `n/a - measured and reverted on Gate E` | 7 |
| `n/a - not a Pine built-in` | 4 |
| `n/a - not worth a primitive` | 2 |
| `port - blocked on data` (→ -1d) | 2 |
| `n/a - never called live in the corpus` | 1 |

⚠ These counts are **asserted**, not retyped: `test_the_docs_quote_the_csvs_actual_split` reads this
table and fails if any number disagrees with the CSV. Four review rounds went by with a stale split
standing in three documents; that is now a test failure rather than a reading exercise.

The scopes those verdicts route to are closed. Their enumerations are kept here because
`test_every_scoped_row_is_named_in_its_task` reads the `ROWS:` line out of the task block itself,
and a scope written only in prose is unguarded — that guard exists because `stc` spent a whole
round "scoped into PINEBI-1b" while existing only as a string in a CSV note.

- [x] **PINEBI-1b — Port the `port` rows. ✅ DONE 2026-09-11.** 16 measured, **9 shipped, 7 built
  and reverted on Gate E**. Zero remain.
  ROWS: none remaining — every one of the 16 reached a terminal verdict; see
  `docs/PineBuiltinsMeasured.md` for the per-column ρ and `REVERTED_ON_GATE_E` in
  `docs/gen_pine_builtin_coverage.py` for why each of the 7 was deleted.

- [x] **PINEBI-1c — The nine alternates. ✅ DONE 2026-09-08.** 7 kept, 2 deleted.
  ROWS: none remaining — all nine resolved; measured table in `docs/PineAlternatesMeasured.md`.

- [x] **PINEBI-1d — The two data-request rows. ✅ DONE 2026-09-08.** `up_and_down_volume` and
  `volume_delta` ship, deliberately OUT of `Category` and in `strategy`'s exclusion list: they
  need a lower-timeframe frame a sweep cannot supply.

- [x] **PINEBI-2 — The community corpus. ✅ CLOSED 2026-09-11**, triage delivered and the porting
  half deferred on its own measurement (2–7 landed indicators for 179–269 files read). The wiring
  pass was done instead, as WIRE-0. **TVPTA-1b's deliverable is already delivered by that triage**
  — read `docs/PineCorpusTriage.md` before writing its spec rather than re-running the classifier.

## CANDLE · INDREF · TALIB · ALTREPO · ALTFIX · ALTPORT — ✅ ALL CLOSED

Full records in [`docs/CompletedWork.md`](docs/CompletedWork.md):

| section | outcome |
|---|---|
| **CANDLE-0/-1/-2** | 11 shortlisted → 8 shipped, 22 columns → **6 deleted** on Gate E; `rectangle` skipped on a pre-registered trigger |
| **INDREF-0/-1** | `docs/gen_indicator_pages.py` + a reference page per shipped indicator, idempotent (`--check` → changed=0) |
| **INDREF-2** | `../Backtesting/docs/indicators/IndicatorSelectionResults.md` — **175 of 233 indicators were never in a position to be selected**; found the 16 broken specs |
| **TALIB-1** | 10 `port` rows → 8 columns shipped, **5 reverted**; seven of the ten are one state machine with two warm-ups |
| **ALTFIX-0…-4** | audit closed; gaps classic 33 → 9, tti 10 → 9, ta-lib 10 → 0 |
| **ALTPORT-0/-1/-2** | 20 candidates → **3 shipped** (`cvi`, `bw_mfi`, `smc_sweep`), all three later cleared by WIRE-0 and now called by the engine |

## MLCOL — per-indicator ML companion columns

✅ **MLCOL-0** (contract) and **MLCOL-2** (reference companions — **0 of 5 shipped**) are closed;
see the archive. MLCOL-2 is the reason MLCOL-1 screens before it builds.

- [~] **MLCOL-1 — Roll the contract out, PX columns first. 🔶 MEASURED IN FULL AND 5 SHIPPED 2026-09-12; the stated Done-when CANNOT be met honestly — see below.** Order the work
  by the dictionary's *"Needs a transform before modelling"* table — those indicators are unusable as
  features today, so they pay back first.
  **Done when:** every `PX` column in the dictionary has a scale-free companion, and the regenerated
  dictionary shows no indicator whose entire output is `PX`.
  ⚠ **Owner's sequencing (2026-09-08): "contract, then roll out with Gate E per companion."** Gate E
  is per companion, not once at the end — one measurement per PX column. (For the count, read the
  opening paragraph of `docs/MLCompanionContract.md`; it is Counter-derived from the generated
  dictionary and asserted by `tests/test_ml_companions.py`. Four different numbers for that one
  quantity were in circulation on 2026-09-08 — do not retype it.)

  ✅ **What was done (2026-09-11/12).** All **137** `PX` columns screened before anything was
  written, then the survivors put through the incremental axis, then redundancy checked *among the
  survivors*. Receipts: `docs/MLCol1Screen.md`, `docs/MLCol1Axes.md`, and the two harnesses
  `../Backtesting/scripts/analysis/measure_mlcol1_{screen,axes}.py`.

  **The funnel, every step measured:**
  137 proposed → **82 restate a shipped column at ρ ≥ 0.90** → 36 land in the disclosure band →
  **2 parents read the future** → 4 could not be probed → **13 clear Gate E** → **6 show
  incremental evidence** → **5 after removing redundancy among the survivors**.

  **SHIPPED (5):** `HA_high_DIST_PCT` (ha), `HW-UPPER_DIST_PCT` + `HW-LOWER_DIST_PCT` (hwc),
  `LINREG_LOWER_2_DIST_PCT` (linreg_channel), `THERMO_20_2_0.5_RATIO_PCT` (thermo). All
  scale-free bit-identical ×8/×64, all causal, `tests/test_mlcol1_companions.py` 34 passed.
  `SF` 207 → **212**.

  🔴 **THE DONE-WHEN AS WRITTEN CANNOT BE SATISFIED HONESTLY, and this is the finding, not an
  excuse.** It asks that *"every `PX` column has a scale-free companion"* and that *"no indicator
  whose entire output is `PX`"* remains — **71 indicators are still all-`PX`**, nearly all of them
  moving averages. Meeting it means emitting ~71 more companions, and the screen MEASURED that
  their `DIST_PCT` forms restate columns the engine already ships: **15 restate
  `NWE_MID_200_8.0_8.0`, 14 restate `bias`** — the exact columns this task's own contract told it
  to screen against. Satisfying the acceptance criterion would therefore require violating the
  contract's non-redundancy rule 82 times over.
  **Proposed amendment, for the owner:** *"every `PX` column has been SCREENED for a companion,
  and one is emitted wherever it clears Gate E, the incremental axis, and redundancy against the
  other survivors."* Under that reading MLCOL-1 is done. Left as `[~]` because rewriting one's own
  acceptance criterion is the owner's call, not the executor's.

  ⚠ **Three findings that outlive this task:**
  1. 🔴 **`ssf` READ THE FUTURE — an undocumented look-ahead in shipped code, now fixed**
     (`f3ff67a`). Its recursion ran `for i in range(0, m)`, so at `i = 0` it read `ssf.iloc[-1]`,
     the LAST bar of the series. Perturbing only bars ≥ 300 of a 400-bar frame moved **bar 0** by
     31.4. `CLAUDE.md` claimed the causality exception list was "complete" at two columns; it was
     three, and the claim is corrected. Independent corroboration: `ssf` vs pandas-ta-classic
     moved `port - alternate impl` → `have`, `divergent` → `identical`, agreeing on all 260
     values — the divergence WAS the bug.
  2. 🔴 **Causality must PRECEDE the incremental axis, not sit beside it.** The leaking `dpo`
     companion was ranked **first** by axis 3a — ΔAUC +0.0473, permutation importance +0.35693,
     15/15 beats-null — in a field where every honest candidate scored ~0.01. Leakage is the
     strongest signal a model can be handed, so the axis *promotes* a non-causal feature rather
     than rejecting it, with every control behaving exactly as designed. Recorded in
     `docs/MLCompanionContract.md`. Note `dpo`'s `centered=True` is its **default**.
  3. **Gate E is blind to redundancy AMONG candidates.** It measures each against the SHIPPED
     set. Three `hwc` companions each cleared it and the axis, then read ρ +0.9257 / +0.9213
     against each other — `HW-MID` is the hub and carries nothing independent once both edges are
     kept. Dropped. This is the PB_LO/PB_UP lesson again: a survivor set is itself a correlation
     gate that nobody ran.

  ⚠ **The contract's single DISTANCE formula does not fit all `PX` parents.** `(close - parent) /
  close` is right for a **level**; 37 of the 137 are price **differences** centred on zero, where
  it evaluates to ≈1.0 with the signal in the fourth decimal. Those are screened and shipped as
  `parent / close` and NAMED `_RATIO_PCT`, because naming is API and calling a ratio a distance
  misdescribes it permanently.

  ⚠ **MLCOL-2 added a prerequisite screen:** Gate E is necessary but NOT sufficient (it would have
  shipped `FVG_BULL_RATE_60`), and every MA-family `DIST_PCT` must be checked against the engine's
  existing relational columns first — `SMA_10_DIST_PCT` died at ρ 0.946 against `NWE_MID_200_8.0_8.0`.
  Use `measure_ml_companion_overlap.py --companions`.

---

**Everything above this line that is marked ✅ or [x] is finished.** The evidence lives in
[`docs/CompletedWork.md`](docs/CompletedWork.md), not here.
