#!/bin/bash
# Volume control script for waybar
# Supports 5% normal steps, 1% fine steps (toggle with middle-click)

FINE_MODE_FILE="/tmp/oblivius-volume-fine-mode"
SINK="@DEFAULT_AUDIO_SINK@"

get_step() {
    if [[ -f "$FINE_MODE_FILE" ]]; then
        echo "1"
    else
        echo "5"
    fi
}

case "$1" in
    up)
        step=$(get_step)
        wpctl set-volume -l 1 "$SINK" "${step}%+"
        ;;
    down)
        step=$(get_step)
        wpctl set-volume "$SINK" "${step}%-"
        ;;
    mute)
        wpctl set-mute "$SINK" toggle
        ;;
    toggle-fine)
        if [[ -f "$FINE_MODE_FILE" ]]; then
            rm "$FINE_MODE_FILE"
            notify-send -t 1000 "Volume" "Normal mode (5%)"
        else
            touch "$FINE_MODE_FILE"
            notify-send -t 1000 "Volume" "Fine mode (1%)"
        fi
        ;;
    *)
        echo "Usage: $0 {up|down|mute|toggle-fine}"
        exit 1
        ;;
esac
