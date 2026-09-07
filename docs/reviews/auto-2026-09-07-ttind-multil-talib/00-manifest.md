# Mode C batch — TTIND · MULTIL · TALIB (2026-09-07)

Invocation: `/brutally-honest-review --auto TTIND-0 TTIND-1 MULTIL-0 MULTIL-1 MULTIL-2 TALIB-0 TALIB-1 TALIB-2`

No pre-gate: Mode C resolves TODO references, which are tasks, not plans carrying
load-bearing reasoning.

## Resolved tasks

| id | scope | source |
|---|---|---|
| TTIND-0 | map tti class names to indicator identities, then diff | `PandasTa/TODO.md` §TTIND |
| TTIND-1 | classify genuine gaps; signal layer judged separately | `PandasTa/TODO.md` §TTIND (GATED by -0) |
| MULTIL-0 | measure length-vs-length ρ grid, pick a kept set | `PandasTa/TODO.md` §MULTIL |
| MULTIL-1 | wire kept set into the engine compute list (`../Backtesting/`) | `PandasTa/TODO.md` §MULTIL |
| MULTIL-2 | check `StrategyMaster.csv` rules still resolve | `PandasTa/TODO.md` §MULTIL |
| TALIB-0 | coverage diff CSV in `docs/` | `PandasTa/TODO.md` §TALIB |
| TALIB-1 | port the `port` rows through Gates A–F | `PandasTa/TODO.md` §TALIB |
| TALIB-2 | scan `ta-lib-python` into `IndicatorList.md` | `PandasTa/TODO.md` §TALIB |

## Phase 2 — clarifications (one batched round, the only interruption)

Four gaps found, all of which changed WHAT gets built.

**Q1 — MULTIL-1/-2 are engine work, which the owner excluded an hour earlier.**
→ **"MULTIL-0 only; defer -1/-2."** MULTIL-0 (the ρ measurement) runs here as library
work; MULTIL-1 and MULTIL-2 move to `Backtesting/TODO.md` beside FVGENG.

**Q2 — TALIB-1 says "port", the ALTREPO contract says "audit only".**
→ **"Port a named shortlist only."** Audit first, then port only rows with no plausible
overlap against shipped columns. Everything else stays audited-not-ported.

**Q3 — the TA-Lib C library was not installed, so `ta-lib-python` could not be called.**
→ **"Install TA-Lib first, then full behavioural audit."** Installed: **TA-Lib 0.7.1,
161 functions**, matching TALIB-2's measured count. Behavioural rigour available.

**Q4 — TALIB-0 and TALIB-2 ask for the same diff in two places.**
→ **"Merge into TALIB-2's shape"**, plus an explicit instruction: **no Claude Artifacts.**
TALIB-0 closes as superseded.

## Consequence of Q3 that the owner should see

Installing TA-Lib **changed the PTCLASSIC verdicts**: `dm` moved
`port - alternate impl` → `have`, because both packages defer to TA-Lib when it is
importable and their outputs then converge. The two regeneration guards caught it
immediately, which is what they are for.

The finding is larger than one row: **these verdicts are a function of the environment,
and neither artifact said so.** Both CSVs now carry a `probe_env` column,
`IndicatorList.md` states the environment it was produced under, and
`test_the_csv_records_the_environment_its_verdicts_depend_on` fails if the committed
stamp disagrees with the interpreter running the suite (3 mutations, 3 caught).

Post-install split, regenerated: have **115** · port - alternate impl
**38** · port **38** · n/a
**28** · unknown **5**.
Divergence: seeding **15** · default-only **8** · maths
**11** · shape **2** · warmup **2**.

⚠ These moved again in review round 1, when the shared comparison stopped short-circuiting on
`type(a) is not type(b)`. Column-aware comparison alone rescued 13 real matches in the classic scan
(have 102 → 115). The numbers above are the CURRENT ones, re-read from the CSVs.

## Execution map

| task | lane | why |
|---|---|---|
| TTIND-0 | main | new scanner; needs judgement on tti's class-per-file shape |
| TTIND-1 | main | GATED by -0's identity map |
| MULTIL-0 | main | measurement; shares the probe-frame harness |
| TALIB-2 | main | new scanner; shares the harness and the ALTREPO contract |
| TALIB-1 | **NOT EXECUTED** | see below |
| TALIB-0 | main | closed as superseded by TALIB-2 (Q4) |
| MULTIL-1 | — | DEFERRED to `Backtesting/TODO.md` (Q1) |
| MULTIL-2 | — | DEFERRED to `Backtesting/TODO.md` (Q1) |

All main-thread: every task touches `PandasTa/docs/` and the shared probe harness in
`gen_altrepo_pandas_ta_classic.py`, so the scopes overlap and parallel worktrees would
collide.

## Standing constraints carried into this run

- **Audit only** for the scans (ALTREPO scope decision, owner 2026-09-07); TALIB-1 is the
  one authorised exception and is limited to a named shortlist.
- **No sibling repo may be committed into `PandasTa`.** Licences: pandas-ta-classic MIT,
  ta-lib-python BSD-2-Clause, tti MIT — permissive, attribution required on any port.
- **Never import a sibling package in-process during tests.** `pandas_ta_classic`
  registers the `df.ta` accessor under the same name as the fork; one in-process import
  took the suite from green to 109 failures. Verified 2026-09-07 that **neither `tti` nor
  `talib` registers a pandas accessor**, so only classic carries this hazard — but the
  subprocess rule stands for all three.
- **No Claude Artifacts** (owner, Q4).

---

## TALIB-1 — NOT EXECUTED

No indicator was ported. The owner authorised "a named shortlist only"; the shortlist is named here
for the first time, because until round 1 of the review the gap list was not trustworthy enough to
cut one from — it contained `CORREL` (the fork ships `correlation`), `BETA` pointing at a fork
function that does not exist, and 20 rows stamped `audited=yes` that had never been compared
numerically.

**The gap is 10: `BETA` `HT_DCPERIOD` `HT_DCPHASE` `HT_PHASOR` `HT_SINE` `HT_TRENDLINE` `HT_TRENDMODE` `IMI` `MAMA` `SAREXT`.**

**The shortlist is NOT the gap.** Q2's criterion was "port only rows with **no plausible overlap**
against shipped columns", so the gap is filtered, not copied:

| excluded | why |
|---|---|
| `SAREXT` | overlaps shipped `psar` |
| `MAMA` | an adaptive MA; overlaps the shipped MA family |

**Shortlist (8):** `BETA` `HT_DCPERIOD` `HT_DCPHASE` `HT_PHASOR` `HT_SINE` `HT_TRENDLINE` `HT_TRENDMODE` `IMI`

The Hilbert-transform family is the core of it — a behaviour the fork has none of, so Gate E overlap
against shipped columns is least likely to force a revert. `IMI` (open→close intrabar momentum, not
RSI) and `BETA` are self-contained singles.

⚠ **Do not cite the pandas-ta-classic scan as independent corroboration.** Both scanners import the
same harness; their agreement confirms the fork surface, not the finding. Round 2 proved the point:
`LINEARREG_ANGLE` was called absent by BOTH scans, and `ta.linreg(angle=True, degrees=True)`
reproduces it to 1.799e-12.

**Why it stopped there.** Porting is Gates A–F per indicator, and Gate E requires measuring the new
column against the engine's full production column set — a `../Backtesting/` measurement script. The
owner removed engine-side work from this batch (Q1). So TALIB-1 stays open with its shortlist
written down, which is the honest state; claiming it done would be claiming Gate E evidence that
does not exist.
