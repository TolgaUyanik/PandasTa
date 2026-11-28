# B2-VOL-ABOVE-MID-20 — auto run manifest

## Task

Single free-form task (Mode C, one item): port `b2_vol_above_mid_20` (issue
#188) through Gates A-D, the five wiring touch points, the test module, and
`docs/B2VolAboveMid20Measured.md`, per the issue text and the issue-solver's
own system-prompt rules (Gate E and the whole suites are the launcher's, not
this session's).

## Clarify

No clarifying questions asked — the issue text and the system-prompt rules
fully specify scope, formula, category (volume, inferred from the
prototype's `@cand` registration and the nm_effort_result_20/bw_mfi
precedent for high/low/close/volume volume-category ports), and the "done
when" criterion.

## Execution map

Single task, main thread (not a parallel subagent lane): implementation
needs continuous judgment across the five wiring touch points and several
interlocking doc/test files that reference each other's counts
(`tests/test_altport2_ports.py`, `README.md`, `docs/MLCompanionContract.md`,
`docs/IndicatorDictionary.md`), so a sequential single-lane run was used
rather than splitting into independent subagent lanes.

## Gate

One Fletcher reviewer subagent (`Explore`, read-only, `--fletcher` persona)
dispatched against the full diff. Report: `01-b2-vol-above-mid-20.md` in
this folder.
