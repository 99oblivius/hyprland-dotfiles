#!/usr/bin/env python3
"""
Brightness Control for DDC Displays
A GTK4/Adwaita app matching the ML4W ecosystem style
"""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Gdk, GLib, Gio
import subprocess
import json
import time
from pathlib import Path
from threading import Thread

APP_ID = "com.oblivius.brightness"
CACHE_FILE = Path("/tmp/oblivius-brightness-displays.json")
CACHE_AGE = 300  # 5 minutes


def run_cmd(cmd, timeout=2):
    """Run command and return output"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return result.stdout.strip()
    except:
        return ""


def detect_displays():
    """Detect DDC displays and cache results"""
    if CACHE_FILE.exists():
        age = time.time() - CACHE_FILE.stat().st_mtime
        if age < CACHE_AGE:
            try:
                return json.loads(CACHE_FILE.read_text())
            except:
                pass

    output = run_cmd("ddcutil detect", timeout=10)
    displays = []
    current_bus = None

    for line in output.split('\n'):
        if 'I2C bus:' in line and 'i2c-' in line:
            current_bus = line.split('i2c-')[-1].split()[0]
        elif 'Model:' in line and current_bus:
            model = line.split('Model:')[-1].strip()
            max_out = run_cmd(f"ddcutil --bus {current_bus} getvcp 10", timeout=3)
            max_val = 100
            if 'max value' in max_out:
                try:
                    max_val = int(max_out.split('max value =')[-1].split(',')[0].strip())
                except:
                    pass
            displays.append({
                'bus': current_bus,
                'model': model,
                'max': max_val
            })
            current_bus = None

    CACHE_FILE.write_text(json.dumps(displays))
    return displays


def get_brightness(bus, max_val):
    """Get current brightness as percentage"""
    output = run_cmd(f"ddcutil --bus {bus} getvcp 10", timeout=3)
    if 'current value' in output:
        try:
            current = int(output.split('current value =')[-1].split(',')[0].strip())
            return int(current * 100 / max_val) if max_val > 0 else current
        except:
            pass
    return 50


def set_brightness(bus, percent, max_val):
    """Set brightness (runs in background)"""
    value = int(percent * max_val / 100)
    subprocess.Popen(f"ddcutil --bus {bus} setvcp 10 {value}", shell=True,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


class BrightnessWindow(Adw.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="Brightness")
        self.displays = []
        self.sliders = []
        self.updating = False
        self.pending_values = {}
        self.pending_timeouts = {}
        self.loading = True

        # Window setup
        self.set_default_size(350, -1)
        self.set_resizable(False)

        # Header bar
        header = Adw.HeaderBar()
        header.set_show_end_title_buttons(True)

        # Main layout
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        main_box.append(header)

        # Content with clamp for nice width
        clamp = Adw.Clamp()
        clamp.set_maximum_size(400)

        self.content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.content_box.set_margin_top(12)
        self.content_box.set_margin_bottom(12)
        self.content_box.set_margin_start(12)
        self.content_box.set_margin_end(12)

        # Loading spinner
        self.spinner_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.spinner_box.set_valign(Gtk.Align.CENTER)
        self.spinner_box.set_margin_top(24)
        self.spinner_box.set_margin_bottom(24)

        spinner = Gtk.Spinner()
        spinner.set_size_request(32, 32)
        spinner.start()
        self.spinner_box.append(spinner)

        loading_label = Gtk.Label(label="Loading displays...")
        loading_label.add_css_class("dim-label")
        self.spinner_box.append(loading_label)

        self.content_box.append(self.spinner_box)

        clamp.set_child(self.content_box)
        main_box.append(clamp)
        self.set_content(main_box)

        # Detect displays and load brightness in background
        Thread(target=self.load_displays_and_brightness, daemon=True).start()

    def load_displays_and_brightness(self):
        """Detect displays and load brightness values in background thread"""
        # Detect displays
        self.displays = detect_displays()

        if not self.displays:
            GLib.idle_add(self.show_no_displays_error)
            return

        # Load brightness values
        max_brightness = 0
        for d in self.displays:
            d['brightness'] = get_brightness(d['bus'], d['max'])
            max_brightness = max(max_brightness, d['brightness'])

        GLib.idle_add(self.build_sliders, max_brightness)

    def show_no_displays_error(self):
        """Show error when no displays found"""
        self.content_box.remove(self.spinner_box)

        error_label = Gtk.Label(label="No DDC displays found")
        error_label.add_css_class("dim-label")
        self.content_box.append(error_label)
        return False

    def build_sliders(self, max_brightness):
        """Build slider UI after loading values"""
        self.content_box.remove(self.spinner_box)

        # Preferences group for "All Displays"
        all_group = Adw.PreferencesGroup()
        all_group.set_title("All Displays")

        all_row = Adw.ActionRow()
        all_row.set_title("Brightness")
        all_row.set_subtitle("Adjust all displays together")

        self.all_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
        self.all_scale.set_value(max_brightness)
        self.all_scale.set_size_request(180, -1)
        self.all_scale.set_valign(Gtk.Align.CENTER)
        self.all_scale.set_draw_value(True)
        self.all_scale.set_value_pos(Gtk.PositionType.LEFT)
        self.all_scale.connect("value-changed", self.on_all_changed)

        all_row.add_suffix(self.all_scale)
        all_group.add(all_row)
        self.content_box.append(all_group)

        # Individual displays group
        displays_group = Adw.PreferencesGroup()
        displays_group.set_title("Individual Displays")

        for d in self.displays:
            row = Adw.ActionRow()
            row.set_title(d['model'][:25])
            row.set_subtitle(f"Bus {d['bus']}")

            scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
            scale.set_value(d['brightness'])
            scale.set_size_request(180, -1)
            scale.set_valign(Gtk.Align.CENTER)
            scale.set_draw_value(True)
            scale.set_value_pos(Gtk.PositionType.LEFT)
            scale.connect("value-changed", self.on_slider_changed, d)

            row.add_suffix(scale)
            displays_group.add(row)
            self.sliders.append((scale, d))

        self.content_box.append(displays_group)
        self.loading = False
        return False

    def debounce_apply(self, key, callback, delay_ms=300):
        """Debounce brightness application"""
        if key in self.pending_timeouts:
            GLib.source_remove(self.pending_timeouts[key])
        self.pending_timeouts[key] = GLib.timeout_add(delay_ms, callback)

    def on_all_changed(self, scale):
        """When All slider changes, update all individual sliders visually"""
        if self.updating:
            return
        self.updating = True

        value = int(scale.get_value())
        for slider, d in self.sliders:
            slider.set_value(value)
            self.pending_values[d['bus']] = (value, d['max'])

        self.updating = False

        # Debounce apply to all displays
        def apply_all():
            for bus, (val, max_val) in list(self.pending_values.items()):
                set_brightness(bus, val, max_val)
            self.pending_values.clear()
            if 'all' in self.pending_timeouts:
                del self.pending_timeouts['all']
            return False

        self.debounce_apply('all', apply_all)

    def on_slider_changed(self, scale, display):
        """Apply brightness with debounce when slider changes"""
        if self.updating:
            return

        value = int(scale.get_value())
        bus = display['bus']
        max_val = display['max']

        def apply_single():
            set_brightness(bus, value, max_val)
            if bus in self.pending_timeouts:
                del self.pending_timeouts[bus]
            return False

        self.debounce_apply(bus, apply_single)


class BrightnessApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID,
                         flags=Gio.ApplicationFlags.FLAGS_NONE)
        self.displays = []

    def do_startup(self):
        Adw.Application.do_startup(self)
        self.load_css()

    def load_css(self):
        """Load ML4W theme colors"""
        css_file = Path.home() / ".config/gtk-4.0/colors.css"
        if css_file.exists():
            css_provider = Gtk.CssProvider()
            css_provider.load_from_path(str(css_file))
            Gtk.StyleContext.add_provider_for_display(
                Gdk.Display.get_default(),
                css_provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )

    def do_activate(self):
        # Create and show window immediately - loading happens in background
        win = BrightnessWindow(self)
        win.present()


def main():
    app = BrightnessApp()
    app.run(None)


if __name__ == "__main__":
    main()
