#!/usr/bin/env bash
# -----------------------------------------------------
# Oblivius Wallpaper - unique wallpaper per monitor
# -----------------------------------------------------

WALLPAPER_DIR="$HOME/.config/ml4w/wallpapers"
CACHE_DIR="$HOME/.cache/ml4w/oblivius-wallpapers"

mkdir -p "$CACHE_DIR"

# Get all monitors
mapfile -t MONITORS < <(hyprctl monitors -j | jq -r '.[].name')

# Get all wallpapers (images only)
mapfile -t WALLPAPERS < <(find "$WALLPAPER_DIR" -maxdepth 1 -type f,l \( -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" -o -iname "*.webp" -o -iname "*.gif" \) | shuf)

# Check we have enough wallpapers
if [[ ${#WALLPAPERS[@]} -lt ${#MONITORS[@]} ]]; then
    echo "Warning: Not enough wallpapers (${#WALLPAPERS[@]}) for monitors (${#MONITORS[@]})"
    echo "Some monitors will share wallpapers"
fi

# Assign unique wallpaper to each monitor
for i in "${!MONITORS[@]}"; do
    monitor="${MONITORS[$i]}"
    # Cycle through wallpapers if we run out
    wallpaper="${WALLPAPERS[$((i % ${#WALLPAPERS[@]}))]}"

    echo "Setting $monitor -> $(basename "$wallpaper")"
    swww img -o "$monitor" "$wallpaper" \
        --transition-type any \
        --transition-duration 2 \
        --transition-fps 60

    # Save current wallpaper for this monitor
    echo "$wallpaper" > "$CACHE_DIR/$monitor"
done

echo "Done!"
