#!/usr/bin/env python3
"""Install the standalone picker and an optional Niri shortcut."""
import argparse
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent
BINDING = '    Mod+apostrophe hotkey-overlay-title="Open Math Symbols" { spawn "math-picker"; }'


def atomic_write(path: Path, content: str, mode=None):
    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    permission = mode if mode is not None else (path.stat().st_mode & 0o777 if path.exists() else 0o644)
    with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, delete=False) as file:
        temporary = Path(file.name)
        try:
            file.write(content)
            file.flush()
            os.fsync(file.fileno())
            temporary.chmod(permission)
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)


def configure_niri(text):
    existing = re.search(r"(?m)^.*Mod\+apostrophe\b.*$", text)
    if existing:
        if existing.group().strip() != BINDING.strip():
            raise ValueError("Super+apostrophe is already assigned; use --no-niri and choose another shortcut")
        return text
    anchor = re.search(r"(?m)^.*Mod\+Period\b.*$", text)
    if not anchor:
        raise ValueError("Cannot locate Niri's symbols shortcut; use --no-niri for manual integration")
    return text[:anchor.end()] + "\n" + BINDING + text[anchor.end():]


def install(no_niri=False):
    for executable in ("wl-copy",):
        if not shutil.which(executable):
            raise SystemExit(f"Missing dependency: {executable}")
    # Import check uses the same Python interpreter as the installed launcher.
    subprocess.run([sys.executable, "-c", 'import gi; gi.require_version("Gtk", "4.0"); from gi.repository import Gtk'], check=True)
    data = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share"))
    config = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    destination = data / "elephant-math"
    binary = Path.home() / ".local/bin/math-picker"
    if binary.exists() and not any(marker in binary.read_text() for marker in
                                   ("elephant-math/picker.py", "# elephant-math launcher")):
        raise SystemExit(f"Refusing to replace another program at {binary}")
    desktop = data / "applications/elephant-math.desktop"
    if desktop.exists() and 'X-Elephant-Math=true' not in desktop.read_text():
        raise SystemExit(f"Refusing to replace an unrelated desktop entry at {desktop}")
    niri_path = config / "niri/config.kdl"
    niri_text = None
    if not no_niri:
        original = niri_path.read_text()
        niri_text = configure_niri(original)
        with tempfile.NamedTemporaryFile(mode="w", suffix=".kdl", dir=niri_path.parent) as staged:
            staged.write(niri_text)
            staged.flush()
            subprocess.run(["niri", "validate", "-c", staged.name], check=True)
    destination.mkdir(parents=True, exist_ok=True)
    for name in ("picker.py", "engine.py", "catalog.py", "style.css"):
        shutil.copy2(ROOT / name, destination / name)
    launcher = "#!/bin/sh\nexec " + shlex.join([sys.executable, str(destination / "picker.py")]) + ' "$@"\n'
    atomic_write(binary, launcher, 0o755)
    desktop_exec = str(binary).replace("\\", "\\\\").replace('"', '\\"').replace("`", "\\`").replace("$", "\\$")
    atomic_write(desktop, f'''[Desktop Entry]
Type=Application
Name=Math Symbols
Comment=Search and copy math symbols, Greek letters, and styled alphabets
Exec="{desktop_exec}"
Icon=accessories-character-map
Terminal=false
Categories=Utility;
Keywords=math;symbols;unicode;greek;equations;
StartupWMClass=dev.local.ElephantMath
X-Elephant-Math=true
''')
    if niri_text is not None:
        backup = destination / "backups/niri-config.kdl"
        if not backup.exists():
            atomic_write(backup, original)
        atomic_write(niri_path, niri_text)
    print(f"Installed {binary}")
    print("Open with Super+apostrophe, or search for Math Symbols in Walker." if not no_niri else "Open with math-picker, or search for Math Symbols in your launcher.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-niri", action="store_true")
    args = parser.parse_args()
    install(args.no_niri)
