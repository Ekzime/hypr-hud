#!/usr/bin/env python3
"""Tech HUD App Launcher — GTK3 + Layer Shell"""

import gi
import subprocess
import os
import signal
import configparser
import json

gi.require_version("Gtk", "3.0")
gi.require_version("GtkLayerShell", "0.1")
from gi.repository import Gtk, Gdk, GtkLayerShell, GLib, Pango

CSS_FILE = os.path.expanduser("~/.config/waybar/scripts/launcher-ui.css")
PID_FILE = "/tmp/launcher-ui.pid"
PINS_FILE = os.path.expanduser("~/.cache/launcher-pins.json")

APP_DIRS = [
    "/usr/share/applications",
    os.path.expanduser("~/.local/share/applications"),
    "/usr/local/share/applications",
]


def load_pins():
    try:
        with open(PINS_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_pins(pins):
    os.makedirs(os.path.dirname(PINS_FILE), exist_ok=True)
    with open(PINS_FILE, "w") as f:
        json.dump(pins, f)


def load_desktop_entries():
    apps = []
    seen = set()

    for app_dir in APP_DIRS:
        if not os.path.isdir(app_dir):
            continue
        for fname in os.listdir(app_dir):
            if not fname.endswith(".desktop") or fname in seen:
                continue
            seen.add(fname)
            path = os.path.join(app_dir, fname)
            try:
                cp = configparser.ConfigParser(interpolation=None)
                cp.read(path, encoding="utf-8")
                entry = cp["Desktop Entry"]

                if entry.get("NoDisplay", "false").lower() == "true":
                    continue
                if entry.get("Hidden", "false").lower() == "true":
                    continue

                name = entry.get("Name", "")
                if not name:
                    continue

                icon = entry.get("Icon", "")
                exec_cmd = entry.get("Exec", "")
                generic = entry.get("GenericName", "")
                keywords = entry.get("Keywords", "")
                comment = entry.get("Comment", "")

                exec_clean = exec_cmd
                for token in ["%f", "%F", "%u", "%U", "%d", "%D", "%n", "%N",
                              "%i", "%c", "%k", "%v", "%m"]:
                    exec_clean = exec_clean.replace(token, "")
                exec_clean = exec_clean.strip()

                search_str = " ".join([
                    name, generic, keywords, comment, fname
                ]).lower()

                apps.append({
                    "name": name,
                    "icon": icon,
                    "exec": exec_clean,
                    "search": search_str,
                    "file": fname,
                })
            except Exception:
                continue

    apps.sort(key=lambda a: a["name"].lower())
    return apps


class AppLauncher(Gtk.Window):
    def __init__(self):
        super().__init__()

        GtkLayerShell.init_for_window(self)
        GtkLayerShell.set_layer(self, GtkLayerShell.Layer.OVERLAY)
        GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.TOP, True)
        GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.LEFT, True)
        GtkLayerShell.set_margin(self, GtkLayerShell.Edge.TOP, 0)
        GtkLayerShell.set_margin(self, GtkLayerShell.Edge.LEFT, 0)
        GtkLayerShell.set_exclusive_zone(self, 0)
        GtkLayerShell.set_keyboard_mode(
            self, GtkLayerShell.KeyboardMode.ON_DEMAND
        )

        self.set_size_request(420, 580)
        self.get_style_context().add_class("launcher-window")

        self._load_css()
        self.apps = load_desktop_entries()
        self.pins = load_pins()
        self.icon_theme = Gtk.IconTheme.get_default()
        self._build_ui()
        self.connect("key-press-event", self._on_key)

    def _load_css(self):
        css_provider = Gtk.CssProvider()
        try:
            css_provider.load_from_path(CSS_FILE)
        except GLib.Error:
            pass
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

    def _build_ui(self):
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        main_box.get_style_context().add_class("main-box")
        self.add(main_box)

        # Header
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        header.get_style_context().add_class("lnc-header")

        title = Gtk.Label(label="APPLICATIONS")
        title.get_style_context().add_class("lnc-title")
        title.set_halign(Gtk.Align.START)
        header.pack_start(title, True, True, 0)

        count = Gtk.Label(label=f"{len(self.apps)}")
        count.get_style_context().add_class("lnc-count")
        header.pack_end(count, False, False, 0)

        main_box.pack_start(header, False, False, 0)

        # Search
        self.search_entry = Gtk.Entry()
        self.search_entry.get_style_context().add_class("lnc-search")
        self.search_entry.set_placeholder_text("SEARCH...")
        self.search_entry.connect("changed", self._on_search_changed)
        main_box.pack_start(self.search_entry, False, False, 0)

        # Scrollable list
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_vexpand(True)

        self.list_box = Gtk.ListBox()
        self.list_box.get_style_context().add_class("lnc-list")
        self.list_box.set_selection_mode(Gtk.SelectionMode.NONE)
        scroll.add(self.list_box)
        main_box.pack_start(scroll, True, True, 0)

        self._populate()

        # Don't auto-focus search
        self.search_entry.set_can_focus(True)
        self.list_box.set_can_focus(True)
        GLib.idle_add(lambda: self.list_box.grab_focus())

    def _populate(self, filter_text=""):
        for child in self.list_box.get_children():
            self.list_box.remove(child)

        ft = filter_text.lower()
        pinned = [a for a in self.apps if a["file"] in self.pins]
        unpinned = [a for a in self.apps if a["file"] not in self.pins]

        if pinned:
            self._add_section_label("  PINNED")
            for app in pinned:
                if ft and ft not in app["search"]:
                    continue
                self.list_box.add(self._make_row(app, True))

        self._add_section_label("  ALL APPS")
        for app in unpinned:
            if ft and ft not in app["search"]:
                continue
            self.list_box.add(self._make_row(app, False))

        self.list_box.show_all()

    def _add_section_label(self, text):
        row = Gtk.ListBoxRow()
        row.set_selectable(False)
        row.set_activatable(False)
        lbl = Gtk.Label(label=text)
        lbl.get_style_context().add_class("lnc-section")
        lbl.set_halign(Gtk.Align.START)
        row.add(lbl)
        self.list_box.add(row)

    def _make_row(self, app, is_pinned):
        row = Gtk.ListBoxRow()
        row.set_selectable(False)
        row.set_activatable(False)

        outer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        outer.get_style_context().add_class("lnc-entry")
        if is_pinned:
            outer.get_style_context().add_class("pinned")

        # Launch button (main area)
        btn = Gtk.Button()
        btn.get_style_context().add_class("lnc-btn")
        btn.set_relief(Gtk.ReliefStyle.NONE)
        btn.connect("clicked", lambda b, a=app: self._launch(a))
        btn.set_hexpand(True)

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        box.get_style_context().add_class("lnc-row")

        icon_widget = self._get_icon(app["icon"])
        box.pack_start(icon_widget, False, False, 4)

        name_label = Gtk.Label(label=app["name"])
        name_label.get_style_context().add_class("lnc-name")
        name_label.set_halign(Gtk.Align.START)
        name_label.set_ellipsize(Pango.EllipsizeMode.END)
        name_label.set_max_width_chars(30)
        box.pack_start(name_label, True, True, 0)

        btn.add(box)
        outer.pack_start(btn, True, True, 0)

        # Pin button
        pin_btn = Gtk.Button(label="󰤱" if is_pinned else "󰤰")
        pin_btn.get_style_context().add_class("lnc-pin-active" if is_pinned else "lnc-pin")
        pin_btn.set_relief(Gtk.ReliefStyle.NONE)
        pin_btn.set_tooltip_text("Unpin" if is_pinned else "Pin")
        pin_btn.connect("clicked", lambda b, a=app, p=is_pinned: self._on_pin(a, p))
        outer.pack_end(pin_btn, False, False, 0)

        row.add(outer)
        return row

    def _on_pin(self, app, is_pinned):
        if is_pinned:
            self.pins.remove(app["file"])
        else:
            self.pins.append(app["file"])
        save_pins(self.pins)
        self._populate(self.search_entry.get_text())

    def _get_icon(self, icon_name):
        ICON_SIZE = 22

        if not icon_name:
            label = Gtk.Label(label="󰣆")
            label.get_style_context().add_class("lnc-icon-fallback")
            return label

        if os.path.isfile(icon_name):
            try:
                from gi.repository import GdkPixbuf
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                    icon_name, ICON_SIZE, ICON_SIZE, True
                )
                img = Gtk.Image.new_from_pixbuf(pixbuf)
                img.get_style_context().add_class("lnc-icon")
                return img
            except Exception:
                pass

        if self.icon_theme.has_icon(icon_name):
            try:
                pixbuf = self.icon_theme.load_icon(
                    icon_name, ICON_SIZE, Gtk.IconLookupFlags.FORCE_SIZE
                )
                img = Gtk.Image.new_from_pixbuf(pixbuf)
                img.get_style_context().add_class("lnc-icon")
                return img
            except Exception:
                pass

        label = Gtk.Label(label="󰣆")
        label.get_style_context().add_class("lnc-icon-fallback")
        return label

    def _launch(self, app):
        self._quit()
        subprocess.Popen(
            app["exec"],
            shell=True,
            start_new_session=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def _on_search_changed(self, entry):
        self._populate(entry.get_text())

    def _on_key(self, widget, event):
        if event.keyval == Gdk.KEY_Escape:
            self._quit()
            return True
        return False

    def _quit(self):
        try:
            os.remove(PID_FILE)
        except FileNotFoundError:
            pass
        self.destroy()
        Gtk.main_quit()


def main():
    if os.path.exists(PID_FILE):
        try:
            old_pid = int(open(PID_FILE).read().strip())
            os.kill(old_pid, signal.SIGTERM)
            os.remove(PID_FILE)
            return
        except (ProcessLookupError, ValueError):
            try:
                os.remove(PID_FILE)
            except FileNotFoundError:
                pass

    with open(PID_FILE, "w") as f:
        f.write(str(os.getpid()))

    def on_sigterm(*args):
        try:
            os.remove(PID_FILE)
        except FileNotFoundError:
            pass
        Gtk.main_quit()

    signal.signal(signal.SIGTERM, on_sigterm)

    win = AppLauncher()
    win.show_all()
    Gtk.main()


if __name__ == "__main__":
    main()
