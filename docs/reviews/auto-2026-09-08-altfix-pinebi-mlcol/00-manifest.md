# Mode C batch — ALTFIX · PINEBI-0b · MLCOL-0 (2026-09-08)

Invocation:
`/brutally-honest-review --auto TALIB-1 ALTFIX-0 ALTFIX-1 ALTFIX-2 ALTFIX-3 ALTFIX-4 MLCOL-0 MLCOL-1 MLCOL-2 PINEBI-0b PINEBI-1b PINEBI-1c PINEBI-1d PINEBI-1e PINEBI-2`

15 refs resolved, **7 executed, 8 deferred by owner decision.** No pre-gate:
Mode C resolves TODO references, which are tasks, not plans carrying
load-bearing reasoning.

## Phase 2 — clarifications (one batched round, the only interruption)

**Q1 — Gate E needs a `../Backtesting/` measurement, which the owner excluded
from the previous batch. That exclusion is what left TALIB-1 unexecuted.**
→ **"Skip all porting this batch."** TALIB-1 and PINEBI-1b/-1c/-1d/-2 are out.

**Q2 — the batch is far larger than the last one, which took 3 rounds and
escalated.**
→ **"Run the small, well-defined ones"**: ALTFIX-0–4, PINEBI-0b, MLCOL-0.

**Q3 — PINEBI-2 names two different queues and defers its acceptance criteria
to a task in the other repo.**
→ **"Defer PINEBI-2 entirely."**

**Q4 — MLCOL-1 would add a scale-free companion to every price-level column of
~200 indicators.**
→ **"Contract, then roll out with Gate E per companion."**

### ASSUMPTION recorded (Q2 vs Q4 interact)

Q4 authorises the MLCOL rollout; Q2's chosen option scoped the batch to
MLCOL-0 alone. Mode C's tiebreak is **the smaller blast radius wins**, and
MLCOL-0's own text says it **GATES the rest**. So: MLCOL-0 lands first, and
MLCOL-1/-2 start only if MLCOL-0 passes its gate with budget remaining.
Rolling ~200 new columns before the contract has survived review is exactly
what MULTIL-0 just demonstrated is expensive to undo.

### ASSUMPTION recorded (what "skip porting" leaves available for Gate E)

Q1 removes engine-side work, but MULTIL-0 established the precedent that
READING `../Backtesting/datastore/cache/*.parquet` is not engine-side work — it
is a read, touching no engine code, no miner and no live book. Any ρ
measurement in this batch uses that route.

⚠ PINEBI-1e was not named in Q1's option but adds four new fork utilities
(`sum`, `pivot`, `normalize`, `covariance`), i.e. new columns. Q2's chosen scope
excludes it. Deferred.

## Executed

| id | scope | severity |
|---|---|---|
| ALTFIX-1 | one shared resolver across the three scanners | MAJOR |
| ALTFIX-0 | measure `correl` / `CORREL` (both currently `unknown`) | MAJOR |
| ALTFIX-2 | gap guards must derive, not list yesterday's mistakes | MAJOR |
| ALTFIX-3 | harden the `seeding` promotion | MINOR |
| ALTFIX-4 | generate the counts in the manifest and TODO files | MINOR |
| PINEBI-0b | audit the 40 unaudited `have` rows | MAJOR |
| MLCOL-0 | the ML companion contract, on three indicators | MAJOR |

## Deferred

| id | why |
|---|---|
| TALIB-1 | Gate E is engine-side (Q1) |
| PINEBI-1b, -1c, -1d | Gate E is engine-side (Q1) |
| PINEBI-1e | adds columns; outside Q2's scope |
| PINEBI-2 | open-ended, criteria owned by another repo's task (Q3) |
| MLCOL-1, -2 | gated on MLCOL-0 passing (see assumption above) |

## Execution map

| task | lane | why |
|---|---|---|
| ALTFIX-1 | main | rewrites the shared resolver every scanner imports |
| ALTFIX-0 | main | consumes -1's two-series path |
| ALTFIX-2 | main | consumes -1's resolver; edits three test modules |
| ALTFIX-3 | main | same shared harness file as -1 |
| ALTFIX-4 | main | edits this manifest and both TODO files |
| PINEBI-0b | main | judgement per row; reads library sources |
| MLCOL-0 | main | new indicator modules + the five wiring touch points |

All main-thread: ALTFIX-0/-1/-2/-3 all touch
`docs/gen_altrepo_pandas_ta_classic.py` or its importers, so parallel worktrees
would collide on the file that matters most.

## Standing constraints

- **Audit only** for the scanners (ALTREPO scope decision). No ports this batch.
- **Never import a sibling package in-process during tests** —
  `pandas_ta_classic` hijacks the `df.ta` accessor; one import took the suite
  from green to 109 failures. Scanners are subprocess-invoked.
- **No sibling repo may be committed into this one.**
- ⚠ **`AlternativeRepos/` is NOT a git repo** (checked 2026-09-08), so the CSVs
  and `IndicatorList.md` this batch edits are unversioned. The generators are
  committed, so the artifacts are reproducible; the artifacts themselves are not
  tracked anywhere.
- **The recurring defect to watch for: a ninth false gap entry.** Eight so far,
  every one from the probe calling fork functions in one narrow way.
