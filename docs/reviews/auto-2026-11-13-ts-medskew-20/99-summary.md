# auto-2026-11-13-ts-medskew-20 — summary

| task | status | rounds | files touched | follow-ups |
|---|---|---|---|---|
| TS-MEDSKEW-20 (PandasTa #98) | DONE, shipped with disclosure | 4 (REVISE ×4, every finding applied; round 4's CRITICAL answered by recording, not editing — the files it names are outside this session's allowed-modify list) | 5 new + 7 modified, listed in `00-manifest.md` | Gate E (launcher), then the receipt session: record the ledger row, replace `test_the_gate_e_row_is_still_owed`, fill §9 of the receipt, and annotate the two stale files named below |

## What shipped

`TS_MEDSKEW_20` — `(mean(r) − median(r)) / sd(r)` over 20 simple returns, sd
with `ddof=1`. The nonparametric skewness of the window: Pearson's second
coefficient without its factor 3, invariant to any affine map of the returns
with a positive slope, bounded by `sqrt(19/20)` = 0.974679 by a theorem with
0.881631 the largest value any window built here reaches.

## The decision a reader should check first

The fork merged `TS_ABOVE_MEAN_20` (issue #97) earlier the SAME day, and it is
a BACKWARDS skewness reading over the SAME 20 returns. Synthetic overlap
reaches **−0.9025** (heavy-tailed) and **−0.8885** (walk); the only real-frame
figure is the 2026-10-24 screen's pooled **0.8428**
(`docs/issues/screen/cand_pairs.csv` line 39 of 56, and quoted in two
committed files). That is **DISCLOSE_GAP** under `r3-perframe-0.90`, not
STRUCK, so the port ships with the disclosure in five places — the dictionary
row, the module docstring, the test module's docstring, the ML contract and
`docs/TsMedskew20Measured.md` §O — and §O names the two things that would
reverse it: a STRUCK Gate E run on this module, or an owner's
question-redundancy ruling on the pair, which the bands do not make.

⚠ Gate E **cannot** re-measure that pair: its 687 comparators are the
Backtesting engine's and hold no pandas_ta port.

## Follow-ups owed outside this session's scope

* `pandas_ta/statistics/ts_above_mean_20.py:178` ("still a prototype and not
  shipped (issue #98)") and `docs/TsAboveMean20Measured.md` §5 lines 586-588
  and 775 ("no module in `pandas_ta/`", "still unshipped") are false from this
  commit on. Both files are outside issue #98's allowed-modify list; the
  correction is recorded in `docs/TsMedskew20Measured.md` §O and in
  `docs/MLCompanionContract.md`, and should be APPENDED to those two files by
  the receipt session or the owner ("nothing struck, nothing removed").
* Gate E, run by the launcher. `docs/TsMedskew20Measured.md` says "pending",
  there is no ledger row, and
  `tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
  fails locally with exactly `['mtd_ret', 'ts_medskew_20']` — as the session
  rules predict.
* Gate C on REAL data comes from that same run; everything in §3 of the
  receipt is synthetic.

## Recorded, not fixed (pre-existing)

Running `tests/test_wiring_accessors.py` before `tests/test_altport2_ports.py`
in one process fails the pinned `CATEGORY_TOTAL` (328 against 331), because
`pandas_ta/core.py:453` hands out the live `Category[name]` list and
`core.py:692` removes names from it. Alphabetical collection hides it. Same
defect recorded in commit `6ace3dd`.

## What the four rounds were about

Not the mathematics — every reviewer re-ran all seven measurement sections and
reported that each table reproduced. All four rounds were documentation
defects of one kind: **a number written from memory instead of read off the
run it came from**, which is the defect `CLAUDE.md` names as this repo's
dominant one. Round 1 found two of them in the SHIPPED module docstring, where
the receipt beside it was right. Rounds 2 and 3 each found the previous
round's fix landing in one of its two sites, the stale copy then propagating
into a third file. Round 4 found the last one outside the change set
altogether. What would have prevented all four is the discipline the reviewers
kept applying and the author kept not applying: grep the tree for the number
before claiming it was corrected.
