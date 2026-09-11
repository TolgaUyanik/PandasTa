# 00 — Manifest: ALTPORT chain (Mode C)

Invocation: `/brutally-honest-review --auto TODO.md`
Run folder: `docs/reviews/auto-2026-09-10-pandasta-8/`
Task file: `d:\AwakenAnalytics\PandasTa\TODO.md`

## Phase 1 — resolved, then narrowed

`TODO.md` held **8** open tasks. Phase 2 narrowed to **3** plus one prerequisite.

| task | line | in scope |
|---|---|---|
| ALTPORT-0 | :639 | **YES** |
| ALTPORT-1 | :654 | **YES** |
| ALTPORT-2 | :667 | **YES** |
| PINEBI-1b | :171 | no — owner: skip this run |
| PINEBI-2 | :290 | no — owner: stays deferred |
| INDREF-1 | :461 | no — owner: stays deferred |
| INDREF-2 | :466 | no — owner: skip, record why |
| MLCOL-1 | :714 | no — owner: stays deferred |

## Phase 2 — clarifications (the ONE permitted round)

| question | answer |
|---|---|
| The three deferred giants back in scope? | **No — only the 3 new ALTPORT tasks** |
| ALTPORT-1 depends on TVPTA-9, which is out of scope. How to screen? | **Fix Gate E inside this run first**, as an unlisted prerequisite |
| INDREF-2 with INDREF-1 deferred? | **Skip it, record why** |
| PINEBI-1b: screen-first or port-all-16? | **Skip PINEBI-1b this run** |

### Recorded reasons for the four exclusions

- **PINEBI-1b** — 16 `port` rows. The 2026-09-08 batch built ~35 columns and deleted
  12 on redundancy against columns the engine already ships. The owner's call is
  that the redundancy question should settle before more supply-side porting.
- **PINEBI-2** — 992 unscanned `.pine` files plus a 43-candidate defer backlog.
- **INDREF-1** — ~201 generated pages.
- **INDREF-2** — its done-when requires linking back to the per-indicator pages
  INDREF-1 would generate. Blocked by construction, not by effort. It was dropped
  from the previous batch for the same reason.

## Phase 3 — execution map

**Every step is main-thread and sequential. No parallel lanes are possible:**
each step consumes the previous step's output, and steps 3–4 write the same files.

| # | step | why this lane |
|---|---|---|
| 0 | **GATEE-FIX** (prerequisite, from `../Backtesting/TODO.md` TVPTA-9) | must precede any screening |
| 1 | ALTPORT-0 — triage the 20 | needs judgement per row; feeds 1 |
| 2 | ALTPORT-1 — screen the BUILDs | consumes 0's verdicts; needs 0's fix |
| 3 | ALTPORT-2 — port the survivors | consumes 1's survivors |

### Why GATEE-FIX runs first

`select_dtypes` silently drops object-dtype comparators from every
`measure_*_overlap_full.py` sweep. `PSAR_Signal` holds `"Bullish"`/`"Bearish"`,
so it has never been in any overlap grid. TALIB-1's `SAREXTs` measured **0.8393**
(ship with disclosure) on the numeric grid and **0.9598** (revert) once coerced.
Screening ALTPORT's candidates before that fix would repeat the exact blind spot,
and every ρ produced would be provisional.

This is TVPTA-9's work, pulled in as a prerequisite by the owner's Phase 2 answer.
It is scoped to the harness change and the ALTPORT screen only — the retroactive
re-run of prior measurements stays with TVPTA-9 in `../Backtesting/TODO.md`.

## ASSUMPTIONS (logged, not asked — Phase 2 is closed)

1. **`fosc` is expected to fail.** It peaks at Spearman **+0.950818** against the
   fork's `cfo` at every length and scalar tried. ALTPORT-0 must not spend its
   triage budget re-deriving that; the measurement is already in the CSV note.
2. **A SKIP is a success.** Several of the 20 carry measured notes saying why they
   are not renames of shipped columns, but "not a rename" is not "worth building".
   The expected outcome is a minority surviving to ALTPORT-2.
3. **`port - alternate impl` (114 rows) is NOT pulled in.** ALTPORT's scope is the
   20 `port` rows only. PINEBI-1c already demonstrated where the variant road ends:
   7 kept on parameter reach alone, zero call sites.

## Standing constraints

- `docs/pine` is untracked on purpose (912 files MPL-2.0 © TradingView, root
  LICENSE MIT). Do not commit it.
- pandas-ta-classic MIT, tti MIT — permissive, attribution still required on any
  port; neither repo may be committed into this one.
- Never import `pandas_ta_classic` in-process: 109 failures. Subprocess only.
- Trading freeze (owner, 2026-07-27) on `deploy/`: untouched by this batch.
- Every claim containing *only/never/always/every/all* or a count must correspond
  to a run.
