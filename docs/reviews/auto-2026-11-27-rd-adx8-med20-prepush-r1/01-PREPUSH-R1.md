# PREPUSH-R1 — fix the round-1 pre-push review's findings

Task (verbatim, from the invocation): "Fix every CRITICAL and MAJOR finding of the pre-push
review gate (round 1 of 3, HEAD ebc180eb00ea) ... fix MINOR/NIT findings only when cheap and
safe." The gate's five findings (one MAJOR, three MINOR, one NIT) are quoted in full in the
invocation and are not repeated here; see the command history.

## Execution log

- Read `docs/RdAdx8Med20Measured.md`, `tests/test_altport2_ports.py` (lines 170-210),
  `docs/gate_e_ledger.csv` (grep for `rd_adx8_med20`), `pandas_ta/trend/rd_adx8_med20.py`,
  `tests/test_rd_adx8_med20.py` (to confirm `min_bars` is only exercised at defaults).
- MAJOR fix (Gate C row): confirmed the ledger row's figures
  (`docs/gate_e_ledger.csv:126`): `non_nan`=395823, `non_zero`=395823 of 398,849 pooled bars,
  89 ALTPORT-1 frames, run `is178-rd_adx8_med20-160a9a66`. Replaced
  "Real-data reachability: owed with Gate E." with the measured sentence, matching the sibling
  receipt's style (`docs/RdAdx3Med10Measured.md:40`).
- MINOR fix 1 (`tests/test_altport2_ports.py`'s `CATEGORY_TOTAL` comment, #178 clause): replaced
  "Gate E: pending, run by issue-solver after this session" with
  "Gate E DISCLOSE_GAP, 0.8089 vs `ADX` (per-frame max median 0.8072), run
  is178-rd_adx8_med20-160a9a66, measured 2026-11-27", matching the #171 sibling entry's shape in
  the same comment.
- MINOR fix 2 (`CATEGORY_BUCKETS` line): dropped the trailing
  `# PLACEHOLDER: fix after measuring` comment. Values (`trend: 70, volatility: 43, volume: 48`)
  unchanged -- they were already correct.
- MINOR fix 3 (Gate E row's precision claim): the port measures 0.8088632042790855 to the
  prototype's 0.8090 -- agreement to three decimals (0.809), not four. Replaced "Matches the
  issue's own prototype measurement (0.8090 vs `ADX`) to the fourth decimal." with
  "0.8089 on the port vs 0.8090 on the prototype -- a 1.4e-4 difference, the prototype's own
  screen harness."
- NIT (not applied): attempted the suggested simplification
  (`min_bars = 2 * adx_length + length`), ran the gate test list, got exactly one failure --
  `test_gate_e_ledger.py::test_row_still_describes_its_module[rd_adx8_med20:RD_ADX8_MED20_8_20]`
  -- because the edit moves the module's sha1 away from the one pinned in the already-recorded
  Gate E ledger row. Reverted the edit. `pandas_ta/trend/rd_adx8_med20.py` is byte-identical to
  before this round (confirmed: `git diff` on that file is empty).

## Review round 1 (this fix round's own first gate)

```
VERDICT: PASS
FINDINGS:
  (none)
SUMMARY: All four required fixes check out against the hard evidence -- docs/RdAdx8Med20Measured.md's Gate C row now states the real measured counts (395,823 non-NaN of 398,849 pooled, all non-zero), matching docs/gate_e_ledger.csv's rd_adx8_med20 row exactly and mirroring RdAdx3Med10Measured.md's sibling style; the Gate E row's precision claim is corrected to a verifiable 1.4e-4 gap (0.80886 vs 0.8090) instead of the false "fourth decimal" claim; test_altport2_ports.py's CATEGORY_TOTAL comment for #178 now carries the real Gate E DISCLOSE_GAP numbers, run id, and date with no stray "pending" leftover anywhere for issue #178; and the PLACEHOLDER comment on CATEGORY_BUCKETS is gone with the pinned values (70/43/48) left intact. The NIT was correctly left alone -- the module's sha1 (f699c01cd00608423ff369bc3924d3b3fae32aaf) is bit-identical to the one pinned in the ledger row, and tests/test_gate_e_ledger.py does hash-check the module against that row, so touching min_bars would have broken a measured, ledgered test for a cosmetic win. Nothing else drifted: Category total 415 / trend 70 stated in the doc's "Wiring counts" section lines up with the test file's pinned constants. Clean work, no gate violations -- ship it.
```

## Outcome

PASS, round 1.
