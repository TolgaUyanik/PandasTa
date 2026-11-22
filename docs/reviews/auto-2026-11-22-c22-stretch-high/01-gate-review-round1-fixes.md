# gate-review-round1-fixes

Fix every CRITICAL and MAJOR finding of the pre-push review gate (round 1 of
3, HEAD d786d7effd37), per the rules in the issue-solver system prompt; fix
MINOR/NIT findings only when cheap and safe.

## Review round 1 (external pre-push gate, verbatim)

```
Reviewed: the two added files, the shipped `ts_strike_20` module and its receipt, the issue's prototype/`fork_overlap.py` in the owner's tracker copy, `CLAUDE.md`'s gate table and ML contract, `C22Mode5Measured.md` §P (the cited float32 precedent), the launcher's `tests.md`, and the `gatee/` directory (empty — consistent with "nothing new ships").

Verified holding: the revert's core thesis (`SB_BinaryStats_mean_longstretch1` on 100 returns is tsfresh's `longest_strike_above_mean`, already shipped and already `length`-parameterized, reachable as `ts_strike_20(close, length=100)` and `df.ta.ts_strike_20(length=100)` — `pandas_ta/core.py:2240-2244`); the §0a rebuttal of the stage-2 0.1593 number (`fork_overlap.py:55` is indeed `getattr(df.ta, name)()`, no `length`); the `#90 TS-STRIKE-20` related-issue tuple (`ind_screen_r3.py:74-75`); both quotes (`CLAUDE.md:138`, `TsStrike20Measured.md:166-167`); the cross-reference to `C22Mode5Measured.md` §P; the harness's window alignment (`out[t]` reads `r[t-100:t]` = closes `t-100..t`, prefix-causal, same convention as the prototype and the shipped module — no look-ahead); the fire counts (1,500 closes → 1,400 at `length=100`, 1,480 at `length=20`); 200 sampled windows/frame × 6 = 1,200, `t=653 ≡ 100 mod 7` so the diagnosed window is in the sampled set; 1,199/1,200 = "99.92%". Deliverables are both present and `tests.md` shows zero regressions in either repo.

