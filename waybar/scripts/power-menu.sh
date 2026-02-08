#!/bin/bash
# Tech HUD Power Menu via wofi

entries="⏻  Shutdown\n⟳  Reboot\n⏾  Suspend\n⇥  Logout"

selected=$(echo -e "$entries" | wofi --dmenu \
    --prompt "SYSTEM" \
    --width 250 \
    --height 200 \
    --cache-file /dev/null \
    --style "$HOME/.config/waybar/scripts/power-menu.css" \
    2>/dev/null)

case "$selected" in
    *Shutdown*)  systemctl poweroff ;;
    *Reboot*)    systemctl reboot ;;
    *Suspend*)   systemctl suspend ;;
    *Logout*)    hyprctl dispatch exit ;;
esac
