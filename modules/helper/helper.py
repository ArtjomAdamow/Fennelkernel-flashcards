"""Launch the main application with the modules/helper overrides, on top of the cluster module.

Run from the repository root:

    .venv/Scripts/python.exe modules/helper/helper.py

The launcher derives the repository root from this file, so it also works when
invoked with an absolute path from another working directory.

Three layers, a higher one replaces files of the lower ones: the main project,
then the cluster module's delta/ (modules/cluster/delta), then this module's
delta/. delta/ mirrors the main project:

    delta/project/<sub>/<name>.py  replaces  project/<sub>/<name>.py (or the cluster module's copy of it)
    delta/cards.py                 replaces  cards.py (the composition root; else the cluster module's delta/cards.py)
    delta/assets/<file>            replaces  assets/<file> (or the cluster module's copy of it)

New files that exist only in a delta/project/ are importable as project.<name>.

Environment: the module has its own uv project (pyproject.toml, uv.lock and
.venv next to this file) with scikit-learn, scipy and the flashcards package
(the main project, editable). At startup the launcher checks the env with
`uv sync --locked --check`, asks before installing anything, and restarts
itself with the env's Python when it was started from another interpreter.
HELPER_ENV_READY=1 marks the restarted process, so it (and the debug
reloader's child) skips the check. On Ctrl+C, which reaches every process of
the console, the first process waits for the restarted one to stop the server
(run_restarted), so no KeyboardInterrupt traceback is printed.

All generated output goes flat into temp/: the merged assets and the module's
own state files (plus their backups): helper_state.json for the cards (deck
view), helper_space_state.json for the decks (space view) and
helper_view_state.json for the checked cards of each deck. Dash serves temp/ as
its assets folder, so its hot reload is switched off (a state save would reload
the browser). No __pycache__ folders are written.

On startup, if a state file exists, the user is asked whether to back them up
(temp/helper_state.json_01.bak, _02.bak, ...) and start fresh.
"""

from __future__ import annotations

import importlib
import importlib.abc
import importlib.util
import os
import shutil
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Callable, Mapping, Optional, Sequence

sys.dont_write_bytecode = True  # no __pycache__ in delta/ or anywhere else

MODULE_DIR = Path(__file__).resolve().parent
# For <repo>/modules/helper/helper.py:
# parents[0] is <repo>/modules; parents[1] is <repo>.
if len(MODULE_DIR.parents) < 2:
    raise RuntimeError(f"Unexpected helper module location: {MODULE_DIR}")
ROOT = MODULE_DIR.parents[1]
DELTA_DIR = MODULE_DIR / "delta"
# The cluster module's delta/, the layer below this module's (a dependency by path)
CLUSTER_DELTA_DIR = ROOT / "modules" / "cluster" / "delta"
# The delta layers in lookup order: this module first, then the cluster module; the main project is the fallback
DELTA_LAYERS = (DELTA_DIR, CLUSTER_DELTA_DIR)
TEMP_DIR = MODULE_DIR / "temp"
STATE_FILE = TEMP_DIR / "helper_state.json"
SPACE_STATE_FILE = TEMP_DIR / "helper_space_state.json"
# The state files the composition root asks for (by name), and where they are kept in temp/
STATE_FILES = {"user_state.json": STATE_FILE, "space_state.json": SPACE_STATE_FILE}
# Written by the cluster module's view settings next to the card state, named after it (view_state_path)
VIEW_STATE_FILE = TEMP_DIR / "helper_view_state.json"
KEPT_FILES = (STATE_FILE, SPACE_STATE_FILE, VIEW_STATE_FILE)

# The module's own env (uv project next to this file)
ENV_DIR = MODULE_DIR / ".venv"
LOCK_FILE = MODULE_DIR / "uv.lock"
ENV_READY = "HELPER_ENV_READY"  # set in a process that runs on the module env after the check

# Main project names.
MAIN_PACKAGE = "project"
MAIN_ENTRY = ROOT / "cards.py"
# delta/ mirrors the main names.
DELTA_PACKAGE = MAIN_PACKAGE
DELTA_ENTRY = MAIN_ENTRY.name
DELTA_ASSETS = "assets"

Layers = Sequence[Path]


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


def _as_layers(layers) -> tuple[Path, ...]:
    """One delta folder or several, highest first."""
    if isinstance(layers, (str, Path)):
        return (Path(layers),)
    return tuple(Path(layer) for layer in layers)


# --- Python overrides --------------------------------------------------------


def code_source(relative: str, layers: Layers = DELTA_LAYERS, root: Path = ROOT) -> Path:
    """The file that runs for `relative` (e.g. "services/similar.py"): this module's delta/project/ if present,
    else the cluster module's, else the main project's."""
    for layer in _as_layers(layers):
        changed = layer / DELTA_PACKAGE / relative
        if changed.is_file():
            return changed
    return root / MAIN_PACKAGE / relative


