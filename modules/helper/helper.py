"""Launch the main application with the modules/helper overrides.

Run from the repository root:

    .venv/Scripts/python.exe modules/helper/helper.py

The launcher derives the repository root from this file, so it also works when
invoked with an absolute path from another working directory.

delta/ mirrors the main project:

    delta/project/<sub>/<name>.py  replaces  project/<sub>/<name>.py
    delta/cards.py                 replaces  cards.py (the composition root)
    delta/assets/<file>            replaces  assets/<file>

A file found in delta/ is used, otherwise the main project's file. New files
that exist only in delta/project/ are importable as project.<name>.

Assets come in three layers, later ones replace files of the same name: the main
assets/, then the navigation module's delta/assets/ (the helper brings its own
navigation logic and uses that module's browser assets), then delta/assets/.

All generated output goes flat into temp/: the merged assets and the module's
own state file helper_state.json (plus its backups). Dash serves temp/ as its
assets folder, so its hot reload is switched off (a state save would reload the
browser). No __pycache__ folders are written.

On startup, if helper_state.json exists, the user is asked whether to back it
up (temp/helper_state.json_01.bak, _02.bak, ...) and start fresh.
"""

from __future__ import annotations

import importlib
import importlib.abc
import importlib.util
import os
import shutil
import sys
from pathlib import Path
from types import ModuleType

sys.dont_write_bytecode = True  # no __pycache__ in delta/ or anywhere else

MODULE_DIR = Path(__file__).resolve().parent
# For <repo>/modules/helper/helper.py:
# parents[0] is <repo>/modules; parents[1] is <repo>.
if len(MODULE_DIR.parents) < 2:
    raise RuntimeError(f"Unexpected helper module location: {MODULE_DIR}")
ROOT = MODULE_DIR.parents[1]
DELTA_DIR = MODULE_DIR / "delta"
TEMP_DIR = MODULE_DIR / "temp"
STATE_FILE = TEMP_DIR / "helper_state.json"

# Main project names.
MAIN_PACKAGE = "project"
MAIN_ENTRY = ROOT / "cards.py"
# delta/ mirrors the main names.
DELTA_PACKAGE = MAIN_PACKAGE
DELTA_ENTRY = MAIN_ENTRY.name
DELTA_ASSETS = "assets"
# The navigation module's assets, relative to the repository root.
NAVIGATION_ASSETS = Path("modules", "navigation", "delta", DELTA_ASSETS)


def asset_layers(root: Path = ROOT, delta_dir: Path = DELTA_DIR) -> tuple[Path, ...]:
    """The asset folders in merge order (main, navigation, helper); a later one replaces same-named files."""
    return (root / "assets", root / NAVIGATION_ASSETS, delta_dir / DELTA_ASSETS)


def _path_matches(entry: str, target: Path) -> bool:
    """Compare sys.path entries robustly, including the empty current-dir entry."""
    try:
        return Path(entry or Path.cwd()).resolve() == target.resolve()
    except (OSError, RuntimeError, TypeError):
        return False


def _prioritize_repository_root() -> None:
    """Put the actual repository root first, independent of the launch cwd."""
    root_string = str(ROOT)
    sys.path[:] = [entry for entry in sys.path if not _path_matches(entry, ROOT)]
    sys.path.insert(0, root_string)


_prioritize_repository_root()


# --- Python overrides --------------------------------------------------------


def code_source(relative: str, delta_dir: Path = DELTA_DIR) -> Path:
    """The file that runs for `relative` (e.g. "services/navigation.py"): delta/project/ if present, else main."""
    changed = delta_dir / DELTA_PACKAGE / relative
    return changed if changed.is_file() else ROOT / MAIN_PACKAGE / relative


def asset_source(name: str, delta_dir: Path = DELTA_DIR, root: Path = ROOT) -> Path:
    """The asset that is served as `name`: delta/assets/, else the navigation module's, else the main assets/."""
    for folder in reversed(asset_layers(root, delta_dir)):
        if (folder / name).is_file():
            return folder / name
    return root / "assets" / name


def delta_modules(delta_dir: Path = DELTA_DIR) -> dict[str, Path]:
    """Map dotted main-package names to their files under delta/project/."""
    package_dir = delta_dir / DELTA_PACKAGE
    found: dict[str, Path] = {}
    if not package_dir.is_dir():
        return found
    for source in sorted(package_dir.rglob("*.py")):
        parts = list(source.relative_to(package_dir).with_suffix("").parts)
        if "__pycache__" in parts:
            continue
        if parts[-1] == "__init__":
            parts.pop()
        found[".".join([MAIN_PACKAGE, *parts])] = source
    return found


