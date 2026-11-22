# C22-ACF-FIRST-MIN — auto run manifest

Invocation: `/brutally-honest-review --auto "C22-ACF-FIRST-MIN: port the
indicator of issue #131 through Gates A-D, the wiring, the tests and
docs/<Name>Measured.md, per the issue and the rules in your system prompt
(catch22 first minimum of the return ACF (100)...). Gate E and the whole
suites are run by the launcher afterwards."`

Mode: **C, batch task execution**, one task (free-form task text, taken as
given per the skill's Phase 1 rule).

## Phase 1 — select

One task: port PandasTa issue #131 (`c22_acf_first_min`, catch22
`CO_FirstMin_ac`) through Gates A-D, the five wiring points, the test
module and the receipt, with Gate E and the whole suites left to the
launcher per the system prompt's override rules.

## Phase 2 — clarify

The issue text and the system prompt's override rules fully specify scope,
the test subset to run, and the Gate E deferral. No gap needed a question.
One judgment call, logged as an ASSUMPTION since `AskUserQuestion` is
unavailable in this headless session:

* **ASSUMPTION**: `CO_FirstMin_ac`'s exact numeric convention (the
  autocorrelation's divisor, the strictness of "local minimum", the
  fallback value when none is found) was not read from the GPL-3.0
  reference's source — the issue and this repo's `CLAUDE.md` forbid
  that — but derived from the public mathematical definition ("the first
  local minimum of the series' own autocorrelation function") and from
  this fork's own `firstzero_ac` sibling, which reads the identical
  window with a closely related scan. The choice was then CHECKED (never
  copied) against the installed `pycatch22` package as a measurement-only
  black box, the same practice `c22_periodicity` and `c22_ami2` already
  use for their own Gate A. Result: bit-equal on every one of 8,400
  sampled windows (`docs/C22AcfFirstMinMeasured.md` §P) — the convention
  was not a free choice that happened to work, it reproduces the
  reference exactly.

## Phase 3 — plan execution

Single task, sequential dependency on nothing else touched this session:
**main thread**, no parallel lane, no worktree isolation needed.

## Phase 4 — execute + gate

Implementation done on the main thread:

* `pandas_ta/statistics/c22_acf_first_min.py` (new)
* `pandas_ta/statistics/__init__.py`, `pandas_ta/__init__.py`,
  `pandas_ta/core.py` (wiring)
* `tests/test_c22_acf_first_min.py` (new, 31 tests)
* `docs/measure_c22_acf_first_min.py`, `docs/measure_c22_acf_first_min_cpu.py` (new)
* `docs/C22AcfFirstMinMeasured.md` (new, the receipt)
* `README.md`, `docs/IndicatorDictionary.md`, `docs/MLCompanionContract.md`,
  `tests/test_altport2_ports.py` (counts)

Gate report: `01-c22-acf-first-min.md` in this folder.

## Phase 5 — report

`99-summary.md` in this folder.
