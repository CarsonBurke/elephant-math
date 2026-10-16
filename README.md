# Math Symbols

A fast native math picker that works alongside Elephant and Walker. It provides
a compact glyph grid, friendly names and aliases, case-sensitive TeX lookup,
favorites, recent symbols, category browsing, and Unicode metadata.

## Use

Press **Super + apostrophe** in Niri, run **`math-picker`**, or search for
**Math Symbols** in Walker. On supported Wayland compositors it opens as a
centered keyboard-focused overlay; otherwise it uses a regular GTK window.

| Search | First result |
| --- | --- |
| `sum`, `summation`, `\sum` | ∑ |
| `real numbers`, `R`, `mathbb{R}`, `\mathbb{R}` | ℝ |
| `gradient`, `nabla`, `del`, `gradiant` | ∇ |
| `bold A` / `bold a` | 𝐀 / 𝐚 |
| `\Sigma` / `\sigma` | Σ / σ |
| `italic x` | 𝑥 |
| `U+2211` or `∑` | ∑ |

Choose a category from the dropdown, or type `sets`, `greek`, `styled letters`,
`superscripts`, or `subscripts`. Prefix a category with `/` to combine it with
a search: `/sets real` or `/styled letters italic x`. `favorites` and `recent`
show your saved or recently copied symbols. The grid shows six complete rows on the current displays, with up to eight
columns. Smaller screens get fewer rows and columns. Scroll or use Page Up/Down
to browse all matches; the result count is the full matching total. GTK
virtualizes the grid so offscreen results do not each need their own tile.

- **Enter** copies the selected Unicode glyph and closes the picker.
- **Ctrl+L** copies its TeX expression and closes the picker.
- **Ctrl+F** toggles a favorite without closing the picker.
- **Up/Down** browse rows while the search input stays focused. **Page Up/Down**
  browse a page at a time. Left/Right edit your query; with an empty query they
  browse individual symbols. Tab into the grid for native arrow-key navigation.
- **Tab** navigates the category dropdown and buttons.
- **Escape** closes the picker.
- **Click a tile** to copy it immediately. Hover to see its name and TeX command.
- The star and clock filters show favorites and recents; category filters combine
  with either view. The keyboard icon opens the shortcut reference.

Favorites have a small gold star. With an empty query, favorites and recents appear
first. Exact names and aliases outrank partial words and typo matches, even if
an unrelated symbol is a favorite. TeX commands and styled Latin letter suffixes
preserve meaningful case. The detail strip shows the selected name, TeX command,
and codepoint; hover over the name for its official Unicode name.

The catalog contains 1,328 characters: common operators, relations, sets, logic,
arrows, Greek letters, superscripts/subscripts, every assigned Mathematical
Alphanumeric Symbol, and legacy styled letters outside that Unicode block.
It excludes incomplete glyph fragments such as “summation bottom.”

TeX expressions depend on your document's fonts and packages; some require
amssymb, amsmath, mathrsfs, or unicode-math. If no TeX mapping is defined,
the TeX copy button is disabled and Ctrl+L explains that no mapping exists. The picker copies text rather than inserting
it into your document automatically.

## Install

Requirements: Python 3.11+, PyGObject, GTK 4.12+, and `wl-clipboard`.
GTK4 Layer Shell enables the Wayland overlay and is optional. Elephant/Walker
are optional: the desktop entry works with other application launchers too.

```sh
python install.py
```

The installer copies the app to `~/.local/share/elephant-math/`, creates
`~/.local/bin/math-picker` and a `Math Symbols` desktop entry, and adds Niri's
Super+apostrophe binding. It validates Niri's proposed config before writing,
follows existing dotfile symlinks, and refuses conflicting bindings or programs.
An original Niri config backup is retained under
`~/.local/share/elephant-math/backups/`.

Pass **`--no-niri`** to install without changing keyboard bindings. XDG config
and data locations are respected; the executable goes in `~/.local/bin`.
No launcher or desktop restart is required. Installed copies run independently
of the source repository; rerun the installer after editing the source.

The existing Walker `.` symbol prefix and apostrophe exact-search prefix are
unchanged. The new shortcut is a desktop hotkey, not a Walker search prefix.

To uninstall, remove the `Mod+apostrophe` line labeled “Open Math Symbols” from
Niri, `~/.local/bin/math-picker`, and
`~/.local/share/applications/elephant-math.desktop`. Delete
`~/.local/share/elephant-math/` if you also want to remove favorites and recents.
Do not restore the whole Niri backup if you have subsequently edited that file.

## Develop

```sh
python -m unittest discover -s tests -v
python picker.py --window
```

`tests/ui_checks.py` exercises GTK grid navigation, keyboard focus, and copying
immediately after changing a query, six-row sizing, virtualized full-catalog
browsing, combined filters, popup dismissal, and mouse/search races. Run it in an isolated desktop session with
a separate `XDG_DATA_HOME`; the regular unit suite does not open any windows.

`catalog.py` defines labels, aliases, and Unicode metadata. `engine.py` owns
search/ranking and atomic persistent state. `picker.py` handles the GTK UI and
clipboard, and `install.py` installs the app. Search needs no network service,
model, or background indexing. On the development machine representative engine
queries took roughly 4–20 ms before rendering; this is not a latency guarantee
for other hardware.

An initial integration experiment used Elephant's dynamic Lua menu API.
Overlapping queries in Elephant 2.22.1 crashed the isolated test daemon with
an index-out-of-range panic in `menus.Query`, where concurrent queries replace
the menu's entries while another query iterates them. The final app runs its
own search and does not install a dynamic menu or modify the Elephant service.