class DeltaFinder(importlib.abc.MetaPathFinder):
    """Serve MAIN_PACKAGE modules from delta/project/ when a file exists there."""

    def __init__(self, delta_dir: Path = DELTA_DIR, root: Path = ROOT) -> None:
        self.package_dir = delta_dir / DELTA_PACKAGE
        self.main_dir = root / MAIN_PACKAGE

    def find_spec(self, fullname, path=None, target=None):
        if fullname != MAIN_PACKAGE and not fullname.startswith(MAIN_PACKAGE + "."):
            return None
        parts = fullname.split(".")[1:]
        changed = self.package_dir.joinpath(*parts)
        if parts and changed.with_suffix(".py").is_file():
            return importlib.util.spec_from_file_location(fullname, changed.with_suffix(".py"))
        init = changed / "__init__.py"
        if init.is_file():
            # Main folder first: unchanged submodules keep coming from the main project.
            locations = [str(folder) for folder in (self.main_dir.joinpath(*parts), changed) if folder.is_dir()]
            return importlib.util.spec_from_file_location(fullname, init, submodule_search_locations=locations)
        return None  # not changed: the normal import finds the main project's file


def install_delta_finder(delta_dir: Path = DELTA_DIR) -> dict[str, Path]:
    """Install the finder before anything imports the main package; return the overrides."""
    overrides = delta_modules(delta_dir)
    preloaded = [name for name in overrides if name in sys.modules]
    if preloaded:
        raise RuntimeError(
            f"{', '.join(preloaded)} imported before the helper overrides; "
            "start the app with modules/helper/helper.py"
        )
    sys.meta_path[:] = [finder for finder in sys.meta_path if not isinstance(finder, DeltaFinder)]
    sys.meta_path.insert(0, DeltaFinder(delta_dir))
    return overrides


# --- temp/: assets and state ---------------------------------------------------


def _kept_in_temp(name: str) -> bool:
    """The state file and its backups survive a temp/ rebuild."""
    return name.startswith(STATE_FILE.name)


def _flat_files(folder: Path) -> dict[str, Path]:
    """All files below `folder` by file name; the same name at two depths is an error."""
    files: dict[str, Path] = {}
    if not folder.is_dir():
        return files
    for source in sorted(folder.rglob("*")):
        if not source.is_file() or "__pycache__" in source.parts:
            continue
        if source.name in files:
            raise ValueError(f"Cannot flatten {folder}: {files[source.name]} and {source} share a name")
        files[source.name] = source
    return files


def build_temp(root: Path = ROOT, delta_dir: Path = DELTA_DIR, temp_dir: Path = TEMP_DIR) -> dict[str, Path]:
    """Rebuild temp/ flat from the asset layers (main, navigation, helper); state file and backups stay.

    Returns the copied file names with their sources.
    """
    temp_dir.mkdir(parents=True, exist_ok=True)
    for entry in temp_dir.iterdir():
        if entry.is_dir():
            shutil.rmtree(entry)
        elif not _kept_in_temp(entry.name):
            entry.unlink()

    merged: dict[str, Path] = {}
    for folder in asset_layers(root, delta_dir):
        merged.update(_flat_files(folder))
    reserved = sorted(name for name in merged if _kept_in_temp(name))
    if reserved:
        raise ValueError(f"Asset name(s) reserved for generated files in temp/: {', '.join(reserved)}")
    for name, source in merged.items():
        shutil.copy2(source, temp_dir / name)
    return merged


def redirect_state(state_file: Path = STATE_FILE) -> None:
    """Make the app's JsonStateStore write to temp/helper_state.json, never to data/."""
    state = importlib.import_module(f"{MAIN_PACKAGE}.store.state")
    original = state.JsonStateStore
    if getattr(original, "redirected_to", None) is not None:
        return

    class ModuleStateStore(original):
        redirected_to = state_file

        def __init__(self, requested_path, *args, **kwargs) -> None:
            self.requested_path = Path(requested_path)  # retained for diagnostics
            super().__init__(state_file, *args, **kwargs)

    state.JsonStateStore = ModuleStateStore


