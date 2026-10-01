#!/usr/bin/env python3
"""Sync a Markdown component index with the real code.

Standalone tool: standard library only, never imports project code
(files are only parsed with `ast`), so it is not part of the main app.

Maintained automatically (per YAML block, only if the key exists there):
    line_start, line_end   position of the component in its .py file
    dependencies           components this one references
    used_in                components that reference this one
Never touched: tags, type, and every other key or comment.

NEW: unindexed components
    Classes/functions that have no entry in the index yet, but are connected
    to indexed components, are written to a generated section at the END of
    the index file, starting with the line
        **The update_index script has found unindexed components:**
    Each block there has a heading with anchor link and a complete YAML block
    (component_id and type are proposals). Copy a block into the outline to
    index it. The section is regenerated on every run: everything from that
    title line to the end of the file is replaced, so do not write your own
    text below it.
    "Connected" means: an indexed component depends on it (forward), or it
    depends on an indexed component (reverse; switch off with --no-reverse).
    --new-depth N continues the search N levels from newly found components,
    in both directions. Test files and folders (tests/, test_*.py, *_test.py,
    conftest.py) are skipped unless --include-tests is given.

Expected index layout (one entry per component):

    ### [`Flashcard:`](./flashcards_app/models.py#Class&nbspFlashcard:)

    ```yaml
    component_id: flashcard
    file: flashcards_app/models.py
    line_start: 0
    line_end: 0
    tags: [manual, tags]
    dependencies: []
    used_in: []
    ```

Symbol lookup uses the link anchor (text after '#'):
    #Class&nbspName        -> class Name
    #def&nbspfunc_name     -> def / async def func_name
    #Class&nbspOuter.Inner -> nested class, #def&nbspClass.method -> method
'&nbsp' (with or without ';'), '%20', '%C2%A0' and a real no-break space
are read as a space. A trailing ':' or '()' is ignored. The kind is
enforced when given. Fallbacks: visible link text, then `component_id`.

Line numbers: 1-based, inclusive, blank lines counted. line_start is the
first decorator line (e.g. @dataclass), line_end the last line of the body.

Dependency analysis (static, heuristic):
  * a name counts if it is used (Load) inside the component and is not
    bound locally there (parameter, assignment, import ...): base classes,
    annotations (also string annotations), calls, decorators
  * `module.Name` counts only for classes (attribute access)
  * methods / nested classes ("Class.method") are indexed for line numbers,
    but are not tracked as dependency targets
  * a component's own name and indexed components nested in it are ignored
  * several candidates with one name: same file wins, then the indexed one;
    otherwise the name is skipped and reported
  * imports are not resolved

Entries in dependencies / used_in are the `component_id` (fallback: code
name). Use --ref name to always use the code name.

Backup: before the index file is written, a copy INDEX_bak_00.md is made next
to it (the next free number if copies exist: _01, _02, ...). If nothing has to
be written, or with --dry-run / --check, no backup is made.

Interactive start: without arguments the script finds INDEX.md (current folder,
then the script's folder) and asks before doing anything:
    Ready to update ... in place (backup copy: ...) y/n   y = run
    n or Enter -> "A report only run with checks will start now y/n"
        y or Enter = INDEX.md --dry-run --check, n = show this usage and exit

Usage:
    python update_index.py                       # interactive start (asks first)
    python update_index.py INDEX.md              # update in place (backup first)
    python update_index.py INDEX.md --dry-run    # only report
    python update_index.py INDEX.md --check      # exit 1 if index is stale (CI)
    python update_index.py INDEX.md --root .     # base dir for `file:` paths
    python update_index.py INDEX.md --fields lines     # only line numbers
    python update_index.py INDEX.md --new-depth 2      # unindexed: 2 levels deep
    python update_index.py INDEX.md --new-depth 0      # no unindexed section
    python update_index.py INDEX.md --scan indexed     # look only in indexed files
    python update_index.py INDEX.md --ignore helper    # never list this name
    python update_index.py INDEX.md --exclude-dir tests
    python update_index.py INDEX.md --no-reverse       # only dependencies of indexed
    python update_index.py INDEX.md --include-tests    # also scan test files

Exit codes: 0 ok, 1 stale (--check), 2 unresolved entries, 3 write failed,
            4 interactive start without INDEX.md or without input.
"""
from __future__ import annotations

