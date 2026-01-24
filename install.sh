#!/bin/bash
# Symlink oblivius dotfiles into ml4w dotfiles directory

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
TARGET_BASE="$HOME"

find "$REPO_DIR/.mydotfiles" -type f | while read -r file; do
  rel_path="${file#$REPO_DIR/}"
  target="$TARGET_BASE/$rel_path"

  mkdir -p "$(dirname "$target")"
  ln -sf "$file" "$target"
  echo "Linked: $rel_path -> $file"
done

# Symlink .config files directly to ~/.config
find "$REPO_DIR/.config" -type f | while read -r file; do
  rel_path="${file#$REPO_DIR/}"
  target="$TARGET_BASE/$rel_path"

  mkdir -p "$(dirname "$target")"
  ln -sf "$file" "$target"
  echo "Linked: $rel_path -> $file"
done

# Vesktop: symlink quickCss.css to settings folders
VESKTOP_CSS="$REPO_DIR/.config/vesktop/settings/quickCss.css"
VESKTOP_DIR="$HOME/.config/vesktop"
if [[ -f "$VESKTOP_CSS" ]] && [[ -d "$VESKTOP_DIR" ]]; then
  # Main settings folder
  mkdir -p "$VESKTOP_DIR/settings"
  ln -sf "$VESKTOP_CSS" "$VESKTOP_DIR/settings/quickCss.css"
  echo "Linked: vesktop quickCss.css -> $VESKTOP_DIR/settings/quickCss.css"

  # Each version-* folder's settings
  for version_dir in "$VESKTOP_DIR"/version-*/; do
    if [[ -d "$version_dir" ]]; then
      mkdir -p "${version_dir}settings"
      ln -sf "$VESKTOP_CSS" "${version_dir}settings/quickCss.css"
      echo "Linked: vesktop quickCss.css -> ${version_dir}settings/quickCss.css"
    fi
  done
fi