def asset_layers(root: Path = ROOT, layers: Layers = DELTA_LAYERS) -> tuple[Path, ...]:
    """The asset folders in merge order (main, cluster, helper); a later one replaces same-named files."""
    return (root / "assets", *[layer / DELTA_ASSETS for layer in reversed(_as_layers(layers))])


def asset_source(name: str, layers: Layers = DELTA_LAYERS, root: Path = ROOT) -> Path:
    """The asset that is served as `name`: this module's delta/assets/, else the cluster module's, else main."""
    for folder in reversed(asset_layers(root, layers)):
        if (folder / name).is_file():
            return folder / name
    return root / "assets" / name


def _layer_modules(delta_dir: Path) -> dict[str, Path]:
    """Map dotted main-package names to their files under one delta/project/."""
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


def delta_modules(layers: Layers = DELTA_LAYERS) -> dict[str, Path]:
    """Map dotted main-package names to their files under the delta layers; a higher layer wins."""
    found: dict[str, Path] = {}
    for layer in reversed(_as_layers(layers)):  # lowest first, so a higher layer replaces the same name
        found.update(_layer_modules(layer))
    return found


class DeltaFinder(importlib.abc.MetaPathFinder):
    """Serve MAIN_PACKAGE modules from the delta layers (highest first) when a file exists there."""

    def __init__(self, layers: Layers = DELTA_LAYERS, root: Path = ROOT) -> None:
        self.package_dirs = [layer / DELTA_PACKAGE for layer in _as_layers(layers)]
        self.main_dir = root / MAIN_PACKAGE

    def find_spec(self, fullname, path=None, target=None):
        if fullname != MAIN_PACKAGE and not fullname.startswith(MAIN_PACKAGE + "."):
            return None
        parts = fullname.split(".")[1:]
        for package_dir in self.package_dirs:
            changed = package_dir.joinpath(*parts)
            if parts and changed.with_suffix(".py").is_file():
                return importlib.util.spec_from_file_location(fullname, changed.with_suffix(".py"))
        for package_dir in self.package_dirs:
            init = package_dir.joinpath(*parts) / "__init__.py"
            if init.is_file():
                # Main folder first, then the layers from the lowest up: unchanged submodules keep coming from below
                folders = [self.main_dir.joinpath(*parts), *[folder.joinpath(*parts) for folder in reversed(self.package_dirs)]]
                locations = [str(folder) for folder in folders if folder.is_dir()]
                return importlib.util.spec_from_file_location(fullname, init, submodule_search_locations=locations)
        return None  # not changed: the normal import finds the main project's file


def install_delta_finder(layers: Layers = DELTA_LAYERS) -> dict[str, Path]:
    """Install the finder before anything imports the main package; return the overrides."""
    overrides = delta_modules(layers)
    preloaded = [name for name in overrides if name in sys.modules]
    if preloaded:
        raise RuntimeError(
            f"{', '.join(preloaded)} imported before the helper overrides; "
            "start the app with modules/helper/helper.py"
        )
    sys.meta_path[:] = [finder for finder in sys.meta_path if not isinstance(finder, DeltaFinder)]
    sys.meta_path.insert(0, DeltaFinder(layers))
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


def build_temp(root: Path = ROOT, layers: Layers = DELTA_LAYERS, temp_dir: Path = TEMP_DIR) -> dict[str, Path]:
    """Rebuild temp/ flat from the asset layers (main, cluster, helper); the state files and backups stay.

    Returns the copied file names with their sources.
    """
    temp_dir.mkdir(parents=True, exist_ok=True)
    for entry in temp_dir.iterdir():
        if entry.is_dir():
            shutil.rmtree(entry)
        elif not _kept_in_temp(entry.name):
            entry.unlink()

    merged: dict[str, Path] = {}
    for folder in asset_layers(root, layers):
        merged.update(_flat_files(folder))
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
    """Return the next available backup path in temp/: helper_state.json_01.bak, _02.bak, ..."""
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


# --- environment: the module's own uv project ----------------------------------------


def env_python(env_dir: Path = ENV_DIR) -> Path:
    """The interpreter of the module env: the Windows layout if it exists (or on Windows), else the POSIX one."""
    windows = env_dir / "Scripts" / "python.exe"
    posix = env_dir / "bin" / "python"
    if windows.exists() or (os.name == "nt" and not posix.exists()):
        return windows
    return posix


def uv_command(*arguments: str, module_dir: Path = MODULE_DIR) -> list[str]:
    return ["uv", *arguments, "--project", str(module_dir)]