import argparse
import ast
import os
import re
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import unquote

SELF = Path(__file__).resolve()
SECTION_TITLE = "**The update_index script has found unindexed components:**"
DEFAULT_SKIP_DIRS = {".git", ".hg", ".svn", "__pycache__", "node_modules", ".venv", "venv",
                     "env", ".tox", ".mypy_cache", ".pytest_cache", ".idea", ".vscode",
                     "build", "dist", "site-packages"}

TEST_DIRS = {"tests", "test"}

FENCE_OPEN = re.compile(r"^\s*```ya?ml\s*$")
FENCE_CLOSE = re.compile(r"^\s*```\s*$")
HEADING = re.compile(r"^#{1,6}\s+\[?`(?P<text>[^`]+)`\]?(?:\((?P<url>[^)\r\n\t ]*)\))?")
KEY = re.compile(r"^\s*(?P<key>[A-Za-z_]\w*):\s*(?P<val>.*?)\s*$")
LIST_ITEM = re.compile(r"^\s*-\s+(?P<item>.*?)\s*$")
NBSP_ENTITY = re.compile(r"&nbsp;?", re.I)
KIND_PREFIX = re.compile(r"^(async\s+def|def|class)\s+(?P<name>\S.*)$", re.I)
PLAIN_ITEM = re.compile(r"^[\w.\-/]+$")
ALL_FIELDS = {"lines", "dependencies", "used_in"}

Ref = tuple  # (kind | None, name)


# --------------------------------------------------------------- name parsing
def normalize(text: str) -> str:
    text = NBSP_ENTITY.sub(" ", text)          # &nbsp / &nbsp;
    text = unquote(text)                        # %20, %C2%A0
    text = text.replace("\u00a0", " ")          # real no-break space
    return re.sub(r"\s+", " ", text).strip().strip("`")


def clean_name(name: str) -> str:
    name = re.sub(r"\(.*\)$", "", name.strip()).strip()   # func() -> func
    return name.rstrip(":").strip()                        # Name: -> Name


def parse_ref(raw: str) -> Ref:
    text = normalize(raw)
    m = KIND_PREFIX.match(text)
    if m:
        kind = "class" if m.group(1).lower() == "class" else "def"
        return kind, clean_name(m["name"])
    return None, clean_name(text)


def label(ref: Ref) -> str:
    kind, name = ref
    return f"{kind} {name}" if kind else name


def name_candidates(m: re.Match) -> list[Ref]:
    raw = []
    url = m.group("url") or ""
    if "#" in url:
        raw.append(url.split("#", 1)[1])
    raw.append(m.group("text"))
    return [parse_ref(r) for r in raw]


def finalize(cands: list[Ref]) -> list[Ref]:
    """The first kind found (normally from the anchor) applies to all candidates."""
    kind = next((k for k, _ in cands if k), None)
    return list(dict.fromkeys((kind, n) for _, n in cands if n))


def snake(name: str) -> str:
    s = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", name)
    s = re.sub(r"(?<=[A-Z])(?=[A-Z][a-z])", "_", s)
    return s.lower()


# ------------------------------------------------------------- code inspection
# symbol = (line_start, line_end, kind, ast_node, qualified_name)
def collect_symbols(py_file: Path) -> dict[str, tuple]:
    tree = ast.parse(py_file.read_text(encoding="utf-8"))
    symbols: dict[str, tuple] = {}

    def visit(node: ast.AST, prefix: str = "") -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                qual = prefix + child.name
                kind = "class" if isinstance(child, ast.ClassDef) else "def"
                start = min([child.lineno] + [d.lineno for d in child.decorator_list])
                symbols.setdefault(qual, (start, child.end_lineno, kind, child, qual))
                if isinstance(child, ast.ClassDef):
                    visit(child, qual + ".")

    visit(tree)
    return symbols


