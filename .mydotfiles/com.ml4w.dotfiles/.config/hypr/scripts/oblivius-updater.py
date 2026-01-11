#!/usr/bin/env python3
"""
Oblivius Package Updater - Interactive TUI for selective package updates.
Uses blessed for terminal UI.
"""

import subprocess
import shutil
import sys
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

try:
    from blessed import Terminal
except ImportError:
    print("Error: 'blessed' library not found.")
    print("Install it with: sudo pacman -S python-blessed")
    sys.exit(1)


class PackageSource(Enum):
    OFFICIAL = "official"
    AUR = "aur"
    FLATPAK = "flatpak"


@dataclass
class Package:
    name: str
    current_version: str
    new_version: str
    source: PackageSource
    selected: bool = True


@dataclass
class UpdateResult:
    name: str
    source: PackageSource
    success: bool
    error: str = ""


def detect_aur_helper() -> Optional[str]:
    """Detect available AUR helper (paru or yay)."""
    for helper in ["paru", "yay"]:
        if shutil.which(helper):
            return helper
    return None


def get_official_updates() -> list[Package]:
    """Get list of official repository updates using checkupdates."""
    packages = []
    try:
        result = subprocess.run(
            ["checkupdates"],
            capture_output=True,
            text=True,
            timeout=60
        )
        if result.returncode == 0 and result.stdout.strip():
            for line in result.stdout.strip().split("\n"):
                parts = line.split()
                if len(parts) >= 4:
                    name = parts[0]
                    current = parts[1]
                    new = parts[3]
                    packages.append(Package(name, current, new, PackageSource.OFFICIAL))
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return packages


def get_aur_updates(helper: str) -> list[Package]:
    """Get list of AUR updates using yay or paru."""
    packages = []
    try:
        result = subprocess.run(
            [helper, "-Qum"],
            capture_output=True,
            text=True,
            timeout=60
        )
        if result.returncode == 0 and result.stdout.strip():
            for line in result.stdout.strip().split("\n"):
                parts = line.split()
                if len(parts) >= 4:
                    name = parts[0]
                    current = parts[1]
                    new = parts[3]
                    packages.append(Package(name, current, new, PackageSource.AUR))
                elif len(parts) >= 2:
                    name = parts[0]
                    current = parts[1] if len(parts) > 1 else "?"
                    packages.append(Package(name, current, "?", PackageSource.AUR))
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return packages


def get_flatpak_updates() -> list[Package]:
    """Get list of flatpak updates."""
    packages = []
    if not shutil.which("flatpak"):
        return packages
    try:
        result = subprocess.run(
            ["flatpak", "remote-ls", "--updates", "--columns=application,version"],
            capture_output=True,
            text=True,
            timeout=60
        )
        if result.returncode == 0 and result.stdout.strip():
            for line in result.stdout.strip().split("\n"):
                parts = line.split("\t")
                if parts:
                    name = parts[0].strip()
                    new_version = parts[1].strip() if len(parts) > 1 else "?"
                    if name:
                        packages.append(Package(name, "installed", new_version, PackageSource.FLATPAK))
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return packages


