#!/bin/bash
# Tech HUD Clipboard menu — top-right under waybar

# Toggle: if wofi is already open, kill it
if pgrep -x wofi > /dev/null; then
    pkill -x wofi
    exit 0
fi

cliphist list | wofi --dmenu \
    --prompt "CLIPBOARD" \
    --width 500 \
    --height 380 \
    --location 3 \
    --yoffset 46 \
    --xoffset 0 \
    --cache-file /dev/null \
    -D close_on_focus_loss=true \
    | cliphist decode | wl-copy
