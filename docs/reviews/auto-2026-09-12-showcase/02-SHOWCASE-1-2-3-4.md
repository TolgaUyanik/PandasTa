# SHOWCASE-1, -2, -3, -4 — the example and its test

**Status:** fixed in round 1; re-gate pending
**Rounds:** 1
**Deliverables:** `examples/market_dashboard.py`, `tests/test_showcase.py`, `setup.py`

These four share two files, so they were built together and gated by three reviewers in
parallel (one on -1/-2, one on -3, one on -4/-5).

## Implementation

- **-1** 125 table specs, all sixteen previously-broken argument lists corrected and each marked
  `# FIXED:` with its defect. The three that take a *derived* series — `long_run`, `short_run`,
  `trend_return` — are quarantined in `DERIVED_SPECS`, because a table keyed on frame-column
  names is structurally incapable of calling them, which is precisely why the original called
  them wrongly.
- **-2** No bare `except:`. Failures collected as `(name, exception)` and returned; exit status
  is 1 if any.
- **-3** 62 fork indicators. Coverage computed from `ta.Category` at runtime.
- **-4** `yfinance` imported only inside the optional loader and given its own `extras_require`
  entry; output path an argument; the test drives everything on a synthetic frame.

## Review round 1 — all three VERDICT: REVISE

### The CRITICAL, found independently by three of four reviewers

> You deleted a bare `except: continue` from the spec loop and then rebuilt the exact same
> swallow, by typo, in the causality probe of the same file.

`check_causality`'s error branch appended `{"causal": f"error: {exc}"}` while every consumer —
`report()`, and `test_no_unknown_lookahead` — reads `"verdict"`. A raising probe therefore
produced a row with `verdict = NaN`: counted in none of clean / known / unknown, printed
nowhere, absent from the exit status, and invisible to the test written for it. With every probe
raising, `report()` would have died on `KeyError: 'verdict'`.

Reproduced before fixing:

```
   column  max prefix drift               causal verdict
   RSI_14               0.0                  NaN  causal
exploding               NaN error: probe blew up     NaN
rows classified UNKNOWN LEAK: 0
```

**Fixed:** key is `"verdict"`, value `ERROR: <Type>: <msg>`; `report()` prints a `PROBE ERRORS`
line; errored probes **and** unknown leaks are folded into `failures`, so both drive a non-zero
exit. `test_a_raising_probe_is_reported_not_swallowed` pins it, and asserts the phantom `causal`
column has not returned.

### The other MAJORs

**Registry keyed on column alone.** `ta.dpo(close)` and `ta.dpo(close, centered=False)` both
emit `DPO_20`, so the safe variant inherited the unsafe one's excuse. Re-keyed on
`(probe label, column)`.

**"asserts exactly this set — no more, no less" was 1/6 true.** Only `DPO_20` had a
still-leaks guard. Now every entry is guarded, split into `SINGLE_CUT_GUARDED` and
`SWEEP_GUARDED` with an assertion that the union covers the registry.

**"72 perturbation cuts" — the shipped test runs 20.** The 72 came from a throwaway script that
is not in the repo. Docstrings now state the sweep parameters inline.

**"the SMC ports" meant five of twenty-one.** Sixteen registered structure modules plus seven
PINEBI alternates and nine other fork originals were untouched with no stated reason. Added.
Coverage **158 → 190 of 233 (68% → 82%)**. `NOT_EXERCISED_BY_DESIGN` now holds a reason per
skip, and the example prints anything unexercised *without* one — currently 43 names, listed
rather than merely counted.

**`pytest.importorskip` on a first-party file.** All 38 tests could vanish as skips, which
satisfies SHOWCASE-5's "0 failed" perfectly. Replaced with `spec_from_file_location`, also
removing a permanent front-of-`sys.path` mutation.

**`_collect` silently dropped unhandled result types.** An indicator returning a scalar or an
array matched no branch, wrote nothing, and was reported as a success. Now returns the column
names written; zero names is a failure, an unhandled type raises.

This found a real defect on its first run: **`aobv` and `obv` both emit a column named `OBV`**.
Values are identical, so it is benign — but the panel holds one column where a caller counting
specs expects two. Reported as a distinct `duplicate column names` line; a collision with
*differing* values is a failure.

### Two findings REJECTED after measurement

**"Assert `worst == (swing_length-1)//2`."** Measured: sl=5 → 2 ✓, sl=7 → **2** (bound 3),
sl=9 → 4 ✓, sl=11 → **4** (bound 5). The formula is the *geometric* reach of a centered window;
a sweep only sees pivots it happens to straddle. Asserting equality would pin a sampling
accident. The test asserts `<= bound` **and** `== measured`, two different numbers, distinction
documented.

**"Probe all six registry entries with one cut."** Impossible: `bos` writes a pivot back only
when a cut straddles one, so a single-cut probe reports zero drift on a demonstrably leaky
implementation — which is exactly how this test failed on its first run. Hence the two-guard
split.

## Also fixed

Blind test extended to the branch that actually swallowed the sixteen (`aberration` called with
`close` alone → `TypeError`) and to `run_fork_specs`; `CONSOLIDATED_SOURCES` declared once and
proven by monkeypatched spies; coverage floor 0.60 → 0.78 and cross-checked against an
independent recomputation; `test_gate_e_reverts_are_not_resurrected` for the seven measured-and-
deleted Pine built-ins; missing ML companion now fails the run; dead `f` prefixes and the unused
`index` parameter removed; `"examples": ["yfinance"]` added to `extras_require`; module runtime
52s → 45s by memoising the scale-free panel.

## End state

```
core specs 125 + 3 derived-input | fork indicators 62
columns 201 core + 176 fork + 8 consolidated = 385
FAILURES 0 | duplicate column names (benign) 1
causality: 19 clean, 3 known exceptions, 0 UNKNOWN LEAKS, 0 PROBE ERRORS
coverage 190/233 (82%)
tests/test_showcase.py: 38 passed, offline, 45s
```
