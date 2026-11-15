# 99 — SK-FCB-WIDTH run summary

**Date:** 2026-11-14 (every measurement in `docs/SkFcbWidthMeasured.md` is stamped that
day; round 4's fixes and the final full-suite re-run landed just after midnight, on
2026-11-15 — the folder keeps the run's start date, as the sibling runs do)
· **Mode:** C, one task · **Rounds:** 4 (the loop's cap)
**Full log — rounds 1 and 2 verbatim, rounds 3 and 4 tabulated, every finding's outcome:**
[`01-sk-fcb-width.md`](01-sk-fcb-width.md) · **Task, assumptions, execution map:**
[`00-manifest.md`](00-manifest.md)

| task | status | rounds | files touched | follow-ups |
|---|---|---|---|---|
| SK-FCB-WIDTH: port `Fcb`'s width (span 2) as `sk_fcb_width` through Gates A–D, the wiring, the tests and the receipt | **shipped** | 4 | 15 — 8 new (the module, its test module, two `docs/measure_*` scripts, the receipt, three review files) and 7 modified (the category `__init__`, `Category`, `core.py`, `README.md`, `MLCompanionContract.md`, `test_altport2_ports.py`, the regenerated dictionary) | **Gate E**, run by the launcher; then the receipt session records the ledger row and Gate C's real-data counts |

## What shipped

One column, `SK_FCB_WIDTH_2` (volatility) — the last confirmed Williams fractal high minus
the last confirmed fractal low, over close, from Skender Stock.Indicators' `Fcb`
(Apache-2.0) as issue #107 names it. `SPAN = 2` and `MIN_BARS = 5` are module constants.

Five wiring touch points, three count surfaces, the dictionary regenerated from its live
probe: `Category` 345 → **346**, accessors 353 → **354**, probed 347 → **348**,
`volatility` 36 → **37**, tagged columns 690 → **691**, `SF` 329 → **330** — all read back
out of the generated file (§M), none incremented by hand.

**160 tests**, passing under both the full dispatch and
`NPY_DISABLE_CPU_FEATURES="AVX512F AVX512_SKX AVX2 FMA3"`. Local full suite, re-run after
the last fix: **3 failed, 9,289 passed, 85 skipped** — `test_pine_coverage_csv` and
`test_altrepo_talib_csv` (the two documented clean-checkout breaks) plus the **owed Gate E
row**, which is expected and which
`tests/test_sk_fcb_width.py::test_the_gate_e_row_is_owed` asserts deliberately. 160 of those 9,289 are
this module, so the rest of the repo is 9,289 − 160 = 9,129 by subtraction (stated as a
subtraction, not as a second run). ⚠ An earlier draft of this page carried 9,286 — the suite as it
stood at round 1, three tests ago — and round 4 caught it.

## Gates

| gate | result |
|---|---|
| **A** | **pass** — bit-equal to a loop transcription of `Fractal` + `Fcb` and to the screen prototype on all eight frames; the centre-index divergence named and measured (differs on 46 .. 839 bars, ρ 0.4638 .. 0.9643); `>=` and `EndType.Close` priced. ⚠ `Fcb.Series.cs` was NOT read — not installed, no `docs/pine/`, no web |
| **B** | **pass** — module caught 0 of 1,499 offsets on each of eight frames (0 of 299 asserted in the suite); five mutants each live, and each caught on each of the six frames other than `flat` (which catches 1 of the 5) and `coarse` (3 of the 5) — **not 36 of 36, and why, in §B**; the weakest carried by §B2's mechanism-aware sweep (0 of 8,743 unexposed offsets, all 30 exposed-but-missed offsets classified 17/9/4 with none left over) |
| **C** | **pass** on synthetic — 1,411 .. 1,493 of 1,500 on seven frames, 0 on `flat` with the reason, and §C3 runs the whole bucket on a flat frame rather than guessing (13 of 63 all-NaN, `j_damiani` among them). Real-data counts **owed** with Gate E |
| **D** | **pass** — x8/x64 bit-identical on all 10,330 fired bars and at three price levels; inexact factors ≤ 1.229e-12 with masks matching and 0 selection flips |
| **E** | **pending, run by issue-solver after this session** |
| **F** | this module 160 passed under both dispatches; both repos' suites are the launcher's, in clean worktrees |

## Review rounds

| round | verdict | findings | applied | declined |
|---|---|---|---|---|
| 1 | REVISE | 2 MAJOR, 3 MINOR, 2 NIT | 7 | 0 |
| 2 | REVISE | 2 MAJOR, 4 MINOR, 2 NIT | 7 (+ half of one) | half of 1, with cited evidence |
| 3 | REVISE | 3 MAJOR, 3 MINOR, 3 NIT | 9 | 0 |
| 4 | REVISE | 3 MAJOR, 2 MINOR, 4 NIT | 9 | 0 |

**No round returned PASS, and round 4 is the cap — so round 4's nine fixes are the only
changes in this port that no reviewer has read.** They are listed in
[`01-sk-fcb-width.md`](01-sk-fcb-width.md)'s round-4 table and repeated at the end of this
file, rather than folded in silently. Eight of the nine are prose; the single code change
is `docs/measure_sk_fcb_width.py`'s `section_F` printing a second ranking (by signed ρ)
instead of describing it, and its output is in the receipt's §F.

### The shape worth carrying forward

**Not one of the 33 findings across the four rounds (7 + 8 + 9 + 9) was about the
mathematics.** Every round
re-ran the measurement script and every cell reproduced; rounds 2 and 3 certified the
window alignment, the strict predicate, the oracle's independence, the prototype retype
and §B2's derivation. What failed, three rounds running, was **prose that narrated a run
instead of reading it** — and twice the *fix for an unmeasured number shipped a fresh
unmeasured number*:

- round 1: `5 .. 105` negative bars was `5 .. 91` (the fix had added `coarse`'s 85 exact
  zeros into a negative count, in four places including the contract the parent repo
  reads);
- round 1: "a divergence from every rolling-window column in this category" was a claim
  about 36 modules that the port's own data refutes — the fix was §C3, which *runs* them;
- round 2: the same "departure from the other volatility columns" claim, still standing on
  the one consumer-facing page, and §F omitting the one real-data figure in scope
  (the screen's fork stage, 0.5873 vs `natr:NATR_14` on 12 real frames);
- round 3: §B2's control total hand-added to 8,730 when it is **8,743**, and its miss
  classification written as 21/9/4 when the printed table says **17/9/4** — a sentence
  that did not even add up to the 30 it claimed in the same breath;
- round 4: the *fix* for round 3's ranking finding re-sorted §F's table and then bolted on
  "`rvi` is ... second-from-last by signed ρ" — it is **last**, at 0.1409, behind both
  invented proxies and two shipped siblings — with the sentence hard-coded inside the
  measurement script, so the script was asserting in its own voice something no run
  produced. And this page's own suite count was the round-1 figure, 157 tests out of date.

The structural fix applied in rounds 3 and 4 is the one to copy: **the script now prints
the pooled rows and both rankings it is quoted for**, so no reader — and no future
session — has to trust an addition or a remembered ordering. Four rounds of correcting
sentences fixed four sentences; printing the figure is what stops the fifth. Two other patterns
recurred and are worth naming: a replacement assertion that was still only a *proxy* for
its own docstring (round 1's tautology → round 2's pair-count bound → round 3's accepted
"count the bars where neither leg moved and the column moved anyway"), and a loose
universal — "every bar", "every offset", "every frame" — re-introduced by each round's new
work and corrected each time.

One finding was **declined with evidence**: round 2 asked for the "an earlier draft said
X, which was wrong" notes to be stripped from the receipt and the test docstrings. They
stay, because that is this repo's own convention for a changed conclusion
(`docs/JAcoscMeasured.md:522`, `docs/TsEnergyLast20Measured.md:628-632`,
`docs/G191158Measured.md:49` and `:83`, `docs/TsAggac60Measured.md:133` and `:270`,
`tests/test_j_acosc.py:763`), and deleting them would make the receipt read as if it had
been right the first time — which is the failure mode those notes exist to prevent. Round
3 checked all five citations and agreed.

## What is owed

1. **Gate E**, run by the launcher on this committed tree, then the receipt session records
   the row with `python docs/gate_e_ledger.py record <run dir> --measured YYYY-MM-DD` and
   replaces `test_the_gate_e_row_is_owed` with one pinning the row's identity.
2. **Gate C's real-data counts**, from the same run.
3. If Gate E comes back **STRUCK**, the column is reverted and
   `docs/SkFcbWidthMeasured.md` stays as the receipt — which, per the issue, closes #107
   exactly as well as a ship.

---

## Round 4 — the cap, and what it leaves unreviewed

Round 4 returned **REVISE** (3 MAJOR, 2 MINOR, 4 NIT) and all nine were applied. Because
the loop's cap is four rounds, **these nine are the only changes in this port that no
reviewer has read.** In full, so a reader does not have to diff for them:

1. §F's signed-ρ sentence, which claimed `rvi:RVI_14` was "second-from-last by signed ρ"
   when it is **last** (0.1409, behind both invented proxies and `chop` 0.1763 /
   `massi` 0.1551) — the sentence is gone and `section_F` now **prints** the signed
   ranking next to the \|ρ\| one. *(the one code change)*
2. This page's suite count, 9,286 → **9,289**, re-run.
3. Rounds 3 and 4 written into `01-sk-fcb-width.md` with their findings and outcomes, and
   the round counts in both log files corrected to four.
4. "spelled two **independent** ways" → "two ways, one of them independent", in the
   receipt (opening, §A1, §A2, Verdict), the module docstring and the test header, because
   the prototype limb is the module's own expression retyped.
5. "on the **eight** frames the first fire lands on bar 7 .. 89" → the seven that fire,
   with the eighth named as the flat one, in the contract and the module docstring.
6. §B's table header: "every bar" → "every bar but bar 0 — 1,499 of 1,500".
7. §B2's two pooled rows folded into the table they total, so they render as cells.
8. The web-access caveat added to `test_the_source_library_is_not_readable_here`, the one
   surface that had claimed all routes were pinned.
9. This page's Gate B row, which had dropped the "six frames other than `flat` and
   `coarse`" qualification and the "not 36 of 36" caveat.

After them: 160 tests pass under both dispatches, the full suite reads 3 failed / 9,289
passed / 85 skipped, and §F reproduces with both rankings printed.
