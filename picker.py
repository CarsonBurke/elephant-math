#!/usr/bin/env python3
"""A compact, on-demand GTK4 math symbol picker."""
from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gdk, Gio, GLib, GObject, Gtk, Pango
try:
    gi.require_version("Gtk4LayerShell", "1.0")
    from gi.repository import Gtk4LayerShell as LayerShell
except (ImportError, ValueError):
    LayerShell = None

from engine import SearchIndex, StateStore


# Grid children have 64px content, 6px padding and a 1px border on each side.
CELL_SIZE = 78
MAX_COLUMNS = 8
MAX_ROWS = 6


class SymbolItem(GObject.Object):
    def __init__(self, symbol):
        super().__init__()
        self.symbol = symbol


def icon_button(icon, label, callback=None, *, text=None):
    button = Gtk.Button()
    content = Gtk.Box(spacing=6, halign=Gtk.Align.CENTER)
    content.append(Gtk.Image.new_from_icon_name(icon))
    if text:
        content.append(Gtk.Label(label=text))
    button.set_child(content)
    button.set_tooltip_text(label)
    button.update_property([Gtk.AccessibleProperty.LABEL], [label])
    if callback:
        button.connect("clicked", callback)
    return button


class Picker(Gtk.Application):
    def __init__(self, as_window=False):
        super().__init__(application_id="dev.local.ElephantMath", flags=Gio.ApplicationFlags.DEFAULT_FLAGS)
        self.index = SearchIndex()
        self.store = StateStore()
        self.state = self.store.read()
        self.results = []
        self.pending = None
        self.window = None
        self.as_window = as_window
        self.scope = "All"
        self.connect("activate", self.activate_picker)

    @property
    def selected(self):
        return self.selection.get_selected()

    def activate_picker(self, _):
        if self.window:
            self.window.present()
            self.search.grab_focus()
            return
        display = Gdk.Display.get_default()
        monitors = display.get_monitors()
        geometries = [monitors.get_item(i).get_geometry() for i in range(monitors.get_n_items())]
        # Work in logical pixels, respecting compositor scaling. Leave room for
        # chrome and the desktop; smaller displays get fewer complete rows.
        # Layer Shell chooses the active output. Fit the smallest connected
        # output so the overlay also fits when opened on a shorter monitor.
        width = min(720, min(g.width for g in geometries) - 48) if geometries else 720
        self.columns = max(3, min(MAX_COLUMNS, (width - 52) // CELL_SIZE))
        height = min(g.height for g in geometries) if geometries else 900
        self.rows = max(2, min(MAX_ROWS, (height - 260) // CELL_SIZE))
        viewport_height = self.rows * CELL_SIZE
        self.window = Gtk.ApplicationWindow(application=self, title="Math Symbols")
        self.window.set_default_size(width, -1)
        self.window.set_resizable(False)
        self.window.set_decorated(False)
        if not self.as_window and LayerShell and LayerShell.is_supported():
            LayerShell.init_for_window(self.window)
            LayerShell.set_namespace(self.window, "elephant-math")
            LayerShell.set_layer(self.window, LayerShell.Layer.OVERLAY)
            LayerShell.set_keyboard_mode(self.window, LayerShell.KeyboardMode.EXCLUSIVE)
        provider = Gtk.CssProvider()
        provider.load_from_path(str(Path(__file__).with_name("style.css")))
        Gtk.StyleContext.add_provider_for_display(display, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        self.window.add_css_class("math-picker")
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.window.set_child(outer)

        header = Gtk.Box(spacing=8)
        self.search = Gtk.SearchEntry(placeholder_text="Search symbols or TeX", hexpand=True)
        self.search.update_property([Gtk.AccessibleProperty.LABEL], ["Search math symbols"])
        self.search.connect("changed", self.schedule_search)
        header.append(self.search)
        header.append(icon_button("window-close-symbolic", "Close · Esc", lambda _: self.quit()))
        outer.append(header)

        controls = Gtk.Box(spacing=12)
        scopes = Gtk.Box(spacing=2)
        scopes.add_css_class("scopes")
        self.scope_buttons = {}
        for scope, icon in (("All", "view-grid-symbolic"), ("Favorites", "starred-symbolic"),
                            ("Recent", "document-open-recent-symbolic")):
            button = Gtk.ToggleButton()
            content = Gtk.Box(spacing=6)
            content.append(Gtk.Image.new_from_icon_name(icon))
            if width >= 640:
                content.append(Gtk.Label(label=scope))
            button.set_child(content)
            button.set_tooltip_text(scope)
            button.update_property([Gtk.AccessibleProperty.LABEL], [scope])
            if self.scope_buttons:
                button.set_group(self.scope_buttons["All"])
            self.scope_buttons[scope] = button
            button.connect("toggled", self.change_scope, scope)
            scopes.append(button)
        self.scope_buttons["All"].set_active(True)
        controls.append(scopes)
        self.categories = ["All", *self.index.categories]
        self.category = Gtk.DropDown.new_from_strings(["All categories", *self.index.categories])
        self.category.update_property([Gtk.AccessibleProperty.LABEL], ["Symbol category"])
        self.category.set_halign(Gtk.Align.END)
        self.category.connect("notify::selected", self.change_category)
        controls.append(self.category)
        outer.append(controls)

        self.model = Gio.ListStore.new(SymbolItem)
        self.selection = Gtk.SingleSelection.new(self.model)
        self.selection.set_autoselect(True)
        self.selection.set_can_unselect(False)
        self.selection.connect("notify::selected-item", lambda *_: self.update_details())
        factory = Gtk.SignalListItemFactory()
        factory.connect("setup", self.setup_tile)
        factory.connect("bind", self.bind_tile)
        self.grid = Gtk.GridView(model=self.selection, factory=factory,
                                 min_columns=self.columns, max_columns=self.columns,
                                 single_click_activate=True, enable_rubberband=False)
        self.grid.update_property([Gtk.AccessibleProperty.LABEL], ["Math symbols; activate to copy"])
        self.grid.connect("activate", self.activate_tile)
        self.scroll = Gtk.ScrolledWindow(hexpand=True)
        self.scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.scroll.set_min_content_height(viewport_height)
        self.scroll.set_max_content_height(viewport_height)
        self.scroll.set_propagate_natural_height(True)
        self.scroll.set_child(self.grid)
        self.pages = Gtk.Stack()
        self.pages.add_named(self.scroll, "symbols")
        empty = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10,
                        halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER)
        empty.append(Gtk.Image(icon_name="edit-find-symbolic", pixel_size=32))
        self.empty_title = Gtk.Label()
        self.empty_title.add_css_class("empty-title")
        empty.append(self.empty_title)
        self.empty_hint = Gtk.Label()
        self.empty_hint.add_css_class("muted")
        empty.append(self.empty_hint)
        clear = Gtk.Button(label="Clear search and filters")
        clear.connect("clicked", self.clear_filters)
        empty.append(clear)
        self.pages.add_named(empty, "empty")
        outer.append(self.pages)

        footer = Gtk.Box(spacing=8)
        footer.add_css_class("details")
        description = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3, hexpand=True,
                              valign=Gtk.Align.CENTER)
        self.details = Gtk.Label(xalign=0, ellipsize=Pango.EllipsizeMode.END)
        self.details.set_max_width_chars(32)
        self.details.add_css_class("symbol-name")
        description.append(self.details)
        self.metadata = Gtk.Label(xalign=0, ellipsize=Pango.EllipsizeMode.END)
        self.metadata.add_css_class("metadata")
        description.append(self.metadata)
        footer.append(description)
        self.star = icon_button("non-starred-symbolic", "Favorite · Ctrl+F", lambda _: self.toggle_favorite())
        footer.append(self.star)
        self.latex = icon_button("text-x-generic-symbolic", "Copy TeX · Ctrl+L",
                                 lambda _: self.copy(latex=True), text="TeX")
        footer.append(self.latex)
        self.copy_button = icon_button("edit-copy-symbolic", "Copy symbol · Enter",
                                       lambda _: self.copy(), text="Copy")
        self.copy_button.add_css_class("primary")
        footer.append(self.copy_button)
        outer.append(footer)

        self.count = Gtk.Label(xalign=0, hexpand=True)
        self.count.add_css_class("muted")
        self.count.set_halign(Gtk.Align.END)
        self.count.set_tooltip_text("Matching symbols")
        controls.insert_child_after(self.count, scopes)
        self.help = Gtk.MenuButton(icon_name="input-keyboard-symbolic")
        self.help.set_tooltip_text("Keyboard shortcuts")
        self.help.update_property([Gtk.AccessibleProperty.LABEL], ["Keyboard shortcuts"])
        popover = Gtk.Popover()
        shortcuts = Gtk.Grid(column_spacing=24, row_spacing=10)
        shortcuts.set_margin_top(12)
        shortcuts.set_margin_bottom(12)
        shortcuts.set_margin_start(12)
        shortcuts.set_margin_end(12)
        for row, (key, action) in enumerate((("Enter", "Copy symbol"), ("Ctrl+L", "Copy TeX"),
                                            ("Ctrl+F", "Toggle favorite"), ("↑ ↓", "Browse rows"),
                                            ("PgUp PgDn", "Browse pages"), ("Esc", "Close"))):
            shortcuts.attach(Gtk.Label(label=key, xalign=0), 0, row, 1, 1)
            shortcuts.attach(Gtk.Label(label=action, xalign=0), 1, row, 1, 1)
        popover.set_child(shortcuts)
        self.help.set_popover(popover)
        header.insert_child_after(self.help, self.search)
        controller = Gtk.EventControllerKey()
        controller.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        controller.connect("key-pressed", self.key_pressed)
        self.window.add_controller(controller)
        self.refresh()
        self.window.present()
        self.search.grab_focus()

    def change_scope(self, button, scope):
        if button.get_active():
            self.scope = scope
            if hasattr(self, "model"):
                self.refresh()
                self.search.grab_focus()

    def change_category(self, *_):
        self.refresh()
        self.search.grab_focus()

    def clear_filters(self, *_):
        self.search.set_text("")
        self.category.set_selected(0)
        self.scope_buttons["All"].set_active(True)
        self.refresh()
        self.search.grab_focus()

    def setup_tile(self, _, item):
        tile = Gtk.Overlay(width_request=64, height_request=64)
        glyph = Gtk.Label()
        glyph.add_css_class("glyph")
        tile.set_child(glyph)
        star = Gtk.Image(icon_name="starred-symbolic", pixel_size=10,
                         halign=Gtk.Align.END, valign=Gtk.Align.START)
        star.add_css_class("favorite-marker")
        star.set_can_target(False)
        tile.add_overlay(star)
        item.set_child(tile)

    def bind_tile(self, _, item):
        symbol = item.get_item().symbol
        tile = item.get_child()
        tile.get_child().set_text(symbol["glyph"])
        favorite = symbol["glyph"] in self.state["favorites"]
        tile.get_child().get_next_sibling().set_visible(favorite)
        tooltip = f'{symbol["label"]} · {symbol["codepoint"]}'
        if symbol["latex"]:
            tooltip += f'\n{symbol["latex"]}'
        tile.set_tooltip_text(tooltip)
        tile.update_property([Gtk.AccessibleProperty.LABEL],
                             [tooltip + (" · Favorite" if favorite else "")])

    def activate_tile(self, _, position):
        # A click refers to the tile currently on screen. A pending text query
        # must not turn its old model position into a different symbol.
        item = self.model.get_item(position)
        if item:
            if self.pending:
                GLib.source_remove(self.pending)
                self.pending = None
            self.copy(symbol=item.symbol)

    def schedule_search(self, _):
        if self.pending:
            GLib.source_remove(self.pending)
        self.pending = GLib.timeout_add(20, self.scheduled_refresh)

    def scheduled_refresh(self):
        self.pending = None
        return self.refresh()

    def ensure_current(self):
        if self.pending or self.search.get_text() != self.rendered_query:
            self.refresh()

    def refresh(self, preserve=None):
        if self.pending:
            GLib.source_remove(self.pending)
        self.pending = None
        category = self.categories[self.category.get_selected()]
        query = self.search.get_text()
        self.rendered_query = query
        self.results = self.index.search(query, category=category, **self.state, limit=len(self.index.symbols))
        if self.scope != "All":
            allowed = self.state["favorites" if self.scope == "Favorites" else "recent"]
            self.results = [symbol for symbol in self.results if symbol["glyph"] in allowed]
            if self.scope == "Recent" and not query.strip():
                order = {glyph: i for i, glyph in enumerate(self.state["recent"])}
                self.results.sort(key=lambda symbol: order[symbol["glyph"]])
        self.model.splice(0, self.model.get_n_items(), [SymbolItem(s) for s in self.results])
        self.selection.set_selected(next((i for i, s in enumerate(self.results) if s["glyph"] == preserve), 0))
        self.scroll.get_vadjustment().set_value(0)
        self.count.set_text(f"{len(self.results):,}")
        self.pages.set_visible_child_name("symbols" if self.results else "empty")
        if not self.results:
            empty_scope = not query.strip() and category == "All"
            if empty_scope and self.scope == "Favorites":
                self.empty_title.set_text("No favorites yet")
                self.empty_hint.set_text("Save a symbol with Ctrl+F.")
            elif empty_scope and self.scope == "Recent":
                self.empty_title.set_text("Nothing copied yet")
                self.empty_hint.set_text("Your recently copied symbols will appear here.")
            else:
                self.empty_title.set_text("No symbols found")
                self.empty_hint.set_text("Try another name or clear the filters.")
        self.update_details()
        if preserve and self.results:
            self.grid.scroll_to(self.selected, Gtk.ListScrollFlags.NONE, None)
        return GLib.SOURCE_REMOVE

    def update_details(self):
        if not hasattr(self, "star"):
            return
        self.metadata.remove_css_class("error")
        self.metadata.set_tooltip_text(None)
        item = self.selection.get_selected_item()
        symbol = item.symbol if item else None
        for button in (self.star, self.copy_button):
            button.set_sensitive(bool(symbol))
        self.latex.set_sensitive(bool(symbol and symbol["latex"]))
        if not symbol:
            self.details.set_text("No selection")
            self.metadata.set_text("")
            return
        self.details.set_text(symbol["label"])
        self.details.set_tooltip_text(symbol["name"])
        self.metadata.set_text(" · ".join(filter(None, (symbol["latex"], symbol["codepoint"]))))
        favorite = symbol["glyph"] in self.state["favorites"]
        self.star.get_child().get_first_child().set_from_icon_name("starred-symbolic" if favorite else "non-starred-symbolic")
        label = "Remove favorite · Ctrl+F" if favorite else "Favorite · Ctrl+F"
        self.star.set_tooltip_text(label)
        self.star.update_property([Gtk.AccessibleProperty.LABEL], [label])
        self.latex.set_tooltip_text("Copy TeX · Ctrl+L" if symbol["latex"] else "No TeX command for this symbol")

    def key_pressed(self, _, key, code, state):
        ctrl = bool(state & Gdk.ModifierType.CONTROL_MASK)
        focus = self.window.get_focus()
        searching = focus is not None and (focus == self.search or focus.is_ancestor(self.search))
        in_grid = focus is not None and (focus == self.grid or focus.is_ancestor(self.grid))
        if key == Gdk.KEY_Escape:
            if self.help.get_popover().get_visible():
                self.help.popdown()
            elif self.category_popup_open():
                # Let Gtk.DropDown consume Escape and restore its own focus.
                return False
            else:
                self.quit()
            return True
        if key in (Gdk.KEY_Return, Gdk.KEY_KP_Enter) and (searching or in_grid):
            self.copy(); return True
        if ctrl and key in (Gdk.KEY_l, Gdk.KEY_L):
            self.copy(latex=True); return True
        if ctrl and key in (Gdk.KEY_f, Gdk.KEY_F):
            self.toggle_favorite(); return True
        moves = {Gdk.KEY_Down: self.columns, Gdk.KEY_Up: -self.columns,
                 Gdk.KEY_Page_Down: self.columns * self.rows, Gdk.KEY_Page_Up: -self.columns * self.rows}
        # Left/Right edit a nonempty query. With an empty search they browse cells.
        if not self.search.get_text():
            moves.update({Gdk.KEY_Right: 1, Gdk.KEY_Left: -1})
        if key in moves and searching and not ctrl:
            self.ensure_current()
            if self.results:
                selected = max(0, min(len(self.results) - 1, self.selected + moves[key]))
                self.selection.set_selected(selected)
                self.grid.scroll_to(selected, Gtk.ListScrollFlags.NONE, None)
            return True
        return False

    def category_popup_open(self):
        def visible_popover(widget):
            child = widget.get_first_child()
            while child:
                if isinstance(child, Gtk.Popover) and child.get_visible():
                    return True
                if visible_popover(child):
                    return True
                child = child.get_next_sibling()
            return False
        return visible_popover(self.category)

    def toggle_favorite(self):
        self.ensure_current()
        if not self.results:
            return
        glyph = self.results[self.selected]["glyph"]
        try:
            self.state = self.store.update(glyph, favorite=True)
            self.refresh(preserve=glyph)
        except (OSError, ValueError) as error:
            self.show_error(str(error))

    def copy(self, latex=False, *, symbol=None):
        if symbol is None:
            self.ensure_current()
            if not self.results:
                return
            symbol = self.results[self.selected]
        if latex and not symbol["latex"]:
            self.show_error("No TeX command for this symbol.")
            return
        value = symbol["latex"] if latex else symbol["glyph"]
        try:
            subprocess.run(["wl-copy"], input=value, text=True, check=True, timeout=5)
            self.store.update(symbol["glyph"])
        except (OSError, ValueError, subprocess.SubprocessError) as error:
            self.show_error(f"Could not copy: {error}")
            return
        self.quit()

    def show_error(self, message):
        self.metadata.set_text(message)
        self.metadata.set_tooltip_text(message)
        self.metadata.add_css_class("error")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--window", action="store_true", help="use a regular window instead of a Wayland overlay")
    args = parser.parse_args()
    raise SystemExit(Picker(as_window=args.window).run([sys.argv[0]]))
