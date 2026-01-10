#!/usr/bin/env bash
#  ___  _     _ _       _             _   _           _       _
# / _ \| |__ | (_)_   _(_)_   _ ___  | | | |_ __   __| | __ _| |_ ___  ___
#| | | | '_ \| | \ \ / / | | | / __| | | | | '_ \ / _` |/ _` | __/ _ \/ __|
#| |_| | |_) | | |\ V /| | |_| \__ \ | |_| | |_) | (_| | (_| | ||  __/\__ \
# \___/|_.__/|_|_| \_/ |_|\__,_|___/  \___/| .__/ \__,_|\__,_|\__\___||___/
#                                          |_|
#
# Oblivius Package Updater Launcher
# Opens the interactive TUI updater in kitty terminal

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
UPDATER_SCRIPT="$SCRIPT_DIR/oblivius-updater.py"

# Launch kitty with the updater script
kitty --class dotfiles-floating \
      --title "Oblivius Package Updater" \
      -o initial_window_width=35c \
      -o initial_window_height=100c \
      "$UPDATER_SCRIPT"
