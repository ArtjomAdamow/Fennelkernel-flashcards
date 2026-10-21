"""Launch the main application with the modules/cluster overrides.

Run from the repository root:

    .venv/Scripts/python.exe modules/cluster/cluster.py

The launcher derives the repository root from this file, so it also works when
invoked with an absolute path from another working directory.

delta/ mirrors the main project:

    delta/project/<sub>/<name>.py  replaces  project/<sub>/<name>.py
    delta/cards.py                 replaces  cards.py (the composition root)
    delta/assets/<file>            replaces  assets/<file>

A file found in delta/ is used, otherwise the main project's file. New files
that exist only in delta/project/ are importable as project.<name>.

All generated output goes flat into temp/: the merged assets and the module's
own state files (plus their backups): cluster_state.json for the cards (deck
view), cluster_space_state.json for the decks (space view) and
cluster_view_state.json for the checked cards of each deck. Dash serves
temp/ as its assets folder, so its hot reload is switched off (a state save
would reload the browser). No __pycache__ folders are written.

On startup, if a state file exists, the user is asked whether to back them up
(temp/cluster_state.json_01.bak, _02.bak, ...) and start fresh.
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
# For <repo>/modules/cluster/cluster.py:
# parents[0] is <repo>/modules; parents[1] is <repo>.
if len(MODULE_DIR.parents) < 2:
    raise RuntimeError(f"Unexpected cluster module location: {MODULE_DIR}")
ROOT = MODULE_DIR.parents[1]
DELTA_DIR = MODULE_DIR / "delta"
TEMP_DIR = MODULE_DIR / "temp"
STATE_FILE = TEMP_DIR / "cluster_state.json"
SPACE_STATE_FILE = TEMP_DIR / "cluster_space_state.json"
# The state files the composition root asks for (by name), and where they are kept in temp/
STATE_FILES = {"user_state.json": STATE_FILE, "space_state.json": SPACE_STATE_FILE}
# Written by project/store/view_settings.py next to the card state: the checked cards of each deck
VIEW_STATE_FILE = TEMP_DIR / "cluster_view_state.json"
KEPT_FILES = (STATE_FILE, SPACE_STATE_FILE, VIEW_STATE_FILE)

# Main project names.
MAIN_PACKAGE = "project"
MAIN_ENTRY = ROOT / "cards.py"
# delta/ mirrors the main names.
DELTA_PACKAGE = MAIN_PACKAGE
DELTA_ENTRY = MAIN_ENTRY.name
DELTA_ASSETS = "assets"


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
    """The file that runs for `relative` (e.g. "layout/map.py"): delta/project/ if present, else main."""
    changed = delta_dir / DELTA_PACKAGE / relative
    return changed if changed.is_file() else ROOT / MAIN_PACKAGE / relative


def asset_source(name: str, delta_dir: Path = DELTA_DIR) -> Path:
    """The asset that is served as `name`: delta/assets/ if present, else the main assets/."""
    changed = delta_dir / DELTA_ASSETS / name
    return changed if changed.is_file() else ROOT / "assets" / name


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
            f"{', '.join(preloaded)} imported before the cluster overrides; "
            "start the app with modules/cluster/cluster.py"
        )
    sys.meta_path[:] = [finder for finder in sys.meta_path if not isinstance(finder, DeltaFinder)]
    sys.meta_path.insert(0, DeltaFinder(delta_dir))
    return overrides


# --- temp/: assets and state ---------------------------------------------------


def _kept_in_temp(name: str) -> bool:
    """The state files and their backups survive a temp/ rebuild."""
    return any(name.startswith(path.name) for path in KEPT_FILES)


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
    """Rebuild temp/ flat: main assets, then delta/assets over them; state file and backups stay.

    Returns the copied file names with their sources.
    """
    temp_dir.mkdir(parents=True, exist_ok=True)
    for entry in temp_dir.iterdir():
        if entry.is_dir():
            shutil.rmtree(entry)
        elif not _kept_in_temp(entry.name):
            entry.unlink()

    merged = _flat_files(root / "assets")
    merged.update(_flat_files(delta_dir / DELTA_ASSETS))
    reserved = sorted(name for name in merged if _kept_in_temp(name))
    if reserved:
        raise ValueError(f"Asset name(s) reserved for generated files in temp/: {', '.join(reserved)}")
    for name, source in merged.items():
        shutil.copy2(source, temp_dir / name)
    return merged


def redirect_state(state_files: dict[str, Path] = STATE_FILES) -> None:
    """Make the app's JsonStateStore write to the module's files in temp/ (by requested name), never to data/."""
    state = importlib.import_module(f"{MAIN_PACKAGE}.store.state")
    original = state.JsonStateStore
    if getattr(original, "redirected_to", None) is not None:
        return

    class ModuleStateStore(original):
        redirected_to = dict(state_files)

        def __init__(self, requested_path, *args, **kwargs) -> None:
            self.requested_path = Path(requested_path)  # retained for diagnostics
            target = state_files.get(self.requested_path.name)
            if target is None:
                raise ValueError(
                    f"No module state file for {self.requested_path.name!r}; expected one of {sorted(state_files)}"
                )
            super().__init__(target, *args, **kwargs)

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
    """Return the next available backup path in temp/: cluster_state.json_01.bak, _02.bak, ..."""
    for i in range(1, 100):
        candidate = state_file.parent / f"{state_file.name}_{i:02d}.bak"
        if not candidate.exists():
            return candidate
    raise RuntimeError("Could not find a free backup name (100 existing backups)")


def prepare_state(state_files=KEPT_FILES) -> None:
    """Check which state files exist and ask once whether to back them up before starting fresh."""
    existing = [path for path in state_files if path.exists()]
    if not existing:
        print("No existing state file found.")
        return

    names = ", ".join(path.name for path in existing)
    print(f"Found existing state files in {existing[0].parent}: {names}")
    try:
        response = input(f"Backup existing {names}? (y/n): ").strip().lower()
    except EOFError:
        # Non-interactive environment (e.g. piped input): keep the existing files.
        print("No input available; keeping existing state files.")
        return

    if response in ("y", "yes"):
        for state_file in existing:
            backup_path = _find_unique_backup_path(state_file)
            state_file.rename(backup_path)
            print(f"Backed up existing state to: {backup_path}")
        print("Starting with fresh state files.")
    else:
        print("Keeping existing state files.")


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


def _report(overrides: dict[str, Path], assets: dict[str, Path], entry: Path) -> None:
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        return  # the debug reloader's child: already reported by the first start
    lines = [f"  {source.relative_to(MODULE_DIR).as_posix()} -> {name}" for name, source in overrides.items()]
    if entry != MAIN_ENTRY:
        lines.append(f"  {entry.relative_to(MODULE_DIR).as_posix()} -> {MAIN_ENTRY.name}")
    lines += [
        f"  {source.relative_to(MODULE_DIR).as_posix()} -> temp/{name}"
        for name, source in assets.items()
        if source.is_relative_to(DELTA_DIR)
    ]
    print("cluster overrides:" if lines else "cluster overrides: none, running the main code")
    for line in lines:
        print(line)
    for entry_path in _ignored_delta():
        print(f"  ignored (not part of the main structure): {entry_path.relative_to(MODULE_DIR).as_posix()}")


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
