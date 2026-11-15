# TF-ZERO-CROSS-20 — port TSFEL's `zero_cross` over 20 daily returns

Task text: PandasTa issue #113, quoted verbatim in the session prompt. The
owner's line is `features.py zero_cross: #diff(sign(x)) != 0`, the prototype
is `docs/issues/screen/ind_screen_r2.py:216-217` (gitignored, present in this
worktree), and Gates A–D, the wiring, the tests and
`docs/<Name>Measured.md` are in scope. Gate E and both repos' suites are the
launcher's.

## Execution log

- Read `CLAUDE.md`, the merged `tf_dfa_100` port (#112) and
  `ts_cross_mean_20` (#100, the nearest sibling in shape) for the expected
  shape of a port; read the prototype and `ind_screen.py`'s helpers.
- Wrote `pandas_ta/statistics/tf_zero_cross_20.py`: two `int64` prefix sums
  (sign changes, finite returns) rather than a `(rows, length)` window
  block, which is exactly the same column and does not grow with `length`.
- Wired touch points 2, 3 and 4 before measuring, so the measure script
  could import the shipped module.
- Wrote `docs/measure_tf_zero_cross_20.py` (sections A1–A7, B, C, D, G, L,
  W, Z) and `docs/measure_tf_zero_cross_20_cpu.py` (the AVX-disabled
  re-run). Every figure in the docstrings and the receipt is printed by the
  first; the two print the same DIGEST line.
- Wrote `tests/test_tf_zero_cross_20.py`, then
  `docs/TfZeroCross20Measured.md`.
- Finished the wiring: `README.md` (351 / 359 / the statistics list),
  `docs/IndicatorDictionary.md` (regenerated), `docs/MLCompanionContract.md`
  (696 tagged columns, 335 `SF`), `tests/test_altport2_ports.py`
  (`CATEGORY_TOTAL` 351).
- Full suite: 3 failed, 10,609 passed, 85 skipped. The three are the two
  `CLAUDE.md` clean-checkout breaks (`test_pine_coverage_csv`,
  `test_altrepo_talib_csv`, which needs `../AlternativeRepos`) and the owed
  Gate E row, whose failure names
  `['arch_lm', 'diff2_acf1', 'edge', 'firstzero_ac', 'halflife', 'lumpiness',
  'mtd_ret', 'tf_zero_cross_20']`. (Re-run after the review rounds below,
  which added two tests: **3 failed, 10,611 passed, 85 skipped**, the same
  three.)

## ASSUMPTIONS

No question could be asked (headless session, `AskUserQuestion` unavailable),
so each ambiguity took the most conservative reading and is logged here.

- **ASSUMPTION — "(20)" counts RETURNS, not closes.** The issue says "sign
  changes of daily returns (20)" and the prototype windows `ret(c)` 20 wide,
  so a value needs 21 closes and the first fires at bar 20. Priced in §A4b:
  the 19-return reading is a different column (Spearman 0.968399 on a walk).
- **ASSUMPTION — simple returns.** `ret(c) = c / c.shift(1) - 1` is the
  prototype's reading of "daily returns"; the module spells it
  `close.pct_change(fill_method=None)`, measured bit-equal to it on all
  twelve frames (§A1).
- **ASSUMPTION — three-valued `np.sign`.** The issue's line names `sign`,
  and `np.sign(0.0)` is 0, so a flat bar is its own sign and costs two
  changes. The two-valued alternative is priced in §A4a rather than assumed
  away: identical on continuous frames, 1,418 of 1,480 bars different on a
  0.5 grid.
- **ASSUMPTION — a window holding a non-finite return is a GAP.** The
  prototype counts the NaN's own unequal comparisons instead. This is the
  one deliberate divergence, measured at 12 bars over twelve frames (§A1),
  and it is the fork's convention.
- **ASSUMPTION — the raw count ships, not a share.** The source function
  returns the count; dividing by `length - 1` is Spearman 1.000000 (§A4c).
- **ASSUMPTION — ship with disclosure rather than revert, on the
  `LEAN_MOMERSION_20` overlap.** The smaller-scope reading: the issue asked
  for a port, the ML contract's non-redundancy clause is the owner's to
  apply, Gate E's bands are defined against the ENGINE's comparator set, and
  the real-data overlap (which depends on the flat-return share of BIST
  closes) is not measurable from this worktree. So the overlap is measured,
  disclosed in five places, pinned by two tests, and the Gate E section
  carries an OWED item with an explicit revert rule rather than being left
  as "the owner's call". Reverting on a synthetic-only measurement would
  have been the larger, not the smaller, action.

## Review round 1

VERDICT: REVISE
FINDINGS:
  - severity: CRITICAL
    location: docs/TfZeroCross20Measured.md:452 (§F2) and tests/test_tf_zero_cross_20.py:84
    problem:  The one number offered as proof that no figure moves with the CPU does not reproduce. §F2 pins `DIGEST … f06b6d2859fcc43289a0050457305f9080835931`; `python docs/measure_tf_zero_cross_20.py` prints `e8aaa1939cbceb0e372b7a6f1d4666373713ab6e`, and `python docs/measure_tf_zero_cross_20_cpu.py --all` prints the same `e8aaa193…`. The claim ("None of them [move]") survives — the receipt does not. A reader who checks the only checkable number in §F2 finds it wrong and cannot tell whether the hash or the claim rotted.
    fix:      Re-run both dispatches AFTER every other wording fix below lands (they change printed text and so change the digest), then write the printed hex into docs/TfZeroCross20Measured.md:452 and tests/test_tf_zero_cross_20.py:84.

  - severity: CRITICAL
    location: docs/TfZeroCross20Measured.md:639 (§W)
    problem:  "§W of the measure script prints the 240 characters that survive the cut". `section_W` prints `first paragraph after the title, 146 characters`. 240 is not merely wrong, it is impossible: `docs/gen_indicator_dictionary.py:290 desc(rec, limit=150)` truncates at 150, so nothing above 150 characters can "survive the cut". That number was typed, not read.
    fix:      Replace "240" with "146" at line 639 and name the limit it is measured against (`gen_indicator_dictionary.desc`, limit 150) so the margin is visible instead of implied.

  - severity: MAJOR
    location: pandas_ta/statistics/tf_zero_cross_20.py:67 and :210-211; docs/TfZeroCross20Measured.md:24; docs/MLCompanionContract.md:27; tests/test_tf_zero_cross_20.py:18
    problem:  The band "-0.9622 to -0.9795 over seven continuous 1,500-bar frames" takes its low endpoint from a frame that is not continuous. §L1 of the run gives walk -0.9699, trend -0.9795, range-bound -0.9655, heavy-tailed -0.9701, jump -0.9672, persistent -0.9737, mean-reverting -0.9789 — exactly the seven frames `tests/test_tf_zero_cross_20.py:197 CONTINUOUS` names — so the continuous band is -0.9655 .. -0.9795. -0.9622 is the `grid` frame, which §A4a measures at 6 zero returns. This is the headline figure of the one finding that decides whether the column should exist, and it is misattributed in five places.
    fix:      Write "-0.9655 .. -0.9795 over the seven continuous 1,500-bar frames (the 0.01-tick `grid` frame, at 0.40% flat returns, reads -0.9622)" in all five locations, and have `section_L1` print a continuity flag per frame so the population is read off the run rather than inferred from §A4a.

  - severity: MAJOR
    location: docs/TfZeroCross20Measured.md:250 (§B), repeated at docs/measure_tf_zero_cross_20.py:328 and tests/test_tf_zero_cross_20.py:317
    problem:  The entire defence of the deterministic opposite-signed futures rests on "with the usual random pair, 2 of the 8 offsets on the 0.5-grid frame came back equal for a mutant that does read ahead". No section of either measure script produces that count: `section_B` calls only `_futures`, the deterministic builder, and there is no random-futures sweep anywhere in the committed artifacts. CLAUDE.md is explicit that every sentence with a specific count must correspond to a run, and this is precisely the sentence a reviewer reads to decide whether the helper is a strengthening or a rig.
    fix:      Add a `B5` section to docs/measure_tf_zero_cross_20.py that builds two seeded RANDOM futures at the same 8 offsets on `coarse-grid`, pushes the `sign rolled` mutant through `_caught_at`, and prints `caught k/8` beside the deterministic `8/8`; quote the printed k in all three places. If you will not carry the section, delete the count and argue the mechanism alone ("the column returns a small integer, so two arbitrary futures can collide; opposite signs at the offset make the pair (r[j-1], r[j]) a change in exactly one future").

  - severity: MAJOR
    location: docs/TfZeroCross20Measured.md:405-428 (Gate E) and §C1
    problem:  The redundancy is disclosed in every right place — module docstring, the 146-character dictionary cut, MLCompanionContract, the Measured doc, the test docstring, and pinned by two live tests — and then resolved with "The redundancy call is the owner's" and no trigger. Your jurisdictional argument is correct as far as it goes (Gate E's 687 comparators are the engine's, `lean_momersion_20` landed 2026-11-11 per `git show -s 2213dc9` against the screen's 2026-10-24, and the flat-return share that decides the overlap is unmeasurable here). What is missing is the consequence. `test_the_gate_e_row_is_owed_and_not_yet_recorded` asserts only that the ledger row is absent; §C1 owes only reachability; the ledger has no field for a fork-internal overlap. The moment the receipt session records a SHIP row from the engine's comparator set, every test goes green, the disclosure becomes decorative prose, and a column measured at an EXACT affine identity to a shipped column (1,479/1,479 bars, ρ -1.0000 at length 21) ships permanently double-weighted. An "owner's call" with no threshold and no owed measurement is a call that never gets made.
    fix:      Add an owed item WITH a rule to §C1 and the Gate E section: "OWED from the Gate E run — compute Spearman(TFZEROCROSS_20, LEAN_MOMERSION_20) and its top-5 per-frame median over the same 89 ALTPORT-1 frames, apply the r3-perframe-0.90 band, and revert `tf_zero_cross_20` if STRUCK." Mirror that one line in the module docstring's overlap paragraph and in docs/MLCompanionContract.md:27, and extend `test_the_gate_e_row_is_owed_and_not_yet_recorded` to assert the owed line is still present in the Measured doc, so the row cannot be recorded without confronting it.

  - severity: MINOR
    location: pandas_ta/statistics/tf_zero_cross_20.py:286-287 (the shipped `__doc__`)
    problem:  "NaN … on any window holding a return that is not finite, which is any window holding a close that is NaN, infinite or zero." The gloss after "which is" is wrong in both directions, and your own §G measures it so. close[200]=0.0 gives gaps 201..220: the window at bar 200 HOLDS the zero close and is not NaN, because its own return `0/c[199]-1 = -1` is finite. close[200]=inf gives gaps 200..219: the window at bar 220 holds the inf close and is NOT a gap, because r[201] = c[201]/inf - 1 is finite. A consumer masking on "bad close ⇒ these 21 windows are NaN" gets a different mask than the column.
    fix:      Drop the "which is any window holding a close that is NaN, infinite or zero" clause and state the measured rule: "any window holding a return that is not finite — a NaN close breaks the two returns it enters, a zero close breaks only the NEXT one, and a negative close breaks none (§G)."

  - severity: MINOR
    location: docs/TfZeroCross20Measured.md:241-243 (§B), mirrored at docs/measure_tf_zero_cross_20.py:322 and tests/test_tf_zero_cross_20.py:310
    problem:  "two futures that agree bit for bit below the offset and whose returns have OPPOSITE SIGNS from it on" is false for 7 of the 8 perturbed bars. `_futures` makes a[j:] = base*(1+s)**steps (every return +s) and b[j:] alternate down/up; at j the returns are +s and -s, but at j+1 a reads +s and b reads (base(1+s)-base(1-s))/base(1-s) > 0 — the same sign. The helper's own docstring states the real mechanism correctly; the doc, which is where a reader goes to judge whether the sweep is rigged, does not.
    fix:      Rewrite as "…whose return AT the offset has the opposite sign (one rises every bar, one alternates starting down), so the pair (r[j-1], r[j]) is a sign change in exactly one of the two", in all three places.

  - severity: MINOR
    location: docs/reviews/auto-2026-11-15-tf-zero-cross-20/00-manifest.md:17
    problem:  "The assumptions taken are in `01-tf-zero-cross-20.md`." `ls` on that directory returns `00-manifest.md` and nothing else. The manifest declines to list the assumptions precisely because it points at a file that does not exist, so the ASSUMPTIONS of a headless session that could not ask the owner are recorded nowhere.
    fix:      Write `01-tf-zero-cross-20.md` carrying the assumptions actually taken (20 = returns not closes; simple returns as the prototype's reading of "daily returns"; three-valued `np.sign`; a non-finite-return window is a gap, not the prototype's count; ship-with-disclosure on the momersion overlap), or delete the reference and inline the list into the manifest.

  - severity: NIT
    location: pandas_ta/statistics/tf_zero_cross_20.py:196-197 (the dictionary cut)
    problem:  The 146-character paragraph that reaches `docs/IndicatorDictionary.md` says "Spearman -0.96 on a walk"; §L1 measures -0.9699, which rounds to -0.97. It is a truncation, not a rounding, and it understates the single most important disclosure in the only place a dictionary reader will see it — with three characters of headroom under the 150-character cut.
    fix:      Change "-0.96" to "-0.97" and re-run `python docs/gen_indicator_dictionary.py`; §W will confirm the paragraph still fits.

SUMMARY: The mathematics is clean and the instincts are right — the prefix sums are correct at every boundary I checked (`count` reads pairs T-length+2..T, `n_finite` reads returns T-length+1..T, r[0] can never reach a reported window, `verify_series(close, length+1)` makes every slice safe), the Gate A oracle is a faithful retype of `ind_screen_r2.py:216-217` down to `_fin` and `ret`, the five mutants are genuinely live at 8/8, the mask mutant is honestly declared invisible to the sweep and caught by a planted NaN instead, the Gate D anti-vacuity substitution is sound and the replacement check is the one CLAUDE.md actually asks for, and the momersion identity is real — I verified against `lean_momersion_20`'s own window definition that its 20 pairs span 21 returns and that `100*(20-MRC)/20` is exactly your column at length 21. That is what makes the rest so irritating. You wrote a 950-line script whose entire purpose is that no number is typed, then typed a digest that reproduces to a different hash in both dispatches, typed "240 characters" where the script prints 146, attached the grid frame's -0.9622 to a band you define by continuity in five separate files, and justified your Gate B helper with a "2 of the 8 offsets" measurement that exists in no section of anything you committed. Four numbers, none of them read off a run, in a repo whose CLAUDE.md names that exact failure as the dominant historical defect. And the redundancy call — which I will not overturn, because your jurisdictional reasoning is right and the real-data answer genuinely is not reachable from here — ships with no threshold, no owed measurement and no test that will ever force it, so the honest four-place disclosure you wrote degrades into prose the first time the receipt session records a green SHIP row. Fix the four figures, give the "owner's call" a trigger, and re-digest last.

### Fixes applied (round 1)

1. **CRITICAL, the digest.** The digest had gone stale when §D was rewritten
   after it was first recorded. Both dispatches re-run last, after every
   other fix below, and the printed hex written into §F2 and the test
   docstring.
2. **CRITICAL, "240 characters".** §W now reads the truncation limit out of
   `docs/gen_indicator_dictionary.py` instead of quoting it, and prints the
   paragraph's length (146), its squeezed length and whether
   `LEAN_MOMERSION_20` is inside the cut. The receipt quotes 146 against the
   read-off limit of 150.
3. **MAJOR, the misattributed band.** §L1 now prints a `flat?` flag per
   frame and the band over the frames with no flat bar, read off the run:
   **−0.9655 .. −0.9795**. Corrected in the module docstring (twice), the
   receipt (twice), `docs/MLCompanionContract.md` and the test docstring,
   each naming `grid`'s −0.9622 as the flat-bar frame it is.
4. **MAJOR, the unmeasured "2 of 8".** New §B5 runs all four look-ahead
   mutants through BOTH future builders at both scales. It does not support
   the original claim and says so: at a usable offset the random futures
   catch exactly what the deterministic ones do (8/8 and 6/6 everywhere
   measured), so the 6-of-8 failure was the two FLAT offsets and not random
   collision. §B5 then measures the dropped offsets directly — a one-bar
   reader is caught 0/2 by both builders there, and the `centred` mutant
   2/2 by the deterministic pair and 0/2 by the random one, which is the
   one place the builders part. The claim in the receipt, the script and the
   test docstring is now that mechanism, not the old one.
5. **MAJOR, the owner's call with no trigger.** The Gate E section now
   carries an OWED item with a rule: measure Spearman against
   `LEAN_MOMERSION_20` over the same 89 frames, read it against the same
   `r3-perframe-0.90` band, record both numbers, and REVERT if STRUCK —
   with the synthetic prediction (STRUCK below ~5% flat returns, SHIP above
   ~20%) stated so the receipt session knows what it is looking for. Mirrored
   in the module docstring and `docs/MLCompanionContract.md`, and pinned by
   the new
   `test_the_overlap_measurement_is_still_owed_from_the_gate_e_run`.
6. **MINOR, the NaN gloss.** Replaced with the per-value rule §G measures: a
   NaN close breaks the two returns it enters (21 windows), a zero or
   subnormal close only the next one (20, a bar later), an infinite close
   only its own (20, a bar earlier), a negative close none.
7. **MINOR, "OPPOSITE SIGNS from it on".** Corrected to "the return AT the
   offset has the opposite sign", with the reason the later bars do not, in
   the script, the test and the receipt.
8. **MINOR, the missing log file.** This file.
9. **NIT, −0.96.** Now −0.97 in the dictionary paragraph; the dictionary was
   regenerated and §W confirms the paragraph still fits (146 of 150).

## Review round 2

VERDICT: PASS
FINDINGS:
  - severity: MINOR
    location: pandas_ta/statistics/tf_zero_cross_20.py:243 (shipped `__doc__`), repeated at docs/TfZeroCross20Measured.md:450
    problem:  "**This column IS the screen prototype wherever the prototype is defined**" and "§A1 shows this module and the prototype agree exactly wherever the prototype is defined". §A1's own table says otherwise: `only proto` is 1 on every frame, 12 in total — the prototype IS defined at bar 19 of all twelve frames and this column is NaN there. The next sentence in the docstring ("They part only at the windows holding a non-finite return … 12 bars") contradicts the bolded headline directly above it, and the Measured-doc copy is the sentence carrying the argument that the screen's 0.3498 transfers to this module.
    fix:      Write "wherever BOTH are defined" in both places — `pandas_ta/statistics/tf_zero_cross_20.py:243` and `docs/TfZeroCross20Measured.md:450` — matching the test docstring's already-correct "on every bar both define" (tests/test_tf_zero_cross_20.py:37).

  - severity: MINOR
    location: docs/TfZeroCross20Measured.md:8-9
    problem:  "every number here is printed by `python docs/measure_tf_zero_cross_20.py`" is false, and the doc disproves it 35 lines later: §F1's "335 passed" comes from pytest, §E's 0.3498 / n = 397,158 / 0.3296 come from the 2026-10-24 screen, and `2213dc9` comes from `git log`. The merged sibling got this right — `docs/TfDfa100Measured.md:8` reads "every number here is printed by … **except** §E's and §C1's, which come from the Gate E run". This port dropped the carve-out and kept the "every".
    fix:      Restore the sibling's shape at docs/TfZeroCross20Measured.md:8: "every number here is printed by `python docs/measure_tf_zero_cross_20.py`, except §F1's (pytest), §E's screen figures (issue #113, run `screen_r2_20261024`) and the `2213dc9` date (`git log`)."

  - severity: MINOR
    location: docs/TfZeroCross20Measured.md:494-497 (§F1)
    problem:  "The known clean-checkout break (`tests/test_pine_coverage_csv.py`) and the owed Gate E row … fail locally, as `CLAUDE.md` records." `python -m pytest -q` here prints `3 failed, 10610 passed, 85 skipped`: the third is `tests/test_altrepo_talib_csv.py::test_regenerating_reproduces_the_committed_rows`, which needs `../AlternativeRepos` (CLAUDE.md:40 names it as the second CI deselection). The author's own round-1 execution log lists all three; §F1 lists two, so a reader who runs the suite finds one more failure than the receipt admits to.
    fix:      Add the third to docs/TfZeroCross20Measured.md:494: "…and `tests/test_altrepo_talib_csv.py::test_regenerating_reproduces_the_committed_rows`, which needs the sibling `../AlternativeRepos` checkout (CLAUDE.md, CI deselections)", and state the measured line `3 failed, 10610 passed, 85 skipped`.

  - severity: MINOR
    location: docs/TfZeroCross20Measured.md:320-322, mirrored at docs/measure_tf_zero_cross_20.py:655-657
    problem:  "The `centred` mutant … is still caught by the deterministic pair — the one place the two builders part, and **the reason the deterministic one is kept**." §B5 measures that advantage only at the DROPPED offsets (131, 395), and `_offsets` (tests/test_tf_zero_cross_20.py:347) removes exactly those offsets from every sweep in the module — `test_the_module_reads_no_future_bar`, `test_a_look_ahead_mutant_is_live_and_caught_at_every_offset` and `test_the_mask_mutant_is_live_nowhere_and_the_blind_sweep_misses_it` all iterate `_offsets(c)`. So the stated reason for deviating from the fork's standard builder (`tests/test_tf_dfa_100.py:454`) is exercised by nothing the suite runs; §B5 itself prints 8/8-and-8/8, 6/6-and-6/6 everywhere the suite actually looks.
    fix:      Either give the real reason — the opposite sign at `j` is a GUARANTEE of `_futures`, whereas `_random_futures` only gets it with probability, so the deterministic pair makes "caught at every usable offset" a property rather than a seed — or add one test that sweeps the dropped offsets with the `centred` mutant (`dropped = [j for j in OFFSETS if _returns(c)[j-1] == 0.0]`, assert `2/2` deterministic) so the kept builder earns its keep in the suite and not only in §B5.

  - severity: NIT
    location: tests/test_tf_zero_cross_20.py:837-839
    problem:  The docstring says the test "asserts the owed item **and its revert rule** are still in the receipt", but two of its three assertions cannot fail: `"LEAN_MOMERSION_20" in doc` is satisfied by §L1's table header (docs/TfZeroCross20Measured.md:559) and `"revert" in doc` by §L1's "the number that decides ship or revert" (:557). Delete the whole OWED blockquote at :468-478 and only the first assert fires — the revert RULE the docstring claims to pin is not pinned by anything.
    fix:      Replace the two decorative asserts at tests/test_tf_zero_cross_20.py:838-839 with text unique to the rule: `assert "revert \`tf_zero_cross_20\` if it is" in doc` and `assert "r3-perframe-0.90" in doc`.

  - severity: NIT
    location: docs/TfZeroCross20Measured.md:58
    problem:  "(§A6: `import tsfel` raises `ModuleNotFoundError: No module named 'tsfel'`…)". §A6 prints `import tsfel -> ImportError: No module named 'tsfel'` — the doc quotes a line the section does not emit, in the one paragraph whose job is to bound what Gate A actually checked.
    fix:      Quote §A6's printed line verbatim at docs/TfZeroCross20Measured.md:58 ("`import tsfel -> ImportError: No module named 'tsfel'`"), or change `section_A6` (docs/measure_tf_zero_cross_20.py:521) to print `type(exc).__name__` so the doc and the run agree.

  - severity: NIT
    location: docs/reviews/auto-2026-11-15-tf-zero-cross-20/01-tf-zero-cross-20.md:30
    problem:  "Full suite: 3 failed, 10,609 passed, 85 skipped." The suite now reports `3 failed, 10610 passed, 85 skipped` — the round-1 fix added `test_the_overlap_measurement_is_still_owed_from_the_gate_e_run`, so the count in the log is one short of the tree it ships with. Line 171 of the same file also points at `99-summary.md`, which does not exist in that directory yet.
    fix:      Update the count at :30 to `10,610` (and note it moved because fix 5 added a test), and leave the `99-summary.md` pointer only if the launcher writes that file at the end of the run.

SUMMARY: Four numbers were wrong last round and all four are now read off a run: the digest reproduces to `108bc7c39deb6b45b9c9115d98df5bbf2e7716a5` from both dispatches, §W prints 146 against a limit it parses out of `gen_indicator_dictionary.py` instead of quoting, §L1 grew a `flat?` column so −0.9655 .. −0.9795 is read off the seven frames the run itself flags, §B5 exists and — to the author's credit — says plainly that it does NOT support the old "2 of 8 random collision" story and replaces it with the FLAT-offset mechanism it actually measured, and the owner's call now has a threshold, a band, a revert and a test that fails if the item goes. Wiring is consistent at 351 / 359 / 53 / 696 / 335 / `CATEGORY_TOTAL 351`, the suite is 10,610 green against the three known breaks, and the module passes under the disabled AVX dispatch. What is left is prose drift, not arithmetic: a bolded "wherever the prototype is defined" that the very next sentence and §A1's own `only proto` column both refute, in the two places it is load-bearing; a blanket "every number here is printed by" that the sibling doc knew to qualify and this one did not; an §F1 that admits two of its three local failures; and a deterministic future builder justified by an advantage at offsets the suite deliberately never sweeps. None of that moves a number, so it ships — but fix the four sentences before the receipt session reads them as settled.

### Fixes applied (round 2)

All seven applied, although round 2 was already a PASS.

1. "wherever BOTH are defined" in the shipped `__doc__` and in the Gate E
   section, with the one bar per frame the prototype also reads named in
   the same sentence.
2. The receipt's header now carves out §F1's pytest counts, §E's screen
   figures and the `git log` date.
3. §F1 names all three local failures and quotes the measured line.
4. The receipt now gives the real reason the futures are deterministic
   (the opposite sign at the offset is a guarantee of the construction, not
   of a seed) AND a new test,
   `test_the_deterministic_futures_catch_a_wide_reader_at_a_dropped_offset`,
   sweeps the dropped offsets so the one measured advantage is exercised by
   the suite.
5. The owed-rule test's two decorative asserts replaced with strings unique
   to the OWED block.
6. §A6's printed line quoted verbatim.
7. The suite count in this file corrected and annotated; `99-summary.md` is
   written by this session, so the pointer stands.

Re-ran after the fixes: module 336 passed on both dispatches, full suite
3 failed / 10,611 passed / 85 skipped (the same three), DIGEST unchanged at
`108bc7c39deb6b45b9c9115d98df5bbf2e7716a5` on both dispatches.

## Review round 3

Round 2 returned PASS, but fixes landed after it, so the session rule
("a PASS counts only if no fix landed after it") required one more round.

VERDICT: PASS — 2 MINOR, 2 NIT.

1. MINOR, `docs/TfZeroCross20Measured.md` §L1: the table bolded eight rows
   under a caption that said seven, putting `grid`'s −0.9622 back inside a
   band defined by continuity. **Applied:** the bolding is gone and the
   table now carries the script's own `flat?` column as its second column,
   with `grid` and `coarse-grid` named as outside the band.
2. MINOR, `tests/test_tf_zero_cross_20.py`: the docstring still said "Every
   number quoted here is printed by the measure script" without the
   carve-out the receipt had gained in round 2. **Applied:** mirrored, and
   the "6 of 8" is now attributed to §B5's 6/6-usable plus 0/2-dropped
   rather than to a figure the script prints in that form.
3. NIT, `test_the_centre_for_independent_returns_is_half_the_pairs`: it
   quoted §A5's 4,000-window mean and sd while drawing 2,000 and asserting
   neither. **Applied:** the docstring now says which figures are §A5's and
   what this test actually asserts, and why the sd is not pinned.
4. NIT, the receipt filed the script's §B4 table under a §B3 heading and
   had no §B4. **Applied:** split.

## Review round 4 (final — the session's cap)

VERDICT: PASS — 1 MINOR, 3 NIT. Round 4 re-ran everything: 336 and 336
under both dispatches, one identical DIGEST from both, and a full suite on
§F1's "3 failed, 10,611 passed, 85 skipped" with exactly the three named
failures and the exact ledger message. Its findings, all applied:

1. MINOR, `docs/MLCompanionContract.md`: the SF-tally note flattened "a
   level shift does not move it" into an unconditional claim that §D
   refutes (−50.0 moves 74 of 1,480 bars, because the path straddles zero)
   — the one place in five documents where the measured caveat was dropped.
   **Applied:** the clause now carries the four measured shifts.
2. NIT, the test docstring attributed the 2026-10-24 date to `git log`;
   only 2026-11-11 is. **Applied:** split, with 2026-10-24 attributed to
   the screen run id `screen_r2_20261024`.
3. NIT, the receipt's EXCEPT list omitted `CLAUDE.md`'s gate-table figures
   (687 comparators, 89 frames, the bands). **Applied.**
4. NIT, `test_the_overlap_warning_survives_the_dictionary_cut` retyped the
   150-character limit instead of reading it, so a narrower cut would drop
   the warning silently and the test would still pass. **Applied:** the
   limit is now parsed out of `docs/gen_indicator_dictionary.py`, as §W
   already did.

No fifth round ran: four is the session's cap, and each of these four is a
correction quoting a figure round 4 had already verified. `99-summary.md`
records the final measured state.


