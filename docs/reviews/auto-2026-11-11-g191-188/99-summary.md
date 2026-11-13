# Auto run summary — g191-188 (issue #83), 2026-11-11

| task | status | rounds | files touched | follow-ups |
|---|---|---|---|---|
| `g191-188` | **ESCALATED** (cap spent at round 4; all 26 findings applied, round 4's fixes not re-reviewed) | 4 (REVISE x4) | `pandas_ta/volatility/g191_188.py`, `pandas_ta/volatility/__init__.py`, `pandas_ta/__init__.py`, `pandas_ta/core.py`, `tests/test_g191_188.py`, `tests/test_altport2_ports.py`, `docs/measure_g191_188.py`, `docs/G191188Measured.md`, `docs/IndicatorDictionary.md`, `docs/MLCompanionContract.md`, `README.md`, this run folder | Gate E (launcher), then a receipt session for the ledger row; the `g191_158` 0.95 synthetic overlap below |

## What the four rounds cost and bought

26 findings, recounted from the four verdict blocks in `01-g191-188.md`:
**9 MAJOR, 11 MINOR, 6 NIT, 0 CRITICAL**. Not one was a
mathematics error. Every round reproduced every number in the artifacts and
then failed the prose around them:

* round 1 — a measurement script that printed the first VALID bar under the
  label `first_displaced`, and a declaration that the prototype's own top Gate E
  comparator "cannot" be spoken to synthetically while the imports needed to
  speak to it sat two lines above;
* round 2 — a causal verdict ("the denominator's LENGTH") drawn from a
  three-variable-at-once proxy, plus a universal the table's own rows falsified;
* round 3 — a `two` and a `no port was found` that two receipts in the same
  directory refute, and a "length only" row that was `SMA(14,1)`, not
  `SMA(14,2)`;
* round 4 — a public docstring telling users that `smooth_length <=
  smooth_weight` raises when `n == m` silently ships a CONSTANT column, and
  "the fork ships ONE adjacent construction" when `massi` and `cvi` ship
  adjacent constructions in the same category.

**Round 4 paid for the whole loop.** Being forced to measure the near
neighbours instead of the far ones surfaced the one number that matters:
`g191_158` (`(H-L)/close`, ported 2026-11-11 under issue #81) measures Spearman
**0.951954** against this column on the 1,500-bar i.i.d.-spread walk — above
the 0.90 strike line, against a shipped `Category` column, and structurally
invisible to the issue's own 0.3338 fork-overlap number, which was measured on
2026-10-24, before `g191_158` existed. The artefact was then measured rather
than argued away: on a second frame with volatility clustering the same overlap
falls to **0.451513** while `g191_109` rises to 0.729682, and the quantity that
drives it (`e/close`'s coefficient of variation) moves 0.1396 -> 0.9382. Real
tapes cluster. Gate E decides.

## Text that landed with the cap spent and was NOT re-reviewed

Round 4's seven fixes, listed in `01-g191-188.md` under "Fixes applied after
round 4". Concretely, the following is unreviewed:

* `pandas_ta/volatility/g191_188.py` — the `smooth_length` three-band
  parameter note; the rewritten "RELATION TO THE FORK'S OTHER RANGE COLUMNS"
  block (the `massi` / `cvi` / `g191_158` numbers and the clustered-frame
  figures); the `adjust=False` seed paragraph in OPERATORS; the scoped `only`
  in the dead-bar paragraph; the public `__doc__`'s nearest-shapes sentence.
* `tests/test_g191_188.py` — `test_a_length_equal_to_the_weight_collapses_the_column_to_zero`
  and the amended docstrings around it.
* `docs/measure_g191_188.py` — the `massi` / `cvi` / `g191_158` rows,
  `_walk_clustered`, `_gtja_sma_local`, and the `e/close` CV block.
* `docs/G191188Measured.md` — the "fork's other range columns" subsection, the
  twelve-row table, the "0.951954 is an artefact of the frame" subsection, the
  engine-column UNKNOWN sentence, the 0.0138 and 0.18/0.15 corrections, the
  Gate A seed paragraph, and the `smooth_length` edge-case row.
* `docs/reviews/auto-2026-11-11-g191-188/00-manifest.md` — ASSUMPTION 7.

Every number in that text comes from `python docs/measure_g191_188.py` run
after the edit, and the suite was re-run after it: **3 failed, 5332 passed, 83
skipped**, `tests/test_g191_188.py` **30 passed**. What is missing is an
independent reader, not a run.

## Open, for the owner

1. **Gate E.** Not run here. The launcher runs
   `gate_e_overlap.py run --module pandas_ta.volatility.g191_188`; the receipt's
   Gate E row says pending and `docs/gate_e_ledger.csv` has no row, so
   `tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
   fails on this tree reporting `['g191_188', 'mtd_ret']`. Expected.
2. **The `g191_158` overlap.** 0.951954 synthetic on an i.i.d. frame, 0.451513
   once the frame clusters. Not a Gate E comparator (Gate E's 687 are engine
   columns), so no band applies to it, but CLAUDE.md's non-redundancy rule
   does. Owner's call whether the fork wants both columns.
3. **The prototype's prior.** 0.8846 / DISCLOSE_GAP vs the engine's
   `Range_ATR`. Nothing measured here moves it; the nearest in-fork proxy lands
   at 0.569340 and the receipt says why that is probably the i.i.d. frame.
4. **Pre-existing, out of scope:** `pandas_ta/core.py:451-453` + `:691-692`
   mutate the live `Category` list, so any `df.ta.strategy("<category>")` call
   permanently deletes the excluded names for the rest of the process. That is
   why `tests/test_altport2_ports.py`'s `CATEGORY_TOTAL` check fails when
   `tests/test_wiring_accessors.py` runs before it in the same process (314 vs
   317) and passes in the full suite's alphabetical order.
