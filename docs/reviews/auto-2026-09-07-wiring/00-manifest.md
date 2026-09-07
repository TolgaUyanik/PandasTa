# auto-run manifest — 2026-09-07 — runid `wiring`

Invocation: `/brutally-honest-review --auto WIRING-1 WIRING-2`
Mode: C (batch task execution). Fletcher gate ON, 3-round cap per task.
Task source: `TODO.md` (PandasTa fork), section **WIRING**, band ACTIVE.

## Resolved tasks

| id | scope | source |
|---|---|---|
| WIRING-1 | Add the 11 missing `core.py` accessor methods | `TODO.md:20` |
| WIRING-2 | Fix `aberration` — `sma` binds the submodule, not the function | `TODO.md:27` |

## Clarifications (Phase 2, one round)

**Q — WIRING-1's done-criterion is "`df.ta.strategy()` runs to completion with no
`exclude` list", but `mcgd` still raises on pandas 2.x and the section's own tie line
assigns `mcgd` to TVPTA-7b in the parent repo. The criterion cannot pass as written.**

**A (user): fix `mcgd` here too.** Two-line `pd.concat` change, so WIRING-1's criterion
becomes literally satisfiable. TVPTA-7b in `../Backtesting/TODO.md:477` is then closed in
passing and must be told so rather than left pointing at a fixed defect.

## Assumptions (logged, not asked)

- A1 — New accessors follow the existing `core.py` shape exactly: `_get_column` for each
  price input, pass-through of named params, `_post_process(result, **kwargs)`. No new
  helper, no validation the neighbours do not have.
- A2 — Each accessor lands in its own category block (`# Momentum`, `# Overlap`,
  `# Trend`, `# Volume`), alphabetically among its neighbours. Conservative: match layout.
- A3 — `ichimoku_ml` has no `offset` parameter; its accessor does not invent one.
- A4 — `ob` and `vol_delta` take `open_`; accessors resolve it via
  `self._get_column(kwargs.pop("open", "open"))`, as `cdl_doji` does at `core.py:836`.

## Execution map

| task | lane | why |
|---|---|---|
| WIRING-1 | main thread | `pandas_ta/core.py` + one new test; needs judgment on per-indicator signatures |
| mcgd fix | main thread, inside WIRING-1 | its blocker; two lines in `pandas_ta/overlap/mcgd.py` |
| WIRING-2 | main thread | 1 import line + one new test; too small to be worth a worktree |

No parallel subagent lanes: three files, all small, two of them coupled through the same
acceptance check (`df.ta.strategy()` with no `exclude`).