def find_symbol(symbols: dict, name: str, kind: str | None):
    pool = {k: v for k, v in symbols.items() if kind is None or v[2] == kind}
    if name in pool:
        return pool[name]
    low = name.lower()
    matchers = (
        lambda k: k.endswith("." + name),
        lambda k: k.lower() == low,
        lambda k: k.lower().endswith("." + low),
    )
    for match in matchers:
        hits = [v for k, v in pool.items() if match(k)]
        if len(hits) == 1:  # ambiguous -> keep looking / treat as missing
            return hits[0]
    return None


def referenced_names(node: ast.AST) -> tuple[set[str], set[str]]:
    """(plain names used, attribute names used) inside a class/function node.

    Names that are bound locally (parameters, assignments, imports, ...) are
    removed from the plain names, so a local variable never counts as a
    reference to a project function of the same name.
    """
    names: set[str] = set()
    attrs: set[str] = set()
    bound: set[str] = set()
    annotations = []
    for n in ast.walk(node):
        if isinstance(n, ast.Name):
            if isinstance(n.ctx, ast.Load):
                names.add(n.id)
            else:
                bound.add(n.id)
        elif isinstance(n, ast.arg):
            bound.add(n.arg)
            if n.annotation is not None:
                annotations.append(n.annotation)
        elif isinstance(n, ast.alias):
            bound.add((n.asname or n.name).split(".")[0])
        elif isinstance(n, ast.ExceptHandler) and n.name:
            bound.add(n.name)
        elif isinstance(n, ast.Attribute):
            attrs.add(n.attr)
        elif isinstance(n, ast.AnnAssign):
            annotations.append(n.annotation)
        elif isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.returns is not None:
            annotations.append(n.returns)
    names -= bound
    for ann in annotations:  # string annotations: "Flashcard", "models.Flashcard"
        for c in ast.walk(ann):
            if isinstance(c, ast.Constant) and isinstance(c.value, str):
                try:
                    sub = ast.parse(c.value.strip(), mode="eval")
                except SyntaxError:
                    continue
                for x in ast.walk(sub):
                    if isinstance(x, ast.Name):
                        names.add(x.id)
                    elif isinstance(x, ast.Attribute):
                        attrs.add(x.attr)
    return names, attrs


def decorator_name(d: ast.AST) -> str:
    if isinstance(d, ast.Call):
        d = d.func
    if isinstance(d, ast.Name):
        return d.id
    if isinstance(d, ast.Attribute):
        return d.attr
    return ""


def component_type(sym: tuple) -> str:
    kind, node = sym[2], sym[3]
    if kind == "class":
        decorators = {decorator_name(d) for d in node.decorator_list}
        return "dataclass" if "dataclass" in decorators else "class"
    return "async_function" if isinstance(node, ast.AsyncFunctionDef) else "function"


def resolve(file_value: str, md_path: Path, root: Path) -> Path | None:
    for base in (root, md_path.parent):
        candidate = (base / file_value).resolve()
        if candidate.is_file():
            return candidate
    return None


def is_test_path(py: Path, root: Path) -> bool:
    try:
        parts = py.relative_to(root).parts
    except ValueError:
        parts = py.parts
    name = py.name
    return (any(p in TEST_DIRS for p in parts[:-1]) or name.startswith("test_")
            or name.endswith("_test.py") or name == "conftest.py")


def iter_py_files(root: Path, exclude: set[str]):
    skip = DEFAULT_SKIP_DIRS | exclude
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames
                       if d not in skip and not Path(dirpath, d, "pyvenv.cfg").exists()]
        for fn in filenames:
            if fn.endswith(".py"):
                yield Path(dirpath, fn).resolve()


# ---------------------------------------------------------------------- model
@dataclass
class Options:
    fields: set
    ref_mode: str = "id"
    new_depth: int = 1
    scan: str = "project"
    ignore: set = field(default_factory=set)
    exclude_dirs: set = field(default_factory=set)
    reverse: bool = True
    include_tests: bool = False


