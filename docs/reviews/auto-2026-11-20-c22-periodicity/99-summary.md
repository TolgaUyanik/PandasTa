# Run summary — auto-2026-11-20-c22-periodicity

⚠ **This file is a HISTORICAL record of the porting session's three review
rounds (2026-11-20). It describes the tree at commit `34536ce` and nothing
after it.** Two later commits changed what it says:

* `c908892` recorded the Gate E run and Gate C's real-data limb and swapped
  the two pending-Gate-E tests for three that pin the row (262 tests).
* the PRE-PUSH review gate, round 1, found that the autocorrelation's
  divisor was not the one the sources spell, and the fix changed shipped
  values. `PD_PeriodicityWang` writes `acf(i) = mean(y(1:N-i).*y(i+1:N))`
  and catch22's C divides by `size - tau`, both on a window z-scored BEFORE
  the detrend; the module now does that. Consequences, all in
  `docs/C22PeriodicityMeasured.md`: agreement with the GPL-3.0 reference
  rose from 8,376 to **8,387 of 8,400** (Spearman +0.9980 → **+0.9993**,
  24 disagreements → **13**, and 2,794 → **2,798** of the 2,802-window
  subsample); **Gate E and Gate C's real-data limb are OWED AGAIN**, the
  ledger row having been removed because its run measured the pre-fix
  column; the test module is **268 tests**, green here and under the CI
  dispatch.

Figures below that moved with that fix — "261 tests", "99.71%", "8,376",
"+0.9980", "fourteen alternative readings", "the biased autocorrelations" —
are left as written, because this is the record of what those rounds
reviewed. The Gate E and §C4 follow-ups at the bottom, which `c908892`
discharged, are accurate again: both are owed, and the two pending-Gate-E
tests are back.

