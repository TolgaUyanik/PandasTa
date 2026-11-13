# `/brutally-honest-review --auto` run — 2026-11-11 — `g191-145`

Mode **C** (batch task execution). The invocation's argument is a free-form task, not a plan
file path, so Mode C applies and there is **no Mode B step-0 pre-gate** — that absence is the
skill's own rule for Mode C, not an omission. `--fletcher` theatrics are ON by skill default.

## Phase 1 — Select

| # | task id | scope (one line) | source |
|---|---|---|---|
| 1 | `g191-145` | Port GTJA191 alpha `#145` (volume oscillator 9/26 over 12) through Gates A–D, the five wiring touch points, the tests, and `docs/G191145Measured.md`. | the `/brutally-honest-review --auto "…"` argument, which quotes issue #78 |

Run folder: `docs/reviews/auto-2026-11-11-g191-145/`.

One task, so Phase 3's parallel map is trivial: **main thread**, no worktree isolation (nothing
to run concurrently against it).

## Phase 2 — Clarify

`AskUserQuestion` is unavailable in this headless session (the system prompt says so
explicitly), so every gap below is resolved by the **most conservative reading — the smaller
scope wins** — and logged here as an ASSUMPTION rather than asked. No questions were put to
anyone.

| # | gap | conservative reading taken | why it is the smaller scope |
|---|---|---|---|
| A1 | The source string `(MEAN(V,9)-MEAN(V,26))/MEAN(V,12)*100` has three windows. How many are parameters? | Three keyword parameters, `fast=9`, `slow=26`, `norm=12`, defaulting to the source's own numbers. Column `G191_145_9_26_12`. | Hard-coding would ship a function that cannot be re-tuned and whose column name hides its own windows, breaking this fork's "naming is API" rule. Exposing them with the source's defaults changes nothing at the shipped defaults, which is what `Category` and Gate E see. |
| A2 | `pvo` already swaps `fast`/`slow` when the caller inverts them. Copy that? | **No swap.** The three lengths are used exactly as given. | Smaller scope: the source formula has no such rule, and a silent swap would make `g191_145(v, fast=26, slow=9)` return the negation of what the caller asked for. |
| A3 | What guards the division? | The prototype's own `sdiv`, i.e. `(a / b).replace([inf, -inf], nan)` (`docs/issues/screen/ind_screen.py:41-42`). | It is the source prototype's own operator, already the house style in `g191_080` / `g191_076` / `g191_191`. Inventing a different guard (an explicit zero mask, a fill) would be a larger, unasked change. |
| A4 | Gate E. | **Not run here.** The system prompt forbids touching `../Backtesting`. `docs/G191145Measured.md` says `Gate E: pending, run by issue-solver after this session`, and `tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one` is expected to fail until the launcher records the row. | The prompt's own instruction; holding the indicator out of `Category` to silence the test is explicitly forbidden. |
| A5 | Gate F. | This repo's suite only (`python -m pytest -q`). The parent repo is the launcher's clean-worktree run. | The prompt's own instruction. |

No pre-authorisation for any destructive step was given or needed: nothing in this task pushes,
deploys, force-pushes, or deletes data.

## Phase 3 — Execution map

| task | lane | why |
|---|---|---|
| `g191-145` | main thread | Single task; the whole change is one coherent edit across five wiring touch points plus docs, and the review gate needs the main context to apply fixes between rounds. |

Review rounds are capped at **4** in total (round 1 + 3 re-runs) per the user's standing global
rule, which overrides the skill's own 3-round cap.

Log: `01-g191-145.md`. Summary: `99-summary.md`.