@dataclass
class Entry:
    a: int                      # index of first line inside the yaml block (-1: new)
    b: int                      # index of the closing fence
    name: str
    old: tuple
    status: str = ""
    py: Path | None = None
    sym: tuple | None = None
    ref: str = ""
    cid: str = ""
    file_value: str = ""
    is_new: bool = False        # found in code, not in the index
    active: bool = False        # new and connected -> listed in the section
    via: str = ""               # why it was found (console report only)
    deps: set = field(default_factory=set)
    used_in: set = field(default_factory=set)


@dataclass
class Result:
    text: str
    report: list
    warnings: list
    new: list
    section_changed: bool


def parse_fields(block: list[str]) -> dict[str, str]:
    return {m["key"]: m["val"].strip("'\"") for l in block if (m := KEY.match(l))}


def build_entry(lines, cands, a, b, md_path, root, cache, ref_mode) -> Entry | None:
    f = parse_fields(lines[a:b])
    if "line_start" not in f or "line_end" not in f or "index_conventions" in f:
        return None  # some other yaml block, leave alone

    cands = list(cands or [])
    if f.get("component_id"):
        cands.append(parse_ref(f["component_id"]))
    cands = finalize(cands)
    e = Entry(a=a, b=b, name=label(cands[0]) if cands else "?",
              old=(f["line_start"], f["line_end"]))

    file_value = f.get("file", "")
    e.file_value = file_value
    e.py = resolve(file_value, md_path, root) if file_value else None
    if e.py is None:
        e.status = f"FILE NOT FOUND: {file_value!r}"
        return e
    if e.py not in cache:
        try:
            cache[e.py] = collect_symbols(e.py)
        except SyntaxError as exc:
            cache[e.py] = {}
            e.status = f"SYNTAX ERROR in {e.py.name}: {exc}"
            return e
    symbols = cache[e.py]

    sym = next((s for k, n in cands if (s := find_symbol(symbols, n, k))), None)
    if sym is None:
        if any(find_symbol(symbols, n, None) for _, n in cands):
            e.status = f"KIND MISMATCH in {e.py.name} (anchor says {cands[0][0]!r})"
        else:
            tried = ", ".join(label(c) for c in cands) or "-"
            e.status = f"SYMBOL NOT FOUND in {e.py.name} (tried: {tried})"
        return e
    e.sym = sym
    e.cid = clean_name(f.get("component_id", ""))
    e.ref = e.cid if (ref_mode == "id" and e.cid) else sym[4]
    return e


# ---------------------------------------------------------------------- graph
def discover_unindexed(entries, cache, root, opts, warnings) -> list[Entry]:
    """All top-level classes/functions in scope that are not in the index."""
    indexed = {(e.py, e.sym[4]) for e in entries if e.sym is not None}
    files = set(cache)
    if opts.scan == "project":
        files |= set(iter_py_files(root, opts.exclude_dirs))
    pool = []
    for py in sorted(files):
        if py == SELF or (not opts.include_tests and is_test_path(py, root)):
            continue
        if py not in cache:
            try:
                cache[py] = collect_symbols(py)
            except (SyntaxError, UnicodeDecodeError, OSError) as exc:
                warnings.append(f"could not parse {py.name}: {exc}")
                cache[py] = {}
        for qual, sym in cache[py].items():
            if "." in qual or qual in opts.ignore or (py, qual) in indexed:
                continue
            pool.append(Entry(a=-1, b=-1, name=label((sym[2], qual)), old=("", ""),
                              py=py, sym=sym, is_new=True))
    return pool


def assign_new_refs(active: list[Entry], entries: list[Entry], ref_mode: str) -> None:
    used = {e.ref for e in entries if e.sym is not None} | {e.cid for e in entries if e.cid}
    for e in sorted(active, key=lambda x: (str(x.py), x.sym[0])):
        base = snake(e.sym[4])
        cid = base if base not in used else f"{e.py.stem}_{base}"
        n = 2
        while cid in used:
            cid = f"{e.py.stem}_{base}_{n}"
            n += 1
        used.add(cid)
        e.cid = cid
        e.ref = cid if ref_mode == "id" else e.sym[4]


