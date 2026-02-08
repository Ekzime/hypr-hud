#!/bin/bash
# Tech HUD Power Menu — top-right under waybar


# Toggle: if wofi is already open, kill it
if pgrep -x wofi > /dev/null; then
    pkill -x wofi
    exit 0
fi

entries="⏻  Shutdown\n⟳  Reboot\n⏾  Suspend\n⇥  Logout"

selected=$(echo -e "$entries" | wofi --dmenu \
    --width 220 \
    --lines 4 \
    --location 3 \
    -D hide_search=true \
    --yoffset 46 \
    --xoffset 0 \
    --cache-file /dev/null \
    --style "$HOME/.config/waybar/scripts/power-menu.css" \
    -D close_on_focus_loss=true \
    2>/dev/null)

case "$selected" in
    *Shutdown*)  systemctl poweroff ;;
    *Reboot*)    systemctl reboot ;;
    *Suspend*)   systemctl suspend ;;
    *Logout*)    hyprctl dispatch exit ;;
esac
