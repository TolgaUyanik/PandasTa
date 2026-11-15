# Run manifest — `/brutally-honest-review --auto` (Mode C)

**Date:** 2026-11-15 · **Run id:** `tf-dfa-100` · **Branch:**
`issue-112-tf-dfa-100`

## Invocation, verbatim

```
/brutally-honest-review --auto "TF-DFA-100: port the indicator of issue #112
through Gates A-D, the wiring, the tests and docs/<Name>Measured.md, per the
issue and the rules in your system prompt (detrended fluctuation analysis
exponent of returns (100). Source: TSFEL (BSD-3-Clause) — `features.py
dfa`.). Gate E and the suites are run by the launcher afterwards."
```

## Phase 1 — Select

One task, given free-form (not a TODO tag, so no lookup).

| id | scope | source |
|---|---|---|
| `tf-dfa-100` | Port TSFEL's `dfa` over 100 daily returns as `pandas_ta/statistics/tf_dfa_100.py`; Gates A–D; the five wiring touch points; `tests/test_tf_dfa_100.py`; `docs/TfDfa100Measured.md`. Gate E owed to the launcher. | the invocation above, plus PandasTa issue #112 as quoted in the session's system prompt |

Run folder: `docs/reviews/auto-2026-11-15-tf-dfa-100/`.

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
   of the source line.** The issue calls the prototype the "scale-free form"
   and Gate E's 0.0979 was measured on it, so reproducing it is the
   smaller-scope reading. The alternative readings are priced rather than
   waved away: §A4 of `docs/TfDfa100Measured.md` builds the every-integer-box
   ladder and the standard forward+backward pass and measures both (ρ 0.89 ..
   0.98, apart by up to 0.92 on a bar).
2. **Gate A does not read TSFEL's source.** TSFEL is not installed,
   `docs/pine/` does not carry it, and web access is unavailable, so Gate A
   checks the QUANTITY the issue's two lines name — the DFA-1 exponent of
   Peng et al. 1994 — spelled three ways (the retyped prototype, a scalar
   loop over the normal equations, `np.polyfit`).
   `test_the_source_library_is_not_readable_here` asserts `import tsfel`
   raises, so the limitation fails loudly if that ever changes. In
   particular, TSFEL's **"plateau cut"** — which the issue mentions and the
   prototype does not implement — is NOT reproduced, and the doc says so
   rather than implying the ladder is TSFEL's own.
3. **ONE deliberate departure from the prototype: the final dot product is a
   weighted sum, not `@`.** This is the LARGER-scope choice of the two and it
   is taken anyway, so it is logged here as the exception. `@` on a
   `(rows, 5)` block is not stable under the block's shape (§Z2), this module
   chunks, and with `@` a bar's value would depend on which chunk it landed
   in. Measured honestly in both directions, and this ASSUMPTION took three
   review rounds to state correctly: the instability is NOT a clean
   threshold. On the default numpy dispatch `@` breaks only at one row per
   chunk; with AVX-512/AVX2/FMA3 off it breaks at 1, 2, 5, 7 and 8 rows per
   chunk and is stable at 6 and 9 (§Z sweeps both). So no "needs a window
   longer than N bars" rule holds -- the earlier `length > 2,097,152` (round
   1) and `length > 1,048,576` (round 3) were both algebra written ahead of
   the second dispatch's run. What IS true is that every swept row count up
   to 8 breaks on one dispatch, which needs a `length` above
   `CHUNK_VALUES // 9 = 233,016`, so the prototype is not wrong on any frame
   anyone will run; and the cost of the fix is that agreement with the
   prototype is 4.441e-16 rather than bit-exact. A mutant of the shipped file
   with `@` put back is asserted bit-equal to the prototype, which keeps the
   Gate A claim exact.
4. **Category `statistics`,** matching the sibling TSFEL ports
   `tf_centroid_20` and `tf_spec_entropy_64`.
5. **Column name `TFDFA_100`,** following `tf_centroid_20` → `TFCENTROID_20`.
6. **The box ladder is fixed at `(4, 5, 6, 8, 10)` and does not scale with
   `length`.** The issue quotes TSFEL as using boxes "up to n/10", which the
   ladder satisfies at the default 100 and not elsewhere; deriving a ladder
   from `length` would be a column the screen never measured.
   `MIN_LENGTH = 2 * max(BOXES) = 20`, so the largest box always has at least
   two boxes to average.
7. **No new public parameter.** `BOXES` and `CHUNK_VALUES` are module
   constants, not keywords, so the call surface stays
   `(close, length, offset, **kwargs)` like every sibling.

## Phase 3 — Execution map

| task | lane | why |
|---|---|---|
| `tf-dfa-100` | main thread | One task, one coherent scope; the measurement script, the module and the test module are written against each other, and every number in the docs comes from a run made between the edits. Nothing to parallelise and no second lane to isolate. |

## Phase 4/5

`01-tf-dfa-100.md` (the task log, every review round verbatim, and the fixes
applied) and `99-summary.md` (the result table) are written as the loop runs
and at its end respectively. Neither exists at the moment this sentence is
written.
