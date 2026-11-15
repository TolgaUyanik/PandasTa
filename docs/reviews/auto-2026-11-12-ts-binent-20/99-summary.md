# Auto run summary — TS-BINENT-20 (PandasTa issue #89)

Mode C, one task, 2026-11-12, branch `issue-89-ts-binent-20`.

| task | status | rounds | files touched | follow-ups |
|---|---|---|---|---|
| `ts-binent-20` | **PASS** (round 4, the loop's last gate) | 4 — R1 REVISE (8 findings, applied), R2 PASS + 5 MINOR/NIT (applied), R3 PASS + 3 MINOR/NIT (applied), R4 PASS + 4 MINOR/NIT (applied **after** the final gate, so those four text-only fixes are themselves unreviewed) | `pandas_ta/statistics/ts_binent_20.py` (new), `pandas_ta/statistics/__init__.py`, `pandas_ta/__init__.py`, `pandas_ta/core.py`, `tests/test_ts_binent_20.py` (new), `tests/test_altport2_ports.py`, `README.md`, `docs/IndicatorDictionary.md`, `docs/MLCompanionContract.md`, `docs/TsBinent20Measured.md` (new), `docs/measure_ts_binent_20.py` (new), this run folder | Gate E (the launcher), then a receipt session for the `docs/gate_e_ledger.csv` row and Gate C's real-data counts |

Every round's verbatim verdict, and a table of the fixes applied after each, is
in `01-ts-binent-20.md`. Two sequencing errors are recorded there rather than
hidden: a round-3 verdict and a round-4 outcome were each drafted before their
review ran, and both were replaced by the reviewers' actual output.

## What shipped

`TS_BINENT_20_5` in `Category["statistics"]`: five equal-width bins across a
20-return window's own `[min, max]`, Shannon entropy of the bin shares in nats.
Bit-equal to issue #89's screen prototype on 1,480 of 1,480 bars of a
1,500-bar walk, and bit-equal to the same definition spelled with numpy's own
`np.histogram` on a walk and on a tick-rounded walk.

Gates A–D are closed in `docs/TsBinent20Measured.md`. Gate E is **owed** and
is the launcher's: `tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
fails here reporting `['mtd_ret', 'ts_binent_20']`, which is expected until a
later session records the row.

Three things the measurement run decided rather than confirmed:

* the equal-frequency (quantile) reading of "binned entropy" is a CONSTANT
  column (`log 5` on 1,480 of 1,480 bars), so equal-width bins are not a
  preference;
* the rounding-noise floor matters more here than for `ts_c3_20`: an exactly
  geometric ladder read unguarded produces values *inside* a real walk's live
  range (114 of 280 between 0.9262 and 1.6094), where `ts_c3_20`'s unguarded
  failure reached 8e+41 and was obvious;
* the column is invariant to the AMPLITUDE of the returns, not only to the
  price level (bit-identical under ×0.5 and ×3 of the returns themselves and
  under +0.004 of log drift a bar) — so it is not a volatility feature, and
  the docstring says so where a consumer reads first.

One real bug was found by the review and fixed: a close pair whose ratio
OVERFLOWS (1e-300 followed by 1e50) passed the close guard and, run unguarded,
reports 0.048729 on all 20 affected windows — a finite, plausible value below
the floor the column claims as its minimum. The module now empties a
non-finite return.

## Runs

* `python -m pytest tests/test_ts_binent_20.py -q` → **126 passed** in 4.30 s.
* `python -m pytest -q` → **3 failed, 5,802 passed, 83 skipped** in 121.34 s.
  The three are the two `CLAUDE.md` *Known breaks*
  (`test_altrepo_talib_csv.py::test_regenerating_reproduces_the_committed_rows`,
  `test_pine_coverage_csv.py::test_audited_rows_carry_their_evidence`) plus the
  owed Gate E ledger row.
* `python docs/measure_ts_binent_20.py` (and each section individually) — the
  source of every number quoted in the module docstring, the test docstring
  and the receipt.
* `python docs/gen_indicator_dictionary.py` → 324 indicators probed,
  `TS_BINENT_20_5` tagged **SF** with a 20-bar warm-up.

## Assumptions (no questions were possible in a headless run)

The five logged in `00-manifest.md` stand: the degenerate window is NaN rather
than 0 (the prototype's reading, which is also what issue #89's Gate E numbers
were screened with); the column name carries the effective parameters; entropy
in nats, unnormalised; `bins` clamped to `length`; Gate E left to the launcher.
Each is priced in the receipt rather than asserted.

Reviews: `01-ts-binent-20.md` carries all four rounds' verdicts verbatim and a
table of the fixes applied after each.
