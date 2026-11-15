# Run manifest — `/brutally-honest-review --auto` (Mode C), 2026-11-14

**Run id:** `j-acosc` · **Folder:** `docs/reviews/auto-2026-11-14-j-acosc/`
**Repo:** PandasTa, worktree `PandasTa-106-j-acosc`, branch `issue-106-j-acosc`.

## The invocation, verbatim

```
/brutally-honest-review --auto "J-ACOSC: port the indicator of issue #106
through Gates A-D, the wiring, the tests and docs/<Name>Measured.md, per the
issue and the rules in your system prompt (Bill Williams acceleration
oscillator. Source: jesse indicators (MIT) — `acosc: AO - SMA(AO,5),
AO = SMA(mid,5)-SMA(mid,34)`.). Gate E and the suites are run by the launcher
afterwards."
```

One free-form task reference, so this is **Mode C** (batch task execution),
not Mode B: there is no plan file, so no step-0 pre-gate. The skill says so
explicitly ("No pre-gate in Mode C. Mode C resolves TODO references, which
are tasks, not plans carrying load-bearing reasoning").

## Phase 1 — Select

| # | task | scope | source |
|---|---|---|---|
| 1 | `j-acosc` — port jesse's `acosc` as `j_acosc` through Gates A–D, wire it, test it, write the receipt | `pandas_ta/momentum/j_acosc.py` + the five wiring touch points + `docs/JAcoscMeasured.md` + `docs/measure_j_acosc*.py` | GitHub issue **#106**, quoted verbatim in the session prompt; local mirror `docs/issues/105-j-acosc.md` (gitignored) |

⚠ **That is not a typo, and the round-3 reviewer flagged it as one.** The
owner's local tracker numbers this issue **105** and GitHub numbers it
**106** — `docs/issues/105-j-acosc.md`'s own first lines are
"`# 105 J-ACOSC`" and "**On GitHub:** [#106]", and
`docs/issues/104-j-damiani.md` is the PREVIOUS port, GitHub #105. The
offset is systematic across the tracker, and `docs/issues/` is gitignored,
so a reviewer on a clone cannot open either file to check. Everything
committed by this port cites **#106**; this row is the only place the
local path appears.

One task, so Phase 3's execution map is trivial: **main thread**, no
parallel lanes, no worktree isolation.

## Phase 2 — Clarify

`AskUserQuestion` is **unavailable** in this headless run, and the session
prompt says so: "Where a skill says to ask, take the most conservative
reading (the smaller scope) and log it as an ASSUMPTION." So no questions
were asked and every open decision is below.

### ASSUMPTIONS

* **A1 — one column.** `J_ACOSC_5_34_5` and nothing else. The issue quotes
  a single series (`acosc: AO - SMA(AO,5)`) and the screen prototype
  returns one. Bill Williams' chart presentation also carries a
  colour/sign state; shipping it would be the wider scope, and it would be
  `np.sign` of this column. Smaller scope wins.
* **A2 — no parameter surface.** `FAST = 5`, `SLOW = 34`, `SIGNAL = 5` are
  module constants, following `j_gator`'s `JAW`/`TEETH`/`LIPS` and
  `j_damiani`'s `FAST`/`SLOW`. The issue names those three numbers and no
  other pairing, and a parameter surface would need a Gate E run per
  setting.
* **A3 — "SMA" is `rolling(n).mean()` at pandas' default
  `min_periods=n`.** The issue's word is SMA and the prototype spells
  `x.rolling(n).mean()`. ⚠ jesse is NOT installed here and web access is
  unavailable, so nothing in this port is evidence about jesse's code.
  `docs/JAcoscMeasured.md` §A4 prices the three readings in reach, and
  §A4(a) is an uncomfortable one: an exponential mean of the same period
  reads Spearman 0.8966 .. 0.9277, so the reading is defended by the
  prototype's bit-equality (§A2) and not by distance. That is disclosed in
  the module docstring, the test docstring, the receipt and
  `docs/MLCompanionContract.md`.
* **A4 — `_sma` is spelled in the module, not imported.**
  `pandas_ta.overlap.sma` computes exactly the same thing;
  `docs/JAcoscMeasured.md` §A3 asserts the two routes bit-equal on all
  seven frames, so the local spelling costs nothing arithmetically and
  avoids a rename plus a second `verify_series` on each of its three
  calls (`_sma(mid, FAST)`, `_sma(mid, SLOW)`, `_sma(ao, SIGNAL)`).
  ⚠ The alternative (importing it) is also defensible; this is the smaller
  change to the package surface, since no shipped helper is touched.
* **A5 — category `momentum`**, where `ao` lives and where the issue's
  parent screen filed it.
* **A6 — `WARMUP = SLOW + SIGNAL - 2` is a module constant.** The two
  warm-ups ADD because the signal leg averages `AO` rather than the price,
  and that is the one easy mistake in this formula, so it is named in the
  code and not only in prose.
* **A7 — one guard, on the divisor only.** `close.where(isfinite &
  >= tiny)`, as in `j_gator`. `mid` is UNguarded, which §G3 measures
  rather than assumes: `rolling(...).mean()` empties a window holding a
  NaN **or** an infinity, so an `inf` high gives a column bit-identical to
  a NaN high with 0 non-finite readings. Adding a `mid` guard would change
  no reading and would hide the 38-bar reach behind a different mechanism.
* **A8 — Gate A is a tolerance against the independent oracle and
  bit-equality against the prototype and the fork route**, with the
  ABSOLUTE bound as the tight one (1e-14; measured 4.536e-16) because the
  column cancels to 1e-16 on some bars and the relative figure there is
  float dust (measured 8.784e-11).
* **A9 — §L1 carries an invented `fwma` proxy, labelled as invented.** The
  screen's top Gate E comparator is the engine's `FWMA_Slope_pct_Pctl`,
  which is not readable from this worktree. A labelled guess is more
  useful to the reader than silence; the label is what stops it becoming
  evidence. ⚠ The conservative alternative — omit it — was rejected
  because the row's VALUE (0.5283 .. 0.6155) is informative about shape
  even when the definition is a guess, and omitting it would have left the
  section with nothing to say about the comparator that drove
  DISCLOSE_GAP.

### Gate E and Gate F, per the session prompt

* **Gate E is the launcher's.** This session must not run
  `gate_e_overlap.py` or read `../Backtesting`. `docs/JAcoscMeasured.md`
  §E says "pending, run by issue-solver after this session", and
  `tests/test_j_acosc.py::test_the_gate_e_row_is_owed` asserts the ledger
  has no `j_acosc` row. `tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
  therefore FAILS locally — expected, and reported as owed on a PR into
  `dev`.
* **Gate F** is run by the launcher in clean worktrees for both repos.
  This session ran `python -m pytest -q` here and
  `python docs/measure_j_acosc_cpu.py` (which sets
  `NPY_DISABLE_CPU_FEATURES="AVX512F AVX512_SKX AVX2 FMA3"` before numpy
  is imported and refuses to run if any of the four survived).

### Destructive steps

None. No push, no deploy, no deletion, no external publication. The
session commits by path on its own branch and the launcher pushes.

## Phase 3 — Execution map

| task | lane | why |
|---|---|---|
| `j-acosc` | main thread | single task; needs judgment on the Gate A/B/D design and on which readings to price; nothing to parallelise |

## Phase 4/5 — where the log lives

`01-j-acosc.md` (implementation log + every review round verbatim),
`99-summary.md` (the table and the follow-ups).

## Write-back

`docs/issues/` is a gitignored read-only copy of the owner's tracker, and
the session prompt forbids `git add -f` under it, so there is no task file
to write a status back into. The status of issue #106 lives on GitHub and
is the launcher's to update. Stated here rather than left implicit, as the
skill's Phase 5 step 14 requires.
