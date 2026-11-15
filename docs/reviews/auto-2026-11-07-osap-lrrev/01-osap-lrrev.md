# Task: osap-lrrev — round log

## Round 1

Implementation: ported `osap_lrrev` (LRREV, De Bondt-Thaler 1985 long-run reversal,
OSAP `LRreversal`) through Gates A-D, all five wiring touch points, `tests/test_osap_lrrev.py`
(12 tests), `docs/OsapLrrevMeasured.md`, `docs/measure_osap_lrrev.py`. Prose and test
shape reused (and re-measured, not copied) from a prior same-issue attempt on commit
`45aa9ff` that was reachable only from `solver-backup/issue-35-osap-lrrev` (an older
`dev` tip) — see `00-manifest.md`.

### Reviewer verdict (round 1)

```
VERDICT: REVISE
FINDINGS:
  - severity: CRITICAL
    location: docs/OsapLrrevMeasured.md:34-36
    problem:  Attributed the quote "Gate A starts from the source formula, not the
      prototype" to CLAUDE.md. grep confirms zero hits in CLAUDE.md for that phrase --
      a fabricated citation. The identical defect was already found and fixed, in this
      same session's sibling port (docs/reviews/auto-2026-11-02-osap-mrrev/01-osap-mrrev.md
      round 2), by re-attributing the quote to the issue text instead. This session
      reused the pre-fix prose verbatim.
    fix:      Attribute the quote to "the issue's own instruction" (it IS present
      verbatim in issue #35's "Gates owed" paragraph), never to CLAUDE.md.
  - severity: MAJOR
    location: pandas_ta/momentum/osap_lrrev.py docstring ASSUMPTION §2; docs/OsapLrrevMeasured.md Gate A §2
    problem:  Asserted as fact "the OSAP paper's own month-indexing convention where
      't-13' is the most recent month" -- an unverifiable claim about an unreachable
      primary source, already flagged and fixed the same way in osap_mrrev's round 1
      review, whose fixed wording cites real, checkable cross-candidate arithmetic in
      the prototype instead (and already names osap_lrrev as one of the two
      corroborating siblings).
    fix:      Drop the "OSAP's own convention" guess; cite the cross-candidate pattern
      already written down in osap_mrrev.py / docs/OsapMrrevMeasured.md (osap_intmom and
      osap_mrrev share the identical far=literal-month-count/near=one-month-less
      arithmetic as osap_lrrev).
  - severity: MINOR
    location: pandas_ta/momentum/osap_lrrev.py docstring, opening paragraph
    problem:  Opening paragraph stated "months t-36 through t-13" unattributed, reading
      as a SignalDoc fact before the Gate A caveat several lines down.
    fix:      Attribute to the issue's restatement in the same sentence, mirroring
      osap_mrrev.py's fixed opening paragraph.
  - severity: NIT
    location: pandas_ta/momentum/osap_lrrev.py docstring / Measured.md
    problem:  No one-sentence note that the ratio is a price return (Close only), not a
      total return.
    fix:      Add one sentence noting this, consistent with the issue's own close-only
      prototype.
SUMMARY: Math, causality mutant, scale-free tests, and all five wiring touch points
clean; every number in the Measured.md reproduces exactly on a live run. The defect was
prose: a fabricated CLAUDE.md citation and an unverifiable "OSAP's own convention" claim,
both already found and fixed once in this session's own sibling port (osap_mrrev) sitting
in the same reviews directory -- reusing the pre-fix prototype commit instead of the
post-fix sibling pattern was an avoidable regression.
```

### Fixes applied (round 1 -> round 2)

- `pandas_ta/momentum/osap_lrrev.py`: rewrote the module docstring's opening paragraph and
  ASSUMPTION §2 to mirror `osap_mrrev.py`'s already-fixed wording — attributed "months
  t-36 through t-13" to the issue's restatement in the opening sentence; replaced the
  "OSAP's own month-indexing convention" guess with the real, checkable cross-candidate
  arithmetic (`osap_intmom`, `osap_mrrev` share the identical far=literal-month-count /
  near=one-month-less pattern); added the price-return-vs-total-return note.
- `docs/OsapLrrevMeasured.md`: same rewrite applied to the summary paragraph and Gate A
  §2; the CLAUDE.md citation is now attributed to "the issue's own instruction" (verified
  present verbatim in issue #35's "Gates owed" paragraph).
- Re-ran `tests/test_osap_lrrev.py` (12/12 still passing — docstring-only changes).

## Round 2

### Reviewer verdict (round 2)

```
VERDICT: PASS
FINDINGS:
  - severity: MINOR
    location: pandas_ta/momentum/osap_lrrev.py:68-87 (ASSUMPTION §2) vs docs/OsapLrrevMeasured.md:31-55 (Gate A §2)
    problem:  The module docstring's ASSUMPTION §2 carried only the two matching
      cross-candidate rows (osap_intmom, osap_mrrev) and omitted Measured.md's extra
      sentence flagging osap_mom12_1/osap_mom6_1 as a related-but-distinct convention --
      the two "same story" documents disclosed different amounts of the picture.
    fix:      Append the same "two further rows ... related but distinct convention"
      sentence to osap_lrrev.py's ASSUMPTION §2.
SUMMARY: All four round-1 findings (CRITICAL fabricated CLAUDE.md citation, MAJOR
unverifiable OSAP-convention claim, MINOR unattributed opening paragraph, NIT missing
price-vs-total-return note) verified genuinely fixed, with the cross-candidate arithmetic
checked by hand against the sibling modules' actual near_length/far_length and found
correct. git status showed only the claimed docstring/doc scope touched. One new MINOR
(a completeness gap between the two Gate A disclosures) -- not a fabrication, not an
overclaim.
```

### Fix applied (round 2)

- `pandas_ta/momentum/osap_lrrev.py`: appended the `osap_mom12_1`/`osap_mom6_1`
  "related but distinct convention" sentence to ASSUMPTION §2, matching
  `docs/OsapLrrevMeasured.md`'s Gate A §2 exactly (mirrors `osap_mrrev.py`'s own
  wording for the same disclosure).
- Re-ran `tests/test_osap_lrrev.py`, `tests/test_altport2_ports.py`,
  `tests/test_readme_counts.py`, `tests/test_wiring_accessors.py`,
  `tests/test_ml_companions.py`: 118 passed, 3 skipped.

**Task status: PASS, round 2. Done.**