VERDICT: REVISE
FINDINGS:
  - severity: MAJOR
    location: docs/C22StretchHighMeasured.md:12-13 (the Gate A and "Non-redundant" table rows), :107, :199-203
    problem:  The central claim — "`ts_strike_20(close, length=100)` ... already gives this exact column" and "by measurement, the same column" — is stated without the one structural difference between the shipped column and the catch22 definition, and the six frames chosen cannot reach it. `pandas_ta/statistics/ts_strike_20.py:14-26,84-85` carries a `NOISE_FLOOR` of `4096 * eps = 9.09e-13`: a window whose return span is at or below that reads **0** regardless of its actual run. The raw `SB_BinaryStats_mean_longstretch1` definition — and this session's own `oracle_longstretch1`, which has no floor — has no such rule. `docs/TsStrike20Measured.md` measures the divergence explicitly (a 1%-a-bar ladder reads 1–4 unguarded vs 0 guarded; price 1e6 with a 0.01 tick reads 8–11 unguarded vs 0; `length + 1` identical closes read 0) and calls the degenerate case "the one case real data reaches" — limit-locked or flat-close BIST bars are exactly that. All six frames here (walk σ=0.015, two tick-rounded walks, AR(1), cosine amp 0.01, Student-t) have return spans many orders above the floor, so the floor never fires in any of the 8,400 windows and the "0 disagree / worst |diff| 0.0" table is silent on it by construction.
    fix:      Add one frame to `FRAMES` where the floor fires — an exact geometric ladder, or a walk with `length + 1` identical closes planted in it, or the 1e6-price/0.001-tick path `TsStrike20Measured.md` already uses — run §A on it, and report the oracle-vs-shipped disagreement it produces. Then restate the two table rows and §6 as what is measured: the candidate is the same statistic as `ts_strike_20`, and the shipped column additionally floors rounding-noise windows to 0, so the two differ exactly on degenerate windows — a deliberate, documented choice (`docs/TsStrike20Measured.md`, *The rounding-noise floor*) that argues for the revert rather than against it, since porting the unguarded definition would ship a column reading float64 noise on flat-close bars.
  - severity: MAJOR
    location: docs/C22StretchHighMeasured.md:127-128 ("catch22's preprocessing step cannot be the reason...") and :145-154 ("the first hypothesis tried ... does NOT hold up" / "What DOES reproduce it"); harness docs/measure_c22_stretch_high.py:254-261
    problem:  §3's "cannot" is an exact-arithmetic identity (`k*y[i]+d > k*mean(y)+d iff y[i] > mean(y)`), measured on one `rng.normal(0, 0.01, 100)` window that has no exact ties. In float it does not hold at a tie: the reference z-scores first and then binarizes against the mean of the **z-scored** series, which is a fresh naive summation whose residual is generically a nonzero ±1e-18-ish value — and a sample sitting exactly at the raw mean becomes exactly 0 in z-space, so a negative residual mean makes it read "above" under the same strict `>` the fork uses. That is precisely the situation in the only disagreeing window (§4: mean numerically 0, 4 samples exactly at it). §4 nonetheless pronounces the precision hypothesis dead having tested only three *raw-window* means (`numpy.mean`, `math.fsum`, and `float32` of the raw window, harness lines 254-261) — never the z-scored path the reference actually computes, and never the float32-internals route this same receipt cites from `docs/C22Mode5Measured.md` §P, where this repo's own measurement infers the reference does its arithmetic in 32-bit. `>=` and a negative z-mean residual both produce 11 on this window, so reproducing 11 with `>=` does not discriminate between them; the receipt picks the one that implies a convention difference with hctsa over the one that implies none. (CLAUDE.md:196-198: every *only/never/always/identical* sentence must correspond to a run.)
    fix:      In §D, z-score the t=653 window the way the reference does (`z = (w - w.mean()) / w.std(ddof=0)`), recompute the mean of `z` in float64 and in float32, and print its sign plus the longest strict-`>` run under each. Report the result: if the z-scored mean is negative in either precision and the run is 11, replace §4's tie-rule attribution with "a last-bit residual in the mean of the z-scored window, consistent with this fork's float32 finding in `C22Mode5Measured.md` §P — the reference's rule is the same strict `>`", and downgrade §3's "cannot be the reason" to "inert except at an exact tie with the window mean, where the z-scored mean's last-bit residual decides the comparison — the case §4 hits". Either way the revert stands; only the attribution and the §3 universal need correcting.
  - severity: MINOR
    location: docs/C22StretchHighMeasured.md:65-85 (§1 "Fork overlap at the MATCHED length (§R)")
    problem:  The section is titled fork overlap at the matched length but reports no overlap statistic: the table is fire counts and distinct-value counts for `TS_STRIKE_100` and `TS_STRIKE_20`, and the parenthetical plus the harness comment (`measure_c22_stretch_high.py:386-388`, "bit-identical to itself trivially") concede the two columns are never compared to each other. The actual matched-length evidence is §2.
    fix:      Retitle it "Fire counts and value spread at both lengths" and move the overlap claim to §2, or add the real number — bar-by-bar agreement and Spearman between `oracle_series` and `TS_STRIKE_100` per frame.
  - severity: MINOR
    location: docs/C22StretchHighMeasured.md:186-197 (§5 Gate F)
    problem:  The subset table reports "1458 passed, 7 skipped" with no failures, while the launcher's `tests.md` records 1 failing PandasTa test at both base and HEAD (pre-existing, 0 regressions) — and `CLAUDE.md:207` claims no test fails on a clean checkout. Nothing here conflicts if that failure lies outside the eight listed files, but the receipt does not say so, leaving a reader to guess whether the subset run was clean or the failure was simply not in it.
    fix:      Name the pre-existing whole-suite failure and state that it is outside the eight files listed (or inside, with its node id), citing the launcher's base-vs-HEAD comparison as the evidence that it is not this change's.
  - severity: NIT
    location: docs/measure_c22_stretch_high.py:268-271 (the `if run_ge == 11` branch) and :28 ("the same 120 lines")
    problem:  The diagnostic message hard-codes "4 of 100 samples exactly AT the mean" and the branch condition hard-codes `11`, so the harness prints a literal where it already has the computed value two lines above (`int((w == mu_np).sum())`) — the pattern CLAUDE.md:196 warns about, even though here the computed value is printed alongside. Separately, `ts_strike_20.py` is 278 lines (≈100 of code), not 120.
    fix:      Interpolate the computed tie count into the message and compare `run_ge` to the measured reference value rather than a literal `11`; drop or correct the "120 lines" figure.