def environment_in_sync(run: Callable = subprocess.run, module_dir: Path = MODULE_DIR) -> tuple[bool, str]:
    """`uv sync --locked --check`: whether the env matches the lockfile (it changes nothing), with uv's message."""
    try:
        result = run(uv_command("sync", "--locked", "--check", module_dir=module_dir), capture_output=True, text=True)
    except FileNotFoundError:
        return False, "uv is not installed or not on PATH"
    message = ((getattr(result, "stderr", "") or getattr(result, "stdout", "") or "")).strip()
    return result.returncode == 0, message


def install_environment(
    run: Callable = subprocess.run, module_dir: Path = MODULE_DIR, lock_file: Path = LOCK_FILE, output: Callable = print
) -> bool:
    """`uv lock` when there is no lockfile yet, then `uv sync --locked`. False when uv is missing or fails."""
    try:
        if not lock_file.exists():
            output("No uv.lock yet: resolving the module env (uv lock) ...")
            if run(uv_command("lock", module_dir=module_dir)).returncode != 0:
                return False
        output("Installing the module env (uv sync --locked) ...")
        return run(uv_command("sync", "--locked", module_dir=module_dir)).returncode == 0
    except FileNotFoundError:
        output("uv is not installed or not on PATH.")
        return False


def _same_interpreter(first: Path, second: Path) -> bool:
    try:
        return first.resolve() == second.resolve() or os.path.samefile(first, second)
    except OSError:
        return False


def ensure_environment(
    run: Callable = subprocess.run,
    ask: Callable = input,
    environ: Mapping[str, str] = os.environ,
    executable: str = sys.executable,
    output: Callable = print,
    module_dir: Path = MODULE_DIR,
    env_dir: Path = ENV_DIR,
    lock_file: Path = LOCK_FILE,
    arguments: Optional[Sequence[str]] = None,
) -> Optional[list[str]]:
    """The environment section of the startup, run once per launch.

    Returns None to go on in this process (it runs on the module env already, or the env was marked ready), or the
    command that restarts the launcher on the module env's Python. Exits when the env is out of sync and is not
    installed now: without input it prints the command and exits.
    """
    if environ.get(ENV_READY) == "1":
        return None
    in_sync, message = environment_in_sync(run, module_dir)
    if not in_sync:
        output(f"The helper env ({env_dir}) is not in sync with its lockfile: {message}")
        try:
            answer = ask("Install it now with uv? (y/n): ").strip().lower()
        except EOFError:
            answer = ""
        if answer not in ("y", "yes") or not install_environment(run, module_dir, lock_file, output):
            output(f"Run: uv sync --project {module_dir}   and start the launcher again.")
            raise SystemExit(1)
    python = env_python(env_dir)
    if not python.exists():
        output(f"The module env has no interpreter at {python}; run: uv sync --project {module_dir}")
        raise SystemExit(1)
    if _same_interpreter(Path(executable), python):
        return None
    return [str(python), str(Path(__file__).resolve()), *(list(sys.argv[1:]) if arguments is None else list(arguments))]


def run_restarted(command: Sequence[str], popen: Callable = subprocess.Popen, grace: float = 10.0) -> int:
    """Run the launcher again on the module env and return its exit code.

    Ctrl+C reaches every process of the console, the restarted launcher included, and it stops the server on its
    own. So this process waits for it instead of raising (subprocess.run prints a KeyboardInterrupt traceback and
    kills it); on a second Ctrl+C, or when it still runs after `grace` seconds, it is killed.
    """
    process = popen(command)
    try:
        return process.wait()
    except KeyboardInterrupt:
        try:
            return process.wait(timeout=grace)
        except (KeyboardInterrupt, subprocess.TimeoutExpired):
            process.kill()
            return process.wait()


# --- composition root ----------------------------------------------------------------


def entry_source(layers: Layers = DELTA_LAYERS) -> Path:
    """This module's delta/cards.py if present, else the cluster module's, else the main composition root."""
    for layer in _as_layers(layers):
        changed = layer / DELTA_ENTRY
        if changed.is_file():
            return changed
    return MAIN_ENTRY


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
    """A source path relative to modules/ (helper/delta/..., cluster/delta/...)."""
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
    print("helper overrides (helper over cluster over main):" if lines else "helper overrides: none, running the main code")
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
    # app.run(debug=True) runs this script again in a reloader child (WERKZEUG_RUN_MAIN=true): check and ask only once
    if os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        restart = ensure_environment()
        if restart is not None:
            os.environ[ENV_READY] = "1"  # the restarted process skips the check
            print(f"Restarting on the module env: {restart[0]}")
            raise SystemExit(run_restarted(restart))
        os.environ[ENV_READY] = "1"  # the reloader child skips the check too
        prepare_state()
    load_app().main()


if __name__ == "__main__":
    main()
