# Run manifest — `/brutally-honest-review --auto`, 2026-11-13

Mode C (batch task execution), one task. Fletcher theatrics on. Run folder
`docs/reviews/auto-2026-11-13-ts-cross-mean-20/`.

## Phase 1 — the task, resolved

One task, given verbatim in the invocation:

> TS-CROSS-MEAN-20: port the indicator of issue #100 through Gates A-D, the
> wiring, the tests and docs/<Name>Measured.md, per the issue and the rules
> in your system prompt (crossings of the window mean by log price (20).
> Source: tsfresh feature_calculators (MIT) —
> `number_crossing_m(x, m=mean) on 20 log closes`.). Gate E and the suites
> are run by the launcher afterwards.

Source line, from the issue: `number_crossing_m(x, m=mean) on 20 log
closes`. Prototype: `docs/issues/screen/ind_screen.py`, candidate
`ts_cross_mean_20` (gitignored, owner's machine; readable in this
worktree).

Done criterion, from the issue: shipped through Gates A–F with the numbers
in `docs/TsCrossMean20Measured.md`, OR measured and reverted with that file
kept as the receipt.

## Phase 2 — clarifications

`AskUserQuestion` is unavailable in this headless session, so by the
skill's own rule every ambiguity was resolved by the **most conservative
(smallest-scope) reading** and logged here as an ASSUMPTION.

* **ASSUMPTION 1 — the output is the RAW COUNT, not a share.** The issue
  names `number_crossing_m`, whose return value is a count, and the screen
  prototype returns the count as a float. Normalising by `length - 1`
  would be an exact, rank-identical rescaling, so it changes no gate — but
  it is an invented transformation and the smaller scope is not to invent
  it. Priced in `docs/TsCrossMean20Measured.md` A5.
* **ASSUMPTION 2 — `x` is `log(close)` over 20 CLOSES, so the first value
  lands at bar 19.** That is the issue's wording and the prototype's
  placement. The alternative readings (raw closes, 20 returns) are priced
  in A5 rather than silently rejected.
* **ASSUMPTION 3 — category `statistics`**, matching every sibling tsfresh
  port in this fork (`ts_above_mean_20`, `ts_peaks_20`, …).
* **ASSUMPTION 4 — one guard family only.** A relative dispersion floor
  plus a bad-close mask. No magnitude bound (G5 derives why none is
  needed) and no `isfinite` backstop (the output is an integer count).
  Adding either would be unmeasurable dead code.
* **ASSUMPTION 5 — Gate E is NOT run here.** The session rules override the
  issue: the launcher runs `gate_e_overlap.py`, and nothing outside this
  worktree is read or written. `docs/TsCrossMean20Measured.md` §E says
  "pending, run by issue-solver after this session", the indicator is wired
  into `Category` as usual, and
  `tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
  fails until the receipt session records the row. That failure is
  expected.

## Phase 3 — execution map

| task | lane | why |
|---|---|---|
| TS-CROSS-MEAN-20 | main thread | one task, one scope; the work needs main-context judgment (which gates pass, what the guards cost, ship vs revert) and the file scope is a single module plus its five wiring points |

No parallel subagent lanes: a single task cannot conflict with itself, and
worktree isolation would buy nothing.

## Destructive steps

None. No push, no deploy, no deletion, no external publication. The commit
is local and by path.
