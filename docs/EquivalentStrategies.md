# Equivalent strategies

Candidates that turned out to restate, or nearly restate, something the package already ships. Check this list
before porting a new candidate: if it is here, the work is already done.

| Strategy to be implemented | Existing equivalent strategy | Related GitHub issue |
|---|---|---|
| `b2_kvo_hlc3_34_55` — Klinger-style volume force oscillator, `VF = ±V` by hlc3 sign, `EMA34(VF) − EMA55(VF)` | `kvo` (`KVO_34_55_13`) — same formula; the candidate only adds a `/ EMA55(V)` scale fix. Per-frame max median ρ 0.8986 vs `KVO_34_55_13` (stage-2 fork overlap on 12 frames, not Gate E; just under the 0.90 line); also overlaps the MFI family (`MFI_Pctl` 0.7989) | [#192](https://github.com/TolgaUyanik/PandasTa/issues/192) |
| `b2_close_beyond_prev` — +1 if `close > high[t-1]`, −1 if `close < low[t-1]`, else 0 | `priorday_fib` — exactly `(PDFIB_HIGH > 0) − (PDFIB_LOW < 0)`; 0 mismatches on 36 synthetic tick-rounded frames (179,964 bars, 7,635 ties) | [#193](https://github.com/TolgaUyanik/PandasTa/issues/193) |
