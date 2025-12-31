# Oblivius Dotfiles

Personal Hyprland customizations for [ML4W Dotfiles](https://github.com/mylinuxforwork/dotfiles).

## Install

```bash
./install.sh
```

Creates symlinks to `~/.mydotfiles/com.ml4w.dotfiles/`.

## Components

### Brightness Control
GTK4/Adwaita app for DDC displays. Sliders for each monitor + "All Displays" sync slider.

**Requires:** `ddcutil`, `python-gobject`, `libadwaita`

### Volume Control
Pulseaudio with 5% scroll steps. Middle-click toggles 1% fine mode.

### Waybar Theme
Custom `oblivius` theme with brightness/volume modules.

### Hyprland Configs
Keybindings, window rules, animations, decorations.
