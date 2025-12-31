#!/usr/bin/env bash
# oblivius-screenshot.sh - Custom screenshot wrapper
#
# Usage:
#   --area      Instant area selection, copy to clipboard only
#   --window    Instant active window, copy to clipboard only
#   (no args)   Open full dialog (delegates to original screenshot.sh)

case "$1" in
    --area)
        # Freeze screen for region selection
        hyprpicker -r -z &
        pid_picker=$!
        trap 'kill "$pid_picker" 2>/dev/null' EXIT
        sleep 0.1

        # User selects region
        region=$(slurp -b "#00000080" -c "#888888ff" -w 1) || exit 0
        [[ -z "$region" ]] && exit 0

        # Unfreeze screen
        kill "$pid_picker" 2>/dev/null
        trap - EXIT

        # Capture directly to clipboard
        grim -g "$region" - | wl-copy
        notify-send -t 1000 "Screenshot copied to clipboard"
        ;;

    --window)
        # Get active window geometry from hyprctl
        geometry=$(hyprctl activewindow -j | jq -r '"\(.at[0]),\(.at[1]) \(.size[0])x\(.size[1])"')
        
        if [[ -z "$geometry" || "$geometry" == "null,null nullxnull" ]]; then
            notify-send -t 2000 "No active window found"
            exit 1
        fi

        # Capture window directly to clipboard
        grim -g "$geometry" - | wl-copy
        notify-send -t 1000 "Window screenshot copied to clipboard"
        ;;

    *)
        # Delegate to original screenshot.sh for full dialog
        exec ~/.config/hypr/scripts/screenshot.sh "$@"
        ;;
esac
