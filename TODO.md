# PandasTa Tolga Uyanik's Fork To-do's

Library-scoped work only. Engine-side work (mining, wiring, live book) lives in
`../Backtesting/TODO.md` — the pine-porting initiative **TVPTA** (TVPTA-0 … TVPTA-7b) is there, and
several sections below extend it rather than restarting it.

Port protocol every section here is bound by: `../Backtesting/docs/TVPTA6-Indicator-Porting-Process.md`
(Gates A–F; overlap ρ ≥ ~0.9 → revert, 0.76–0.80 → ship with disclosure, < 0.76 → ship).
Column inventory and ML form of everything currently shipped: `docs/IndicatorDictionary.md`.

---

# ═══ ACTIVE ═══

**Three items are open: MLCOL-1 (its acceptance criterion cannot be met honestly), SHOWCASE and
IMPL (both added 2026-09-12 on the owner's request).** Everything else in this file's history is finished; the full blocks — with the
measured evidence, the reverts and the traps — moved to **[`docs/CompletedWork.md`](docs/CompletedWork.md)**
on 2026-09-12. Read that before re-opening anything, because most of what it records is *why a
column is not here*.

Suite at that point: **3,166 passed / 0 failed / 23 skipped**. `Category` **233**.

## Open

Three items: **MLCOL-1** (below, open only because its acceptance criterion cannot be
met honestly), **SHOWCASE** and **IMPL** (both new 2026-09-12, owner-requested).

## IMPL — the indicator implementation manual + scaffolding (NEW 2026-09-12, owner)

> **Goal (user):** *"I will find different type of indicators and I want to implement all of them
> easily. We need an indicator implementation document."*

**This is not greenfield, and pretending it is would produce the eighth scattered copy of the same
knowledge.** What exists today, measured 2026-09-12:

| where | what it holds | why it is not the manual |
|---|---|---|
| `../Backtesting/docs/TVPTA6-Indicator-Porting-Process.md` (328 lines) | Gates A–F, the five touch points, the review gate | written as a **retrospective case study** (§6 Results, §7 Decisions Worth Recording), and it lives in the **other repo** |
| `CLAUDE.md` → *Porting a Pine indicator* | gate table, Pine arithmetic traps | a summary that **links to TVPTA6 as `../Backtesting/...`** |
| `CLAUDE.md` → *Porting a TA-Lib indicator* | TALIB-1's four traps | source-specific, and again a summary |
| `docs/*Measured.md` (7 files) | per-indicator Gate E receipts | evidence, not method |

🔴 **The cross-repo link is broken for every reader who is not the owner.** `PandasTa` is public and
is pip-installed from GitHub; a clone has no `../Backtesting`, so the fork's own `CLAUDE.md` points
its porting protocol at a path that does not resolve. **Owner decision 2026-09-12: absorb it** —
`PandasTa` gets the manual, `TVPTA6` stays in `Backtesting` as the historical case study with a
pointer forward.

**Owner decision 2026-09-12 on sources:** all four, *"whatever source I find"* — TradingView/Pine,
other Python libraries, TA-Lib C, and **papers / books / blog posts**. The last one is the gap:
the current process assumes a runnable oracle exists, and for a paper it does not.

- [ ] **IMPL-0 — Outline the manual and fix the generator's contract FIRST (design, blocks 1–3).**
  Two things are genuinely undecided and are cheap now / expensive later: (a) the doc's spine —
  source-agnostic pipeline with a per-source Gate A branch, vs one chapter per source; (b) exactly
  what `new_indicator.py` emits, and what it refuses to emit (a generator that writes a *passing*
  test is worse than no generator — the pre-written gate tests must fail until the indicator is
  real).
  **Done when:** a one-page outline lists every section with its acceptance criterion, and the
  generator's emitted-file manifest is written down and agreed, before any prose is drafted.

- [ ] **IMPL-1 — Write `docs/ImplementingAnIndicator.md`, the recipe (MAJOR).** Absorb TVPTA6's
  content and re-shape it from case study into procedure: numbered steps, each with a command to
  run and a check that must pass. Must cover, because each has already cost this repo a round:
  the **five wiring touch points** (module → category `__init__` → `Category` in
  `pandas_ta/__init__.py` → `core.py` accessor → `tests/test_<name>.py`); **naming is API**
  (column names encode parameters and are matched on by mined rules downstream — a rename is a
  break); **price levels are not features** (ship a percent distance, put the level behind
  `raw=True`, per the TALIB-1 convention); **difference parents take `parent / close` named
  `_RATIO_PCT`**, not the distance form; and that **deleting a column you just built is the
  expected outcome, not a failure**.
  **Done when:** the doc walks one indicator end-to-end from source to green suite with real
  commands, and a reader who has never seen the repo can follow it without opening `TVPTA6`.
  ⚠ Do not retype `Category`'s count, the accessor count, or the suite total into this doc. Four
  documents carried a stale split for four review rounds; generated numbers or a pointer only.

- [ ] **IMPL-2 — The Gate A oracle table, including the case with no oracle (MAJOR).** Gate A is
  the only gate whose method changes with the source. One table, four rows plus the fallback:
  **Pine** — line-by-line against the `.pine`, citing line numbers; `int/int` is fractional in
  Pine v6; `ta.stdev(biased=true)` is `ddof=0`. **TA-Lib** — cite the C function name; `talib` is
  a **dev-only** dependency and must never be imported by shipped code
  (`test_no_shipped_module_imports_talib` pins the two upstream files that may).
  **Another Python library** — numeric comparison, run in a **subprocess**: importing
  `pandas_ta_classic` in-process registers a `df.ta` accessor under the same name and corrupts the
  run. **Paper / book / blog** — 🔴 **no oracle exists**, so Gate A becomes formula transcription
  plus a **hand-computed fixture** committed with the arithmetic shown, and the doc must say
  plainly that this is the weakest Gate A of the four.
  **Done when:** each row names its oracle, its citation format, and its failure mode; the
  paper/book row specifies the fixture format and minimum bar count.
  ⚠ Licensing rides on the source and belongs in this section: the Pine ports are **MPL-2.0 ©
  their individual authors** while this repo's root `LICENSE` is MIT, so 30 modules carry their own
  headers and `docs/pine/` is untracked on purpose. A new port from a licensed source lands with
  its header or it does not land.

- [ ] **IMPL-3 — `docs/new_indicator.py`, the scaffolding generator (MAJOR).**
  `python docs/new_indicator.py <category> <name>` stamps out all five touch points plus a test
  module whose gate tests are already written: causality (with the **mutant** — a real
  non-causal implementation the probe must catch, because prefix truncation alone cannot see
  back-dating), scale-invariance ×8/×64 bit-identical, reachability `0 < fires < n`, and a Gate E
  placeholder that fails until a measured ρ is pasted in. Categories are the eleven real ones:
  `candles cycles ml momentum overlap performance statistics trend utils volatility volume`.
  **Done when:** running it on a throwaway name produces a suite that **fails** (unimplemented
  body, unmeasured Gate E) and passes only once the indicator is real and measured; running it
  twice on the same name refuses rather than overwriting; and `git status` after a run shows
  exactly the manifest from IMPL-0 and nothing else.
  ⚠ This is the sub-task that pays for the whole section. Touch points 3 and 4 drifted apart once
  already — **11 indicators sat in `Category` with no accessor** and `df.ta.strategy()` raised
  `AttributeError` (WIRING-1, fixed 2026-09-07). `tests/test_wiring_accessors.py` catches that
  *after* the fact; the generator prevents it.

- [ ] **IMPL-4 — Repoint every reference and kill the dangling links (MINOR).** `CLAUDE.md`'s two
  porting sections, `TODO.md`'s header, and any `docs/` page that sends a reader to
  `../Backtesting/docs/TVPTA6-...` now point at the in-repo manual. `TVPTA6` gains a header line
  saying it is the historical record and the manual has moved.
  **Done when:** `grep -rn "\.\./Backtesting" *.md docs/*.md` returns only links that are
  deliberate and labelled as owner-only, and every remaining relative link in the repo's markdown
  resolves from a fresh clone.

- [ ] **IMPL-5 — Prove the manual works by using it, and guard it against drift (MAJOR).** A
  procedure nobody has executed is a draft. Run the manual verbatim on **one real new indicator**
  from a source that is *not* Pine or TA-Lib — the paper/book path, since that is the one no
  existing process covers — and record every place the doc was wrong or silent.
  **Done when:** that indicator is shipped or measured-and-reverted with the manual's own receipts,
  the doc is corrected from what the run found, and `tests/test_impl_doc.py` asserts the five
  touch points and the eleven categories the doc lists are **read from the package**, not retyped —
  so the manual cannot go stale without a red test.
  ⚠ A measured-and-reverted outcome satisfies this equally. The point is that the recipe was
  executed, not that a column shipped.

⚠ **Ties.** Supersedes the recipe half of `../Backtesting/docs/TVPTA6-Indicator-Porting-Process.md`
(which keeps its case-study half). Feeds **SHOWCASE-3**, which has to demonstrate the fork's own
indicators and will need this doc's covered-name discipline. Gate rationale and the ρ ≈ 0.9 revert
/ 0.76–0.80 disclose / < 0.76 ship lines come from the same protocol — do not restate them with
different numbers. Companion-column rules live in `docs/MLCompanionContract.md` and stay there; the
manual links, it does not fork them. Reference-page generation is already solved by
`docs/gen_indicator_pages.py` + `docs/indicators/_TEMPLATE.md` — the manual's last step is to run
it, not to reinvent it.

⚠ **The honesty gate that applies to this document more than to any other.** This repo's dominant
historical defect is **a claim written before it was measured** — 17 of 18 candidates failed first
review, almost none of them on the mathematics. A manual is where that defect propagates fastest,
because every future port inherits its wording. Every sentence in it containing *only, never,
always, every, all, identical* or a specific count must correspond to a run, and the doc must say
so about itself.

## SHOWCASE — a runnable demo that shows what the fork can actually do (NEW 2026-09-12, owner)

> **Goal (user):** *"I want to add `Backtesting/SpeedyAnalysisDaily.py` to PandasTa with latest
> improvements. It can show the full potential of the library."* — a flagship example in this repo
> that a stranger can run, that exercises the fork rather than upstream, and that is honest about
> what it computes.

**Source file, measured 2026-09-12:** `../Backtesting/SpeedyAnalysisDaily.py`, 1,207 lines,
**untracked in git** (`git status` → `??`, not ignored). It calls **128 distinct pandas_ta names**
— 104 `INDICATOR_SPECS` rows plus 24 direct `ta.<name>(` calls — of which **125 are in `Category`**
(`drawdown`, `hwma`, `vp` are module-level only). **16 of those raise on every call**, so what the
file demonstrates today is **109 of 233** registered indicators, and **zero of the 34 this fork
added**. As a showcase of "full potential" it is currently a showcase of upstream.

- [~] **SHOWCASE-0 — Decide what may be published, BEFORE writing any code (BLOCKER). 🔶 DELIVERED 2026-09-12, ESCALATED: needs the owner's signature.** OUTCOME: [`docs/SHOWCASE_SCOPE.md`](docs/SHOWCASE_SCOPE.md) — 15 blocks, each `publish`/`synthesise`/`drop`. Owner chose **drop** for the scoring layer, overruling this task's own `synthesise` default. Enforced by `test_examples_contain_no_strategy_content` and `test_no_private_universe_leaks_into_the_examples`. 🔴 **The signature line is the acceptance criterion and only the owner can supply it** — an executor signing on the owner's behalf would defeat an IP gate. ⚠ SHOWCASE-1..5 were built before it closed, contrary to this item's own wording. Log: [`docs/reviews/auto-2026-09-12-showcase/`](docs/reviews/auto-2026-09-12-showcase/)

  ⚠ **Two self-inflicted leaks were caught during the run, both in files that ship publicly.** The scope document itself restated the exact threshold ladder, weights and verdict boundaries it was refusing to publish; and the leak-guard test hard-coded twenty real symbols. Both fixed — the doc now names the *shape* of a rule and never its values, and the test compares truncated SHA-256 digests. **A document about what must not be published is the worst possible place to leak from; check new prose against the never-infer list, not against the block table.**

  `PandasTa` is a **public** repo and the root `CLAUDE.md` rule is *"Do not publish strategy rules
  externally — these are internal IP."* The file as it stands cannot be copied across:
  it imports `SIGNAL_THRESHOLDS`, `INDICATOR_WEIGHTS`, `GLOBAL_MARKETS`, `US_SECTOR_ETFS`,
  `BIST_SECTORS`, `get_all_market_tickers` from `deploy/app/core/config.py`, and
  `MarketSignalCalculator.calculate_composite_score` encodes a live weighting and threshold ladder
  (RSI bands, ADX strength cuts, the 25/25/25/25 composite, the BULLISH/NEUTRAL/BEARISH cut points).
  **Done when:** a short `docs/SHOWCASE_SCOPE.md` states, per block, `publish` / `synthesise` /
  `drop`, and the owner has signed it. Default proposal, for the owner to accept or overrule:
  publish the **indicator computation**, replace every threshold/weight with neutral demo constants
  defined *in the example file itself*, drop the BIST sector map and the ticker universes, keep no
  import from `deploy/`.
  ⚠ This is the gate. Nothing below starts until it closes.

- [x] **SHOWCASE-1 — Fix the 16 broken specs IN THE COPY. ✅ DONE 2026-09-12.** OUTCOME: all 16 corrected in `examples/market_dashboard.py`, each marked `# FIXED:` with its defect. The three needing a DERIVED series (`long_run`, `short_run`, `trend_return`) are in `DERIVED_SPECS` — a table keyed on column names cannot express them, which is why the original called them wrongly. 125 specs + 3 derived → **0 failures**. The blind test reinstates the original defect (`aberration` with `close` alone) to prove the reporting path sees a raising call. Log: [`docs/reviews/auto-2026-09-12-showcase/`](docs/reviews/auto-2026-09-12-showcase/)
  <!-- superseded heading text follows -->
- [ ] ~~SHOWCASE-1 (original text)~~ ** The file carries a **7th copy**
  of the `INDICATOR_SPECS` table — INDREF-2 §5d counted six, and this untracked file was outside
  that census. All **16** known-broken arg lists are present, verified 2026-09-12:
  `aberration eom hilo kc long_run pdist pgo pvol pvr rvgi short_run smi squeeze thermo
  trend_return ttm_trend`. Each raises `TypeError` (`smi` raises `ValueError`) and is swallowed by
  the bulk loop's bare `except: continue`, so it has never emitted a column.
  **Done when:** the example's spec table calls every one of the 16 with a signature-correct arg
  list, and a test executes all 104 specs against a synthetic frame asserting **zero** swallowed
  exceptions. Publishing the table unfixed would ship the defect as the fork's recommended usage.
  ⚠ **Scope is the PandasTa copy only.** The four copies inside `deploy/` are frozen (owner
  decision 1 in this file's *Owner decisions outstanding*); do not touch them, and do not treat
  fixing them as implied by this task.

- [x] **SHOWCASE-2 — Delete the bare `except: continue`. ✅ DONE 2026-09-12.** OUTCOME: failures returned as `(name, exception)` and printed; exit status non-zero on any failure, on an unknown look-ahead, or on a probe that raised. 🔴 **The gate caught the same swallow rebuilt by typo** — `check_causality`'s error branch wrote a `causal` key while every reader looked at `verdict`, so a raising probe became a NaN, invisible to the summary, the exit code and its own test. Three of four reviewers found it independently. Pinned by `test_a_raising_probe_is_reported_not_swallowed`. Log: [`docs/reviews/auto-2026-09-12-showcase/`](docs/reviews/auto-2026-09-12-showcase/)
  <!-- superseded -->
- [ ] ~~SHOWCASE-2 (original text)~~ ** `calculate_advanced_indicators`
  wraps each call in `except: continue` and the per-block helpers in
  `except Exception as e: print(...)`. That construct is exactly what hid the 16 for the life of
  the file. An example teaches its error handling as much as its indicators.
  **Done when:** failures are collected into a reported list (name → exception) and printed as a
  summary, the run's exit status reflects an unexpected failure, and no bare `except:` remains.

- [x] **SHOWCASE-3 — Make it exercise THIS fork, not upstream. ✅ DONE 2026-09-12.** OUTCOME: coverage **158 → 190 of 233 (68% → 82%)**, computed from `ta.Category` at runtime and asserted by test. First pass shipped five SMC ports and called the family done; the gate found 16 more registered structure modules plus 7 PINEBI alternates and 9 other fork originals untouched. All five MLCOL-1 companions reachable and asserted; `HW-MID_DIST_PCT` pinned absent; the seven Gate-E reverts pinned un-resurrected. `NOT_EXERCISED_BY_DESIGN` carries a reason per skip and the example prints the 43 that still have none. Log: [`docs/reviews/auto-2026-09-12-showcase/`](docs/reviews/auto-2026-09-12-showcase/)
  <!-- superseded -->
- [ ] ~~SHOWCASE-3 (original text)~~ ** 108 `Category` names are
  never touched, and none of the fork's additions appear. Add a section covering the fork's own
  work: the Pine built-ins (`pzo`, `szo`, `vzo`, `wpo`, `frama`, `ht`, `stc_tv`, `vstop`,
  `vstop2`), the TA-Lib gap fills (Hilbert family, `imi`, `sarext`), the chart patterns, the SMC
  ports, `ichimoku_ml`, `wilder_rma`, and the five MLCOL-1 companions.
  **Done when:** the example's covered-name count is **printed by the example itself** and
  asserted by a test against `Category` — never retyped into prose. Two named columns from the
  fork's ML-companion work appear in the output frame.
  ⚠ Deliberate absences are load-bearing: `beta`, `up_and_down_volume` and `volume_delta` are out
  of `Category` on purpose, and the seven Gate-E reverts must not be "completed" back in. State
  the covered count as a fraction of what is registered, not as coverage of everything nameable.

- [x] **SHOWCASE-4 — Sever `yfinance` and `deploy/` from the test path. ✅ DONE 2026-09-12.** OUTCOME: `tests/test_showcase.py`, **38 passed offline in 45s**. `yfinance` imported only inside the optional loader and given its own `extras_require["examples"]`; output path an argument; no `deploy/` reference. 🔴 **The gate found the test module gated behind `pytest.importorskip` on a FIRST-PARTY file** — all 38 could vanish as skips, which satisfies SHOWCASE-5's "0 failed" perfectly. Replaced with `spec_from_file_location`, which also removed a permanent `sys.path` mutation. Log: [`docs/reviews/auto-2026-09-12-showcase/`](docs/reviews/auto-2026-09-12-showcase/)
  <!-- superseded -->
- [ ] ~~SHOWCASE-4 (original text)~~ ** The file
  downloads from Yahoo, `sys.path`-injects `deploy/app/core`, and writes CSVs into a sibling
  `CSVs/` directory. None of that can run in `PandasTa`'s suite.
  **Done when:** the example takes a DataFrame, a data loader is one optional pluggable function,
  `yfinance` is an `extras_require` entry and never a hard import, output path is an argument, and
  the test drives the whole pipeline on a synthetic frame with **no network and no `deploy/`
  import**. `tests/test_showcase.py`, green offline.

- [~] **SHOWCASE-5 — Land it and point at it. 🔶 DELIVERED 2026-09-12, ESCALATED on its own numeric criterion.** OUTCOME: README *Runnable examples* section links both files and says what they do NOT do; the example's docstring names version, branch and commit; `.gitignore` gained `!examples/*.ipynb` (a blanket `*.ipynb` would have made the notebook uncommittable). 🔴 **The done-when is "`pytest -q` stays at 0 failed" and it is 1.** `tests/test_pine_coverage_csv.py::test_audited_rows_carry_their_evidence` fails on a clean checkout: it requires every audit citation in `docs/pine_builtin_coverage.csv` to resolve to a file, and `8d8f705` untracked `docs/pine/` for licensing reasons. **Pre-existing and unrelated to this work**, now recorded in `CLAUDE.md` *Known breaks* — which until today read "None outstanding" and was false. Owner's call. Log: [`docs/reviews/auto-2026-09-12-showcase/`](docs/reviews/auto-2026-09-12-showcase/)
  <!-- superseded -->
- [ ] ~~SHOWCASE-5 (original text)~~ ** Place as `examples/market_dashboard.py`
  (or `docs/examples/`) with a README section that says what it demonstrates and what it does not.
  **Done when:** `README.md` links it, the file's docstring names the fork commit it was written
  against, and `python -m pytest -q` stays at **0 failed**.

⚠ **The showcase is a claim surface.** Every count in the example's own output and in its prose
must come from a run — this repo's dominant historical defect is a number written before it was
measured (17 of 18 ports failed first review on exactly that). Prefer printing a computed number
over writing one down. Ties to [[data-split-contamination]] on the data side: the demo must not
imply its yfinance output is clean BIST data — `clean_if_bist` lives in the consumer, not here.

## Owner decisions outstanding — not tasks, and not mine to take

1. 🔴 **The 16 broken `INDICATOR_SPECS` arg lists** (INDREF-2 §5d). Sixteen of the 104 specs pass
   an argument list that does not match the pandas_ta signature, raise `TypeError` on every bar of
   every run, and are swallowed by a bare `except: continue` — so they have never emitted a
   column. The same 16 are broken in **all six copies** of the table, **four of which are inside
   `deploy/`**, where repairing them would make 16 indicators start emitting columns in the live
   container. That is a strategy-affecting change under the TRADING FREEZE.
2. 🔴 **2,211 `.pine` files are TRACKED in `Backtesting`** with 912 MPL-2.0 headers under hundreds
   of individual rightsholders, and that repo has **no `LICENSE` file**. Untracking them in
   `PandasTa` (2026-09-07) closed this for *this* repo only. Whether the other repo is public is
   unverified. Remediation means history rewriting and a force-push.
3. ⚠ **`dpo` ships `centered=True` as its DEFAULT**, so `ta.dpo(close)` silently returns a
   look-ahead column, and `dpo` is in `Category`, so `df.ta.strategy()` sweeps it. Documented
   upstream behaviour the fork inherited — left alone rather than changed unasked, but it is a
   live trap. (`ssf` was a third, undocumented look-ahead; that one was a bug and is fixed.)

# ═══ BACKLOG ═══

## PINEBI — TradingView built-ins ✅ CLOSED

Full record: [`docs/CompletedWork.md`](docs/CompletedWork.md). PINEBI-0, -0b, -1a…-1e and -2 are
all closed. **Zero `port` rows remain** in `docs/pine_builtin_coverage.csv`.

**Verdict split, generated — this is the table the -1b…-1e scopes are cut from.**
Produced by `docs/gen_pine_builtin_coverage.py` (PINEBI-0, done 2026-09-07).

| verdict | n |
|---|---|
| `have` | 73 |
| `port - primitive` (→ -1a) | 18 |
| `n/a - measured and reverted on Gate E` | 7 |
| `n/a - not a Pine built-in` | 4 |
| `n/a - not worth a primitive` | 2 |
| `port - blocked on data` (→ -1d) | 2 |
| `n/a - never called live in the corpus` | 1 |

⚠ These counts are **asserted**, not retyped: `test_the_docs_quote_the_csvs_actual_split` reads this
table and fails if any number disagrees with the CSV. Four review rounds went by with a stale split
standing in three documents; that is now a test failure rather than a reading exercise.

The scopes those verdicts route to are closed. Their enumerations are kept here because
`test_every_scoped_row_is_named_in_its_task` reads the `ROWS:` line out of the task block itself,
and a scope written only in prose is unguarded — that guard exists because `stc` spent a whole
round "scoped into PINEBI-1b" while existing only as a string in a CSV note.

- [x] **PINEBI-1b — Port the `port` rows. ✅ DONE 2026-09-11.** 16 measured, **9 shipped, 7 built
  and reverted on Gate E**. Zero remain.
  ROWS: none remaining — every one of the 16 reached a terminal verdict; see
  `docs/PineBuiltinsMeasured.md` for the per-column ρ and `REVERTED_ON_GATE_E` in
  `docs/gen_pine_builtin_coverage.py` for why each of the 7 was deleted.

- [x] **PINEBI-1c — The nine alternates. ✅ DONE 2026-09-08.** 7 kept, 2 deleted.
  ROWS: none remaining — all nine resolved; measured table in `docs/PineAlternatesMeasured.md`.

- [x] **PINEBI-1d — The two data-request rows. ✅ DONE 2026-09-08.** `up_and_down_volume` and
  `volume_delta` ship, deliberately OUT of `Category` and in `strategy`'s exclusion list: they
  need a lower-timeframe frame a sweep cannot supply.

- [x] **PINEBI-2 — The community corpus. ✅ CLOSED 2026-09-11**, triage delivered and the porting
  half deferred on its own measurement (2–7 landed indicators for 179–269 files read). The wiring
  pass was done instead, as WIRE-0. **TVPTA-1b's deliverable is already delivered by that triage**
  — read `docs/PineCorpusTriage.md` before writing its spec rather than re-running the classifier.

## CANDLE · INDREF · TALIB · ALTREPO · ALTFIX · ALTPORT — ✅ ALL CLOSED

Full records in [`docs/CompletedWork.md`](docs/CompletedWork.md):

| section | outcome |
|---|---|
| **CANDLE-0/-1/-2** | 11 shortlisted → 8 shipped, 22 columns → **6 deleted** on Gate E; `rectangle` skipped on a pre-registered trigger |
| **INDREF-0/-1** | `docs/gen_indicator_pages.py` + a reference page per shipped indicator, idempotent (`--check` → changed=0) |
| **INDREF-2** | `../Backtesting/docs/indicators/IndicatorSelectionResults.md` — **175 of 233 indicators were never in a position to be selected**; found the 16 broken specs |
| **TALIB-1** | 10 `port` rows → 8 columns shipped, **5 reverted**; seven of the ten are one state machine with two warm-ups |
| **ALTFIX-0…-4** | audit closed; gaps classic 33 → 9, tti 10 → 9, ta-lib 10 → 0 |
| **ALTPORT-0/-1/-2** | 20 candidates → **3 shipped** (`cvi`, `bw_mfi`, `smc_sweep`), all three later cleared by WIRE-0 and now called by the engine |

## MLCOL — per-indicator ML companion columns

✅ **MLCOL-0** (contract) and **MLCOL-2** (reference companions — **0 of 5 shipped**) are closed;
see the archive. MLCOL-2 is the reason MLCOL-1 screens before it builds.

- [~] **MLCOL-1 — Roll the contract out, PX columns first. 🔶 MEASURED IN FULL AND 5 SHIPPED 2026-09-12; the stated Done-when CANNOT be met honestly — see below.** Order the work
  by the dictionary's *"Needs a transform before modelling"* table — those indicators are unusable as
  features today, so they pay back first.
  **Done when:** every `PX` column in the dictionary has a scale-free companion, and the regenerated
  dictionary shows no indicator whose entire output is `PX`.
  ⚠ **Owner's sequencing (2026-09-08): "contract, then roll out with Gate E per companion."** Gate E
  is per companion, not once at the end — one measurement per PX column. (For the count, read the
  opening paragraph of `docs/MLCompanionContract.md`; it is Counter-derived from the generated
  dictionary and asserted by `tests/test_ml_companions.py`. Four different numbers for that one
  quantity were in circulation on 2026-09-08 — do not retype it.)

  ✅ **What was done (2026-09-11/12).** All **137** `PX` columns screened before anything was
  written, then the survivors put through the incremental axis, then redundancy checked *among the
  survivors*. Receipts: `docs/MLCol1Screen.md`, `docs/MLCol1Axes.md`, and the two harnesses
  `../Backtesting/scripts/analysis/measure_mlcol1_{screen,axes}.py`.

  **The funnel, every step measured:**
  137 proposed → **82 restate a shipped column at ρ ≥ 0.90** → 36 land in the disclosure band →
  **2 parents read the future** → 4 could not be probed → **13 clear Gate E** → **6 show
  incremental evidence** → **5 after removing redundancy among the survivors**.

  **SHIPPED (5):** `HA_high_DIST_PCT` (ha), `HW-UPPER_DIST_PCT` + `HW-LOWER_DIST_PCT` (hwc),
  `LINREG_LOWER_2_DIST_PCT` (linreg_channel), `THERMO_20_2_0.5_RATIO_PCT` (thermo). All
  scale-free bit-identical ×8/×64, all causal, `tests/test_mlcol1_companions.py` 34 passed.
  `SF` 207 → **212**.

  🔴 **THE DONE-WHEN AS WRITTEN CANNOT BE SATISFIED HONESTLY, and this is the finding, not an
  excuse.** It asks that *"every `PX` column has a scale-free companion"* and that *"no indicator
  whose entire output is `PX`"* remains — **71 indicators are still all-`PX`**, nearly all of them
  moving averages. Meeting it means emitting ~71 more companions, and the screen MEASURED that
  their `DIST_PCT` forms restate columns the engine already ships: **15 restate
  `NWE_MID_200_8.0_8.0`, 14 restate `bias`** — the exact columns this task's own contract told it
  to screen against. Satisfying the acceptance criterion would therefore require violating the
  contract's non-redundancy rule 82 times over.
  **Proposed amendment, for the owner:** *"every `PX` column has been SCREENED for a companion,
  and one is emitted wherever it clears Gate E, the incremental axis, and redundancy against the
  other survivors."* Under that reading MLCOL-1 is done. Left as `[~]` because rewriting one's own
  acceptance criterion is the owner's call, not the executor's.

  ⚠ **Three findings that outlive this task:**
  1. 🔴 **`ssf` READ THE FUTURE — an undocumented look-ahead in shipped code, now fixed**
     (`f3ff67a`). Its recursion ran `for i in range(0, m)`, so at `i = 0` it read `ssf.iloc[-1]`,
     the LAST bar of the series. Perturbing only bars ≥ 300 of a 400-bar frame moved **bar 0** by
     31.4. `CLAUDE.md` claimed the causality exception list was "complete" at two columns; it was
     three, and the claim is corrected. Independent corroboration: `ssf` vs pandas-ta-classic
     moved `port - alternate impl` → `have`, `divergent` → `identical`, agreeing on all 260
     values — the divergence WAS the bug.
  2. 🔴 **Causality must PRECEDE the incremental axis, not sit beside it.** The leaking `dpo`
     companion was ranked **first** by axis 3a — ΔAUC +0.0473, permutation importance +0.35693,
     15/15 beats-null — in a field where every honest candidate scored ~0.01. Leakage is the
     strongest signal a model can be handed, so the axis *promotes* a non-causal feature rather
     than rejecting it, with every control behaving exactly as designed. Recorded in
     `docs/MLCompanionContract.md`. Note `dpo`'s `centered=True` is its **default**.
  3. **Gate E is blind to redundancy AMONG candidates.** It measures each against the SHIPPED
     set. Three `hwc` companions each cleared it and the axis, then read ρ +0.9257 / +0.9213
     against each other — `HW-MID` is the hub and carries nothing independent once both edges are
     kept. Dropped. This is the PB_LO/PB_UP lesson again: a survivor set is itself a correlation
     gate that nobody ran.

  ⚠ **The contract's single DISTANCE formula does not fit all `PX` parents.** `(close - parent) /
  close` is right for a **level**; 37 of the 137 are price **differences** centred on zero, where
  it evaluates to ≈1.0 with the signal in the fourth decimal. Those are screened and shipped as
  `parent / close` and NAMED `_RATIO_PCT`, because naming is API and calling a ratio a distance
  misdescribes it permanently.

  ⚠ **MLCOL-2 added a prerequisite screen:** Gate E is necessary but NOT sufficient (it would have
  shipped `FVG_BULL_RATE_60`), and every MA-family `DIST_PCT` must be checked against the engine's
  existing relational columns first — `SMA_10_DIST_PCT` died at ρ 0.946 against `NWE_MID_200_8.0_8.0`.
  Use `measure_ml_companion_overlap.py --companions`.

---

**Everything above this line that is marked ✅ or [x] is finished.** The evidence lives in
[`docs/CompletedWork.md`](docs/CompletedWork.md), not here.



[ ] Create a disclaimer text preventing the legal issues and show it from the readme.md file. 