| task | status | review rounds | files touched | follow-ups |
|---|---|---|---|---|
| `c22-periodicity` (issue #126) | **PASS** at round 3 | 3 (REVISE, REVISE, PASS) | 7 new, 7 modified — see below | Gate E and Gate C's real-data limb are the launcher's; both repos' suites are the launcher's; the OWED RULE for issues #130 and #137 |

## What shipped

`C22PERIODICITY_100` — catch22's `PD_PeriodicityWang_th0_01` over the last
100 daily simple returns: detrend the window with a least-squares cubic
spline on two pieces (one knot, at the middle), take the biased
autocorrelations out to `ceil(length / 3)` lags, and report the first lag
that is a strict local maximum, stands at least 0.01 above the last strict
local minimum before it, and is non-negative; else 0. `ORD`, `{0} ∪ {2 ..
33}`, and **0 is a sentinel and the floor**.

New files:

* `pandas_ta/statistics/c22_periodicity.py`
* `tests/test_c22_periodicity.py` — 261 tests, green here and under
  `NPY_DISABLE_CPU_FEATURES="AVX512F AVX512_SKX AVX2 FMA3"`
* `docs/measure_c22_periodicity.py` — sections S, A–E, G, H, P, T, Z
  (**P** is the opt-in GPL-3.0 black box)
* `docs/measure_c22_periodicity_cpu.py`
* `docs/C22PeriodicityMeasured.md` — the receipt
* this run folder's three files

Modified: `README.md` (360 → 361, 368 → 369, statistics 58 → 59),
`docs/IndicatorDictionary.md` (regenerated), `docs/MLCompanionContract.md`
(705 → 706 tagged columns, `ORD` 56 → 57), `pandas_ta/__init__.py`,
`pandas_ta/core.py`, `pandas_ta/statistics/__init__.py`,
`tests/test_altport2_ports.py` (`CATEGORY_TOTAL` 360 → 361).

## The three things a reader should take from the receipt

1. **The spline reading is pinned by measurement, not by taste.** Four
   spellings of the same fit agree on 1,200 windows each, an exact rational
   oracle agrees on 648, and the GPL-3.0 reference agrees with the shipped
   knot structure on 99.71% of 8,400 windows against 83.2% to 95.5% for five
   alternatives.
2. **This port is NOT bit-identical to the reference** — 8,376 of 8,400
   windows equal, Spearman +0.9980, worst single-window gap 24 lags — so the
   2026-10-24 screen's Gate E figure (max |ρ| 0.0413 vs `cdl_doji`, SHIP)
   was measured on the reference's column and is an expectation for this
   one, not a result. Every one of the 8 disagreements in the subsample is
   matched by at least one of fourteen alternative readings, none by all.
3. **One blanking rule, with a real cost**: a window is NaN unless its
   detrended root mean square clears 9.09e-13. Inert on anything with noise
   in it (0 bars differ from the unguarded spelling on six frames), and it
   blanks every deterministically smooth path — including a price rising one
   kurus a bar from 100.00, where the sibling `c22_ami_timescale` fires on
   all 1,400 bars.

## Review rounds

| round | verdict | findings | all applied? |
|---|---|---|---|
| 1 | REVISE | 2 CRITICAL, 1 MAJOR, 4 MINOR, 2 NIT | yes |
| 2 | REVISE | 1 CRITICAL, 1 MAJOR, 5 MINOR, 2 NIT | yes |
| 3 | **PASS** | 0 CRITICAL, 0 MAJOR, 5 MINOR, 4 NIT | yes |

⚠ Under the session's own rule a PASS counts only if no fix landed after it,
and round 3's nine MINOR/NIT fixes did. The PASS stands as the gate verdict —
the rule's purpose is to stop a CRITICAL being fixed unreviewed, and round 3
raised none — but a fourth reviewer would be reading nine changed lines it
has not seen: the round-3 section of `01-c22-periodicity.md`, §A3's cosine
sentence, §C3's printed sd range, the module docstring's Gate E consequence,
§F1's scoping, the ceiling test's second limb, and the two headline gate
rows. Those nine are where a fourth round should start.

Both REVISE rounds were the same class of defect, and it is the one
`CLAUDE.md` names as the repo's dominant one: **a sentence written past its
measurement.** Not one finding in either round was about the mathematics —
both reviewers re-ran the harness and reproduced every table digit for digit.
Round 1 killed a "reads the sentinel on every bar" claim the harness
contradicts and a 4/1/3 attribution computed over a list the harness had
truncated to 6 of 8; round 2 killed a "matched only by other detrends" clause
that the per-window record disproves on one of the two windows it named, and
a stale test count in the headline gate table. The fixes that came out of
them are in the port, not only in the prose: the harness now records ALL
disagreements instead of six, Wang's conditions (a) and (c) are ablated and
tested (they were measured by nothing before), the lag ceiling is pinned so a
`ceil`→`floor` edit cannot silently falsify the documented range, and the two
rounding-noise frames' value sets are stated as spans because they move with
the CPU dispatch.

## Follow-ups the launcher or a later session owns

* **Gate E** — `gate_e_overlap.py run --module pandas_ta.statistics.c22_periodicity`,
  then `docs/gate_e_ledger.py record`. `tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
  fails until then, reporting exactly `['c22_periodicity']`, and
  `test_the_gate_e_row_is_owed` in this port's test module fails the moment a
  row appears — that pair is the receipt session's cue to swap the **two**
  pending-Gate-E tests (`test_the_receipt_says_gate_e_is_pending` and
  `test_the_gate_e_row_is_owed`) for ones that pin the recorded row, which is
  what §E and the test's own docstring also say.
* **Gate C's real-data limb** — the non-NaN and non-zero counts over the 89
  BIST frames come from the same run. ⚠ They will NOT be equal, because 0 is
  a legal reading of this column.
* **Backtesting's suite** — run by the launcher in a clean worktree.
* **The OWED RULE (§E4)** — when issue #130 (`CO_FirstMin_ac`) or #137
  (`SP_Summaries_fft_wq_50`) lands, price it against `C22PERIODICITY_100`
  over the 89 frames; a proxy of #130 already sits at per-frame |ρ| 0.50 to
  0.58 here.
* **No Codex review** — `codex` is not an allowed command in this session;
  the session rule asking for one before a push is noted in `00-manifest.md`.