def build_graph(entries, pool, new_depth, warnings, ref_mode, reverse=True) -> list[Entry]:
    """Fill deps / used_in. Returns the unindexed components to list."""
    live = [e for e in entries if e.sym is not None]

    seen: dict[str, Entry] = {}
    for e in live:
        if e.ref in seen and seen[e.ref].sym is not e.sym:
            warnings.append(f"duplicate reference {e.ref!r} used by two different components")
        seen.setdefault(e.ref, e)

    by_name: dict[str, list[Entry]] = {}
    for e in live + pool:
        if "." not in e.sym[4]:              # methods / nested: not a target
            by_name.setdefault(e.sym[4], []).append(e)

    refs_cache: dict[int, tuple] = {}
    warned: set[str] = set()

    def refs_of(e: Entry):
        key = id(e.sym[3])
        if key not in refs_cache:
            refs_cache[key] = referenced_names(e.sym[3])
        return refs_cache[key]

    def contained(t: Entry, s: Entry) -> bool:
        return t.py == s.py and s.sym[0] <= t.sym[0] and t.sym[1] <= s.sym[1]

    def pick(name: str, src: Entry, classes_only: bool) -> list[Entry]:
        cands = [t for t in by_name.get(name, [])
                 if (not classes_only or t.sym[2] == "class") and not contained(t, src)]
        if len(cands) <= 1:
            return cands
        for narrowed in ([t for t in cands if t.py == src.py],      # same file wins
                         [t for t in cands if not t.is_new]):       # then the indexed one
            if len(narrowed) == 1:
                return narrowed
        if name not in warned:
            warned.add(name)
            warnings.append(f"ambiguous name {name!r} exists in several files - skipped")
        return []

    def targets_of(src: Entry) -> list[Entry]:
        names, attrs = refs_of(src)
        found = [t for n in names for t in pick(n, src, False)]
        found += [t for a in attrs for t in pick(a, src, True)]
        return found

    # reverse map: who depends on whom (only unindexed components as dependents)
    users_of: dict[int, list[Entry]] = {}
    if reverse:
        for p in pool:
            for t in targets_of(p):
                users_of.setdefault(id(t), []).append(p)

    # phase A: which unindexed components are connected (up to new_depth levels)?
    frontier = live
    for _ in range(new_depth):
        nxt = []
        for src in frontier:
            for t in targets_of(src):                     # forward: src depends on t
                if t.is_new and not t.active:
                    t.active, t.via = True, f"used by {src.sym[4]}"
                    nxt.append(t)
            for u in users_of.get(id(src), []):           # reverse: u depends on src
                if not u.active:
                    u.active, u.via = True, f"uses {src.sym[4]}"
                    nxt.append(u)
        frontier = nxt
        if not frontier:
            break
    active = [p for p in pool if p.active]
    assign_new_refs(active, entries, ref_mode)

    # phase B: relations among indexed + listed components
    for src in live + active:
        for t in targets_of(src):
            if t.is_new and not t.active:
                continue
            src.deps.add(t.ref)
            t.used_in.add(src.ref)
    return sorted(active, key=lambda x: (str(x.py), x.sym[0]))


# ------------------------------------------------------------------ md editing
def eol_of(line: str) -> str:
    return line[len(line.rstrip("\r\n")):]


def set_value(line: str, key: str, value: int) -> str:
    indent = line[: len(line) - len(line.lstrip())]
    return f"{indent}{key}: {value}{eol_of(line)}"


def yaml_item(text: str) -> str:
    return text if PLAIN_ITEM.match(text) else '"' + text.replace('"', '\\"') + '"'


def flow(items) -> str:
    return "[" + ", ".join(yaml_item(i) for i in sorted(items)) + "]"


