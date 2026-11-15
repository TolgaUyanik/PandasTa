# Run manifest — auto-2026-11-11-g191-158

**Mode:** `/brutally-honest-review --auto` (Mode C, batch task execution — the
invocation's argument is a task reference, not a plan file, so there is no
step-0 pre-gate; Mode C deliberately has none).
**Date:** 2026-11-11
**Run folder:** `docs/reviews/auto-2026-11-11-g191-158/`

## Phase 1 — the resolved task

One task, taken verbatim from the invocation:

> G191-158: port the indicator of issue #81 through Gates A-D, the wiring,
> the tests and docs/<Name>Measured.md, per the issue and the rules in your
> system prompt (range over close. Source: GTJA191 (Guotai Junan 2017
> report; HKUDS/Vibe-Trading copy, MIT) — `#158:
> ((H-SMA(C,15,2))-(L-SMA(C,15,2)))/C = (H-L)/C`.). Gate E and the suites
> are run by the launcher afterwards.

Source of the task: the issue-solver launcher's session prompt for
TolgaUyanik/PandasTa #81 (local tracker copy: `docs/issues/080-g191-158.md`,
gitignored). "Done" criterion, from the issue: shipped through Gates A–F
with the numbers in `docs/<Name>Measured.md`, OR measured and reverted with
that file kept as the receipt.

## Phase 2 — clarifications

**None asked.** `AskUserQuestion` is unavailable in this headless session,
and the skill's rule for that case is to take the most conservative reading
(the smaller scope) and log it as an ASSUMPTION. Four were logged:

* **ASSUMPTION 1 — ship the source's own reduced form `(H-L)/C`, not the
  literal `((H-SMA(C,15,2))-(L-SMA(C,15,2)))/C`.** Smaller scope: no
  parameters, no smoother, no warm-up. Backed by the issue's own formula
  string (which states the reduction itself), by the prototype
  (`ind_screen.py:518`, `return (h - l) / c`), and by the port being
  bit-identical to the expression whose Gate E prior the issue quotes.
  Both spellings are measured against each other anyway — see
  `docs/G191158Measured.md`, Gate A.
* **ASSUMPTION 2 — no tunable parameters.** The source's `15` and `2` live
  only inside the cancelled term, so exposing them would expose knobs that
  cannot change the output. Column name `G191_158`, no parameter suffix.
* **ASSUMPTION 3 — category `volatility`.** A one-bar normalised range is a
  volatility feature, and it sits next to `g191_109`, the fork's other
  GTJA191 range port.
* **ASSUMPTION 4 — the `/close` division is left unguarded.** The smaller
  change: the prototype uses a bare `/` here (it uses the screen's `sdiv`
  on other candidates) and `g191_003` ships an unguarded `/close` for the
  same reason. Behaviour pinned by a test rather than left implicit.

## Phase 3 — execution map

| task | lane | why |
|---|---|---|
| G191-158 port | main thread | One indicator, five wiring touch points in shared files (`pandas_ta/__init__.py`, `pandas_ta/core.py`), plus doc counts that must be regenerated in sequence. No independent second task to parallelise against, and worktree isolation would buy nothing. |

Gate: a fresh read-only Fletcher reviewer subagent per round (`Explore`,
`--fletcher` on by Mode C's default), never the main thread reviewing its
own work. Cap: 3 REVISE rounds by the skill, raised to 4 total rounds by the
user's standing review-loop rule.

## Hard limits that applied

* No destructive or outward-facing step was in scope: **no push, no PR, no
  `gh`, no `pip`** — the launcher pushes.
* **Gate E was not run and `docs/gate_e_ledger.csv` was not touched**: this
  session has no access to `../Backtesting`. The Measured doc records Gate E
  as pending, run by the launcher.
* `docs/issues/` was read, never written, and nothing under it is committed
  (it is gitignored).
