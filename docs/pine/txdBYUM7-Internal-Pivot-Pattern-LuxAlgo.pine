// This work is licensed under a Attribution-NonCommercial-ShareAlike 4.0 International (CC BY-NC-SA 4.0) https://creativecommons.org/licenses/by-nc-sa/4.0/
// © LuxAlgo

//@version=6
indicator('Internal Pivot Pattern [LuxAlgo]', 'LuxAlgo - Internal Pivot Pattern', overlay = true, max_lines_count = 500)
//---------------------------------------------------------------------------------------------------------------------}
//CONSTANTS & STRINGS & INPUTS
//---------------------------------------------------------------------------------------------------------------------{
GREEN               = #089981
RED                 = #F23645
BLUE                = #2962FF
ORANGE              = #FF5D00

EM_SPACE            = ' '
FOUR_PER_EM_SPACE   = ' '
SIX_PER_EM_SPACE    = ' '

dotLowSpacing       = SIX_PER_EM_SPACE
linesSpacing        = EM_SPACE + FOUR_PER_EM_SPACE + FOUR_PER_EM_SPACE
barHighSpacing      = EM_SPACE + FOUR_PER_EM_SPACE

STYLE_GROUP         = 'Style'

timeframeInput      = input.timeframe('1',  'Timeframe')
dashboardInput      = input.bool(     true,                 'Accuracy Dashboard')

dotLowEnabledInput  = input.bool(     true,                 '',                                 group = STYLE_GROUP, inline = 'pivotLow')
dotLowColorInput    = input(          GREEN,                'Internal Pivot Low'+dotLowSpacing, group = STYLE_GROUP, inline = 'pivotLow')

dotHighEnabledInput = input.bool(     true,                 '',                                 group = STYLE_GROUP, inline = 'pivotHigh')
dotHighColorInput   = input(          RED,                  'Internal Pivot High',              group = STYLE_GROUP, inline = 'pivotHigh')

linesEnabledInput   = input.bool(     true,                 '',                                 group = STYLE_GROUP, inline = 'lines')
lineLowColorInput   = input(          GREEN,                'Zig-Zag'+linesSpacing,             group = STYLE_GROUP, inline = 'lines')
lineHighColorInput  = input(          RED,                  '',                                 group = STYLE_GROUP, inline = 'lines')

barsEnabledInput    = input.bool(     true,                 '',                                 group = STYLE_GROUP, inline = 'bars')
barLowColorInput    = input(          color.new(BLUE,50),   'Candles'+barHighSpacing,           group = STYLE_GROUP, inline = 'bars')
barHighColorInput   = input(          color.new(ORANGE,50), '',                                 group = STYLE_GROUP, inline = 'bars')

//---------------------------------------------------------------------------------------------------------------------}
//DATA STRUCTURES & VARIABLES
//---------------------------------------------------------------------------------------------------------------------{
var int   os          = na
var int   x1          = na
var color css         = na
var float y1          = na
var float prev_close  = na

var int acc_ph        = 0
var int acc_pl        = 0
var int tot_ph        = 0
var int tot_pl        = 0

//---------------------------------------------------------------------------------------------------------------------}
//USER-DEFINED FUNCTIONS
//---------------------------------------------------------------------------------------------------------------------{
high_low() => [high, low]

dashboard() =>
    var table tb = table.new(position.top_right,2,2
      , bgcolor      = #1e222d
      , border_color = #373a46
      , border_width = 1
      , frame_color  = #373a46
      , frame_width  = 1)
    
    if barstate.isfirst
        table.cell(tb, 0, 0, 'PH Accuracy'
          , text_color = color.gray)
          
        table.cell(tb, 1, 0, 'PL Accuracy'
          , text_color = color.gray)

    if barstate.islast
        per_ph = acc_ph/tot_ph*100
        per_pl = acc_pl/tot_pl*100
        
        table.cell(tb, 0, 1
          , text        = str.tostring(per_ph,'#.##') + '%'
          , text_color  = per_ph > 50 ? GREEN : RED
          , bgcolor     = color.new(per_ph > 50 ? GREEN : RED,80)
          , text_halign = text.align_left)
        
        table.cell(tb, 1, 1
          , text        = str.tostring(per_pl,'#.##') + '%'
          , text_color  = per_pl > 50 ? GREEN : RED
          , bgcolor     = color.new(per_pl > 50 ? GREEN : RED,80)
          , text_halign = text.align_left)

//---------------------------------------------------------------------------------------------------------------------}
//MUTABLE VARIABLES & EXECUTION
//---------------------------------------------------------------------------------------------------------------------{
n       = bar_index
[h, l]  = request.security_lower_tf(syminfo.tickerid, timeframeInput, high_low())
mid     = math.ceil(array.size(h)/2)
buy     = array.indexof(l,low)  == mid
sell    = array.indexof(h,high) == mid

if buy
    tot_pl += 1

    if os == 0
        css    := close < prev_close ? lineLowColorInput : lineHighColorInput
        acc_ph += close < prev_close ? 1 : 0
    else
        css    := close > prev_close ? lineLowColorInput : lineHighColorInput
        acc_pl += close > prev_close ? 1 : 0

    if linesEnabledInput    
        line.new(x1,y1,n,low, color = css, style = line.style_dashed)
      
    prev_close  := close
    y1          := low
    x1          := n

if sell
    tot_ph += 1
    
    if os == 0
        css    := close < prev_close ? lineLowColorInput : lineHighColorInput
        acc_ph += close < prev_close ? 1 : 0
    else 
        css    := close > prev_close ? lineLowColorInput : lineHighColorInput
        acc_pl += close > prev_close ? 1 : 0

    if linesEnabledInput     
        line.new(x1,y1,n,high, color = css, style = line.style_dashed)
      
    prev_close  := close
    y1          := high
    x1          := n

os := buy ? 1 : sell ? 0 : os

if dashboardInput
    dashboard()

plot(buy and dotLowEnabledInput ? low : na,"Internal PL"
  , color     = dotLowColorInput
  , linewidth = 2
  , style     = plot.style_circles)

plot(sell and dotHighEnabledInput ? high : na,"Internal PH"
  , color     = dotHighColorInput
  , linewidth = 2
  , style     = plot.style_circles)

barcolor(barsEnabledInput ? (os == 1 ? barLowColorInput : barHighColorInput) : na )

//---------------------------------------------------------------------------------------------------------------------}