# Run summary — TF-MEDIAN-ABSDIFF-20 (issue #118)

| task | status | rounds | files touched | follow-ups |
|---|---|---|---|---|
| TF-MEDIAN-ABSDIFF-20 (port `tf_median_absdiff_20`, issue #118) | PASS | 1 | `pandas_ta/volatility/tf_median_absdiff_20.py`, `tests/test_tf_median_absdiff_20.py`, `docs/TfMedianAbsdiff20Measured.md`, `docs/measure_tf_median_absdiff_20.py`, `pandas_ta/__init__.py`, `pandas_ta/core.py`, `pandas_ta/volatility/__init__.py`, `README.md`, `docs/IndicatorDictionary.md`, `docs/MLCompanionContract.md`, `tests/test_altport2_ports.py` | Gate E (owed, run by the issue-solver launcher); real-data Gate C counts (same Gate E run); a pre-existing, unrelated `strategy()`/`Category`-mutation bug disclosed in `docs/TfMedianAbsdiff20Measured.md` but not fixed (out of scope) |

Ported TSFEL's `median_abs_diff` formula to a 20-bar scale-free rolling median of absolute
bar-to-bar log returns (`MEDABSDIFF_20`, category `volatility`). Gates A, B, D cleared with
independent-loop and future-perturbation mutant tests; C is synthetic-only; E is explicitly out
of scope for this session per the task's own instructions ("Gate E and the suites are run by the
launcher afterwards") and is recorded as pending in `docs/TfMedianAbsdiff20Measured.md`. Full
suite at hand-off: 3 failed (all pre-existing or an expected consequence of Gate E being pending
— see `01-tf-median-absdiff-20.md`), 3272 passed, 83 skipped.

Round 1 found one real (MINOR) defect — a measured number cited to a git history that doesn't
exist, for a discarded (non-shipped) formula variant — and verified every other specific claim in
the port by independently re-running it: the mutant leak counts, the scale-invariance residuals,
the wiring, the README's regenerated counts, and the full-suite failure list all reproduced
exactly as documented. The one finding was fixed (made reproducible via a script block) even
though PASS did not require it, since an unverifiable number is this project's named dominant
defect regardless of severity.
