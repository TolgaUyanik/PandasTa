# -*- coding: utf-8 -*-
from .alma import alma
from .bpress import bpress
from .dema import dema
from .ema import ema
from .ema_align import ema_align
from .fwma import fwma
from .hilo import hilo
from .hl2 import hl2
from .hlc3 import hlc3
from .hma import hma
from .hwma import hwma
from .jma import jma
from .kama import kama
from .ichimoku import ichimoku
from .ichimoku_ml import ichimoku_ml
from .linreg import linreg
from .linreg_channel import linreg_channel
from .ma import ma
# iama imports pandas_ta.volatility.atr, whose own top-level `from
# pandas_ta.overlap import ma` resolves against THIS partially-built
# module while overlap/__init__.py is still executing (a circular
# self-import) -- placing this line before `ma` is bound above makes
# Python fall back to binding the SUBMODULE `pandas_ta.overlap.ma`
# instead of the function, breaking every caller of atr() fork-wide with
# `TypeError: 'module' object is not callable` (verified: moving this
# import above the `from .ma import ma` line reproduces the break across
# the whole suite, not just iama's own tests). This is a PRE-EXISTING
# fork hazard, not iama-specific: independently reproduced by hoisting
# the unrelated, already-present `.supertrend` import above `.ma`
# instead, with iama nowhere involved (TVPTA-6 candidate-12 Fletcher
# review, 2026-08-14) -- any overlap-package module that transitively
# imports atr()/ma() would trip this if placed above line 19.
# Must stay below the `ma` import.
from .iama import iama
from .ma_disparity import ma_disparity
from .mcgd import mcgd
from .midpoint import midpoint
from .mmar import mmar
from .midprice import midprice
from .nadaraya_watson_envelope import nadaraya_watson_envelope
from .ohlc4 import ohlc4
from .pwma import pwma
from .rainbow import rainbow
from .rma import rma
from .sinwma import sinwma
from .sma import sma
from .ssf import ssf
from .supertrend import supertrend
from .swma import swma
from .t3 import t3
from .tema import tema
from .trima import trima
from .vidya import vidya
from .vwap import vwap
from .vwma import vwma
from .wcp import wcp
from .wma import wma
from .zlma import zlma