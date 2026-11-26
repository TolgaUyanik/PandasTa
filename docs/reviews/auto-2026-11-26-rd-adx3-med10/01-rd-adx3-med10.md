# Task RD-ADX3-MED10 — port `rd_adx3_med10` (issue #171)

## Implementation summary

Ported "rolling median of ADX(3) (10)" (Reddit, tier 4, rd:quant:1gc3o70) as `rd_adx3_med10`
(category `trend`): `ADX_3 = adx(high, low, close, length=3)`, then `ADX_3.rolling(10).median()`.
Re-uses this fork's own already-tested `adx()` rather than re-deriving ADX from scratch. Ships
exactly the one combination issue #171 names (ADX(3), median window 10) out of the poster's six
(ADX 3/5/8 x median 10/20) — the other five are out of this issue's scope.

Files added: `pandas_ta/trend/rd_adx3_med10.py`, `tests/test_rd_adx3_med10.py` (13 tests),
`docs/RdAdx3Med10Measured.md`, `docs/measure_rd_adx3_med10.py`, `docs/measure_rd_adx3_med10_cpu.py`.

Files modified (wiring + counts): `pandas_ta/trend/__init__.py` (export), `pandas_ta/__init__.py`
(`Category["trend"]`), `pandas_ta/core.py` (accessor), `README.md`, `docs/IndicatorDictionary.md`
(regenerated), `docs/MLCompanionContract.md` (tally), `tests/test_altport2_ports.py`
(`CATEGORY_TOTAL`/`CATEGORY_BUCKETS`).

Gates A-D cleared this session (measured numbers in `docs/RdAdx3Med10Measured.md`). Gate E and both
repos' whole suites are the launcher's job, per this session's rules — `docs/RdAdx3Med10Measured.md`
states Gate E as pending.

## Assumptions

- ASSUMPTION: "Gate A starts from the source formula, not the prototype" is satisfied by citing and
  re-using this fork's own existing, already-Gate-A'd `adx()` implementation rather than
  re-deriving Wilder's ADX arithmetic from scratch — there is no screen-prototype script for this
  specific issue beyond the quoted Reddit words, and ADX itself is a well-established, independently
  verifiable formula already ported and tested in this repo. Most conservative reading available
  given no prototype file was provided for this issue; no user available to ask (headless session).

## Review rounds

### Round 1 — Fletcher (Explore subagent, read-only)

```
VERDICT: REVISE
FINDINGS:
- severity: MAJOR
  location: downloaded_files/dashboard.lock
  problem: The tracked, empty placeholder file is missing from the working tree in this session
    (`git status` shows an unstaged `D`; the `downloaded_files/` directory does not exist on disk
    at all). This is the exact same defect already discovered and fixed during the #169 port
    (commit 7c8baa8, "restore downloaded_files/dashboard.lock, deleted by mistake in the port
    commit"), recurring here.
  fix: Run `git checkout HEAD -- downloaded_files/dashboard.lock` before committing anything from
    this session, and track down whichever step in the port workflow deletes it so it stops
    needing a dedicated restore commit after every port.
- severity: MINOR
  location: tests/test_rd_adx3_med10.py:170
  problem: `test_scale_within_tolerance` asserts `< 1e-6`, but the measured x10/x3.7 diffs are
    ~3e-13 (reproduced: 3.055e-13 / 3.624e-13), and every sibling Reddit-port test for the same
    check — including the explicit house template `tests/test_rd_range100_pct500.py:189` — pins
    `1e-9`. No stated reason for the 1000x-looser bound here.
  fix: Tighten to `< 1e-9` to match house convention and the module's own measured precision, or
    state explicitly in the test docstring / Measured.md why 1e-6 was chosen instead.
SUMMARY: The actual indicator work is clean -- Gate A's reuse of adx() is honestly cited and
verified, Gate B's mutant is genuine with correctly-reasoned 5-of-9 catch math, Gate D's claims
and every number in docs/RdAdx3Med10Measured.md reproduce exactly, all five wiring touch points
are present and correct, and the required test command reproduces the one expected Gate-E-owed
failure. What drags this to REVISE is process hygiene: a tracked placeholder file missing from the
tree, and one test's tolerance 1000x looser than the measurement for no stated reason.
```

**Investigation:** the `downloaded_files/dashboard.lock` disappearance is a recurring environment
artifact, not caused by this session's edits — nothing in the repo's own `.py` files references
that path (`grep -rl downloaded_files -- '*.py'` returns nothing), and it recurred identically
during the prior port (#169). It reappears after every `pytest` invocation in this sandbox
regardless of what is being tested. Deferred to a final `git restore` immediately before
committing, after all test runs for this session are done (confirmed present at commit time below).

**Fix applied for the MINOR finding:** `tests/test_rd_adx3_med10.py`'s `test_scale_within_tolerance`
tightened `< 1e-6` to `< 1e-9`; `docs/RdAdx3Med10Measured.md`'s Gate D row edited to say "within the
1e-9 test tolerance, matching house convention" instead of citing 1e-6. Re-ran the full required
test command: 1 failed (expected, Gate E owed), 1687 passed, 7 skipped — unchanged from before the
fix.

### Round 2 — Fletcher (Explore subagent, read-only)

```
VERDICT: PASS
FINDINGS: (none)
SUMMARY: Both round-1 findings are resolved. The tolerance fix landed exactly as described:
tests/test_rd_adx3_med10.py:68,88,170 all use 1e-9, and docs/RdAdx3Med10Measured.md's Gate D row
now cites "1e-9 test tolerance, matching house convention" with no stray 1e-6 references anywhere
in either file. The full specified test run reproduces exactly the expected result (1 failed — the
known-owed Gate E ledger test — 1687 passed, 7 skipped, no other failures). The module docstring's
SCALE-FREE section makes no tolerance claim to contradict the doc edit, and
docs/RdAdx3Med10Measured.md is internally consistent end-to-end. Clean; ship.
```

## Outcome

PASS at round 2. Task done.