def redirect_assets(temp_dir: Path = TEMP_DIR) -> None:
    """Make the server build Dash on temp/ as assets folder, without hot reload."""
    os.environ.setdefault("DASH_HOT_RELOAD", "false")
    server = importlib.import_module(f"{MAIN_PACKAGE}.server")
    original = getattr(server, "Dash", None)
    if not isinstance(original, type):
        raise RuntimeError(f"{server.__file__} must import Dash as 'from dash import Dash'")
    if getattr(original, "assets_redirected_to", None) is not None:
        return

    class TempAssetsDash(original):
        assets_redirected_to = temp_dir

        def __init__(self, *args, **kwargs) -> None:
            kwargs["assets_folder"] = str(temp_dir)
            super().__init__(*args, **kwargs)

    server.Dash = TempAssetsDash


def _find_unique_backup_path(state_file: Path = STATE_FILE) -> Path:
    """Return the next available backup path in temp/: helper_state.json_01.bak, _02.bak, ..."""
    for i in range(1, 100):
        candidate = state_file.parent / f"{state_file.name}_{i:02d}.bak"
        if not candidate.exists():
            return candidate
    raise RuntimeError("Could not find a free backup name (100 existing backups)")


def prepare_state(state_file: Path = STATE_FILE) -> None:
    """Check if helper_state.json exists and ask for backup before starting fresh."""
    if not state_file.exists():
        print("No existing state file found.")
        return

    print(f"Found existing state file: {state_file}")
    try:
        response = input(f"Backup existing {state_file.name}? (y/n): ").strip().lower()
    except EOFError:
        # Non-interactive environment (e.g. piped input): keep the existing file.
        print("No input available; keeping existing state file.")
        return

    if response in ("y", "yes"):
        backup_path = _find_unique_backup_path(state_file)
        state_file.rename(backup_path)
        print(f"Backed up existing state to: {backup_path}")
        print(f"Starting with a fresh {state_file.name}.")
    else:
        print("Keeping existing state file.")


# --- composition root ----------------------------------------------------------------


def entry_source(delta_dir: Path = DELTA_DIR) -> Path:
    """delta/cards.py if present, otherwise the main project's composition root."""
    changed = delta_dir / DELTA_ENTRY
    return changed if changed.is_file() else MAIN_ENTRY


def _load_entry(source: Path) -> ModuleType:
    """Load the composition root under the main entry's module name (``cards``)."""
    if not source.is_file():
        raise FileNotFoundError(f"Project application entry point not found: {source}")
    name = MAIN_ENTRY.stem
    loaded = sys.modules.get(name)
    if loaded is not None:
        origin = getattr(getattr(loaded, "__spec__", None), "origin", None)
        if origin and Path(origin).resolve() == source.resolve():
            return loaded
        raise RuntimeError(f"A different module named {name!r} was imported first: {origin}")

    spec = importlib.util.spec_from_file_location(name, source)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not create an import spec for {source}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        sys.modules.pop(name, None)
        raise
    return module


def _ignored_delta(delta_dir: Path = DELTA_DIR) -> list[Path]:
    known = {DELTA_PACKAGE, DELTA_ENTRY, DELTA_ASSETS, "__pycache__"}
    if not delta_dir.is_dir():
        return []
    return [entry for entry in sorted(delta_dir.iterdir()) if entry.name not in known]


def _shown(source: Path) -> str:
    """A source path relative to modules/ (helper/delta/..., navigation/delta/...)."""
    return source.relative_to(MODULE_DIR.parent).as_posix()


def _report(overrides: dict[str, Path], assets: dict[str, Path], entry: Path) -> None:
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        return  # the debug reloader's child: already reported by the first start
    lines = [f"  {_shown(source)} -> {name}" for name, source in overrides.items()]
    if entry != MAIN_ENTRY:
        lines.append(f"  {_shown(entry)} -> {MAIN_ENTRY.name}")
    lines += [
        f"  {_shown(source)} -> temp/{name}"
        for name, source in assets.items()
        if source.is_relative_to(MODULE_DIR.parent)
    ]
    print("helper overrides:" if lines else "helper overrides: none, running the main code")
    for line in lines:
        print(line)
    for entry_path in _ignored_delta():
        print(f"  ignored (not part of the main structure): {_shown(entry_path)}")


def load_app() -> ModuleType:
    """Install the overrides, rebuild temp/, redirect state and assets, then load the composition root."""
    overrides = install_delta_finder()
    assets = build_temp()
    redirect_state()
    redirect_assets()
    entry = entry_source()
    _report(overrides, assets, entry)
    return _load_entry(entry)


def main() -> None:
    # app.run(debug=True) runs this script again in a reloader child (WERKZEUG_RUN_MAIN=true): ask only once
    if os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        prepare_state()
    load_app().main()


if __name__ == "__main__":
    main()
