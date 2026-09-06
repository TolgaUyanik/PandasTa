// This Pine Script® code is subject to the terms of the Mozilla Public License 2.0 at https://mozilla.org/MPL/2.0/
// © ChartPrime

//@version=6
indicator("RSI Shift Zone [ChartPrime]", overlay = false, max_labels_count = 500)


// --------------------------------------------------------------------------------------------------------------------}
// 📌 𝙐𝙎𝙀𝙍 𝙄𝙉𝙋𝙐𝙏𝙎
// --------------------------------------------------------------------------------------------------------------------{
rsi_len = input.int(14, "RSI length")
upper_level = input.int(70, "Upper RSI Level", minval = 50)
lower_level = input.int(30, "Lower RSI Level", maxval = 50)
min_channel_len = input.int(15, "Minimal bars length of the channel")

display_rsi_val = input.bool(false, "Display RSI Values at the Zones")

upper_col = input.color(#21c997, "↑", inline = "colors")
lower_col = input.color(#cc24e2, "↓", inline = "colors")

var start = int(na)
var trigger = false
var float upper = na 
var float lower = na
var channel_color = color(na)
color bar_color = na



// --------------------------------------------------------------------------------------------------------------------}
// 📌 𝙄𝙉𝘿𝙄𝘾𝘼𝙏𝙊𝙍 𝘾𝘼𝙇𝘾𝙐𝙇𝘼𝙏𝙄𝙊𝙉𝙎
// --------------------------------------------------------------------------------------------------------------------{

rsi = ta.rsi(close, rsi_len)

channel_upper = ta.crossover(rsi, 70) and not trigger 
channel_lower = ta.crossunder(rsi, 30) and not trigger 

rsi_color = color.from_gradient(rsi, 30, 70, lower_col, upper_col)

if channel_upper
    label.new(bar_index, rsi, style = label.style_circle, size = size.tiny, color = color.new(rsi_color, 45))
    label.new(bar_index, rsi, str.tostring(upper_level), style = label.style_label_center, size = size.small, color = color.new(rsi_color, 100))

    start := bar_index
    trigger := true
    upper := high
    lower := low
    channel_color := rsi_color
    bar_color := rsi_color

    if display_rsi_val
        label.new(bar_index, hl2, "RSI: " + str.tostring(upper_level), style = label.style_label_right, color = color.new(rsi_color, 100), textcolor = chart.fg_color, force_overlay = true)

if channel_lower
    label.new(bar_index, rsi, style = label.style_circle, size = size.tiny, color = color.new(rsi_color, 45))
    label.new(bar_index, rsi, str.tostring(lower_level), style = label.style_label_center, size = size.small, color = color.new(rsi_color, 100))

    start := bar_index
    trigger := true
    upper := high
    lower := low
    channel_color := rsi_color
    bar_color := rsi_color

    if display_rsi_val
        label.new(bar_index, hl2, "RSI: " + str.tostring(lower_level), style = label.style_label_right, color = color.new(rsi_color, 100), textcolor = chart.fg_color, force_overlay = true)


if bar_index-start >= min_channel_len 
    trigger := false


trigger_change = channel_upper != channel_upper[1] or channel_lower != channel_lower[1]

// --------------------------------------------------------------------------------------------------------------------}
// 📌 𝙑𝙄𝙎𝙐𝘼𝙇𝙄𝙕𝘼𝙏𝙄𝙊𝙉
// --------------------------------------------------------------------------------------------------------------------{

barcolor(bar_color)
prsi = plot(rsi, "RSI", color = rsi_color, linewidth = 2)
p50 = plot(50, color = color.gray, editable = false)
plower = plot(lower_level, "Lower RSI Level", color = bar_index % 3 == 0 ? na : color.gray)
pupper = plot(upper_level, "Upper RSI Level", color = bar_index % 3 == 0 ? na : color.gray)

fill(prsi, pupper, rsi >= upper_level ? color.new(rsi_color, 80) : na)
fill(prsi, plower, rsi <= lower_level ? color.new(rsi_color, 80) : na)

plot(trigger_change ? float(na) : upper, force_overlay = true, style = plot.style_linebr, offset = -1, color = channel_color, editable = false)
plot(trigger_change ? float(na) : lower, force_overlay = true, style = plot.style_linebr, offset = -1, color = channel_color, editable = false)

p1 = plot(trigger_change ? float(na) : upper, force_overlay = true, style = plot.style_linebr, color = color.new(channel_color, 70), linewidth = 3, editable = false)
p2 = plot(trigger_change ? float(na) : lower, force_overlay = true, style = plot.style_linebr, color = color.new(channel_color, 70), linewidth = 3, editable = false)

fill(p1, p2, color.new(channel_color, 90))

plot(trigger_change ? float(na) : math.avg(upper, lower), force_overlay = true, style = plot.style_linebr, offset = -1, color = color.gray, editable = false)
plot(trigger_change ? float(na) : math.avg(upper, lower), force_overlay = true, style = plot.style_linebr, color = color.gray, editable = false)
// --------------------------------------------------------------------------------------------------------------------}
