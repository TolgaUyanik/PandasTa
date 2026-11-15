# Manifest — auto-2026-11-08-a101-048

Mode C (batch task execution), single task, resolved from a free-form `--auto` argument
(issue-solver headless invocation for issue #41 / A101-048).

## Task

> A101-048: port the indicator of issue #41 through Gates A-D, the wiring, the tests and
> docs/<Name>Measured.md, per the issue and the rules in your system prompt
> (autocorrelation-scaled return. Source: Alpha101 (Kakushadze 2016, Wilmott; vnpy alpha101
> copy) — `#48 without IndNeutralize: corr(delta(close,1), delta(delay(close,1),1), 250) *
> delta(close,1)/close /). Gate E and the suites are run by the launcher afterwards.

## Clarifications (Phase 2)

None needed. The task, the issue text (#41), and the session's system-prompt rules
(Gate E left pending, suites run by `python -m pytest -q` only in this worktree, allowed
file list) fully specify scope, formula, and done-criterion. `AskUserQuestion` is
unavailable in this headless session per the system prompt's override; no ambiguity arose
that would have required it.

## Execution map (Phase 3)

Single task, main thread (no parallel lanes — one indicator, sequential file wiring with
ordering dependencies between the module, its wiring, its tests, and the docs that quote
counts derived from the wired state).

An earlier attempt at this exact issue existed on `solver-backup/issue-41-a101-048`
(commits `1c23db8`/`faec5fa`/`48d3529`), discovered via `git log --all` before any new code
was written. Its Gates A-D implementation (module, test file, measurement script) was
reused as a verified-correct starting point — re-run and independently checked in this
session, not trusted blindly — but its two Gate-E-filling commits were NOT reused: this
session's rules require Gate E to stay `pending, run by issue-solver after this session`,
which the backup branch's later commits violated (apparently why that attempt was reset).
All doc/count edits (README, IndicatorDictionary, MLCompanionContract, CATEGORY_TOTAL) were
recomputed fresh against this branch's current baseline, since `vol_sign_rev` (issue #43)
had landed in between and shifted every running count.

## Done criterion

Gates A-D cleared and measured in `docs/A101048Measured.md`; the five wiring touch points
wired (module, `pandas_ta/momentum/__init__.py`, `Category["momentum"]`, `core.py` accessor,
`tests/test_a101_048.py`); `python -m pytest -q` run and its baseline recorded; Fletcher
review gate PASS. Gate E and both repos' full suites are explicitly out of scope — the
launcher runs those after this session.