class UpdaterTUI:
    # Button definitions for each mode
    SELECT_BUTTONS = ["Select All", "Deselect All", "Update", "Exit"]
    CONFIRM_BUTTONS = ["Yes, Update", "Go Back"]
    RESULTS_BUTTONS = ["Exit"]

    def __init__(self, term: Terminal, packages: list[Package], aur_helper: Optional[str]):
        self.term = term
        self.packages = packages
        self.aur_helper = aur_helper
        self.cursor = 0
        self.scroll_offset = 0
        self.mode = "select"  # select, confirm, updating, results
        self.in_button_area = False
        self.button_cursor = 0
        self.results: list[UpdateResult] = []

    @property
    def visible_height(self) -> int:
        return self.term.height - 10  # Reserve lines for header/footer/buttons

    @property
    def current_buttons(self) -> list[str]:
        if self.mode == "select":
            return self.SELECT_BUTTONS
        elif self.mode == "confirm":
            return self.CONFIRM_BUTTONS
        elif self.mode == "results":
            return self.RESULTS_BUTTONS
        return []

    def draw(self):
        print(self.term.home + self.term.clear, end="")

        # Header
        title = "OBLIVIUS PACKAGE UPDATER"
        print(self.term.center(self.term.bold_cyan(title)))
        print(self.term.center("─" * 40))

        if self.mode == "select":
            self.draw_select_mode()
        elif self.mode == "confirm":
            self.draw_confirm_mode()
        elif self.mode == "updating":
            self.draw_updating_mode()
        elif self.mode == "results":
            self.draw_results_mode()

    def draw_select_mode(self):
        selected_count = sum(1 for p in self.packages if p.selected)
        total_count = len(self.packages)

        # Status line
        status = f"Selected: {selected_count}/{total_count}"
        print(self.term.center(status))
        print()

        # Package list
        visible_packages = self.packages[self.scroll_offset:self.scroll_offset + self.visible_height]

        for i, pkg in enumerate(visible_packages):
            actual_idx = i + self.scroll_offset
            is_cursor = (actual_idx == self.cursor) and not self.in_button_area

            # Arrow indicator instead of highlight
            arrow = ">" if is_cursor else " "
            checkbox = "[x]" if pkg.selected else "[ ]"

            source_label = {
                PackageSource.OFFICIAL: self.term.green("repo"),
                PackageSource.AUR: self.term.yellow("AUR"),
                PackageSource.FLATPAK: self.term.blue("flat"),
            }[pkg.source]

            # Truncate package name if needed
            max_name_len = self.term.width - 25
            name = pkg.name[:max_name_len] if len(pkg.name) > max_name_len else pkg.name

            line = f" {arrow} {checkbox} {source_label} {name}"
            print(line)

        # Padding
        for _ in range(self.visible_height - len(visible_packages)):
            print()

        # Scroll indicator
        if len(self.packages) > self.visible_height:
            scroll_pct = (self.scroll_offset / max(1, len(self.packages) - self.visible_height)) * 100
            print(self.term.center(f"─── {scroll_pct:.0f}% ───"))
        else:
            print(self.term.center("─" * 20))

        print()
        self.draw_buttons()

    def draw_confirm_mode(self):
        selected = [p for p in self.packages if p.selected]
        print()
        print(self.term.center(f"Update {len(selected)} package(s)?"))
        print()

        # Show selected packages
        display_count = min(self.visible_height, len(selected))
        for pkg in selected[:display_count]:
            source_label = {
                PackageSource.OFFICIAL: self.term.green("repo"),
                PackageSource.AUR: self.term.yellow("AUR"),
                PackageSource.FLATPAK: self.term.blue("flat"),
            }[pkg.source]
            print(self.term.center(f"{source_label} {pkg.name}"))

        if len(selected) > display_count:
            print(self.term.center(f"... and {len(selected) - display_count} more"))

        # Padding to push buttons to bottom
        used_lines = min(display_count, len(selected)) + (1 if len(selected) > display_count else 0) + 3
        for _ in range(self.visible_height - used_lines):
            print()

        print()
        self.draw_buttons()

    def draw_updating_mode(self):
        print()
        print(self.term.center("Updating packages..."))
        print()
        print(self.term.center("Please wait..."))

    def draw_results_mode(self):
        successes = [r for r in self.results if r.success]
        failures = [r for r in self.results if not r.success]

        print()
        if failures:
            print(self.term.center(self.term.yellow(f"{len(successes)} succeeded, {len(failures)} failed")))
        else:
            print(self.term.center(self.term.green(f"All {len(successes)} packages updated!")))
        print()

        # Calculate available height for results
        available_height = self.visible_height

        # Show results
        results_shown = 0

        # Show successes first
        for r in successes:
            if results_shown >= available_height:
                break
            source_label = {
                PackageSource.OFFICIAL: "repo",
                PackageSource.AUR: "AUR",
                PackageSource.FLATPAK: "flat",
            }[r.source]
            line = f" {self.term.green('✓')} [{source_label}] {r.name}"
            print(line)
            results_shown += 1

        # Show failures
        for r in failures:
            if results_shown >= available_height:
                break
            source_label = {
                PackageSource.OFFICIAL: "repo",
                PackageSource.AUR: "AUR",
                PackageSource.FLATPAK: "flat",
            }[r.source]
            # Truncate error to fit
            max_err_len = self.term.width - len(r.name) - 20
            error = r.error[:max_err_len] if len(r.error) > max_err_len else r.error
            line = f" {self.term.red('✗')} [{source_label}] {r.name}: {error}"
            print(line)
            results_shown += 1

        # Padding
        for _ in range(available_height - results_shown):
            print()

        print()
        self.draw_buttons()

    def draw_buttons(self):
        buttons = self.current_buttons
        button_strs = []

        for i, btn in enumerate(buttons):
            if self.in_button_area and i == self.button_cursor:
                button_strs.append(f"[{self.term.reverse(btn)}]")
            else:
                button_strs.append(f"[{btn}]")

        print(self.term.center("  ".join(button_strs)))

    def move_cursor(self, delta: int):
        if self.in_button_area:
            self.button_cursor = max(0, min(len(self.current_buttons) - 1, self.button_cursor + delta))
        else:
            self.cursor = max(0, min(len(self.packages) - 1, self.cursor + delta))
            # Adjust scroll
            if self.cursor < self.scroll_offset:
                self.scroll_offset = self.cursor
            elif self.cursor >= self.scroll_offset + self.visible_height:
                self.scroll_offset = self.cursor - self.visible_height + 1

    def move_to_buttons(self):
        self.in_button_area = True
        self.button_cursor = 0

    def move_to_list(self):
        self.in_button_area = False

    def toggle_current(self):
        if not self.in_button_area and self.packages:
            self.packages[self.cursor].selected = not self.packages[self.cursor].selected

    def select_all(self):
        for pkg in self.packages:
            pkg.selected = True

    def deselect_all(self):
        for pkg in self.packages:
            pkg.selected = False

    def activate_button(self):
        """Handle button activation based on current mode."""
        if self.mode == "select":
            btn = self.SELECT_BUTTONS[self.button_cursor]
            if btn == "Select All":
                self.select_all()
                self.move_to_list()
            elif btn == "Deselect All":
                self.deselect_all()
                self.move_to_list()
            elif btn == "Update":
                if any(p.selected for p in self.packages):
                    self.mode = "confirm"
                    self.in_button_area = True
                    self.button_cursor = 0
            elif btn == "Exit":
                return "exit"

        elif self.mode == "confirm":
            btn = self.CONFIRM_BUTTONS[self.button_cursor]
            if btn == "Yes, Update":
                return "run_updates"
            elif btn == "Go Back":
                self.mode = "select"
                self.in_button_area = False

        elif self.mode == "results":
            return "exit"

        return None

    def run_updates(self):
        """Execute updates for selected packages."""
        self.mode = "updating"
        self.draw()

        selected = [p for p in self.packages if p.selected]

        # Group by source
        official = [p for p in selected if p.source == PackageSource.OFFICIAL]
        aur = [p for p in selected if p.source == PackageSource.AUR]
        flatpaks = [p for p in selected if p.source == PackageSource.FLATPAK]

        self.results = []

        # Exit fullscreen for actual updates
        print(self.term.exit_fullscreen, end="")
        print(self.term.normal, end="")
        print("\n" + "=" * 60)
        print("Starting package updates...")
        print("=" * 60 + "\n")

        # Update official + AUR packages
        pacman_pkgs = official + aur
        if pacman_pkgs and self.aur_helper:
            # Sync database first
            print("\n[Syncing package database...]\n")
            subprocess.run([self.aur_helper, "-Sy"], capture_output=True)

            # Update each package
            total = len(pacman_pkgs)
            for i, pkg in enumerate(pacman_pkgs, 1):
                source_label = "repo" if pkg.source == PackageSource.OFFICIAL else "AUR"
                print(f"\n[{i}/{total}] Updating {pkg.name} ({source_label})...\n")
                result = subprocess.run(
                    [self.aur_helper, "-S", "--needed", "--noconfirm", pkg.name],
                    capture_output=False,
                    text=True,
                    stderr=subprocess.PIPE
                )
                if result.returncode != 0:
                    error_lines = [l.strip() for l in (result.stderr or "").split("\n") if l.strip()]
                    last_error = error_lines[-1] if error_lines else "Unknown error"
                    self.results.append(UpdateResult(pkg.name, pkg.source, False, last_error))
                    print(f"  FAILED: {last_error}")
                else:
                    self.results.append(UpdateResult(pkg.name, pkg.source, True))

        # Update flatpaks
        if flatpaks:
            total = len(flatpaks)
            for i, pkg in enumerate(flatpaks, 1):
                print(f"\n[{i}/{total}] Updating {pkg.name} (flatpak)...\n")
                result = subprocess.run(
                    ["flatpak", "update", "-y", pkg.name],
                    capture_output=False,
                    text=True,
                    stderr=subprocess.PIPE
                )
                if result.returncode != 0:
                    error_lines = [l.strip() for l in (result.stderr or "").split("\n") if l.strip()]
                    last_error = error_lines[-1] if error_lines else "Unknown error"
                    self.results.append(UpdateResult(pkg.name, pkg.source, False, last_error))
                    print(f"  FAILED: {last_error}")
                else:
                    self.results.append(UpdateResult(pkg.name, pkg.source, True))

        print("\n" + "=" * 60)
        print("Updates complete! Returning to results view...")
        print("=" * 60)

        # Signal waybar to refresh
        subprocess.run(["pkill", "-RTMIN+1", "waybar"], capture_output=True)

        # Brief pause then show results
        import time
        time.sleep(1)

        # Return to TUI for results
        self.mode = "results"
        self.in_button_area = True
        self.button_cursor = 0

    def run(self):
        with self.term.fullscreen(), self.term.cbreak(), self.term.hidden_cursor():
            while True:
                self.draw()
                key = self.term.inkey(timeout=None)

                # Handle navigation (works in select, confirm, results modes)
                if self.mode in ("select", "confirm", "results"):
                    if key.name == "KEY_UP" or key.lower() in ("w", "k"):
                        if self.in_button_area and self.mode == "select":
                            self.move_to_list()
                            self.cursor = len(self.packages) - 1
                            self.scroll_offset = max(0, len(self.packages) - self.visible_height)
                        else:
                            self.move_cursor(-1)
                    elif key.name == "KEY_DOWN" or key.lower() in ("s", "j"):
                        if not self.in_button_area and self.mode == "select":
                            if self.cursor >= len(self.packages) - 1:
                                self.move_to_buttons()
                            else:
                                self.move_cursor(1)
                        elif self.in_button_area:
                            pass  # Already at buttons, nowhere to go
                    elif key.name == "KEY_LEFT":
                        if self.in_button_area:
                            self.move_cursor(-1)
                    elif key.name == "KEY_RIGHT":
                        if self.in_button_area:
                            self.move_cursor(1)
                    elif key.name == "KEY_PGUP":
                        if not self.in_button_area:
                            self.move_cursor(-self.visible_height)
                    elif key.name == "KEY_PGDOWN":
                        if not self.in_button_area:
                            self.move_cursor(self.visible_height)
                    elif key.name == "KEY_HOME":
                        if not self.in_button_area:
                            self.cursor = 0
                            self.scroll_offset = 0
                    elif key.name == "KEY_END":
                        if not self.in_button_area:
                            self.cursor = len(self.packages) - 1
                            self.scroll_offset = max(0, len(self.packages) - self.visible_height)
                    elif key == " ":
                        if self.mode == "select":
                            if self.in_button_area:
                                action = self.activate_button()
                                if action == "exit":
                                    break
                                elif action == "run_updates":
                                    self.run_updates()
                            else:
                                self.toggle_current()
                    elif key.name == "KEY_ENTER":
                        if self.in_button_area:
                            action = self.activate_button()
                            if action == "exit":
                                break
                            elif action == "run_updates":
                                self.run_updates()
                        elif self.mode == "select":
                            self.toggle_current()
                    elif key.lower() == "q":
                        break


def main():
    term = Terminal()

    print(term.clear + term.home)
    print(term.center(term.bold("Oblivius Package Updater")))
    print()
    print(term.center("Checking for updates..."))

    # Detect AUR helper
    aur_helper = detect_aur_helper()
    if not aur_helper:
        print(term.center(term.red("Warning: No AUR helper found (yay/paru)")))

    # Gather packages
    packages: list[Package] = []

    print(term.center("  Checking official repos..."))
    packages.extend(get_official_updates())

    if aur_helper:
        print(term.center("  Checking AUR..."))
        packages.extend(get_aur_updates(aur_helper))

    print(term.center("  Checking Flatpak..."))
    packages.extend(get_flatpak_updates())

    if not packages:
        print()
        print(term.center(term.green("No updates available!")))
        print()
        print(term.center("Press Enter to exit..."))
        input()
        # Signal waybar to refresh
        subprocess.run(["pkill", "-RTMIN+1", "waybar"], capture_output=True)
        return

    print(term.center(f"  Found {len(packages)} updates."))
    print()

    # Run TUI
    tui = UpdaterTUI(term, packages, aur_helper)
    tui.run()


if __name__ == "__main__":
    main()
