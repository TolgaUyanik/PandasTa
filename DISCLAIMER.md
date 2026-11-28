# Disclaimer

**Not financial advice.** This repository is software that computes technical-analysis
indicators and machine-learning features from price data. Nothing in it — the code, its
outputs, the documentation, the measurements under `docs/` or any example — is investment,
financial, trading, tax or legal advice, or a recommendation to buy, sell or hold any security,
currency, commodity or other instrument. It is not tailored to anyone's situation.

**Yatırım tavsiyesi değildir.** Bu depodaki yazılım, çıktıları ve belgeler yatırım danışmanlığı
kapsamında değildir; herhangi bir varlığın alım, satım veya elde tutulmasına yönelik bir öneri
niteliği taşımaz. Yatırım kararlarınızı kendi değerlendirmenizle veya yetkili bir kuruluştan
alacağınız danışmanlıkla veriniz. Yatırım danışmanlığı hizmeti, yetkili kuruluşlarla
imzalanacak yatırım danışmanlığı sözleşmesi çerçevesinde sunulur. (The English text governs.)

**No warranty.** The software is provided "as is", without warranty of any kind, as stated in
the [MIT License](LICENSE) and, for the MPL-2.0 files listed in [NOTICE](NOTICE), the Mozilla
Public License 2.0. NOTICE also lists files whose source licence is not yet verified.
Indicators may contain errors, may differ from the sources they implement, and may change
between versions; a column's values can change under the same name when a bug is fixed. Check
every result yourself before relying on it.

**Trading involves risk.** Trading and investing can lose part or all of the money put in. Past
behaviour of an indicator, a feature or a backtest does not predict future results. Any number
in this repository about how a column behaved on historical data is a research measurement of
that column, not a claim that it is profitable or predictive.

**Data.** The library computes on the data you give it. It does not check that data for errors,
splits, gaps or survivorship bias; results are only as good as the input. Optional download
helpers use third-party services whose terms and accuracy are their own.

**Written largely by AI agents.** Most of this code, its tests and its documentation were
written by AI coding agents and checked by automated tests and by an automated reviewer, with a
human owner deciding what is built; changes merge on automated checks, not on a human code
review. That process reduces mistakes; it does not remove them, and it is not a warranty.

**Sources and licences.** Indicators are implemented from published formulas, papers, books,
open-source scripts and public descriptions; each module names its source. Where a module
translates code that is MPL-2.0 (by the script's header or, where the script states none, by
the owner's stated assumption), that file stays under MPL-2.0 and is listed in
[NOTICE](NOTICE). Code published under other licences (for example GPL) was used, where at all,
only as a reference or as an external test oracle, not copied; modules whose source licence did
not fit this repository were removed. If you believe a file uses your work without the right
licence or credit, open an issue and it will be fixed or removed.

**Your responsibility.** You decide how to use this software and are responsible for those
decisions and their consequences, including compliance with the laws and regulations that apply
to you. To the extent permitted by law, the authors and contributors accept no liability for
any loss or damage arising from its use.

**No affiliation.** This is an independent fork of pandas-ta (twopirllc,
[PyPI](https://pypi.org/project/pandas-ta/)). Names of indicators, platforms, libraries and
data providers (for example TradingView, TA-Lib, catch22) are used only to identify the source
of a formula and may be trademarks of their owners; their use does not imply affiliation with
or endorsement by them.
