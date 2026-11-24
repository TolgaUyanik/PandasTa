# Task log — level_shift_size (issue #163)

## Implementation summary

- `pandas_ta/statistics/level_shift_size.py` — new module. Kats tsfeatures'
  `get_level_shift_features` max-of-diffs, on a rolling `length`-bar (default 100) window
  of log close, sliding 20-bar means (`WINDOW_SIZE`, imported from the sibling
  `level_shift_idx` rather than redefined). Fed `log(close / the window's own first
  close)` rather than plain `log(close)`, so the output is bit-identical under a
  power-of-two price rescale (the ratio-to-first-bar device `stl_spikiness` /
  `stl_seasonal_strength` use) — needed because this column's output is a continuous
  value, unlike `level_shift_idx`'s rounded-before-`argmax` discrete index.
  `MIN_LENGTH = WINDOW_SIZE + 1` (21).
- `tests/test_level_shift_size.py` — 30 tests: correctness vs an independent plain-Python
  oracle and a closed-form single-step construction, causality (future-blindness +
  mutant + bad-tick blanking), scale-free (x8/x64 bit-identical, x10/x3.7 tolerance,
  fires-and-not-constant), edge cases (flat/jitter, bad input, length floor, chunk
  boundaries), wiring (Category + accessor).
- `docs/measure_level_shift_size.py`, `docs/measure_level_shift_size_cpu.py` — measurement
  and CPU-feature-restricted test-runner scripts, mirroring the sibling's.
- `docs/LevelShiftSizeMeasured.md` — the receipt. Gate E recorded as pending.
- Wiring: `pandas_ta/statistics/__init__.py` export, `pandas_ta/__init__.py` Category
  entry, `pandas_ta/core.py` accessor — all alphabetically between `level_shift_idx` and
  `lot_zeroret_60`.
- Counters: `tests/test_altport2_ports.py` CATEGORY_TOTAL 391→392; README.md 391→392
  registered / 399→400 callable / statistics (79)→(80); `docs/MLCompanionContract.md`
  736→737 tagged / 368→369 `SF` (new entry prepended); `docs/IndicatorDictionary.md`
  regenerated.

## Review round 1

Dispatched one Fletcher reviewer (`Explore`, read-only) against the full new+modified
file set, instructed that Gate E and whole-suite runs are out of scope this session and
that the ledger-row test failure is expected.

```
VERDICT: PASS
FINDINGS:
  (none)
SUMMARY: The port is clean on every axis checked. Gate A's cumsum-on-ratio vectorisation
algebraically matches the docstring's `Y = LN(close/close[win_start])`, `means[k]`,
`d[k] = ABS(diff)`, `MAX(d)` formula, and an independent plain-loop oracle plus a
hand-derived closed form (V/20) both match the module to ~1e-15, confirmed by actually
re-running `docs/measure_level_shift_size.py` and getting numbers matching the
Measured.md table almost exactly (minor machine-timing variance aside). The x8/x64
bit-identical claim is sound IEEE-754 reasoning (two numbers each exactly scaled by a
power-of-two have their ratio's correctly-rounded result unchanged), it is exercised by
`test_price_scale_is_bit_identical`/`test_price_scale_within_tolerance`, and the
measurement script reproduces the exact reported diffs (0.0 for x8/x64, 1.11e-16/8.33e-17
for x10/x3.7). The Gate B mutant (`length - 1` -> `length - 2`) is proven live and the
real module proven clean at five shift positions, same shape as the already-accepted
sibling. MIN_LENGTH=21 was checked by hand-tracing the cumsum arithmetic at length=21:
two means, one diff, division only by the constant WINDOW_SIZE (never by a diff count),
so the "divides by nothing" claim is correct and there is no index/divide-by-zero bug.
Wiring is complete and alphabetically consistent across all five touch points
(`pandas_ta/__init__.py` Category, `pandas_ta/core.py` accessor,
`pandas_ta/statistics/__init__.py` import, module, test file), all placed between
`level_shift_idx` and `lot_zeroret_60` as claimed. Counter arithmetic (391->392,
399->400, statistics 79->80, MLCompanionContract 736->737 tagged/368->369 SF) is
internally consistent across README.md, IndicatorDictionary.md, MLCompanionContract.md
and test_altport2_ports.py. The required Gate F command was re-run and produced exactly
1,544 passed, 7 skipped, 1 failed -- the expected, documented ledger-row failure --
matching the Measured.md claim verbatim, and the CPU-restricted variant reproduced the
claimed 30 passed. `git status`/`git diff --stat` confirm only the allowed files were
modified and only allowed new-file patterns were added; nothing out of scope was touched.
The one surface oddity -- the IndicatorDictionary.md row rendering
`max |mean(w) - mean(w+1)|` as `max /mean(w) - mean(w+1)/` -- is pre-existing generator
behavior (`docs/gen_indicator_dictionary.py`'s `desc()` replaces `|` with `/` to protect
the markdown table), reproduced identically on unrelated pre-existing rows (e.g. `wvma`),
so it is not a defect introduced by this port.
```

Status: **PASS**, round 1. No fixes required.
