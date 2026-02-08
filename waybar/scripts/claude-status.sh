#!/bin/bash
# Claude Code activity indicator for waybar

# Check if any claude process is running
claude_pids=$(pgrep -f "claude" 2>/dev/null)

if [ -n "$claude_pids" ]; then
    # Count active claude processes
    count=$(echo "$claude_pids" | wc -l)

    # Check if there's heavy CPU usage (thinking)
    cpu=$(ps -p $(echo "$claude_pids" | head -1) -o %cpu= 2>/dev/null | awk '{printf "%.0f", $1}')

    if [ "${cpu:-0}" -gt 10 ]; then
        echo "{\"text\": \"  ◆\", \"class\": \"thinking\", \"tooltip\": \"Claude is thinking... (${count} processes)\"}"
    else
        echo "{\"text\": \"  ●\", \"class\": \"active\", \"tooltip\": \"Claude active (${count} processes)\"}"
    fi
else
    echo '{"text": " ○", "class": "idle", "tooltip": "Claude idle"}'
fi
