"""Run inside an isolated Wayland session: python tests/ui_checks.py."""
from pathlib import Path
import sys
import tempfile
import traceback
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine import StateStore
from picker import Picker, CELL_SIZE, Gdk, GLib, Gtk

app = Picker(as_window=True)
data = tempfile.TemporaryDirectory(prefix="math-picker-ui-")
app.store = StateStore(Path(data.name) / "state.json")
app.state = app.store.read()
failures = []


def checks():
    try:
        # Complete rows and full-catalog browsing, with a bounded widget pool.
        assert 2 <= app.rows <= 6
        assert app.scroll.get_height() == app.rows * CELL_SIZE, app.scroll.get_height()
        assert app.model.get_n_items() == len(app.index.symbols)
        rendered = 0
        child = app.grid.get_first_child()
        while child:
            rendered += 1
            child = child.get_next_sibling()
        assert rendered < len(app.results), rendered
        app.refresh()
        app.search.grab_focus()
        app.key_pressed(None, Gdk.KEY_Down, 0, Gdk.ModifierType(0))
        assert app.selected == app.columns
        app.key_pressed(None, Gdk.KEY_Page_Down, 0, Gdk.ModifierType(0))
        assert app.selected == app.columns * (app.rows + 1)
        app.search.set_text("sum")
        app.refresh()
        assert app.results[0]["glyph"] == "∑"
        assert app.key_pressed(None, Gdk.KEY_Right, 0, Gdk.ModifierType(0)) is False
        assert app.selected == 0
        app.category.grab_focus()
        assert app.key_pressed(None, Gdk.KEY_Return, 0, Gdk.ModifierType(0)) is False
        assert app.key_pressed(None, Gdk.KEY_Down, 0, Gdk.ModifierType(0)) is False
        app.star.grab_focus()
        assert app.key_pressed(None, Gdk.KEY_Return, 0, Gdk.ModifierType(0)) is False

        # Favorites and categories intersect; Recent orders by time, even when
        # an older symbol is a favorite.
        app.state = app.store.update("∑", favorite=True)
        app.store.update("∑")
        app.state = app.store.update("∇")
        app.clear_filters()
        app.scope_buttons["Recent"].set_active(True)
        assert [s["glyph"] for s in app.results] == ["∇", "∑"]
        app.scope_buttons["Favorites"].set_active(True)
        assert [s["glyph"] for s in app.results] == ["∑"]
        app.category.set_selected(app.categories.index("Greek"))
        assert not app.results
        assert app.pages.get_visible_child_name() == "empty"
        assert not app.star.get_sensitive()
        assert not app.copy_button.get_sensitive()
        assert not app.latex.get_sensitive()
        app.clear_filters()
        assert len(app.results) == len(app.index.symbols)

        # Copy actions flush a pending query and return from the application.
        app.search.set_text("gradient")
        with patch("picker.subprocess.run") as copied, patch.object(app, "quit") as quit_app:
            app.copy()
            assert copied.call_args.kwargs["input"] == "∇"
            quit_app.assert_called_once()
        app.search.set_text("sum")
        with patch("picker.subprocess.run") as copied, patch.object(app, "quit") as quit_app:
            app.copy(latex=True)
            assert copied.call_args.kwargs["input"] == r"\sum"
            quit_app.assert_called_once()
        # A mouse activation copies the activated tile, not the previous selection.
        app.clear_filters()
        expected = app.results[5]["glyph"]
        app.search.set_text("gradient")  # The old tiles are still on screen.
        with patch("picker.subprocess.run") as copied, patch.object(app, "quit"):
            app.grid.emit("activate", 5)
            assert copied.call_args.kwargs["input"] == expected
        assert app.pending is None
        # A failed mouse copy stays visible; subsequent keyboard copying still
        # resolves the typed query rather than the old model.
        with patch("picker.subprocess.run", side_effect=OSError("clipboard unavailable")):
            app.grid.emit("activate", 5)
        assert app.metadata.has_css_class("error")
        with patch("picker.subprocess.run") as copied, patch.object(app, "quit"):
            app.copy()
            assert copied.call_args.kwargs["input"] == "∇"
        missing_tex = next(s for s in app.index.symbols if not s["latex"])
        app.search.set_text(missing_tex["glyph"])
        app.refresh()
        assert not app.latex.get_sensitive()
        with patch("picker.subprocess.run") as copied:
            app.copy(latex=True)
            copied.assert_not_called()
        app.help.popup()
        assert app.help.get_popover().get_visible()
        app.key_pressed(None, Gdk.KEY_Escape, 0, Gdk.ModifierType(0))
        assert not app.help.get_popover().get_visible()
        app.category.get_first_child().set_active(True)
        assert app.category_popup_open()
        with patch.object(app, "quit") as quit_app:
            assert app.key_pressed(None, Gdk.KEY_Escape, 0, Gdk.ModifierType(0)) is False
            quit_app.assert_not_called()
        print(f"GTK checks passed: {app.rows} full rows, virtualized catalog ({rendered} grid children), navigation, filters, copy, shortcuts", flush=True)
    except Exception as error:
        failures.append(error)
        print(f"GTK checks failed: {error!r}", file=sys.stderr, flush=True)
        traceback.print_exc()
    finally:
        app.quit()
    return GLib.SOURCE_REMOVE


app.connect("activate", lambda _: GLib.timeout_add(300, checks))
GLib.timeout_add_seconds(15, lambda: (failures.append(TimeoutError("UI checks timed out")), app.quit(), False)[-1])
app.run([sys.argv[0]])
data.cleanup()
raise SystemExit(bool(failures))
