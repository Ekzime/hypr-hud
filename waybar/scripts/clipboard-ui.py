#!/usr/bin/env python3
"""Tech HUD Clipboard Manager — GTK3 + Layer Shell"""

import gi
import subprocess
import json
import os
import signal

gi.require_version("Gtk", "3.0")
gi.require_version("GtkLayerShell", "0.1")
from gi.repository import Gtk, Gdk, GtkLayerShell, GLib, Pango

PINS_FILE = os.path.expanduser("~/.cache/clipboard-pins.json")
CSS_FILE = os.path.expanduser("~/.config/waybar/scripts/clipboard-ui.css")
PID_FILE = "/tmp/clipboard-ui.pid"


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


def get_clipboard_entries():
    result = subprocess.run(["cliphist", "list"], capture_output=True, text=True)
    entries = []
    for line in result.stdout.strip().split("\n"):
        if not line:
            continue
        tab = line.find("\t")
        if tab == -1:
            continue
        entry_id = line[:tab]
        content = line[tab + 1 :]
        entries.append({"id": entry_id, "content": content, "raw": line})
    return entries


def copy_entry(raw_line):
    proc = subprocess.Popen(
        ["cliphist", "decode"], stdin=subprocess.PIPE, stdout=subprocess.PIPE
    )
    decoded, _ = proc.communicate(raw_line.encode())
    subprocess.Popen(["wl-copy"], stdin=subprocess.PIPE).communicate(decoded)


def delete_entry(raw_line):
    proc = subprocess.Popen(["cliphist", "delete"], stdin=subprocess.PIPE)
    proc.communicate(raw_line.encode())