SUMMARY: This is a code-free measured revert, and its thesis is right: `SB_BinaryStats_mean_longstretch1` on 100 returns is tsfresh's `longest_strike_above_mean`, which this fork shipped as `ts_strike_20` already parameterized by `length` and reachable at 100 through the function, the accessor and `strategy()` — the §0a demolition of the stage-2 0.1593 number is correct and I verified `fork_overlap.py:55` myself, the window alignment is prefix-causal with no look-ahead, and every quote and cross-reference I checked is accurate. But the receipt IS the deliverable here, and it over-claims twice in exactly the way this repo's own protocol forbids. It declares the candidate "this exact column" while the shipped column carries a 9.09e-13 noise floor the catch22 definition does not have, on frames chosen such that the floor can never fire — the fork's own `TsStrike20Measured.md` measures that divergence and calls the degenerate case the one real data reaches, so the gap is documented elsewhere and omitted here. And it kills the float-precision explanation for its single reference disagreement by testing three variants of the *raw* window mean, when the reference binarizes against the mean of the *z-scored* window, which is where an exact tie actually gets decided — then asserts in §3 that z-scoring "cannot" matter, a claim true in real arithmetic and false in float at precisely the tie the one failing window contains. Both fixes are cheap, both leave the revert intact, and neither is optional: a receipt kept as the permanent record of why this feature was not ported must not be the thing that tells the next session the two columns are bit-for-bit the same statistic.
```

## Execution log

- Added a seventh frame `flat-tick` (monotone one-tick-per-bar ladder, price
  1e6 / tick 0.001 — the same price/tick pair `docs/TsStrike20Measured.md`
  already documents as floor-triggering) to `FRAMES` in
  `docs/measure_c22_stretch_high.py`, so §A and §P now measure the floor
  divergence directly instead of only on frames that can never reach it.
- Re-ran `python docs/measure_c22_stretch_high.py A Z R` and
  `python docs/measure_c22_stretch_high.py P D`: on `flat-tick`, the
  unguarded oracle disagrees with the shipped `ts_strike_20(100)` on
  1,353/1,400 windows (worst |diff| 99), and the real GPL-3.0 reference
  disagrees with it on 193/200 sampled windows — both exactly the
  `NOISE_FLOOR` divergence `TsStrike20Measured.md` already documents.
  Updated the Gate A table (§2), the header table's Gate A / Non-redundant
  rows, and §6 to state the revert's thesis with that caveat instead of
  "this exact column".
- Rewrote `section_D` in the harness to z-score the t=653 window the way
  the reference does (`(w - mean) / std(ddof=0)`) in float64 and float32,
  print the sign of the z-scored mean and the longest strict-`>` run under
  it, and fetch the real `pycatch22` value to compare against instead of a
  hard-coded `11`. Measured: the z-scored mean is negative in both
  precisions (float64 `-1.110e-18`, float32 `-1.788e-09`), and the longest
  run under either is 11 — an exact match to the live reference's 11.0,
  under the SAME strict `>` the module uses. Updated §3 (downgraded
  "cannot be the reason" to "inert except at an exact tie...") and §4
  (replaced the tie-rule attribution with the z-scored-mean-residual one)
  accordingly.
- MINOR: retitled §1 to "Fire counts and value spread at both lengths" and
  added a sentence stating it reports no overlap statistic (the real
  comparison is §2).
- MINOR: added a paragraph to §5 naming the launcher's pre-existing
  whole-suite failure
  (`tests/test_altrepo_talib_csv.py::test_regenerating_reproduces_the_committed_rows`,
  needs the sibling `../AlternativeRepos` checkout, the same test
  `CLAUDE.md`'s CI section says is deselected) and stating it is outside
  the eight files the subset run covers, 0 regressions per `gate-1/tests.md`.
- NIT: interpolated the computed tie count into `section_D`'s message and
  compare against the measured `ref_value` instead of a literal `11`;
  corrected "the same 120 lines" to "~100 lines of code" (measured:
  `ts_strike_20.py` is 277 lines, code ends at line 100) in §0.
- Verification: `python -m pytest -q tests/test_readme_counts.py
  tests/test_altport2_ports.py tests/test_wiring_accessors.py
  tests/test_ml_companions.py tests/test_gate_e_ledger.py
  tests/test_pine_coverage_csv.py tests/test_prose_counts_match_the_csvs.py
  tests/test_ts_strike_20.py` → 1458 passed, 7 skipped (unchanged from
  before the fixes).

### Fixes applied
- MAJOR 1 (floor divergence silent by construction) → fixed: new frame,
  re-measured, tables and prose restated.
- MAJOR 2 (precision hypothesis killed on the wrong mean) → fixed: z-scored
  the window, measured a negative residual mean reproducing the reference's
  11 under strict `>`.
- MINOR 1 (§1 title/claim mismatch) → fixed.
- MINOR 2 (Gate F silent on the pre-existing failure) → fixed.
- NIT (hardcoded literals, line count) → fixed.

## Review round 2 (Fletcher, Explore subagent, verbatim)

```
VERDICT: REVISE
FINDINGS:
  - severity: CRITICAL
    location: docs/measure_c22_stretch_high.py:186-188 (section_R's trailing print, inside the default `A Z R` invocation)
    problem:  MAJOR-1's fix added `flat-tick` to the shared `FRAMES` dict and correctly updated section_A's table and the doc's prose, but left section_R's hardcoded closing message untouched. Running the exact command the doc's own header tells readers to run (`python docs/measure_c22_stretch_high.py`, i.e. sections A, Z, R) now prints, immediately under the §R per-frame table that includes a `flat-tick` row: "Conclusion: section A shows 0 disagreement between an independent read of catch22's own definition and this fork's shipped ts_strike_20(length=100) on every frame above -- the candidate IS that column under a new name." That is false and self-contradicting within the SAME run: section A's own output two screens above it (verified by me, `python docs/measure_c22_stretch_high.py A Z R`) shows `flat-tick n=1400 disagree=1353 worst|diff|=99.0` — not 0, and "every frame above" explicitly includes flat-tick since §R just iterated and printed it. A fix that adds the one frame designed to break the universal claim, then leaves the universal claim's own print statement unqualified, is worse than not having §2's careful restatement at all — the harness itself still asserts the thing MAJOR 1 was opened to correct.
    fix:      Either drop flat-tick's wording from the generic tail message (e.g. gate it on `name != "flat-tick"` inside the loop and change the closing text to "0 disagreement on every NON-DEGENERATE frame above; see flat-tick's own row, and §2 of the receipt, for the floor-triggering exception") or move the universal claim out of section_R entirely now that it is no longer universally true. Re-run `python docs/measure_c22_stretch_high.py` afterward and confirm the printed text no longer contradicts the printed table three lines above it.
SUMMARY: The five round-1 findings were otherwise handled competently and I verified every number by rerunning the harness myself: section A's 1,353/1,400 and worst|diff|=99.0 on flat-tick, section Z's four k/d rows, section D's z-scored means (-1.110e-18 float64, -1.788e-09 float32) and the resulting run of 11 matching the live pycatch22 reference, section P's total of 194/1400 disagreements decomposing correctly into 1/1,200 (six frames) + 193/200 (flat-tick) by the print ordering, the tie counts (0/0/0/0/20/0/700 by frame) <!--stale-by-design-->, the §5 Gate F subset count (1458 passed, 7 skipped, confirmed by rerunning pytest), and the 277-line count on `ts_strike_20.py` all check out exactly as written — none of that is cause for applause, it's the bar. What is not acceptable is that the fix for MAJOR 1 planted the one frame engineered to break the script's own "0 disagreement, this IS that column" conclusion and then failed to touch the line of code that still prints exactly that conclusion, unqualified, right under a table row proving it false — a receipt whose entire credibility rests on "every number is this script's own output" cannot ship with the script contradicting itself on a bare run.
```

### Fixes applied (round 2)
- CRITICAL (section_R's tail print still asserted universal "0 disagreement
  ... every frame above") → fixed: reworded the print to scope the claim to
  non-degenerate frames and point to `flat-tick`'s own row plus the
  receipt's §2 for the deliberate exception. Re-ran
  `python docs/measure_c22_stretch_high.py` (bare, no args — sections A, Z,
  R) and confirmed the tail text no longer contradicts the table printed
  immediately above it. Re-ran the pytest subset: unchanged, 1458 passed,
  7 skipped.

## Review round 3 (Fletcher, Explore subagent, verbatim)

```
VERDICT: PASS
FINDINGS:
  - severity: NIT
    location: docs/C22StretchHighMeasured.md:54
    problem:  The receipt quotes the harness's §R conclusion as "the candidate IS that column under a new name" — but the harness's CURRENT text (docs/measure_c22_stretch_high.py:188-189, confirmed by running it) is "the candidate IS that column under a new name there," immediately followed by the flat-tick-exception sentence. The doc's clipped quote drops both the trailing "there" and the adjacent qualifier, so a reader diffing the quote against the live print output gets a literal mismatch — harmless here only because §2/§6 restate the qualifier elsewhere, but it's exactly the kind of drift that produced the prior CRITICAL.
    fix:      Either quote the full current sentence ("...on every NON-DEGENERATE frame above -- the candidate IS that column under a new name there.") or drop the quotation marks and paraphrase, so the doc never holds a string that can silently decouple from the script's own prose again.
SUMMARY: The round-2 CRITICAL is actually closed this time — section_R's closing print now says "on every NON-DEGENERATE frame above" and explicitly calls out flat-tick as the deliberate exception, pointing to section A and receipt §2, so a bare run of sections A/Z/R no longer contradicts itself; I ran the harness bare and with `P D` and every printed number (section A's 1,353/1,400 flat-tick disagreement, section R's fire/distinct counts, section P's 194/1,400 total disagreements and tie counts, section D's z-scored-mean match) lines up exactly with the receipt's tables and prose, including the newly-qualified Gate A row and §6 conclusion. Diff and status confirm only the two docs files plus the untracked docs/reviews/ artifact changed — no pandas_ta/ file touched, consistent with a revert that ships nothing. One cosmetic quote-drift nit in §0a is the only residue; it does not reopen the contradiction and does not block this round.
```

### Fixes applied (round 3)
- NIT (§0a's quoted fragment could drift from the harness's own print text)
  → fixed: de-quoted the sentence in §0a to a plain paraphrase ("this
  receipt's claim that the candidate restates `ts_strike_20` under a new
  name") instead of holding a literal string that must track the script's
  wording.
- Separately caught while re-running the pytest subset after this round:
  `tests/test_pine_coverage_csv.py::test_no_other_document_retypes_the_split`
  started failing because this log's own SUMMARY quote above
  ("0/0/0/0/20/0/700") coincidentally matches that test's 5-or-more-slash-
  joined-numbers heuristic for a retyped PINEBI verdict split. Same guard,
  same fix precedent as `docs/reviews/auto-2026-11-12-ts-c3-20/01-ts-c3-20.md`
  (round 2 there hit the identical false positive): added
  `<!--stale-by-design-->` on that same line so the verbatim quote above
  stays byte-exact while satisfying the guard.

## Outcome
PASS (round 3). `python -m pytest -q tests/test_readme_counts.py
tests/test_altport2_ports.py tests/test_wiring_accessors.py
tests/test_ml_companions.py tests/test_gate_e_ledger.py
tests/test_pine_coverage_csv.py tests/test_prose_counts_match_the_csvs.py
tests/test_ts_strike_20.py` → 1458 passed, 7 skipped.