def read_list(block: list[str], idx: int):
    """(items, index after the list) for `key: [a, b]` or block-style lists."""
    val = KEY.match(block[idx])["val"]
    end = idx + 1
    if val.startswith("[") and val.endswith("]"):
        items = [x.strip().strip("'\"") for x in val[1:-1].split(",") if x.strip()]
        return items, end
    if val == "":
        items = []
        while end < len(block) and (m := LIST_ITEM.match(block[end])):
            items.append(m["item"].strip("'\""))
            end += 1
        return items, end
    return None, end  # unsupported format (e.g. plain scalar): leave alone


def set_list(block: list[str], key: str, values: list[str]):
    idx = next((i for i, l in enumerate(block)
                if (m := KEY.match(l)) and m["key"] == key), None)
    if idx is None:
        return block, None
    old, end = read_list(block, idx)
    if old is None or sorted(old) == sorted(values):
        return block, None
    indent = block[idx][: len(block[idx]) - len(block[idx].lstrip())]
    new_line = f"{indent}{key}: {flow(values)}{eol_of(block[idx])}"
    change = f"{key} [{', '.join(old)}] -> [{', '.join(values)}]"
    return block[:idx] + [new_line] + block[end:], change


def parse_blocks(lines: list[str]):
    blocks, heading, i = [], None, 0
    while i < len(lines):
        if m := HEADING.match(lines[i]):
            heading = name_candidates(m)
        if FENCE_OPEN.match(lines[i]):
            j = i + 1
            while j < len(lines) and not FENCE_CLOSE.match(lines[j]):
                j += 1
            blocks.append((heading, i + 1, j))
            heading, i = None, j + 1
            continue
        i += 1
    return blocks


def rel_path(base: Path, target: Path) -> str:
    try:
        return os.path.relpath(target, base).replace("\\", "/")
    except ValueError:  # e.g. different drive on Windows
        return target.as_posix()


def render_section(new: list[Entry], md_path: Path, root: Path, eol: str, dot_style: bool) -> str:
    if not new:
        return ""
    out = [SECTION_TITLE + eol, eol]
    for e in new:
        name, kind = e.sym[4], e.sym[2]
        text, anchor = ((f"{name}:", f"Class&nbsp{name}:") if kind == "class"
                        else (f"{name}()", f"def&nbsp{name}"))
        link = rel_path(md_path.parent, e.py)
        if not link.startswith("."):
            link = "./" + link
        file_value = rel_path(root, e.py)
        if dot_style and not file_value.startswith("."):
            file_value = "./" + file_value
        rows = [("component_id", yaml_item(e.cid)), ("type", component_type(e.sym)),
                ("file", yaml_item(file_value)), ("line_start", e.sym[0]),
                ("line_end", e.sym[1]), ("tags", "[]"),
                ("dependencies", flow(e.deps)), ("used_in", flow(e.used_in))]
        out += [f"### [`{text}`]({link}#{anchor}){eol}", eol, f"```yaml{eol}"]
        out += [f"{k}: {v}{eol}" for k, v in rows]
        out += [f"```{eol}", eol]
    return "".join(out)


