# Tech HUD — Waybar + SwayNC Theme

Sci-fi inspired status bar and notification center for Hyprland.

Dark background, cyan/color-coded indicators, glow animations, sharp edges.

## Preview

```
⬡  1  2  3  4  5  // kitty     󰂜  Sun 08 Feb  22:03:45     CPU 4%  RAM 18%  TEMP 20°  │  󰃠 73%  󰕾 100%  󰖩 93%  │  󰌌 EN  󰂄 94%  ⏻
```

## Dependencies

```bash
pacman -S waybar swaync wofi jq brightnessctl playerctl
```

Font: [JetBrainsMono Nerd Font](https://www.nerdfonts.com/)

```bash
pacman -S ttf-jetbrains-mono-nerd
```

## Installation

```bash
# Backup existing configs
cp -r ~/.config/waybar ~/.config/waybar.bak
cp -r ~/.config/swaync ~/.config/swaync.bak

# Install waybar
cp waybar/config ~/.config/waybar/config
cp waybar/style.css ~/.config/waybar/style.css
mkdir -p ~/.config/waybar/scripts
cp waybar/scripts/* ~/.config/waybar/scripts/
chmod +x ~/.config/waybar/scripts/*.sh

# Install swaync theme
cp swaync/config.json ~/.config/swaync/config.json
cp swaync/style.css ~/.config/swaync/style.css

# Restart services
killall waybar; waybar &
swaync-client -rs
```

## Structure

```
waybar/
├── config              # Bar modules and settings
├── style.css           # Tech HUD theme (GTK CSS)
└── scripts/
    ├── power-menu.sh   # Wofi power menu (shutdown/reboot/suspend/logout)
    ├── power-menu.css  # Power menu styling
    └── notification-count.sh  # Notification badge with unread count
swaync/
├── config.json         # Notification center settings
└── style.css           # Matching Tech HUD theme
```

## Features

- Color-coded system indicators (CPU, RAM, temp, network, battery)
- Nerd Font icons with animated glow effects
- Notification badge with live unread count
- Power menu (wofi) positioned under the bar button
- SwayNC notifications with urgency-based accent colors
- Workspaces with active indicator underline
- Active window class display
- Fully monospace, no rounded corners — clean HUD aesthetic

## Customization

Colors are defined as CSS variables at the top of each `style.css`:

| Variable   | Default   | Used for                  |
|------------|-----------|---------------------------|
| `@accent`  | `#00e5ff` | Primary highlights, cyan  |
| `@green`   | `#00e676` | Network, volume, battery  |
| `@magenta` | `#d500f9` | Memory, MPRIS             |
| `@yellow`  | `#ffd740` | Backlight, battery warn   |
| `@red`     | `#ff1744` | Critical states, power    |
| `@orange`  | `#ff9100` | Language indicator         |

## Hyprland

Add to `~/.config/hypr/hyprland.conf`:

```
exec-once = waybar
exec-once = swaync
```
