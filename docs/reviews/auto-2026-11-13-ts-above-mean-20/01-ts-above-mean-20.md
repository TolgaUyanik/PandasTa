# 01 — TS-ABOVE-MEAN-20

Task log. Four Fletcher rounds: **REVISE, REVISE, REVISE, PASS**. 22 findings
applied before the PASS, 7 more (all MINOR/NIT, from the PASS's own list)
applied after it.

Every reviewer was a fresh read-only `Explore` subagent with the Fletcher
persona, the original ask verbatim, the explicit file list, the session's
rules (Gate E owed, no CPU-dependent float pins, the allowed-paths list) and
the repo's `CLAUDE.md`. Rounds 2–4 were also handed the previous round's
findings and what was done about each, with the instruction to verify the
fixes rather than re-report them.

## Implementation

1. Read `CLAUDE.md`, the two most recent sibling ports (`ts_cid_ce_20`,
   `ts_peaks_20`) and their commits, and the screen prototype
   (`docs/issues/screen/ind_screen.py:609-610`).
2. Wrote `pandas_ta/statistics/ts_above_mean_20.py`:
   `sliding_window_view` over the simple returns, the window mean from that
   window's own values, a strict `>` count spelled column by column, a
   RELATIVE dispersion floor and a per-return magnitude bound.
3. Wrote `docs/measure_ts_above_mean_20.py` (sections `gate_a gate_b gate_c
   gate_d guards overlap shape cost`) and ran every section; the docstring
   and the receipt were written FROM its output, not before it.
4. Wrote `tests/test_ts_above_mean_20.py` and
   `docs/measure_ts_above_mean_20_cpu.py`, which runs the module's tests with
   numpy's `AVX512F`, `AVX512_SKX`, `AVX2` and `FMA3` dispatch disabled.
5. Wired the five touch points, regenerated `docs/IndicatorDictionary.md`,
   updated `README.md` (330 / 338 / statistics 39), `docs/MLCompanionContract.md`
   (675 tagged columns / 317 `SF`) and `tests/test_altport2_ports.py`
   (`CATEGORY_TOTAL` 329 → 330).
6. Wrote `docs/TsAboveMean20Measured.md`.

Final: 165 tests in the module, passing with and without the four CPU
features; full suite 3 failed / 7,058 passed / 85 skipped, the three being the
two `CLAUDE.md` Known breaks and the owed Gate E row.

---

## Round 1 — VERDICT: REVISE

1 CRITICAL, 4 MAJOR, 4 MINOR, 2 NIT.

* **CRITICAL** — `pandas_ta/statistics/ts_above_mean_20.py`, the per-return
  bound's comment. It claimed a 1e+8/1e+100/1e+300 return "empties exactly
  the 20 windows holding it" and "1,779 later bars". Section G5 says those
  windows read **0.05** and only 1e+307 empties them, and the bar count is
  **1,780** — which the module's own docstring said four paragraphs later.
  *Applied*: comment rewritten to the measured text.
* **MAJOR** — "invariant to any AFFINE map of the returns" was asserted of
  the column. The floor is scale-invariant and NOT shift-invariant.
  *Applied*: the claim is split into COUNT and reported MASK in all five
  places; measure section G6 added (580/600 fired undrifted, **0/600** after
  a +0.004 drift, spread fixed at 1.332e-15, floor 9.095e-19 → 3.639e-15);
  `test_that_invariance_is_the_counts_and_not_the_reported_masks` added.
* **MAJOR** — the ×10/×3.7/×0.1 test asserted full bit-equality while its own
  docstring said it did not, with a dead `eq >= FIRED - 5` band.
  *Applied*: masks asserted exactly, values banded through a new
  `_shared_equal`, Spearman loosened to `> 0.999`; the affine test banded the
  same way.
* **MAJOR** — receipt §5 omitted the screen's real-frame fork overlap
  (0.2405). *Applied, but not as proposed*: the row is quoted AND the receipt
  states that it does NOT bound the overlap with `OSAP_RETSKEW_21`, because
  `pandas_ta/statistics/osap_retskew_21.py` landed 2026-11-02 (git log), nine
  days after the 2026-10-24 screen, so it cannot have been in that comparator
  set. Round 2 verified the date.
* **MAJOR** — an unmeasured superlative in `docs/MLCompanionContract.md`
  ("the fork's highest in-fork overlap figures of this port series"), which
  the same paragraph refutes two sentences later. *Applied*: deleted.
* MINOR ×4 / NIT ×2 — stale narration in `cost()`; the 19-ulp summation bound
  skipping the divide-by-`length` step; the CPU script claiming "non-AVX
  kernels" while leaving `AVX`/`AVX512CD` enabled; the uncovered mutant index
  not disclosed; a "tie-free monotone relation" that this column is the
  opposite of; D4's numbering vanishing. All applied.

## Round 2 — VERDICT: REVISE

1 CRITICAL, 1 MAJOR, 2 MINOR, 2 NIT. Round 1's fixes were re-measured and
held — except one.

* **CRITICAL** — round 1's disclosure fix had INVENTED a claim: it said a
  mutant on the floor's `hi`/`lo` "is not LIVE on any frame here", with no
  such mutant ever built, and that contradicted the receipt's own G2
  (`reported` IS False at bar 19 on every frame, which is why the floor
  "costs 1 bar"). *Applied*: the sixth mutant `SHIFTED_FLOOR` was built, added
  to `gate_b`, and the measured truth replaced the invention — live on all
  three frames, bar 19 NaN → **0.0**, blind sweep **0/37**; then a designed
  frame (`_floored_patches`) catches it **36/37** while the real module still
  leaks 0/37.
* **MAJOR** — §5 quoted `fork_overlap.csv` line 72 but omitted
  `cand_pairs.csv` line 39: `ts_above_mean_20,ts_medskew_20,0.8428`, a
  real-frame pooled overlap with another skewness candidate, written by the
  same script in the same run. *Applied*: quoted, with what `ts_medskew_20`
  is, that it is not shipped (issue #98), and why it corroborates the
  disclosure rather than triggering a revert.
* MINOR ×2 / NIT ×2 — "1e-6 spread over 1e-14" where every run uses 1e-13;
  the `test_wiring_accessors` + `test_altport2_ports` ordering hazard
  (`core.py:453`/`:692` mutate the live `Category` list) unrecorded; the ×10
  mask assertion justified as "structural" when it is a margin; timings
  quoted to 0.1 ms reading as pins. All applied.

## Round 3 — VERDICT: REVISE

1 CRITICAL, 1 MAJOR, 3 MINOR. Round 2's fix was itself trimmed to fit.

* **CRITICAL** — the sixth mutant was claimed to move only bar 19. It moves
  **two** bars: `np.roll` wraps window 0's NaN extrema onto the LAST window,
  turning a reported value into NaN — and both the test and `gate_b` sliced
  `len(close) - 1`, so the number printed as zero. *Applied*: both slices
  widened, `gate_b` prints the moved-bar index list (`[19, 1499]` on all three
  frames), the test asserts the moved SET rather than a count, and the receipt
  names bar 19 as the look-ahead and the last bar as a wrap, with the two
  separate reasons the sweep sees neither.
* **MAJOR** — "236 interior windows" was the total NaN count with the 20
  warm-up bars still inside it. *Applied*: **216** interior (36 patches × 6
  all-zero windows) + 20 warm-up = 236 of 1,500, with `gate_b` printing the
  interior count separately.
* MINOR ×3 — the probe test's premise assertion held on every frame and
  pinned nothing (now asserts the interior empty count); two tests recompute
  the statistic instead of calling the module (now say so, naming Gate A1 as
  the bridge); `docs/issues/screen/sanity.csv` line 72 held real-frame
  reachability and was not quoted (now in §3, with Gate C still OWED).

## Round 4 — VERDICT: PASS

0 CRITICAL, 0 MAJOR, 5 MINOR, 2 NIT. The reviewer reproduced `gate_a`,
`gate_b`, `gate_c`, `gate_d`, `guards`, `overlap`, `shape`, `cost`, the
CPU-disabled run, the full suite and the four gitignored screen rows, and
verified all five round-3 fixes.

All seven findings were applied after the PASS; none of them was a wrong
number:

* the 0.5 level was justified by "mean = median", which is not the reason —
  replaced by the REFLECTION argument (`x → 2u − x` preserves the law and
  swaps the counts) in the test and in receipt §6;
* the module docstring quoted the −0.8137 and the level table as properties
  of the column without saying they are computed on the STATISTIC — the
  caveat round 3 added to the tests and the receipt now also sits in the
  docstring a consumer reads through `help()`;
* `assert ratio > 1e4 * eps` was weaker than the `ratio > 1e-9` above it, a
  dead assertion in the margin test — replaced by `ratio / eps > 1e7`
  (measured 7.0e+08), which is the quantity the claim is about;
* the §7 timings had drifted off the clock — re-measured and re-stated as one
  run's numbers with an explicit "these move by a few per cent";
* this file and `99-summary.md` were missing;
* §8 pointed at a commit message for the full-suite numbers instead of
  stating them — now recorded in the receipt;
* `assert 0 < fired < len(close)` followed `assert fired == FIRED` and could
  never fire — moved to the flat and ladder frames, where it bites.

**Reviewer's one-sentence caveat, kept verbatim:** *both Gate C on real data
and Gate E are still OWED, so the launcher's run, not this receipt, decides
whether a column that reads pooled 0.8428 against an unshipped sibling
skewness candidate actually stays.*