def sync(md_path: Path, root: Path, opts: Options) -> Result:
    raw = md_path.read_bytes().decode("utf-8")
    eol = "\r\n" if "\r\n" in raw else "\n"
    all_lines = raw.splitlines(keepends=True)
    sec = next((i for i, l in enumerate(all_lines) if l.strip() == SECTION_TITLE), None)
    lines = all_lines if sec is None else all_lines[:sec]   # generated section is not parsed
    old_section = "" if sec is None else "".join(all_lines[sec:])
    cache: dict = {}
    warnings: list[str] = []

    entries = [e for heading, a, b in parse_blocks(lines)
               if (e := build_entry(lines, heading, a, b, md_path, root, cache, opts.ref_mode))]

    graph_on = bool(opts.fields & {"dependencies", "used_in"})
    new: list[Entry] = []
    if graph_on:
        pool = (discover_unindexed(entries, cache, root, opts, warnings)
                if opts.new_depth >= 1 else [])
        new = build_graph(entries, pool, opts.new_depth, warnings, opts.ref_mode, opts.reverse)

    out, pos, report = [], 0, []
    for e in entries:
        out.extend(lines[pos:e.a])
        block, changes = lines[e.a:e.b], []
        if e.sym is not None:
            if "lines" in opts.fields and e.old != (str(e.sym[0]), str(e.sym[1])):
                changes.append(f"lines {e.old[0]}-{e.old[1]} -> {e.sym[0]}-{e.sym[1]}")
                block = [set_value(l, m["key"], e.sym[0] if m["key"] == "line_start" else e.sym[1])
                         if (m := KEY.match(l)) and m["key"] in ("line_start", "line_end") else l
                         for l in block]
            for key, values in (("dependencies", e.deps), ("used_in", e.used_in)):
                if key in opts.fields:
                    block, change = set_list(block, key, sorted(values))
                    if change:
                        changes.append(change)
        out.extend(block)
        pos = e.b
        report.append({"name": e.name, "changes": changes,
                       "status": e.status or ("updated" if changes else "ok")})
    out.extend(lines[pos:])
    head_text = "".join(out)

    section_enabled = graph_on and opts.new_depth >= 1
    dot_style = any(e.file_value.startswith("./") for e in entries)
    rendered = render_section(new, md_path, root, eol, dot_style) if section_enabled else old_section
    if not section_enabled or rendered.rstrip() == old_section.rstrip():
        text, section_changed = head_text + old_section, False      # keep byte-identical
    else:
        base = head_text.rstrip("\r\n \t")
        text = (base + eol if base else "") + ((eol + rendered) if rendered else "")
        section_changed = True
    return Result(text, report, warnings, new if section_enabled else [], section_changed)


def next_backup_path(md_path: Path) -> Path:
    """INDEX.md -> INDEX_bak_00.md; continues after the highest existing number."""
    pattern = re.compile(rf"^{re.escape(md_path.stem)}_bak_(\d+){re.escape(md_path.suffix)}$", re.I)
    numbers = [int(m.group(1)) for f in md_path.parent.iterdir() if (m := pattern.match(f.name))]
    n = max(numbers) + 1 if numbers else 0
    while True:
        candidate = md_path.with_name(f"{md_path.stem}_bak_{n:02d}{md_path.suffix}")
        if not candidate.exists():
            return candidate
        n += 1


def find_default_index() -> Path | None:
    for folder in dict.fromkeys([Path.cwd().resolve(), SELF.parent]):
        exact = folder / "INDEX.md"
        if exact.is_file():
            return exact
        for p in sorted(folder.glob("*.md")):
            if p.name.lower() == "index.md":
                return p
    return None


def usage_text() -> str:
    doc = __doc__ or ""
    return doc[doc.rindex("Usage:"):].rstrip() if "Usage:" in doc else ""


def ask(question: str) -> str:
    try:
        return input(question).strip().lower()
    except EOFError:
        print("\nno input available - nothing was run.\n")
        print(usage_text())
        sys.exit(4)


