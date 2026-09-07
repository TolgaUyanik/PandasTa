# Brutally honest review — the PandasTa fork, whole repo — 2026-09-07

Mode A (standalone, advisory). Target: `d:\AwakenAnalytics\PandasTa\`, closing review of a session
that rewrote the docs, fixed six defect classes, added 18 Pine primitives and a 107-row coverage
audit, and put the PINEBI work through eight review rounds.

**VERDICT: REVISE** — 3 CRITICAL · 3 MAJOR · 5 MINOR · 1 NIT.
**Do not commit until the four blockers below are cleared.** Nothing found here is in the code that
was reviewed eight times; it is all in the parts nobody opened.

---

## The verdict in one line

The engineering is good and the packaging around it is lying about it. Both generators reproduce
byte-identical output, the suite is genuinely green at **1,252 passed / 21 skipped**, and the mutant
tests are the real article. And none of it is committable as it stands.

---

## CRITICAL — four blockers

### 1. `.gitignore` eats PINEBI-0's only deliverable

`git check-ignore -v docs/pine_builtin_coverage.csv` → `.gitignore:134: *.csv`. **Verified.**

You would push the generator, a 493-line guard module and four downstream task scopes
(PINEBI-1b/-1c/-1d/-1e) that are *cut from* that CSV — and not the CSV. On a fresh clone `_rows()`
hits `pytest.skip("coverage CSV not generated")`, so 8 of 12 tests in `test_pine_coverage_csv.py`
silently evaporate, including all three guards built across rounds 6-8.

**Fix:** add `!docs/pine_builtin_coverage.csv`, or narrow `*.csv` to what the surrounding block
actually means. Then replace that `pytest.skip` with a hard assert — a committed artifact going
missing is a failure, not a skip.

### 2. The README still tells readers the `fvg` columns are dead

`README.md:218` — "`IN_FVG_BULL`/`IN_FVG_BEAR` are constant zero — 0 fires in 12,000 probe bars",
with a "do not feed those two columns to a model" instruction and line citations that now point at
the repaired loop.

Measured on the live package, same 12,000-bar probe: **4,223 / 4,493 fires**. `CLAUDE.md:120` says
FVGDEAD is closed; `TODO.md` marks it DONE. The README was written at 01:51 and the repair landed
after it.

This is the repo's own named dominant defect — a claim outliving the measurement that refutes it —
in the first document a reader opens.

**Fix:** replace with the measured state (22.17% / 19.85% on 408,253 BIST bars, Gates C/D/E cleared,
max |ρ| 0.6390 / 0.5962). Then grep the tree for `constant zero`, `FVGDEAD` and `12,000` and
reconcile every hit.

### 3. Licence posture: 46MB of MPL-2.0 TradingView source under a root MIT licence

`git ls-files docs/pine | wc -l` → **2,211. The corpus is tracked, not untracked** — three documents
(`CLAUDE.md:82`, `TODO.md`, `test_pine_coverage_csv.py:16`) say otherwise. **912 of those files carry
`Mozilla Public License 2.0` / `© TradingView`**; the rest are community scripts with no stated
licence, i.e. all-rights-reserved by default. There is no `NOTICE`, no `THIRD_PARTY`, no `LICENSES/`.

MPL-2.0 §3.1/§3.2 require the licence text to accompany covered source you distribute, and a root
MIT implicitly relicenses the tree. Secondary cost: `pip install git+…` — the documented install path
— clones 46MB the package never reads.

**Fix (recommended):** `git rm -r --cached docs/pine && echo "docs/pine/" >> .gitignore`. That makes
the three "untracked" claims true and drops the exposure. The corpus is a working input, not a
distributable. If you keep it instead, add `docs/pine/NOTICE.md` with the MPL text, per-file
attribution for the 912, and an explicit statement that root MIT does not extend there.

### 4. `setup.py` — the consumer will never receive any of this session's fixes

Untouched all session: `version="0.2.67b"`, `author="Kevin Johnson"`,
`url=".../twopirllc/pandas-ta"`, description advertising "130+ indicators" for a fork shipping ~200.

`Backtesting/` installs with `pip install -U git+https://github.com/TolgaUyanik/PandasTa`. pip resolves
that to `pandas_ta==0.2.67b0`, finds it already satisfied, and **does not reinstall**. The 11
accessors, the `mcgd` pandas-2 fix, the three module-shadowing fixes, the `squeeze` offset fix and
the `fvg` repair do not reach the only consumer without `--force-reinstall`.