class ClipboardManager(Gtk.Window):
    def __init__(self):
        super().__init__()

        GtkLayerShell.init_for_window(self)
        GtkLayerShell.set_layer(self, GtkLayerShell.Layer.OVERLAY)
        GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.TOP, True)
        GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.RIGHT, True)
        GtkLayerShell.set_margin(self, GtkLayerShell.Edge.TOP, 0)
        GtkLayerShell.set_exclusive_zone(self, 0)
        GtkLayerShell.set_margin(self, GtkLayerShell.Edge.RIGHT, 0)
        GtkLayerShell.set_keyboard_mode(
            self, GtkLayerShell.KeyboardMode.ON_DEMAND
        )

        self.set_size_request(550, 600)
        self.get_style_context().add_class("clipboard-window")

        self._load_css()
        self.pins = load_pins()
        self.entries = get_clipboard_entries()
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
        header.get_style_context().add_class("header")

        title = Gtk.Label(label="CLIPBOARD")
        title.get_style_context().add_class("header-title")
        title.set_halign(Gtk.Align.START)
        header.pack_start(title, True, True, 0)

        clear_btn = Gtk.Button(label="CLEAR ALL")
        clear_btn.get_style_context().add_class("clear-all-btn")
        clear_btn.connect("clicked", self._on_clear_all)
        header.pack_end(clear_btn, False, False, 0)

        count = Gtk.Label(label=f"{len(self.entries)}")
        count.get_style_context().add_class("header-count")
        header.pack_end(count, False, False, 8)

        main_box.pack_start(header, False, False, 0)

        # Search
        self.search_entry = Gtk.Entry()
        self.search_entry.get_style_context().add_class("search-entry")
        self.search_entry.set_placeholder_text("SEARCH...")
        self.search_entry.connect("changed", self._on_search_changed)
        main_box.pack_start(self.search_entry, False, False, 0)

        # Scrollable list
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_vexpand(True)

        self.list_box = Gtk.ListBox()
        self.list_box.get_style_context().add_class("entries-list")
        self.list_box.set_selection_mode(Gtk.SelectionMode.NONE)
        scroll.add(self.list_box)
        main_box.pack_start(scroll, True, True, 0)

        self._populate_entries()

    def _add_section_label(self, text):
        row = Gtk.ListBoxRow()
        row.set_selectable(False)
        row.set_activatable(False)
        lbl = Gtk.Label(label=text)
        lbl.get_style_context().add_class("section-label")
        lbl.set_halign(Gtk.Align.START)
        row.add(lbl)
        self.list_box.add(row)

    def _populate_entries(self, filter_text=""):
        for child in self.list_box.get_children():
            self.list_box.remove(child)

        ft = filter_text.lower()
        pinned = [e for e in self.entries if e["id"] in self.pins]
        unpinned = [e for e in self.entries if e["id"] not in self.pins]

        if pinned:
            self._add_section_label("  PINNED")
            for entry in pinned:
                if ft and ft not in entry["content"].lower():
                    continue
                self.list_box.add(self._make_row(entry, True))

        self._add_section_label("  RECENT")
        for entry in unpinned:
            if ft and ft not in entry["content"].lower():
                continue
            self.list_box.add(self._make_row(entry, False))

        self.list_box.show_all()

    def _make_row(self, entry, is_pinned):
        row = Gtk.ListBoxRow()
        row.set_selectable(False)
        row.set_activatable(False)

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        box.get_style_context().add_class("entry-row")
        if is_pinned:
            box.get_style_context().add_class("pinned")

        # Icon
        content = entry["content"]
        is_binary = content.startswith("[[ binary data")
        icon_text = "󰋩" if is_binary else "󰧮"

        icon = Gtk.Label(label=icon_text)
        icon.get_style_context().add_class("entry-icon")
        box.pack_start(icon, False, False, 4)

        # Text
        display = content if is_binary else content.replace("\n", " ")[:100]
        text = Gtk.Label(label=display)
        text.get_style_context().add_class("entry-text")
        if is_binary:
            text.get_style_context().add_class("binary")
        text.set_halign(Gtk.Align.START)
        text.set_ellipsize(Pango.EllipsizeMode.END)
        text.set_max_width_chars(40)
        text.set_hexpand(True)
        box.pack_start(text, True, True, 0)

        # Copy btn
        copy_btn = Gtk.Button(label="󰆏")
        copy_btn.get_style_context().add_class("act-copy")
        copy_btn.set_tooltip_text("Copy")
        copy_btn.set_relief(Gtk.ReliefStyle.NONE)
        copy_btn.connect("clicked", lambda b, e=entry: self._on_copy(e))
        box.pack_end(copy_btn, False, False, 0)

        # Delete btn
        del_btn = Gtk.Button(label="󰆴")
        del_btn.get_style_context().add_class("act-delete")
        del_btn.set_tooltip_text("Delete")
        del_btn.set_relief(Gtk.ReliefStyle.NONE)
        del_btn.connect("clicked", lambda b, e=entry: self._on_delete(e))
        box.pack_end(del_btn, False, False, 0)

        # Pin btn
        pin_btn = Gtk.Button(label="󰤱" if is_pinned else "󰤰")
        pin_btn.get_style_context().add_class("act-pin-active" if is_pinned else "act-pin")
        pin_btn.set_tooltip_text("Unpin" if is_pinned else "Pin")
        pin_btn.set_relief(Gtk.ReliefStyle.NONE)
        pin_btn.connect("clicked", lambda b, e=entry, p=is_pinned: self._on_pin(e, p))
        box.pack_end(pin_btn, False, False, 0)

        row.add(box)
        return row

    def _on_copy(self, entry):
        copy_entry(entry["raw"])
        self._quit()

    def _on_pin(self, entry, is_pinned):
        if is_pinned:
            self.pins.remove(entry["id"])
        else:
            self.pins.append(entry["id"])
        save_pins(self.pins)
        self._populate_entries(self.search_entry.get_text())

    def _on_delete(self, entry):
        delete_entry(entry["raw"])
        self.entries = [e for e in self.entries if e["id"] != entry["id"]]
        if entry["id"] in self.pins:
            self.pins.remove(entry["id"])
            save_pins(self.pins)
        self._populate_entries(self.search_entry.get_text())

    def _on_clear_all(self, btn):
        subprocess.run(["cliphist", "wipe"])
        self.entries = []
        self.pins = []
        save_pins(self.pins)
        self._populate_entries()

    def _on_search_changed(self, entry):
        self._populate_entries(entry.get_text())

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

    win = ClipboardManager()
    win.show_all()
    Gtk.main()


if __name__ == "__main__":
    main()