def interactive_start() -> list[str]:
    """Used when the script is started without arguments. Returns the argv to run."""
    md = find_default_index()
    if md is None:
        print("No INDEX.md found in the current folder or next to this script.\n")
        print(usage_text())
        sys.exit(4)
    if md.parent != Path.cwd().resolve():
        print(f"index file: {md}")
    answer = ask(f"Ready to update the file {md.name} in place "
                 f"(backup copy: {next_backup_path(md).name}) y/n ")
    if answer in ("y", "yes"):
        return [str(md)]
    answer = ask("A report only run with checks will start now y/n ")
    if answer in ("", "y", "yes"):
        return [str(md), "--dry-run", "--check"]
    print()
    print(usage_text())
    sys.exit(0)


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        argv = interactive_start()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("index", type=Path, help="Markdown index file")
    ap.add_argument("--root", type=Path, help="base dir for `file:` paths (default: index dir)")
    ap.add_argument("--dry-run", action="store_true", help="report only, write nothing")
    ap.add_argument("--check", action="store_true", help="exit 1 if the index is stale")
    ap.add_argument("--fields", default=",".join(sorted(ALL_FIELDS)),
                    help="comma list of: lines, dependencies, used_in (default: all)")
    ap.add_argument("--ref", choices=("id", "name"), default="id",
                    help="what to write into dependencies/used_in (default: component_id)")
    ap.add_argument("--new-depth", type=int, default=1, metavar="N",
                    help="levels of unindexed dependencies to list; 0 = no section (default: 1)")
    ap.add_argument("--scan", choices=("project", "indexed"), default="project",
                    help="where to look for unindexed components (default: all .py under root)")
    ap.add_argument("--ignore", action="append", default=[], metavar="NAME",
                    help="never list this component name (repeatable)")
    ap.add_argument("--exclude-dir", action="append", default=[], metavar="DIR",
                    help="extra directory name to skip while scanning (repeatable)")
    ap.add_argument("--no-reverse", dest="reverse", action="store_false",
                    help="do not list unindexed components that depend on indexed ones")
    ap.add_argument("--include-tests", action="store_true",
                    help="also scan test files/folders (skipped by default)")
    args = ap.parse_args(argv)

    fields = {f.strip() for f in args.fields.split(",") if f.strip()}
    if not fields or not fields <= ALL_FIELDS:
        ap.error(f"--fields must be a comma list of {sorted(ALL_FIELDS)}")
    if args.new_depth < 0:
        ap.error("--new-depth must be >= 0")
    opts = Options(fields=fields, ref_mode=args.ref, new_depth=args.new_depth, scan=args.scan,
                   ignore=set(args.ignore), exclude_dirs=set(args.exclude_dir),
                   reverse=args.reverse, include_tests=args.include_tests)

    md_path = args.index.resolve()
    root = (args.root or md_path.parent).resolve()
    res = sync(md_path, root, opts)

    for r in res.report:
        print(f"{r['status']:<14} {r['name']}")
        for c in r["changes"]:
            print(f"{'':<15}{c}")
    if res.new:
        print(f"\nunindexed components found ({len(res.new)}):")
        for e in res.new:
            users = ", ".join(sorted(e.used_in)) or "-"
            print(f"  {label((e.sym[2], e.sym[4])):<30} {rel_path(root, e.py)}:{e.sym[0]}-{e.sym[1]}"
                  f"   used in: {users}   ({e.via})")
    for w in res.warnings:
        print(f"WARNING: {w}")

    report = res.report
    n_upd = sum(r["status"] == "updated" for r in report)
    n_ok = sum(r["status"] == "ok" for r in report)
    n_bad = sum(r["status"] not in ("ok", "updated") for r in report)
    changed = n_upd > 0 or res.section_changed
    print(f"\n{len(report)} entries: {n_upd} stale, {n_ok} ok, {n_bad} unresolved; "
          f"{len(res.new)} unindexed" + (" (section will change)" if res.section_changed else ""))
    print(f"index file: {md_path}")

    if not changed:
        print("nothing to write: no stale entry found.")
    elif args.dry_run or args.check:
        print("NOT written (--dry-run / --check given).")
    else:
        try:
            backup = next_backup_path(md_path)
            shutil.copy2(md_path, backup)
        except OSError as exc:
            print(f"BACKUP FAILED: {exc} - the index file was not touched.")
            return 3
        print(f"backup: {backup.name}")
        try:
            md_path.write_bytes(res.text.encode("utf-8"))
        except OSError as exc:
            print(f"WRITE FAILED: {exc}")
            return 3
        again = sync(md_path, root, opts)  # verify by re-reading from disk
        left = sum(r["status"] == "updated" for r in again.report) + int(again.section_changed)
        if left == 0:
            print(f"wrote {n_upd} entries" + (" and the unindexed section" if res.section_changed else "")
                  + " (verified by re-reading the file).")
        else:
            print(f"wrote, but {left} items are still stale on re-read: "
                  "another process or an editor may have overwritten the file.")
            return 3
    if args.check and changed:
        return 1
    return 2 if n_bad else 0


if __name__ == "__main__":
    sys.exit(main())