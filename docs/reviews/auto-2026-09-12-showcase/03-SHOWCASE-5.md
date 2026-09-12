# SHOWCASE-5 — land it and point at it

**Status:** 🔴 ESCALATED (numeric acceptance criterion not met)
**Rounds:** 1
**Deliverables:** `README.md`, `CLAUDE.md`, the provenance block in `examples/market_dashboard.py`

## Implementation

- README gains a *Runnable examples* section: both files linked, what they demonstrate, what
  they deliberately do not, the `--offline` invocation first, and `pip install "pandas-ta[examples]"`
  for the optional loader. The notebook row states it is **not executed by the suite**.
- The example's docstring carries a PROVENANCE block: version `0.2.67b1+tu.1`, branch `dev`,
  commit `43d0685`, with a note preferring `--version` over the commit for anyone cloning.
- `.gitignore` gained `!examples/*.ipynb`; a blanket `*.ipynb` at line 135 would otherwise have
  made the notebook uncommittable. No rule touches the `.py`.

## Review round 1 — VERDICT: REVISE, then an ADDENDUM after the full suite finished

Reviewer summary, verbatim:

> You wrote 716 lines of code whose central thesis [...] is that swallowing an exception is how
> sixteen broken indicators survived undetected for the life of a file. And then, in
> `check_causality`, the one function whose job is to find look-ahead leaks, you typed the wrong
> dictionary key in the error branch and built yourself a swallowed exception that prints
> `UNKNOWN LEAKS   : 0` over the top of a probe that never ran. [...] Then you gated the whole
> thing behind `pytest.importorskip` on your own first-party file, so the deliverable that
> SHOWCASE-5 measures by "0 failed" can skip all 33 tests and still hand you a green light — and
> none of it is committed, so the clone story you spent a docstring paragraph on is currently
> fiction. The spec table is genuinely good work, the sixteen repairs are named and pinned
> individually, the scale-free double-verdict is correct and the `bos` bound is measured rather
> than asserted. Fix the key, fix the import, land the files. Then we talk.

And the addendum, once the 15-minute run completed:

> SHOWCASE-5's acceptance criterion is, verbatim, "`python -m pytest -q` stays at **0 failed**".
> It does not. [...] It is almost certainly not caused by the showcase work [...] but the gate
> you wrote for yourself does not say "0 failed among tests you touched". It says 0. You do not
> get to grade your own homework on a curve you invented after the run.

Verified clean by that reviewer, for the record: no module-level `yfinance` import; no `deploy/`,
`backtesting_engine` or `config` reference in either example; `--out` a genuine argument
exercised against `tmp_path`; `.gitignore` negation resolves correctly; commit `43d0685` exists,
is HEAD of `dev`, and is pushed, so it means something to a cloner; README states both what the
example demonstrates and what it does not.

## Why this is ESCALATED

`tests/test_pine_coverage_csv.py::test_audited_rows_carry_their_evidence` **fails on a clean
checkout**. It asserts that every `<path>:<n>` citation in `docs/pine_builtin_coverage.csv`
resolves to a real file; the first failing row is `supertrend`, citing `RA2vGpkA-ta.pine`.

The cause is `8d8f705`, which untracked the 2,211-file `docs/pine/` corpus because 912 of those
files are MPL-2.0 under a root MIT `LICENSE`. The citations were never updated, so the guard now
demands files the repo deliberately does not carry. **Pre-existing and unrelated** — nothing in
this run touches pine coverage — but the criterion says 0, and it is 1.

Recorded in `CLAUDE.md`'s *Known breaks*, which until this run read "None outstanding" and was
therefore false.

**Owner's call, both ways:** re-adding the corpus reverses a licensing decision; relaxing the
guard removes the only thing separating "audited" from "asserted". A third option is to amend
SHOWCASE-5's done-when to name this one permitted failure explicitly — rewriting one's own
acceptance criterion is not the executor's call.
