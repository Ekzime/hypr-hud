#!/bin/bash
# Tech HUD Power Menu via wofi — anchored top-right under waybar

entries="⏻  Shutdown\n⟳  Reboot\n⏾  Suspend\n⇥  Logout"

# Get screen width to position menu at top-right
screen_w=$(hyprctl monitors -j | jq '.[0].width')
menu_w=220
pos_x=$(( screen_w - menu_w - 8 ))

selected=$(echo -e "$entries" | wofi --dmenu \
    --prompt "SYSTEM" \
    --width $menu_w \
    --height 195 \
    --location 2 \
    --xoffset $pos_x \
    --yoffset 50 \
    --cache-file /dev/null \
    --style "$HOME/.config/waybar/scripts/power-menu.css" \
    2>/dev/null)

case "$selected" in
    *Shutdown*)  systemctl poweroff ;;
    *Reboot*)    systemctl reboot ;;
    *Suspend*)   systemctl suspend ;;
    *Logout*)    hyprctl dispatch exit ;;
esac
