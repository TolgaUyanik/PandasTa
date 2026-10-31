# Mode C manifest — ovn-split

**Run:** `docs/reviews/auto-2026-10-31-ovn-split/`
**Original ask (verbatim):** "OVN: port the indicator of issue #14 through Gates A-D, the
wiring, the tests and docs/<Name>Measured.md, per the issue and the rules in your system prompt
(rolling sums of the close→open (overnight) and open→close (intraday) returns, as two). Gate E
and the suites are run by the launcher afterwards."

## Phase 1 — Select

One task, free-form (not a TODO tag): port issue #14 (OVN, overnight/intraday return split,
rolling) through Gates A-D + wiring + tests + `docs/OvnSplitMeasured.md`. Gate E and both repos'
suites are the launcher's job per this session's system prompt, which overrides the issue text.

## Phase 2 — Clarify

`AskUserQuestion` is unavailable in this headless session (per the system prompt's explicit
override), so every gap took the most conservative, smallest-scope reading and is logged as an
ASSUMPTION in `docs/OvnSplitMeasured.md` rather than asked:

1. Return form: log returns, not simple returns (additive identity under rolling sum).
2. Window length: 21 (one trading month), unexamined default.
3. Ship the difference column (`OVNINTDIFF_21`) rather than holding it back as optional.
4. Category: `momentum` (alongside the closest existing analog, `gapm`), not `performance` or
   `statistics`.
5. Bar 0's intraday leg is blanked to align both legs' warm-up.

**Risk check named by the issue ("measure how trustworthy the yfinance BIST open is... before
building") was NOT performed**: no network access, no BIST OHLC fixture in this worktree. Logged
as an open item in `docs/OvnSplitMeasured.md`, owed to the Gate E run, not silently skipped.

## Phase 3 — Plan execution

Single task, needs main-context judgment (formula design, gate numbers, ASSUMPTION calls) →
main thread, not a parallel subagent lane.

## Phase 4/5 — see `01-ovn-split.md` and `99-summary.md`.
