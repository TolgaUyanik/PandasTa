# Run manifest — auto-2026-11-10-g191-043

## Original ask (verbatim)

> G191-043: port the indicator of issue #69 through Gates A-D, the wiring, the tests and
> docs/<Name>Measured.md, per the issue and the rules in your system prompt (6-day signed
> volume (OBV slope). Source: GTJA191 (Guotai Junan 2017 report; HKUDS/Vibe-Trading copy, MIT)
> — `#43: SUM(C>C1 ? V : (C<C1 ? -V : 0), 6)`.). Gate E and the suites are run by the launcher
> afterwards.

## Task resolution

Single free-form task (no TODO tags, no plan file). Mode C, one task: `g191-043`.

## Phase 2 — clarify

Checked for gaps: scope, formula, column name, category, and done-criteria are all stated
in the issue text and this session's system-prompt rules (Gate E/F deferred to the launcher,
`docs/issues/` read-only, file-scope allowlist). No ambiguity found that needs a question.
**No gaps — none needed.**

One ASSUMPTION made during implementation (conservative reading, logged per the headless
rules since `AskUserQuestion` is unavailable in this environment):

* **Category placement.** The issue doesn't name a category. The prototype
  (`docs/issues/screen/ind_screen.py:357-359`) reads both `close` and `volume`, computing a
  signed-volume ratio — the same shape as this fork's own `obv` (`pandas_ta/volume/obv.py`).
  Placed in `volume`, the smaller-scope reading (matches the sibling `g191_080`/`g191_144`
  volume ports already in this category, rather than creating precedent for a new category).

## Phase 3 — execution map

One task, non-parallel (single file scope, no dependency conflict with anything else in the
tree). Main thread, in this session.

| Task | Lane | Why |
|---|---|---|
| g191-043 | main thread | single indicator port; the five wiring touch points all live in files already open this session; no benefit from subagent isolation |
