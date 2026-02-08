#!/bin/bash
# Notification badge for waybar

count=$(swaync-client -c 2>/dev/null)
dnd=$(swaync-client -D 2>/dev/null)

if [ "$dnd" = "true" ]; then
    echo '{"text": " 󰂛 ", "class": "dnd", "tooltip": "Do Not Disturb"}'
elif [ "$count" -gt 0 ] 2>/dev/null; then
    echo "{\"text\": \"󰂚 ${count}\", \"class\": \"unread\", \"tooltip\": \"${count} notifications\"}"
else
    echo '{"text": "󰂜", "class": "none", "tooltip": "No notifications"}'
fi
