# run summary — auto-2026-11-13-ts-imq-20

| task | status | rounds | files touched | follow-ups |
|---|---|---|---|---|
| `ts-imq-20` (PandasTa #99) | **PASS** | 4 (REVISE, REVISE, PASS, PASS) | added `pandas_ta/statistics/ts_imq_20.py`, `tests/test_ts_imq_20.py`, `docs/measure_ts_imq_20.py`, `docs/measure_ts_imq_20_cpu.py`, `docs/TsImq20Measured.md`, this folder; modified `pandas_ta/statistics/__init__.py`, `pandas_ta/__init__.py`, `pandas_ta/core.py`, `tests/test_altport2_ports.py`, `README.md`, `docs/IndicatorDictionary.md`, `docs/MLCompanionContract.md` | Gate E (launcher), then the receipt session: record the ledger row and replace `test_the_gate_e_row_is_owed`; write the real-data reachability counts into §C |

## What shipped

`TS_IMQ_20` — tsfresh `index_mass_quantile(q=0.5)` over the trailing 20
simple returns: **where in the window half the absolute-return mass sits**,
as `k / 20` for an integer `k` in 1..20. Near 1 the big moves are recent,
near 0 they are old. A POSITION, not a size.

Gates A–D measured in `docs/TsImq20Measured.md`. Gate E **pending, run by
issue-solver after this session**. Gate F: both repos' suites are the
launcher's; locally 212 module tests pass with and without AVX-512 / AVX2 /
FMA3 dispatch, and the full suite is 3 failed / 7,495 passed / 85 skipped
(the two pre-existing breaks plus the owed Gate E row).

## The one thing a reader should carry away

The column overlaps the shipped **`TFCENTROID_20`** — TSFEL's temporal
centroid, the energy-weighted MEAN position of the same 20 returns against
this absolute-mass MEDIAN position — at pooled Spearman **+0.846649** over
nine synthetic frames (n = 13,320), per-frame |rho| median 0.8545, max
0.8857, **0 of 9 frames at or above 0.90**. That is DISCLOSE_GAP under
`r3-perframe-0.90`, not STRUCK, so it ships with the warning in five places
(module docstring, dictionary row, contract, receipt §O, test header).

⚠ Those figures are **SYNTHETIC**, and no real-frame figure bounds the pair:
the 2026-10-24 screen's fork overlap was taken six days before
`tf_centroid_20` entered `Category` (commit `4f1063b`, 2026-10-30), and Gate
E's 687 comparators are the engine's and hold no pandas_ta port.
`docs/TsImq20Measured.md` §E names what would reverse the ship decision.

## What the four rounds were about

Not the mathematics. Every reviewer re-ran all seven measurement sections
and every figure reproduced, including the gitignored screen's. All eleven
findings across rounds 1–2 were the same class — a claim one notch stronger
than the run behind it:

* two tests that could not fail (a `+ 1` "priced" by subtracting the
  conclusion from itself; a backstop test that re-implemented the module
  inside itself);
* exact bit-equal counts pinned against oracles whose summation order
  differs from the module's, on the one frame the port's own §D2 proves is a
  knife-edge tie;
* "exactly 0.05" against a printed 0.050000000000000044;
* a timing quoted as the fastest of several observations;
* and, in round 3, the mirror image — a coverage claim one size too large
  written on top of the fix for an over-assertion.

Round 4 found one stale "three", one "cannot" that should have been "did
not", two unillustrated timing rows, and this folder's absence.

## Not run

`codex exec -s read-only` — not an allowed command in this session. Only the
BHR loop ran. Gate E and the two clean-worktree suites are the launcher's.
