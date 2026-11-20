# Brutally Honest Review — c22_whiten_timescale port (issue #139), round 2

**Date:** 2026-11-21
**Target:** docs/C22WhitenTimescaleMeasured.md, docs/measure_c22_whiten_timescale.py, docs/measure_c22_whiten_timescale_cpu.py, pandas_ta/statistics/c22_whiten_timescale.py, tests/test_c22_whiten_timescale.py, docs/reviews/2026-11-20-c22-whiten-timescale-review.md
**Type:** code (with its measurement receipt)
**Verdict:** PASS

Reviewer: a fresh read-only `Explore` subagent (Mode A). It could not run code, so the quoted outputs were checked by reading the scripts, not by running them. Scope: verify that each round-1 CRITICAL/MAJOR is resolved (report `docs/reviews/2026-11-20-c22-whiten-timescale-review.md`), and review the files changed since then for new problems. Files unchanged since round 1 were not re-reviewed, and round-1 MINORs left unfixed were not re-raised.

## Round-1 MAJORs

- **(a) Gate A dispatch figures could not be reproduced — RESOLVED.** `docs/measure_c22_whiten_timescale_cpu.py` sets `NPY_DISABLE_CPU_FEATURES` before importing numpy. It prints numpy's version, the variable and the dispatch features still enabled, and exits if AVX2 or FMA3 survived. Section A1 prints each split's window, bar, module value, FFT value and exact value. Section X runs the module against the exact oracle on all 1,400 cosine windows and is in `SECTIONS`. The receipt, the module docstring and the test docstrings cite the command behind each dispatch-dependent number.
- **(b) The "12 other synthetic frames … 0.6304" sentence — RESOLVED.** It was deleted, and a grep finds no trace of it. §E3 now reports the largest per-frame |ρ| and the CLAUDE.md bands.

## Findings

### MINOR / NIT
- **MINOR — docs/measure_c22_whiten_timescale_cpu.py:2-5, :31, :55** — The docstring calls `"AVX2 FMA3"` "the setting the port's CPU check re-runs test modules under". Both sibling reproducers set and check four features, `"AVX512F AVX512_SKX AVX2 FMA3"`, and describe that list as the one issue-solver uses. On this machine the result is the same, because it has no AVX-512. On an AVX-512 host, though, the guard would pass while AVX-512 kernels still run, so the script would not reproduce the 8,399 / window 1122 split.
  - Fix: Set `NPY_DISABLE_CPU_FEATURES = "AVX512F AVX512_SKX AVX2 FMA3"`, check all four in the guard loop, and update the label in the receipt (:13, :79-82), the module docstring (:202) and the test docstrings (:13-14, :233-243, :263). Alternatively, drop the "the setting the port's CPU check …" wording and say the run was made on a host without AVX-512.
- **MINOR — tests/test_c22_whiten_timescale.py:13-14** — The "8,399 with AVX2 and FMA3 disabled" figure is credited to `docs/measure_c22_whiten_timescale_cpu.py` with no arguments. With no arguments that script runs the test module, which checks only every third window and never prints 8,399. Only `..._cpu.py A` prints it.
  - Fix: Cite `docs/measure_c22_whiten_timescale_cpu.py A` on line 14, and add "(section X of both scripts)" on line 18 after "under both dispatches".
- **NIT — tests/test_c22_whiten_timescale.py:5** — "Every number here was measured by `docs/measure_c22_whiten_timescale.py`" is no longer true: the disabled-dispatch figures come from the `_cpu.py` reproducer. The receipt's exception list was widened; the test header was not.
  - Fix: Append "; the disabled-dispatch figures by `docs/measure_c22_whiten_timescale_cpu.py A X`."
- **NIT — tests/test_c22_whiten_timescale.py:243** — The edit left a line of about 100 characters in a docstring wrapped at about 76.
  - Fix: Re-wrap lines 241-246 to the file's width.

## Summary

Both round-1 MAJORs are resolved: the dispatch figures are now printed by a committed reproducer, and the unreproducible 0.6304 sentence is gone. Every quoted output matches what the scripts would print. What is left is minor. The new reproducer drops the AVX-512 half of the four-feature list that both sibling scripts use, while still describing itself as the standard CPU check. That is harmless on this machine, which has no AVX-512, but it is the wrong description and not portable to an AVX-512 host. One test-docstring citation also points at the no-argument mode, which cannot print the figure credited to it. No CRITICAL or MAJOR remains, so the verdict is PASS. Fix the two MINORs before merge.
