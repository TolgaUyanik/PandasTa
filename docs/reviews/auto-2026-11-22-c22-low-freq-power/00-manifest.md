# Run manifest — C22-LOW-FREQ-POWER (issue #141)

Mode C (batch task execution), single task, no parallelism needed.

## Task

Port the catch22 feature `SP_Summaries_fft_area_5_1` (share of return power
in the lowest fifth of frequencies) as `pandas_ta/statistics/c22_low_freq_power.py`,
through Gates A-D, the five wiring touch points, its test module, and
`docs/C22LowFreqPowerMeasured.md`. Gate E and the whole suites are the
launcher's job, not this session's.

## Clarifications

None needed — the issue and `CLAUDE.md` fully specify scope, source, and
gate requirements. One design choice the source definition itself leaves
open (equal-frequency-width vs equal-bin-count band cutoff) was settled in
the module docstring with a derivation, not left as an open question.

## Execution map

Single task, main thread (no parallel lanes): the module, its wiring, its
test suite, the measurement harness, and the receipt all depend on the same
design decisions and had to be written in sequence.

## Review rounds

1. Round 1 (Explore, Fletcher persona): REVISE — one MAJOR, an unsupported
   ("can diverge at other lengths") and in fact false docstring claim about
   the equal-width vs equal-bin-count band-cutoff conventions.
2. Fix applied: corrected the docstring and `docs/C22LowFreqPowerMeasured.md`
   §0 with the actual derivation (the two conventions are provably identical
   for every length, since NBANDS=5 never divides a power of two), and added
   a computational test (`test_the_equal_width_cutoff_matches_the_equal_bin_count_cutoff`)
   that checks this across 15 lengths instead of leaving it as prose.
3. Round 2 (Explore, Fletcher persona): PASS, no findings.
