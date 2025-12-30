#!/bin/bash
# Copy oblivius dotfiles into ml4w dotfiles directory

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
TARGET_BASE="$HOME"

find "$REPO_DIR/.mydotfiles" -type f | while read -r file; do
  rel_path="${file#$REPO_DIR/}"
  target="$TARGET_BASE/$rel_path"
  
  mkdir -p "$(dirname "$target")"
  cp "$file" "$target"
  echo "Copied: $rel_path"
done
