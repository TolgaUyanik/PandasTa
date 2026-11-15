# Run manifest — `/brutally-honest-review --auto` (Mode C)

**Date:** 2026-11-15 · **Run id:** `tf-spec-entropy-64` · **Branch:**
`issue-111-tf-spec-entropy-64`

## Invocation, verbatim

```
/brutally-honest-review --auto "TF-SPEC-ENTROPY-64: port the indicator of
issue #111 through Gates A-D, the wiring, the tests and
docs/<Name>Measured.md, per the issue and the rules in your system prompt
(spectral entropy of daily returns (64). Source: TSFEL (BSD-3-Clause) —
`features.py spectral_entropy: normalised entropy of the power spectrum`.).
Gate E and the suites are run by the launcher afterwards."
```

## Phase 1 — Select

One task, given free-form (not a TODO tag, so no lookup).

| id | scope | source |
|---|---|---|
| `tf-spec-entropy-64` | Port TSFEL's `spectral_entropy` over 64 daily returns as `pandas_ta/statistics/tf_spec_entropy_64.py`; Gates A–D; the five wiring touch points; `tests/test_tf_spec_entropy_64.py`; `docs/TfSpecEntropy64Measured.md`. Gate E owed to the launcher. | the invocation above, plus PandasTa issue #111 as quoted in the session's system prompt |

Run folder: `docs/reviews/auto-2026-11-15-tf-spec-entropy-64/`.

**No pre-gate.** Mode C resolves task references, not a plan carrying
load-bearing reasoning; the skill's absence of a Mode C pre-gate is
deliberate. `--refute` was not passed.

## Phase 2 — Clarify

`AskUserQuestion` is unavailable in this headless session, and the system
prompt's rule is explicit: *"Where a skill says to ask, take the most
conservative reading (the smaller scope) and log it as an ASSUMPTION."* So no
questions were asked; the gaps are recorded as assumptions instead.

### ASSUMPTIONS

1. **The port follows the screen PROTOTYPE's expression, not a literal reading
   of the one-line source quote.** The issue calls the prototype "scale-free
   form: DC removed" and Gate E's 0.0284 was measured on it, so matching it bit
   for bit is the smaller-scope reading; a literal reading would be a column
   the screen never measured. The alternative is priced rather than waved away
   — §A4 of `docs/TfSpecEntropy64Measured.md` builds the DC-keeping,
   non-zero-normalised variant and measures it at max |d| 0.0088, Spearman
   0.9865 .. 1.0000.
2. **Gate A does not read TSFEL's source.** TSFEL is not installed, `docs/pine/`
   does not carry it, and web access is unavailable, so Gate A checks the
   QUANTITY the issue's one-line quote names, spelled three ways (the retyped
   prototype, a scalar-loop DFT, and numpy's complex `fft`); §A4's DC-keeping
   variant is the reading this port did NOT take, not a fourth oracle.
   `test_the_source_library_is_not_readable_here` asserts `import tsfel` raises,
   so the limitation fails loudly if that ever changes.
3. **Category `statistics`,** matching the sibling TSFEL port `tf_centroid_20`
   and every other window-statistic port of this series.
4. **Column name `TFSPECENT_64`,** following `tf_centroid_20` → `TFCENTROID_20`.
5. **Two divergences from the prototype are deliberate** (undefined windows are
   NaN, not the prototype's -0.0). This is the fork's existing convention
   (`tf_centroid_20`, `maxvol_adv`, `entropy`) and the smaller-scope reading of
   "ship a feature": a -0.0 entropy for a window that has no spectrum is a
   value a model would read as real.
6. **No new public parameter.** `CHUNK_VALUES` is a module constant, not a
   keyword, so the call surface is `(close, length, offset, **kwargs)` like
   every sibling.

## Phase 3 — Execution map

| task | lane | why |
|---|---|---|
| `tf-spec-entropy-64` | main thread | One task, one coherent scope; the measurement script, the module and the test module are written against each other, and the numbers in the docs come from runs made between the edits. Nothing to parallelise and no second lane to isolate. |

## Phase 4/5

Owed at the time this manifest was written, and written at the end of the
loop: `01-tf-spec-entropy-64.md` (the task log, every review round verbatim,
and the fixes applied) and `99-summary.md` (the result table). Round 1 caught
this sentence asserting in the present tense that both already existed — the
repo's named dominant defect, inside the folder whose job is the audit trail.