**Fix:** bump to a fork-distinct version, correct author/url/download_url/description, add
`python_requires`, drop the bogus `package_data`, and swap `distutils` (gone in 3.12) for
`setuptools`.

---

## MAJOR

- **`tests/test_pine_coverage_csv.py:12`** — the guard module's own docstring quotes a stale split
  (`60/18/13/9/4/2/1/1`; actual `55/18/16/9/4/2/2/1`, and the quoted figures sum to 108 against 107
  rows). The file's own text names its docstring as one of the three places the number went stale,
  and the guard reads only `TODO.md`. Round 8 fixed the instances and left the class open **inside
  the test written to close it**. → make the guard iterate `TODO.md`, `03-PINEBI.md` and `__file__`,
  and delete the hand-typed split.
- **`CLAUDE.md:18`** — "1250 pass, 21 skip, ~2min"; measured 1,252 and ~4min. The house rule that
  every count must correspond to a run, broken in the house rules. → stop quoting the count.
- **`setup.py`** — see CRITICAL 4.

## MINOR

- **README indicator arithmetic doesn't close** — headline 199/201, per-category headers sum to 200
  (`performance (4)` includes `drawdown`, which `Category` excludes), and three items sit outside
  `Category` (`drawdown`, `vp`, `ma`) making 202 callable. `CLAUDE.md:8` independently says 201.
  → pick one definition and have the dictionary generator emit all three counts.
- **`_pine.py:32-40` na-policy table contradicts itself** — the "unverified" row lists three items
  while the row below adds a fourth (`ta.max`), and the "NaN is FALSE" row omits
  `pivot_point_levels`'s `anchor`, which is routed through `_as_condition`. → close it with a test
  that walks `__all__` for condition-shaped parameters.
- **`_pine.py:68-75`** — `_length` promises to reject typos, then `int()` silently truncates:
  `highest(s, 2.7)` → `HIGHEST_2`. → raise on non-integral.
- **`tests/test_pine_coverage_csv.py:222`** — `NOT_NAME_KEYED = {"SHAPE_UNUSED"}` excludes an
  attribute that does not exist: a pre-opened hole in the reachability guard.
- **Mutant tests cover one of two patched sites** — `test_pivot_mutant_backdating_is_caught` patches
  both pivot writes and only compares `pivothigh`; `test_fvg.py` mutates `in_fvg_bull` only.

## NIT

- **No CI.** `.github/` has three issue templates and no workflow, so nothing enforces the green
  suite. The `Makefile` still drives `unittest` over upstream globs that match nothing here, and
  `make init` wants a `requirements.txt` that `.gitignore` deliberately ignores.

---

## What the reviewer confirmed as sound

Stated once, because it is load-bearing for the commit decision:

- both generators reproduce **byte-identical** output (107-row CSV, 416-line dictionary);
- the suite is green at **1,252 / 21**, and the 21 skips are the upstream correlation suite;
- the mutant tests read the module source, assert the patch-site count so a refactor fails loudly,
  `exec` in memory and compare — "better than most of what passes for a causality guard";
- `stc`, `dm` and `adx` are correctly classified and could not be broken.

## Recommended order

1. `.gitignore` (blocker 1) — one line.
2. README `fvg` paragraph (blocker 2) — one paragraph, plus the grep sweep.
3. Licence posture (blocker 3) — `git rm -r --cached docs/pine`; also fixes three false claims.
4. `setup.py` (blocker 4) — without it the fixes do not ship.
5. Re-run both generators and the suite, **then** commit.
