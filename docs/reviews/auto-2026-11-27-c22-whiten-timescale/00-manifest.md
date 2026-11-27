# Auto run manifest — C22-WHITEN-TIMESCALE (issue #139)

## Task

> C22-WHITEN-TIMESCALE: port the indicator of issue #139 through Gates A-D, the
> wiring, the tests and docs/<Name>Measured.md, per the issue and the rules in
> the system prompt (catch22 ACF timescale of 1-bar forecast residuals vs
> returns (100). Source: catch22 (Lubba et al. 2019, Data Min. Knowl. Disc.
> 33:1821; reference code pycatch22 1.0.2, GPL-3.0 -- port from the
> definitions)). Gate E and the whole suites are run by the launcher
> afterwards.

Single task, free-form (Mode C, batch-of-one).

## Phase 2 — clarify

The issue text plus the repo's `CLAUDE.md` gate table and the launcher's own
override rules (never run Gate E or the whole suite; write "Gate E: pending,
run by issue-solver after this session" in the receipt; wire into `Category`
even though the ledger test stays red until the launcher's run) were fully
actionable as written. No clarification needed.

One judgment call made during implementation, logged as an ASSUMPTION: the
issue names the feature `FC_LocalSimple_mean1_taurat`; catch22's own
definition (confirmed against the installed `pycatch22` black box, used only
for measurement) computes this as hctsa's `CO_FirstZero`, a LINEARLY
INTERPOLATED fractional lag, not a bare integer one. An initial build that
scanned only the integer lag read exactly 1.0 on every sampled window while
the reference read ~0.70-0.73 on the same windows; the interpolation was
added and closed the gap to 0 of 8,400 windows disagreeing beyond 1e-9. This
is documented in the module docstring, the test module, and
`docs/C22WhitenTimescaleMeasured.md` section 1.1.

## Phase 3 — execution map

Single task, main thread (needs judgment: reading the catch22 definition,
deriving the ACF-timescale-ratio algorithm, and fitting the interpolation
step against the GPL-3.0 reference as a black box are not mechanically
delegable). No parallel lanes.

## Phase 4 — gate

See `01-c22-whiten-timescale.md` for the implementation log and the Fletcher
reviewer's verdict.
