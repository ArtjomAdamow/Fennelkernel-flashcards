#!/usr/bin/env python3
"""Sync a Markdown component index with the real code.

Standalone tool: standard library only, never imports project code
(files are only parsed with `ast`), so it is not part of the main app.

Maintained automatically (per YAML block, only if the key exists there):
    line_start, line_end   position of the component in its .py file
    used_in                components that reference this one directly
Agent index only (computed, never in the index file):
    used_in_transitive     components that reach this one through module-level
                           variables, each with the path of the data flow
Never touched: tags, type, and every other key or comment.

NEW: unindexed components
    Classes/functions that have no entry in the index yet, but are connected
    to indexed components, are written to a generated section at the END of
    the index file, starting with the line
        **The update_index script has found unindexed components:**
    Each block there has a details/Summary HTML link with a line-range anchor
    and a complete YAML block (component_id and type are proposals). Copy a block into the outline to
    index it. The section is regenerated on every run: everything from that
    title line to the end of the file is replaced, so do not write your own
    text below it.
    "Connected" means: an indexed component depends on it (forward), or it
    depends on an indexed component (reverse; switch off with --no-reverse).
    --new-depth N continues the search N levels from newly found components,
    in both directions. Test files and folders (tests/, test_*.py, *_test.py,
    conftest.py) are skipped unless --include-tests is given.

Expected index layout (one entry per component). Three forms, may be mixed:

  ANCHOR (recommended) - the index keeps only what a human maintains:

    #### [Clean question](./flashcards_app/parser.py#L31-40 "parser:_clean_question")

    ```yaml
    tags: [manual, tags]
    ```

    Link text: the readable name of the code name (readable_name or ReadableName
    -> "Readable name"), no backticks. Link target: file and lines exactly as the
    editor wants them. The editor selects up to line_end + 1, so #L31-40 means
    line_start 31 and line_end 39 (the console report always uses the yaml
    convention: 31-39). Title: the component_id.
    The script finds the code again by the readable name (case and every
    non-alphanumeric character are ignored: 'Clean question' = _clean_question;
    'Flashcard flip' = Flashcard.flip), then by the part of the component_id after
    the last ':', and finally by the exact old line range. Several matches: the one
    nearest to the old lines wins. It rewrites only the lines in the target and
    the title; your link text and the rest of the line are kept. A new entry
    needs only [Readable name](./path/file.py): lines and a proposed component_id
    (file stem and snake_case code name, e.g. parser:deck_parser) are filled in.
    The tags block is optional and never touched. file comes from the link, type
    from the code (dataclass, class, function, async_function), used_in and
    used_in_transitive are computed. All of them appear only in the agent index (and as
    arrows in the diagrams).
    --slim converts the other two forms to this one (a backup is made; custom keys,
    a type that differs from the code, and comments are reported).

  SYMBOL (previous slim form, still read and updated; convert with --slim):

    #### [`Flashcard:`](./flashcards_app/models.py#Class&nbspFlashcard: "models:flashcard | 4-9")

  FULL (older form) - the whole block lives in the index:

    ### [`Flashcard:`](./flashcards_app/models.py#Class&nbspFlashcard:)

    ```yaml
    component_id: flashcard
    file: flashcards_app/models.py
    line_start: 0
    line_end: 0
    tags: [manual, tags]
    used_in: []
    ```

Symbol lookup of the SYMBOL and FULL forms uses the link anchor (text after '#'):
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
    bound locally there (parameter, assignment ...): base classes,
    annotations (also string annotations), calls, decorators
  * imports of project modules are resolved statically (nothing is run):
        import pkg.mod / import pkg.mod as m / from pkg import mod [as m]
        from pkg.mod import name [as n] / relative imports (from . import x)
        names re-exported through a package's __init__.py
    so `runtime.available_decks()` (with `from flashcards_app import runtime`),
    `m.func()`, `m.Class` and a bare imported name are linked exactly, for
    functions and classes alike. `module.Class.method` is linked as well when
    that method is indexed. Names imported from modules that are not part of
    the project (flask, os, ...) never match a project component.
  * module-level variables are transparent: after
        ENABLED_DECKS = [d for d in load_enabled_decks(STATE_PATH)]
    every component that uses ENABLED_DECKS (same file, `from x import
    ENABLED_DECKS`, or `module.ENABLED_DECKS`) uses load_enabled_decks indirectly,
    also through further variables (COPY = list(ENABLED_DECKS)).
    used_in lists direct references only. Indirect ones are written to the agent
    index as used_in_transitive, one entry per component with the path of the
    data flow (provider first; the file path is repeated when the flow changes
    the file); a relation that is direct as well is listed only in used_in:
        used_in_transitive:
          - "decks:add_enabled_deck":
              flows_to: "flashcards_app/runtime.py -> ENABLED_DECKS"
  * data flow at module level is transitive too: in
        CARDS = load_decks(ENABLED_DECKS)
    load_decks consumes what load_enabled_decks produced (through ENABLED_DECKS),
    so load_enabled_decks gets
          - "parser:load_decks":
              flows_to: "flashcards_app/runtime.py -> ENABLED_DECKS -> CARDS"
    (the last variable is the one that receives the result of the call). A
    component called directly inside the argument, load_decks(load_enabled_decks()),
    gives "... -> CARDS". Method calls on variables (ENABLED_DECKS.append(x)) do
    not count as calls. With several paths the shortest is written.
  * without import information (same-file references, star imports) the
    heuristic is: a bare name matches by name; an attribute name matches
    classes only
  * methods / nested classes ("Class.method") are indexed for line numbers;
    they are dependency targets only via an explicit import-resolved reference
  * a component's own name is ignored, and so are components nested in it
    or enclosing it (a method does not depend on its own class)
  * several candidates with one name: same file wins, then the indexed one;
    otherwise the name is skipped and reported

Entries in used_in / used_in_transitive are the `component_id` (fallback: code
name). Use --ref name to always use the code name.

GENERATED FILES (derived from the index - never edit them by hand)
    Agent index     agent_index.yaml next to the index (--agent-file; "none" = off)
        Only the YAML blocks of the resolved entries, in index order, no other
        text. A duplicate entry (same symbol indexed twice) is written once.
        .yaml: header as '#' comments, then one YAML document per block,
        separated by '---'. A file name ending in .md writes fenced ```yaml
        blocks instead (e.g. INDEX_agent.md). The header (everything before the
        first block) is kept if the file exists, so you can edit it; otherwise a
        default header with the minimal agent instructions is written.
        It is complete only if the index has no unindexed section and no
        unresolved entry. Otherwise the script says so on exit: finalize the
        index and run the script again (--strict: exit code 5).
    Diagrams        inside the index (--diagrams inline|file|off, default: inline)
        One Mermaid diagram per section = the nearest preceding plain heading
        of level --section-level (default 3 = '###'). Arrow A --> B means
        "B uses A" (provider --> consumer). Nodes are the section's components
        plus, dashed, their direct neighbours in other sections
        (--diagram-external off: only relations inside the section).
        The edges are read from the used_in lists as they are in the updated
        index; transitive relations (used_in_transitive) are drawn as dashed
        arrows (A -.-> B). Node ids are sanitized (models:flashcard becomes
        n_models_flashcard["models:flashcard"]); sections without any relation
        get no diagram.
        inline  (default) put each diagram right below its section heading in the index,
                between the marker lines
                    <!-- diagram:start (generated by update_index.py - do not edit) -->
                    <!-- diagram:end -->
                (regenerated on every run). Switching to file or off leaves
                existing marker regions untouched - delete them by hand.
        file    write all diagrams to --diagram-file (<index>_diagrams.md)
    Both files are written atomically, without numbered backups (they can
    always be regenerated), and only when their content changes. --check
    treats a missing or outdated generated file as stale.

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
    python update_index.py INDEX.md --agent-file INDEX_agent.md   # other agent file
    python update_index.py INDEX.md --agent-file none  # no agent file
    python update_index.py INDEX.md --diagrams inline  # diagrams inside the index
    python update_index.py INDEX.md --diagrams off     # no diagrams
    python update_index.py INDEX.md --diagram-file d.md  # other diagram file
    python update_index.py INDEX.md --section-level 2  # sections are '##' headings
    python update_index.py INDEX.md --diagram-external off  # no neighbour nodes
    python update_index.py INDEX.md --strict           # exit 5 if agent index incomplete
    python update_index.py INDEX.md --slim             # convert to the anchor form

Exit codes: 0 ok, 1 stale (--check), 2 unresolved entries, 3 write failed,
            4 interactive start without INDEX.md or without input,
            5 agent index incomplete (only with --strict).
"""
from __future__ import annotations

import argparse
import ast
import html
import os
import re
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import unquote

SELF = Path(__file__).resolve()
SECTION_TITLE = '<font color="#3b82f6">**The update_index script has found unindexed components:**</font>'
DEFAULT_SKIP_DIRS = {".git", ".hg", ".svn", "__pycache__", "node_modules", ".venv", "venv",
                     "env", ".tox", ".mypy_cache", ".pytest_cache", ".idea", "modules", "tools", "scripts", "archive", ".vscode",
                     "build", "dist", "site-packages"}

TEST_DIRS = {"tests", "test"}

FENCE_OPEN = re.compile(r"^\s*```ya?ml\s*$")
FENCE_CLOSE = re.compile(r"^\s*```\s*$")
HEADING = re.compile(r"^#{1,6}\s+(?:\[?`(?P<text>[^`]+)`\]?|\[(?P<ptext>[^]`\r\n]+)\])"
                     r"(?:\((?P<url>[^)\r\n\t\"]*?)(?:\s+\"(?P<title>[^\"\r\n]*)\")?\s*\))?")
HTML_HEADING = re.compile(
    r"^\s*(?:<details>\s*)?<Summary>\s*<a\b(?P<attrs>[^>]*)>(?P<html_text>.*?)</a>\s*</Summary>",
    re.IGNORECASE,
)
HTML_ATTR = re.compile(r"""(?P<name>[\w:.-]+)\s*=\s*(?P<quote>[\"'])(?P<value>.*?)(?P=quote)""")
ANCHOR = re.compile(r"^L(?P<s>\d+)(?:\s*-\s*L?(?P<e>\d+))?$")
PLAIN_HEADING = re.compile(r"^#{1,6}\s+\S")
TITLE = re.compile(r"^\s*(?P<id>[\w.:\-/]*)\s*(?:\|\s*(?P<s>\d+)\s*-\s*(?P<e>\d+))?\s*$")
KEY = re.compile(r"^\s*(?P<key>[A-Za-z_]\w*):\s*(?P<val>.*?)\s*$")
LIST_ITEM = re.compile(r"^\s*-\s+(?P<item>.*?)\s*$")
NBSP_ENTITY = re.compile(r"&nbsp;?", re.I)
KIND_PREFIX = re.compile(r"^(async\s+def|def|class)\s+(?P<name>\S.*)$", re.I)
PLAIN_ITEM = re.compile(r"^[\w.\-/]+$")
ALL_FIELDS = {"lines", "used_in"}

# default header of a new agent index (the minimal agent instructions)
AGENT_HEADER_LINES = [
    "**Important:**",
    "  line_numbers: 1-based, inclusive, blank lines counted",
    "  line_start: first decorator line (e.g. @dataclass) or def/class line",
    "  line_end: last line of the body",
    "Never edit this file.",
]
DIAGRAM_START = "<!-- diagram:start (generated by update_index.py - do not edit) -->"
DIAGRAM_END = "<!-- diagram:end -->"

MERMAID_HEADER = """graph LR
    %% arrow A --> B: B uses A; dashed = component of another section
    %% dashed arrow A -.-> B: transitive relation (data flow through module-level variables)
    classDef ext stroke: #3b82f6,stroke-dasharray: 4 3
    linkStyle default stroke: #3b82f6, color: #3b82f6
    classDef default fill: #000000ff, stroke: #3b82f6, color: #ffffffff"""


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


def html_heading_attrs(m: re.Match) -> dict[str, re.Match]:
    """Quoted attributes on the HTML summary link, keyed by lowercase name."""
    attrs = m.groupdict().get("attrs")
    if attrs is None:
        return {}
    return {attr["name"].lower(): attr for attr in HTML_ATTR.finditer(attrs)}


def heading_url(m: re.Match) -> str:
    attrs = html_heading_attrs(m)
    if attrs:
        href = attrs.get("href")
        return html.unescape(href["value"]) if href else ""
    return m.groupdict().get("url") or ""


def heading_title(m: re.Match) -> str | None:
    attrs = html_heading_attrs(m)
    if attrs:
        title = attrs.get("title")
        return html.unescape(title["value"]) if title else None
    return m.groupdict().get("title")


def is_html_heading(m: re.Match) -> bool:
    return m.groupdict().get("attrs") is not None


def heading_text(m: re.Match) -> str:
    if is_html_heading(m):
        text = re.sub(r"<[^>]*>", "", m.group("html_text"))
        return html.unescape(text).strip()
    return m.groupdict().get("text") or m.groupdict().get("ptext") or ""


def is_py_url(m: re.Match) -> bool:
    """Does the heading link point to a .py file?"""
    return heading_url(m).split("#", 1)[0].strip().lower().endswith(".py")


def heading_match(line: str) -> re.Match | None:
    """Match of a component link in Markdown or a details/Summary HTML block."""
    html_match = HTML_HEADING.match(line)
    if html_match is not None and is_py_url(html_match):
        return html_match
    m = HEADING.match(line)
    if m is None:
        return None
    return m if (m.groupdict().get("text") is not None or is_py_url(m)) else None


def parse_title(title: str | None) -> tuple[str, str, str, bool]:
    """Old link title "component_id | start-end" -> (id, start, end, unparseable)."""
    if title is None:
        return "", "", "", False
    m = TITLE.match(title)
    if not m:
        return "", "", "", True
    return m["id"], m["s"] or "", m["e"] or "", False


def edit_html_heading(line: str, m: re.Match, url: str | None = None,
                      title: str | None = None, text: str | None = None) -> str:
    """Update selected details/Summary link values while preserving its HTML structure."""
    attrs = html_heading_attrs(m)
    replacements = []
    base = m.start("attrs")
    if url is not None:
        href = attrs.get("href")
        if href:
            replacements.append((base + href.start("value"), base + href.end("value"),
                                 html.escape(url, quote=True)))
    if title is not None:
        title_attr = attrs.get("title")
        if title_attr:
            replacements.append((base + title_attr.start("value"), base + title_attr.end("value"),
                                 html.escape(title, quote=True)))
        else:
            replacements.append((m.end("attrs"), m.end("attrs"),
                                 f' title="{html.escape(title, quote=True)}"'))
    if text is not None:
        replacements.append((m.start("html_text"), m.end("html_text"),
                             html.escape(text, quote=False)))
    for start, end, value in sorted(replacements, reverse=True):
        line = line[:start] + value + line[end:]
    return line


def set_title(line: str, m: re.Match, title: str) -> str:
    """The heading line with its link title replaced (or added)."""
    if is_html_heading(m):
        return edit_html_heading(line, m, title=title)
    return line[: m.end("url")].rstrip() + f' "{title}"' + line[m.end() - 1:]


def set_link(line: str, m: re.Match, url: str, title: str) -> str:
    """The heading line with link target and title replaced; text and rest kept."""
    if is_html_heading(m):
        return edit_html_heading(line, m, url=url, title=title)
    return line[: m.start("url")] + f'{url} "{title}")' + line[m.end():]


def render_link_heading(line: str, m: re.Match, text: str, url: str, title: str) -> str:
    """Render a component link, keeping its current Markdown or HTML format."""
    if is_html_heading(m):
        return edit_html_heading(line, m, url=url, title=title, text=text)
    prefix = re.match(r"^#{1,6}\s+", line).group(0)
    return f'{prefix}[{text}]({url} "{title}"){line[m.end():]}'


def anchor_fragment(sym: tuple) -> str:
    """Editor selection of a component: the editor selects up to line_end + 1."""
    return f"L{sym[0]}-{sym[1] + 1}"


def norm_name(text: str) -> str:
    return re.sub(r"[^0-9a-z]", "", text.lower())


def readable(name: str) -> str:
    """parse_deck / _clean_question / CardPosition -> Parse deck / Clean question / Card position."""
    words = [w for w in re.split(r"[_.\s]+", snake(name)) if w]
    text = " ".join(words).lower()
    return text[:1].upper() + text[1:] if text else name


def locate(symbols: dict, texts: list[str], old: tuple[int, int] | None):
    """(symbol, how, ambiguous) for a link: by readable name, then id suffix, then position.

    A readable name matches a code name when both are equal after dropping case and
    every character that is not a letter or digit ('Clean question' = '_clean_question').
    Several matches: the one nearest to the old position wins if that is unambiguous."""
    for text in texts:
        target = norm_name(text)
        if not target:
            continue
        exact = [v for k, v in symbols.items() if norm_name(k) == target]
        cands = exact or [v for k, v in symbols.items() if norm_name(k.split(".")[-1]) == target]
        if len(cands) == 1:
            return cands[0], "name", False
        if len(cands) > 1:
            if old is None:
                return None, "", True
            ranked = sorted(cands, key=lambda v: abs(v[0] - old[0]))
            if abs(ranked[0][0] - old[0]) < abs(ranked[1][0] - old[0]):
                return ranked[0], "name", False
            return None, "", True
    if old is not None:
        hits = [v for v in symbols.values() if v[0] == old[0] and v[1] == old[1]]
        if len(hits) == 1:
            return hits[0], "position", False
    return None, "", False


def label(ref: Ref) -> str:
    kind, name = ref
    return f"{kind} {name}" if kind else name


def name_candidates(m: re.Match) -> list[Ref]:
    raw = []
    url = heading_url(m)
    if "#" in url:
        raw.append(url.split("#", 1)[1])
    raw.append(heading_text(m))
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


@dataclass
class RefInfo:
    names: set          # names read (Load) and not bound locally
    chains: list        # maximal attribute chains rooted at a name: ("runtime", "available_decks")
    loose_attrs: set    # attribute names of chains not rooted at a plain name, e.g. f().x
    bound: set          # names bound inside the component (assignments, parameters, ...)
    imports: list       # import statements inside the component


def _chains(nodes) -> tuple[list, set]:
    nodes = list(nodes)
    inner = {id(n.value) for n in nodes
             if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Attribute)}
    chains, loose = [], set()
    for n in nodes:
        if isinstance(n, ast.Attribute) and id(n) not in inner:
            parts, cur = [], n
            while isinstance(cur, ast.Attribute):
                parts.append(cur.attr)
                cur = cur.value
            if isinstance(cur, ast.Name):
                chains.append(tuple([cur.id] + parts[::-1]))
            else:
                loose.update(parts)
    return chains, loose


def reference_info(node: ast.AST) -> RefInfo:
    """What a class/function node refers to (names, attribute chains, imports)."""
    walk = list(ast.walk(node))
    names: set[str] = set()
    bound: set[str] = set()
    annotations, imports = [], []
    for n in walk:
        if isinstance(n, ast.Name):
            (names if isinstance(n.ctx, ast.Load) else bound).add(n.id)
        elif isinstance(n, ast.arg):
            bound.add(n.arg)
            if n.annotation is not None:
                annotations.append(n.annotation)
        elif isinstance(n, (ast.Import, ast.ImportFrom)):
            imports.append(n)
        elif isinstance(n, ast.ExceptHandler) and n.name:
            bound.add(n.name)
        elif isinstance(n, ast.AnnAssign):
            annotations.append(n.annotation)
        elif isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.returns is not None:
            annotations.append(n.returns)
    names -= bound
    chains, loose = _chains(walk)
    for ann in annotations:  # string annotations: "Flashcard", "models.Flashcard"
        for c in ast.walk(ann):
            if isinstance(c, ast.Constant) and isinstance(c.value, str):
                try:
                    sub = ast.parse(c.value.strip(), mode="eval")
                except SyntaxError:
                    continue
                sub_nodes = list(ast.walk(sub))
                names.update(x.id for x in sub_nodes if isinstance(x, ast.Name))
                ch, lo = _chains(sub_nodes)
                chains += ch
                loose |= lo
    return RefInfo(names, chains, loose, bound, imports)


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
class ImportResolver:
    """Resolves imports between project modules statically (nothing is imported/run).

    A binding is ("mod", stem) for a module/package, ("from", stem, name) for
    `from <stem> import name`, or ("ext",) for anything outside the project.
    `stem` is a path without suffix: <stem>.py or <stem>/__init__.py.
    """

    def __init__(self, root: Path, md_dir: Path, cache: dict):
        self.root = root
        self.bases = list(dict.fromkeys([root, md_dir]))
        self.cache = cache                      # file -> symbols (shared)
        self._imports: dict[Path, dict] = {}
        self._vars: dict[Path, dict] = {}
        self._module_files: dict[Path, Path | None] = {}

    # -- files and symbols
    def module_file(self, stem: Path) -> Path | None:
        if stem not in self._module_files:
            py, init = stem.with_name(stem.name + ".py"), stem / "__init__.py"
            self._module_files[stem] = (py.resolve() if py.is_file()
                                        else init.resolve() if init.is_file() else None)
        return self._module_files[stem]

    def module_exists(self, stem: Path) -> bool:
        return self.module_file(stem) is not None or stem.is_dir()

    def symbols_of(self, py: Path) -> dict:
        if py not in self.cache:
            try:
                self.cache[py] = collect_symbols(py)
            except (SyntaxError, UnicodeDecodeError, OSError):
                self.cache[py] = {}
        return self.cache[py]

    # -- import bindings
    def _search_bases(self, py: Path) -> list[Path]:
        ups = []
        for parent in py.parents:                # importing file's folders, up to the root
            ups.append(parent)
            if parent == self.root:
                break
        return list(dict.fromkeys([*ups, *self.bases]))

    def _absolute_stem(self, parts: list[str], py: Path) -> Path | None:
        for base in self._search_bases(py):
            stem = base.joinpath(*parts)
            if self.module_exists(stem):
                return stem
        return None

    def bindings(self, nodes, py: Path) -> dict[str, tuple]:
        out: dict[str, tuple] = {}
        for st in nodes:
            if isinstance(st, ast.Import):
                for al in st.names:
                    parts = al.name.split(".")
                    if al.asname:
                        stem = self._absolute_stem(parts, py)
                        out[al.asname] = ("mod", stem) if stem else ("ext",)
                    else:                        # `import a.b.c` binds the name `a`
                        stem = self._absolute_stem(parts[:1], py)
                        out[parts[0]] = ("mod", stem) if stem else ("ext",)
            else:
                if st.level:                     # relative import
                    base = py.parent
                    for _ in range(st.level - 1):
                        base = base.parent
                    stem = base.joinpath(*(st.module.split(".") if st.module else []))
                    stem = stem if self.module_exists(stem) else None
                else:
                    stem = self._absolute_stem(st.module.split("."), py) if st.module else None
                for al in st.names:
                    if al.name != "*":
                        out[al.asname or al.name] = ("from", stem, al.name) if stem else ("ext",)
        return out

    @staticmethod
    def _toplevel_stmts(body):
        """Statements of the module level, also inside if / try / with blocks (not in defs)."""
        container = (ast.If, ast.Try, ast.With, getattr(ast, "TryStar", ast.Try))
        for st in body:
            yield st
            if isinstance(st, container):
                parts = [st.body, getattr(st, "orelse", []), getattr(st, "finalbody", [])]
                parts += [h.body for h in getattr(st, "handlers", [])]
                for sub in parts:
                    yield from ImportResolver._toplevel_stmts(sub)

    def vars_of(self, py: Path) -> dict[str, list]:
        """Module-level variables of a file: name -> assignment statements."""
        if py not in self._vars:
            found: dict[str, list] = {}
            self._vars[py] = found
            try:
                tree = ast.parse(py.read_text(encoding="utf-8"))
            except (SyntaxError, UnicodeDecodeError, OSError):
                return found

            def names(target):
                if isinstance(target, ast.Name):
                    yield target.id
                elif isinstance(target, (ast.Tuple, ast.List)):
                    for t in target.elts:
                        yield from names(t)

            for st in self._toplevel_stmts(tree.body):
                if isinstance(st, ast.Assign):
                    targets = [n for t in st.targets for n in names(t)]
                elif isinstance(st, ast.AnnAssign) and st.value is not None:
                    targets = list(names(st.target))
                else:
                    continue
                for n in targets:
                    found.setdefault(n, []).append(st)
        return self._vars[py]

    @staticmethod
    def _toplevel_imports(body):
        container = (ast.If, ast.Try, ast.With, getattr(ast, "TryStar", ast.Try))
        for st in body:
            if isinstance(st, (ast.Import, ast.ImportFrom)):
                yield st
            elif isinstance(st, container):      # TYPE_CHECKING blocks, try/except ImportError
                parts = [st.body, getattr(st, "orelse", []), getattr(st, "finalbody", [])]
                parts += [h.body for h in getattr(st, "handlers", [])]
                for sub in parts:
                    yield from ImportResolver._toplevel_imports(sub)

    def imports_of(self, py: Path) -> dict[str, tuple]:
        if py not in self._imports:
            self._imports[py] = {}               # guards against import cycles
            try:
                tree = ast.parse(py.read_text(encoding="utf-8"))
            except (SyntaxError, UnicodeDecodeError, OSError):
                return self._imports[py]
            self._imports[py] = self.bindings(list(self._toplevel_imports(tree.body)), py)
        return self._imports[py]

    def imports_for(self, py: Path, local_nodes: list) -> dict[str, tuple]:
        base = self.imports_of(py)
        return {**base, **self.bindings(local_nodes, py)} if local_nodes else base

    # -- resolution
    def resolve_symbol(self, stem: Path, name: str, depth: int = 0):
        f = self.module_file(stem)
        if f is None or depth > 4:
            return None
        if name in self.symbols_of(f):
            return (f, name)
        binding = self.imports_of(f).get(name)   # re-export through __init__.py
        if binding and binding[0] == "from":
            return self.resolve_symbol(binding[1], binding[2], depth + 1)
        return None

    def resolve_chain(self, stem: Path, parts: list[str], depth: int = 0) -> list[tuple]:
        """(file, qualified name) targets for <stem>.<parts[0]>.<parts[1]>..."""
        if not parts or depth > 8:
            return []
        hit = self.resolve_symbol(stem, parts[0])
        if hit:
            f, qual = hit
            out, symbols = [hit], self.symbols_of(f)
            for part in parts[1:]:               # Class.method, if that exists
                qual = f"{qual}.{part}"
                if qual not in symbols:
                    break
                out.append((f, qual))
            return out
        sub = stem / parts[0]
        return self.resolve_chain(sub, parts[1:], depth + 1) if self.module_exists(sub) else []

    def resolve_var(self, stem: Path, name: str, depth: int = 0):
        """(file, name) of the module-level variable `name` in module `stem` (follows re-exports)."""
        f = self.module_file(stem)
        if f is None or depth > 4:
            return None
        if name in self.vars_of(f) and name not in self.symbols_of(f):
            return (f, name)
        binding = self.imports_of(f).get(name)
        if binding and binding[0] == "from":
            return self.resolve_var(binding[1], binding[2], depth + 1)
        return None

    def resolve_var_chain(self, stem: Path, parts: list[str], depth: int = 0) -> list[tuple]:
        """Variable targets for <stem>.<parts[0]>... (the variable is parts[0], or in a submodule)."""
        if not parts or depth > 8:
            return []
        hit = self.resolve_var(stem, parts[0])
        if hit:
            return [hit]
        sub = stem / parts[0]
        return self.resolve_var_chain(sub, parts[1:], depth + 1) if self.module_exists(sub) else []

    def resolve_var_binding(self, binding: tuple, rest: list[str]) -> list[tuple]:
        if binding[0] == "mod":
            return self.resolve_var_chain(binding[1], rest)
        if binding[0] == "from":
            return self.resolve_var_chain(binding[1], [binding[2], *rest])
        return []

    def resolve_binding(self, binding: tuple, rest: list[str]) -> list[tuple]:
        if binding[0] == "mod":
            return self.resolve_chain(binding[1], rest)
        if binding[0] == "from":
            return self.resolve_chain(binding[1], [binding[2], *rest])
        return []                                # external module


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
    agent_file: Path | None = None      # None: no agent index
    diagrams: str = "inline"            # inline | file | off
    section_level: int = 3
    diagram_external: str = "one-hop"   # one-hop | off
    slim: bool = False                  # convert full yaml blocks to the slim form


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
    used_in: set = field(default_factory=set)
    section: int = -1           # ordinal of the section heading above the block (-1: none)
    duplicate: bool = False     # same symbol indexed twice; only the first one counts
    final_block: list = field(default_factory=list)   # yaml lines after the update (= agent block)
    extra_lines: list = field(default_factory=list)   # transitive yaml lines appended in the agent block (full form)
    tused: dict = field(default_factory=dict)         # transitive used_in: ref -> data flow ((file, variable), ...)
    extra_bound: set = field(default_factory=set)     # names bound outside a partial expression
    form: str = "full"          # full | symbol (old slim: #Class&nbspName "id | s-e") | anchor (#L31-40 "id")
    migrated: bool = False      # converted to the anchor form in this run (--slim)
    was_full: bool = False      # ... and the index block had the full keys before
    title_bad: bool = False     # symbol form: link title is not "component_id | start-end"
    title_id: str = ""          # component_id as found in the link title
    path_part: str = ""         # link target before '#', as written
    frag: str = ""              # link fragment as written (without '#')
    note: str = ""              # remark to report as a warning
    head: int = -1              # index of the heading line
    head_match: object = None   # regex match of the heading line
    block_fields: dict = field(default_factory=dict)
    tags_lines: list = field(default_factory=list)    # the `tags` lines of the index block


@dataclass
class Result:
    text: str
    report: list
    warnings: list
    new: list
    section_changed: bool
    agent_text: str | None = None       # generated agent index (None: switched off)
    diagram_text: str | None = None     # generated diagram file (None: not in file mode)
    inline_changed: bool = False        # inline diagram regions in the index changed


def parse_fields(block: list[str]) -> dict[str, str]:
    return {m["key"]: m["val"].strip("'\"") for l in block if (m := KEY.match(l))}


def tags_lines(block: list[str], eol: str) -> list[str]:
    """The `tags` key (one line, or a block-style list) of a yaml block; `tags: []` if absent."""
    for i, l in enumerate(block):
        m = KEY.match(l)
        if m and m["key"] == "tags":
            _, end = read_list(block, i)
            return [x if x.endswith(("\n", "\r")) else x + eol for x in block[i:end]]
    return [f"tags: []{eol}"]


def build_entry(lines, hidx, hm, a, b, md_path, root, cache, ref_mode) -> Entry | None:
    """One index entry: a full yaml block, or a slim heading link (+ optional tags block).

    hidx / hm: line index and regex match of the component heading above (or None).
    a / b: first line and closing fence of the yaml block (None: heading without block)."""
    f = parse_fields(lines[a:b]) if a is not None else {}
    cands = list(name_candidates(hm)) if hm is not None else []
    slim = False
    if "line_start" not in f or "line_end" not in f or "index_conventions" in f:
        if "index_conventions" in f or hm is None or not is_py_url(hm):
            return None  # some other yaml block, leave alone
        slim = True

    path_part, frag, form = "", "", "full"
    start = end = None
    if slim:
        path_part, _, frag = heading_url(hm).partition("#")
        path_part, frag = path_part.strip(), frag.strip()
        file_value = path_part
        am = ANCHOR.match(frag) if frag else None
        if frag and not am:
            form = "symbol"                        # #Class&nbspName "id | start-end"
            cid_raw, s0, e0, bad = parse_title(heading_title(hm))
            old = (s0, e0)
        else:
            form, bad = "anchor", False            # #L31-40 "id" (or no fragment yet)
            title = heading_title(hm)
            tm = TITLE.match(title) if title is not None else None
            cid_raw = (tm["id"] if tm else (title or "").strip())
            if am:
                start = int(am["s"])
                end = max(start, int(am["e"]) - 1) if am["e"] else start   # editor: line_end + 1
            old = (str(start), str(end)) if am else ("", "")
    else:
        file_value = f.get("file", "")
        cid_raw = f.get("component_id", "")
        old, bad = (f["line_start"], f["line_end"]), False
        if cid_raw:
            cands.append(parse_ref(cid_raw))
    cands = finalize(cands)
    name = (readable_label := heading_text(hm)) if form == "anchor" else (label(cands[0]) if cands else "?")
    e = Entry(a=-1 if a is None else a, b=-1 if b is None else b, name=name, old=old)
    e.form, e.title_bad, e.block_fields = form, bad, f
    e.head, e.head_match = (-1 if hidx is None else hidx), hm
    e.title_id = clean_name(cid_raw) if slim else ""
    e.path_part, e.frag = path_part, frag

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

    if form == "anchor":
        texts = [heading_text(hm)] + ([cid_raw.rsplit(":", 1)[-1]] if cid_raw else [])
        sym, how, ambiguous = locate(symbols, texts, (start, end) if start is not None else None)
        if sym is None:
            tried = ", ".join(repr(t) for t in texts if t)
            e.status = (f"AMBIGUOUS NAME in {e.py.name} (tried: {tried}; give a line range)" if ambiguous
                        else f"SYMBOL NOT FOUND in {e.py.name} (tried: {tried})")
            return e
        if how == "position":
            e.note = (f"link text {heading_text(hm)!r} does not match the code name {sym[4]!r} "
                      "(found by its line range)")
        e.name = label((sym[2], sym[4]))
    else:
        sym = next((s for k, n in cands if (s := find_symbol(symbols, n, k))), None)
        if sym is None:
            if any(find_symbol(symbols, n, None) for _, n in cands):
                e.status = f"KIND MISMATCH in {e.py.name} (anchor says {cands[0][0]!r})"
            else:
                tried = ", ".join(label(c) for c in cands) or "-"
                e.status = f"SYMBOL NOT FOUND in {e.py.name} (tried: {tried})"
            return e
    e.sym = sym
    e.cid = clean_name(cid_raw)
    e.ref = e.cid if (ref_mode == "id" and e.cid) else sym[4]
    return e


KNOWN_KEYS = {"component_id", "type", "file", "line_start", "line_end", "tags",
              "dependencies", "used_in"}


def convert_to_slim(e: Entry, lines, md_path: Path, root: Path, eol: str, warnings: list) -> bool:
    """--slim: full block / old slim form -> anchor form: [Readable name](path#L4-10 "id")."""
    hm = e.head_match
    if hm is None or not is_py_url(hm):
        warnings.append(f"{e.name!r}: the heading has no link to a .py file - not converted")
        return False
    if e.form == "full":
        link_py = resolve(e.path_part or heading_url(hm).split("#", 1)[0].strip(), md_path, root)
        if link_py != e.py:
            warnings.append(f"{e.name!r}: file: {e.file_value!r} differs from the heading link - not converted")
            return False
        block = lines[e.a:e.b]
        for k in e.block_fields:
            if k not in KNOWN_KEYS:
                warnings.append(f"{e.name!r}: custom key {k!r} is dropped by the anchor form")
        if e.block_fields.get("type") and e.block_fields["type"] != component_type(e.sym):
            warnings.append(f"{e.name!r}: type {e.block_fields['type']!r} is dropped, "
                            f"the anchor form derives {component_type(e.sym)!r} from the code")
        if any(l.lstrip().startswith("#") for l in block):
            warnings.append(f"{e.name!r}: comment lines in the yaml block are dropped by the anchor form")
        e.tags_lines = tags_lines(block, eol)
        e.path_part = heading_url(hm).split("#", 1)[0].strip()
    e.was_full, e.form = e.form == "full", "anchor"
    e.migrated, e.title_id = True, e.cid
    return True


def yaml_scalar(text: str) -> str:
    return text if re.fullmatch(r"[\w.\-/:]+", text) else '"' + text.replace('"', '\\"') + '"'


def dq(text: str) -> str:
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


def flow_path(flow: tuple, root: Path) -> str:
    """((runtime.py, ENABLED_DECKS), (runtime.py, CARDS)) -> "flashcards_app/runtime.py -> ENABLED_DECKS -> CARDS"."""
    parts, last = [], None
    for py, name in flow:
        if py != last:
            parts.append(rel_path(root, py))
            last = py
        parts.append(name)
    return " -> ".join(parts)


def transitive_lines(e: Entry, root: Path) -> list[str]:
    """The `used_in_transitive` key of a component: a list with one entry per component."""
    if not e.tused:
        return ["used_in_transitive: []"]
    out = ["used_in_transitive:"]
    for ref in sorted(e.tused):
        out += [f"  - {dq(ref)}:", f"      flows_to: {dq(flow_path(e.tused[ref], root))}"]
    return out


def slim_block(e: Entry, root: Path) -> list[str]:
    """The full yaml block of a slim entry as it goes into the agent index."""
    rows = [("component_id", yaml_scalar(e.cid)), ("type", component_type(e.sym)),
            ("file", yaml_item(rel_path(root, e.py))),
            ("line_start", e.sym[0]), ("line_end", e.sym[1])]
    out = [f"{k}: {v}" for k, v in rows]
    out += [l.rstrip() for l in e.tags_lines]
    out += [f"used_in: {flow(e.used_in)}"]
    return out + transitive_lines(e, root)


# ---------------------------------------------------------------------- graph
TOOL_MARK = "Sync a Markdown component index with the real code"


def is_tool_copy(py: Path) -> bool:
    """Is this file a copy of update_index.py itself? (never project code)"""
    try:
        with open(py, encoding="utf-8", errors="ignore") as fh:
            return TOOL_MARK in fh.read(3000)
    except OSError:
        return False


def discover_unindexed(entries, cache, root, opts, warnings) -> list[Entry]:
    """All top-level classes/functions in scope that are not in the index."""
    indexed = {(e.py, e.sym[4]) for e in entries if e.sym is not None}
    files = set(cache)
    if opts.scan == "project":
        files |= set(iter_py_files(root, opts.exclude_dirs))
    pool, copies = [], []
    for py in sorted(files):
        if py == SELF or (not opts.include_tests and is_test_path(py, root)):
            continue
        if py not in cache and is_tool_copy(py):
            copies.append(rel_path(root, py))
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
    if copies:
        warnings.append(f"ignored {len(copies)} copy/copies of update_index.py found under the root "
                        f"(not project code): {', '.join(copies)}")
    return pool


def assign_new_refs(active: list[Entry], entries: list[Entry], ref_mode: str) -> None:
    used = {e.ref for e in entries if e.sym is not None} | {e.cid for e in entries if e.cid}
    for e in sorted(active, key=lambda x: (str(x.py), x.sym[0])):
        base = f"{e.py.stem}:{snake(e.sym[4])}"
        cid, n = base, 2
        while cid in used:
            cid = f"{base}_{n}"
            n += 1
        used.add(cid)
        e.cid = cid
        e.ref = cid if ref_mode == "id" else e.sym[4]


def build_graph(entries, pool, new_depth, warnings, ref_mode, reverse=True, resolver=None) -> list[Entry]:
    """Fill deps / used_in. Returns the unindexed components to list."""
    live_all = [e for e in entries if e.sym is not None]
    live = [e for e in live_all if not e.duplicate]    # a symbol indexed twice counts once

    seen: dict[str, Entry] = {}
    for e in live:
        if e.ref in seen and seen[e.ref].sym is not e.sym:
            warnings.append(f"duplicate reference {e.ref!r} used by two different components")
        seen.setdefault(e.ref, e)

    by_name: dict[str, list[Entry]] = {}
    for e in live + pool:
        if "." not in e.sym[4]:              # methods / nested: not a target
            by_name.setdefault(e.sym[4], []).append(e)

    entry_by_key = {(e.py, e.sym[4]): e for e in live + pool}
    infos: dict[int, RefInfo] = {}
    warned: set[str] = set()

    def info_of(e: Entry) -> RefInfo:
        key = id(e.sym[3])
        if key not in infos:
            infos[key] = reference_info(e.sym[3])
        return infos[key]

    def contained(t: Entry, s: Entry) -> bool:
        return t.py == s.py and s.sym[0] <= t.sym[0] and t.sym[1] <= s.sym[1]

    def related(t: Entry, s: Entry) -> bool:
        """Same component, or one is nested in the other (e.g. method and its class)."""
        return contained(t, s) or contained(s, t)

    def pick(name: str, src: Entry, classes_only: bool) -> list[Entry]:
        cands = [t for t in by_name.get(name, [])
                 if (not classes_only or t.sym[2] == "class") and not related(t, src)]
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

    def via_import(src: Entry, binding: tuple, rest: list[str]) -> list[Entry]:
        found = []
        for key in resolver.resolve_binding(binding, rest):
            t = entry_by_key.get(key)
            if t is not None and not related(t, src):
                found.append(t)
        return found

    def collect(src: Entry, path: frozenset = frozenset(), depth: int = 0) -> list[tuple]:
        """(component, via) pairs referenced by src. via is None for a direct reference,
        otherwise the chain of module-level variables ((file, name) pairs, nearest to src
        first) through which the component is reached (ENABLED_DECKS = [d for d in
        load_enabled_decks(...)] links the users of ENABLED_DECKS to load_enabled_decks)."""
        info = info_of(src)
        bound = info.bound | src.extra_bound
        imports = resolver.imports_for(src.py, info.imports) if resolver else {}
        own = resolver.symbols_of(src.py) if resolver else {}
        mine = resolver.vars_of(src.py) if resolver else {}
        found: list[tuple] = []
        var_refs: list[tuple] = []
        for n in sorted(info.names - src.extra_bound):       # bare names
            b = imports.get(n)
            if b is None:
                if n in mine and n not in own:     # module variable of the same file
                    var_refs.append((src.py, n))
                else:
                    found += [(t, None) for t in pick(n, src, False)]
            else:
                hit = via_import(src, b, [])
                found += [(t, None) for t in hit]
                if not hit and resolver:           # imported variable: from x import VAR
                    var_refs += resolver.resolve_var_binding(b, [])
        for chain in sorted(info.chains):          # module_alias.func(), Class.method, ...
            b = None if chain[0] in bound else imports.get(chain[0])
            if b is None:                          # no import information: classes only
                for a in chain[1:]:
                    found += [(t, None) for t in pick(a, src, True)]
            else:
                hit = via_import(src, b, list(chain[1:]))
                found += [(t, None) for t in hit]
                if not hit and resolver:           # module_alias.VAR
                    var_refs += resolver.resolve_var_binding(b, list(chain[1:]))
        for a in sorted(info.loose_attrs):
            found += [(t, None) for t in pick(a, src, True)]
        if resolver and depth < 8:
            for key in sorted(set(var_refs), key=lambda k: (str(k[0]), k[1])):
                if key in path:                    # cycle between variables
                    continue
                for st in resolver.vars_of(key[0]).get(key[1], []):
                    pseudo = Entry(a=-1, b=-1, name=key[1], old=("", ""), py=key[0],
                                   sym=(st.lineno, st.end_lineno, "var", st, key[1]))
                    for t, v in collect(pseudo, path | {key}, depth + 1):
                        found.append((t, (key, *(v or ()))))
        return found

    flows: dict | None = None

    def flow_deps() -> dict:
        """Data flow at module level: in `CARDS = load_decks(ENABLED_DECKS)` the called component
        (load_decks) consumes the components behind its arguments (load_enabled_decks).
        -> {(file, qualified name of the consumer): [(provider, data flow), ...]}"""
        nonlocal flows
        if flows is not None:
            return flows
        flows = {}
        if resolver is None:
            return flows
        for py in sorted(resolver.cache, key=str):
            stmts: dict[int, tuple] = {}            # statement -> (statement, target names)
            for name, sts in resolver.vars_of(py).items():
                for st in sts:
                    stmts.setdefault(id(st), (st, []))[1].append(name)
            for st, targets in stmts.values():
                outer = reference_info(st).bound
                for call in (n for n in ast.walk(st.value) if isinstance(n, ast.Call)):
                    def part(node):
                        return Entry(a=-1, b=-1, name="expr", old=("", ""), py=py,
                                     sym=(node.lineno, node.end_lineno, "var", node, "expr"),
                                     extra_bound=set(outer))
                    callees = [t for t, v in collect(part(call.func)) if v is None]
                    if not callees:
                        continue
                    for arg in [*call.args, *(k.value for k in call.keywords)]:
                        for d, v in collect(part(arg)):
                            for c in callees:
                                if d is c or related(d, c):
                                    continue
                                for x in sorted(targets):
                                    flows.setdefault((c.py, c.sym[4]), []).append(
                                        (d, (*reversed(v or ()), (py, x))))
        return flows

    def targets_of(src: Entry) -> list[tuple]:
        """(component, flow) pairs: flow is None for a direct reference, else the data flow
        from the component to src as ((file, variable), ...), provider first."""
        out = [(t, None if v is None else tuple(reversed(v)))
               for t, v in collect(src) if not related(t, src)]
        out += [(t, f) for t, f in flow_deps().get((src.py, src.sym[4]), []) if not related(t, src)]
        return out

    # reverse map: who depends on whom (only unindexed components as dependents)
    users_of: dict[int, list[Entry]] = {}
    if reverse:
        for p in pool:
            for t, _ in targets_of(p):
                users_of.setdefault(id(t), []).append(p)

    # phase A: which unindexed components are connected (up to new_depth levels)?
    frontier = live
    for _ in range(new_depth):
        nxt = []
        for src in frontier:
            for t, _ in targets_of(src):                  # forward: src depends on t
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
    def keep_shortest(mapping: dict, ref: str, flow: tuple) -> None:
        def rank(f):
            return (len(f), [(str(py), name) for py, name in f])
        old = mapping.get(ref)
        if old is None or rank(flow) < rank(old):
            mapping[ref] = flow

    for src in live + active:
        for t, flow in targets_of(src):
            if t.is_new and not t.active:
                continue
            if flow is None:                        # direct reference
                t.used_in.add(src.ref)
            else:                                   # reached through variables / module data flow
                keep_shortest(t.tused, src.ref, flow)
    for e in live + active:                         # direct wins over transitive
        for ref in [r for r in e.tused if r in e.used_in]:
            del e.tused[ref]
    first = {(e.py, e.sym[4]): e for e in live}
    for dup in live_all:                    # later duplicate: same lists as the first block
        if dup.duplicate:
            f1 = first[(dup.py, dup.sym[4])]
            dup.used_in, dup.tused = set(f1.used_in), dict(f1.tused)
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


def scan_sections(lines: list[str], level: int) -> list[tuple[int, str]]:
    """[(line index, title)] of plain headings of exactly `level` hashes.

    Component headings (backticked text) and anything inside code fences are
    not sections."""
    pat = re.compile(rf"^#{{{level}}}\s+(?P<title>\S.*?)\s*$")
    found, in_fence = [], False
    for i, line in enumerate(lines):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        m = pat.match(line.rstrip("\r\n"))
        if m and not heading_match(line):
            found.append((i, m["title"]))
    return found


def parse_entries(lines: list[str], level: int = 3):
    """[(heading index, heading match, first line, closing fence, section ordinal)]

    One item per yaml block (with the component heading above it, if any), plus one
    item (without block: first line and fence are None) for every component heading
    whose link points to a .py file but that has no yaml block."""
    sections = scan_sections(lines, level)

    def ordinal(i: int) -> int:
        return max((k for k, (idx, _) in enumerate(sections) if idx < i), default=-1)

    items, head, i = [], None, 0

    def flush() -> None:
        nonlocal head
        if head is not None and is_py_url(head[1]):
            items.append((head[0], head[1], None, None, ordinal(head[0])))
        head = None

    while i < len(lines):
        line = lines[i]
        if FENCE_OPEN.match(line):
            j = i + 1
            while j < len(lines) and not FENCE_CLOSE.match(lines[j]):
                j += 1
            items.append((head[0] if head else None, head[1] if head else None, i + 1, j, ordinal(i)))
            head, i = None, j + 1                  # the block consumes the heading
            continue
        if line.lstrip().startswith("```"):        # any other code fence: skip it
            j = i + 1
            while j < len(lines) and not FENCE_CLOSE.match(lines[j]):
                j += 1
            i = j + 1
            continue
        if m := heading_match(line):
            flush()
            head = (i, m)
        elif PLAIN_HEADING.match(line):
            flush()
        i += 1
    flush()
    return items


def rel_path(base: Path, target: Path) -> str:
    try:
        return os.path.relpath(target, base).replace("\\", "/")
    except ValueError:  # e.g. different drive on Windows
        return target.as_posix()


def render_section(new: list[Entry], md_path: Path, root: Path, eol: str, dot_style: bool,
                   slim: bool = False) -> str:
    if not new:
        return ""
    out = [SECTION_TITLE + eol, eol]
    for e in new:
        name = e.sym[4]
        link = rel_path(md_path.parent, e.py)
        if not link.startswith("."):
            link = "./" + link
        link = f"{link}#{anchor_fragment(e.sym)}"
        summary = html.escape(readable(name), quote=False)
        title = html.escape(e.cid, quote=True)
        heading = (f'<details><Summary><a href="{html.escape(link, quote=True)}" '
                   f'title="{title}">{summary}</a></Summary>{eol}')
        if slim:
            out += [heading, eol, f"```yaml{eol}", f"tags: []{eol}", f"```{eol}", f"</details>{eol}", eol]
            continue
        file_value = rel_path(root, e.py)
        if dot_style and not file_value.startswith("."):
            file_value = "./" + file_value
        rows = [("component_id", yaml_scalar(e.cid)), ("type", component_type(e.sym)),
                ("file", yaml_item(file_value)), ("line_start", e.sym[0]),
                ("line_end", e.sym[1]), ("tags", "[]"),
                ("used_in", flow(e.used_in))]
        out += [heading, eol, f"```yaml{eol}"]
        out += [f"{k}: {v}{eol}" for k, v in rows]
        out += [f"```{eol}", eol]
    return "".join(out)


def get_list(block: list[str], key: str) -> list[str]:
    """Items of `key: [a, b]` (or block style) inside a yaml block; [] if absent."""
    for i, l in enumerate(block):
        m = KEY.match(l)
        if m and m["key"] == key:
            items, _ = read_list(block, i)
            return [x for x in (items or []) if x]
    return []


def mark_duplicates(entries: list[Entry], warnings: list) -> None:
    first: dict = {}
    for e in entries:
        if e.sym is None:
            continue
        key = (e.py, e.sym[4])
        if key in first:
            e.duplicate = True
            warnings.append(f"{e.name!r} ({e.cid or 'no component_id'}) is indexed twice - "
                            "the later block is left out of agent index and diagrams")
        else:
            first[key] = e


# ------------------------------------------------------------ agent index
def render_agent(entries: list[Entry], path: Path, eol: str) -> str:
    """Header + the yaml blocks of the given entries, nothing else."""
    as_md = path.suffix.lower() in (".md", ".markdown")
    header = None
    if path.is_file():
        old = path.read_bytes().decode("utf-8").splitlines()
        start = next((i for i, l in enumerate(old)
                      if (FENCE_OPEN.match(l) if as_md else l.strip() == "---")), None)
        header = old[:start] if start is not None else old
    if header is None or not any(l.strip() for l in header):
        header = [l if as_md else ("# " + l if l else "#") for l in AGENT_HEADER_LINES]
    while header and not header[-1].strip():
        header.pop()
    out = list(header)
    if as_md:
        out.append("")
    for e in entries:
        body = [l.rstrip() for l in strip_key(e.final_block, "dependencies")] + e.extra_lines
        if as_md:
            out += ["```yaml", *body, "```", ""]
        else:
            out += ["---", *body]
    if as_md and out and out[-1] == "":
        out.pop()
    return eol.join(out) + eol


# --------------------------------------------------------------- diagrams
def strip_key(block: list[str], key: str) -> list[str]:
    """The yaml lines without a top-level key (and its block-style list)."""
    out, i = [], 0
    while i < len(block):
        m = KEY.match(block[i])
        if m and m["key"] == key and not block[i][:1].isspace():
            i = read_list(block, i)[1]
            continue
        out.append(block[i])
        i += 1
    return out


def collect_relations(live: list[Entry], new: list[Entry], warnings: list) -> list[tuple]:
    """Sorted edges (provider, consumer, transitive) from the final used_in lists and used_in_transitive."""
    direct: set = set()
    known = {e.ref for e in [*live, *new]}
    for e in live:
        direct |= {(e.ref, u) for u in get_list(e.final_block, "used_in")}
    for e in new:
        direct |= {(e.ref, u) for u in e.used_in}
    for k in sorted({k for edge in direct for k in edge if k not in known}):
        warnings.append(f"reference to {k!r} in used_in, but no such component in the index")
    transitive: set = set()
    for e in [*live, *new]:
        transitive |= {(e.ref, u) for u in e.tused}
    transitive -= direct
    return ([(a, b, False) for a, b in sorted(direct)]
            + [(a, b, True) for a, b in sorted(transitive)])


def mermaid_id(key: str, ids: dict) -> str:
    if key not in ids:
        base = "n_" + re.sub(r"\W", "_", key)
        cand, n = base, 2
        while cand in ids.values():
            cand = f"{base}_{n}"
            n += 1
        ids[key] = cand
    return ids[key]


def mermaid_node(key: str, ids: dict, ext: bool = False, indent: str = "    ") -> str:
    label_text = key.replace('"', "#quot;")
    return f'{indent}{mermaid_id(key, ids)}["{label_text}"]' + (":::ext" if ext else "")


def render_section_diagram(members: list[str], edges: list[tuple], external: str, ids: dict,
                           section_title: str, section_index: int) -> str | None:
    inside = set(members)
    use = [(a, b, dotted) for a, b, dotted in edges
           if (a in inside or b in inside) and (external == "one-hop" or (a in inside and b in inside))]
    if not use:
        return None
    outside = sorted({k for a, b, _ in use for k in (a, b) if k not in inside})
    subgraph_id = f"sg_section_{section_index}" if section_index >= 0 else "sg_no_section"
    title_text = section_title.replace('"', "#quot;")
    lines = [MERMAID_HEADER, "", f'    subgraph {subgraph_id}["{title_text}"]']
    lines += [mermaid_node(k, ids, indent="        ") for k in members]
    lines += ["    end", f"    style {subgraph_id} color: #3b82f6, fill: #000000ff"]
    lines += [mermaid_node(k, ids, ext=True) for k in outside]
    lines += [f"    {mermaid_id(a, ids)} {'-.->' if dotted else '-->'} {mermaid_id(b, ids)}"
              for a, b, dotted in use]
    return "\n".join(lines)


def render_diagram_file(items: list[tuple[str, str | None]], eol: str) -> str:
    out = ["# Component diagrams", "",
           "Generated by `update_index.py` from the index - do not edit. "
           "Arrow `A --> B`: B uses A. Dashed boxes belong to another section.", ""]
    for title, diagram in items:
        out += [f"## {title}", ""]
        out += ["```mermaid", *diagram.split("\n"), "```", ""] if diagram else ["_No usages._", ""]
    return eol.join(out)


def apply_inline(text: str, diagrams: dict[int, str], level: int, eol: str) -> str:
    """Replace the marker regions of the index by fresh ones below the section headings."""
    kept: list[str] = []
    skipping = False
    for l in text.splitlines(keepends=True):
        if skipping:
            skipping = l.strip() != DIAGRAM_END
            continue
        if l.strip() == DIAGRAM_START:
            skipping = True
            if kept and not kept[-1].strip():       # the blank line we inserted
                kept.pop()
            continue
        kept.append(l)
    insert_after = {idx: diagrams[k] for k, (idx, _) in enumerate(scan_sections(kept, level))
                    if diagrams.get(k)}
    out: list[str] = []
    for i, l in enumerate(kept):
        out.append(l if (not l or l.endswith(("\n", "\r"))) else l + eol)
        if i in insert_after:
            out += [eol, DIAGRAM_START + eol, "```mermaid" + eol,
                    insert_after[i].replace("\n", eol) + eol, "```" + eol, DIAGRAM_END + eol]
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

    sec_titles = [t for _, t in scan_sections(lines, opts.section_level)]
    entries = []
    for hidx, hm, a, b, ordinal in parse_entries(lines, opts.section_level):
        if e := build_entry(lines, hidx, hm, a, b, md_path, root, cache, opts.ref_mode):
            e.section = ordinal
            entries.append(e)
    mark_duplicates(entries, warnings)
    legacy = [e.name for e in entries if e.form == "full" and "dependencies" in e.block_fields]
    if legacy:
        warnings.append(f"the key 'dependencies' is no longer maintained and not written to the agent index "
                        f"({len(legacy)} full block(s) still have it; --slim removes it)")

    for e in entries:                       # slim forms: tags block, notes; --slim: convert
        if e.note:
            warnings.append(f"{e.name!r}: {e.note}")
        if opts.slim and e.form != "anchor" and e.sym is not None:
            if e.form == "symbol":
                e.tags_lines = tags_lines(lines[e.a:e.b], eol) if e.a >= 0 else [f"tags: []{eol}"]
            convert_to_slim(e, lines, md_path, root, eol, warnings)
        elif e.form != "full":
            e.tags_lines = tags_lines(lines[e.a:e.b], eol) if e.a >= 0 else [f"tags: []{eol}"]
            for k in e.block_fields:
                if k != "tags":
                    warnings.append(f"{e.name!r}: key {k!r} in a slim block is ignored "
                                    "(only 'tags' is kept in the index)")
        if e.title_bad:
            warnings.append(f"{e.name!r}: the link title is not 'component_id | start-end' - it will be replaced")
    missing = [e for e in entries if e.form != "full" and e.sym is not None and not e.cid]
    assign_new_refs(missing, entries, opts.ref_mode)   # slim entry without id: propose one

    graph_on = "used_in" in opts.fields
    need_graph = graph_on or any(e.form != "full" and e.sym is not None for e in entries)
    new: list[Entry] = []
    if need_graph:                          # slim entries need the lists for the agent index
        pool = (discover_unindexed(entries, cache, root, opts, warnings)
                if opts.new_depth >= 1 else [])
        resolver = ImportResolver(root, md_path.parent, cache)
        new = build_graph(entries, pool, opts.new_depth, warnings,
                          opts.ref_mode, opts.reverse, resolver)

    edits, report = [], []                  # edits: (first line, end line, new lines)
    for e in entries:
        block, changes = lines[e.a:e.b], []
        if e.form != "full":
            if e.sym is not None:
                lines_now = (str(e.sym[0]), str(e.sym[1]))
                if e.migrated or (e.form == "anchor" and "lines" in opts.fields):
                    new_url = f"{e.path_part}#{anchor_fragment(e.sym)}"
                    if e.migrated:                 # text, target and title in the anchor form
                        new_line = render_link_heading(lines[e.head], e.head_match,
                                                       readable(e.sym[4]), new_url, e.cid)
                    else:                          # text stays, target and title are refreshed
                        new_line = set_link(lines[e.head], e.head_match, new_url, e.cid)
                    if e.form == "anchor" and e.title_id != e.cid:
                        changes.append(f"component_id {e.title_id or '-'} -> {e.cid}")
                    if e.old != lines_now:
                        was = f"{e.old[0]}-{e.old[1]}" if e.old[0] else "(none)"
                        changes.append(f"lines {was} -> {lines_now[0]}-{lines_now[1]}")
                    if e.migrated:
                        changes.append("converted to the anchor form")
                        if e.was_full:
                            edits.append((e.a, e.b, e.tags_lines))
                    elif new_line != lines[e.head] and not changes:
                        changes.append("link normalized")
                    if new_line != lines[e.head]:
                        edits.append((e.head, e.head + 1, [new_line]))
                elif e.form == "symbol" and "lines" in opts.fields:      # old slim form, kept as is
                    title = f"{e.cid} | {e.sym[0]}-{e.sym[1]}"
                    if e.title_bad or e.title_id != e.cid or e.old != lines_now:
                        if e.title_id != e.cid:
                            changes.append(f"component_id {e.title_id or '-'} -> {e.cid}")
                        if e.old != lines_now:
                            was = f"{e.old[0]}-{e.old[1]}" if e.old[0] else "(none)"
                            changes.append(f"lines {was} -> {lines_now[0]}-{lines_now[1]}")
                        edits.append((e.head, e.head + 1, [set_title(lines[e.head], e.head_match, title)]))
                e.final_block = slim_block(e, root)
        else:
            if e.sym is not None:
                if "lines" in opts.fields and e.old != (str(e.sym[0]), str(e.sym[1])):
                    changes.append(f"lines {e.old[0]}-{e.old[1]} -> {e.sym[0]}-{e.sym[1]}")
                    block = [set_value(l, m["key"], e.sym[0] if m["key"] == "line_start" else e.sym[1])
                             if (m := KEY.match(l)) and m["key"] in ("line_start", "line_end") else l
                             for l in block]
                for key, values in (("used_in", e.used_in),):
                    if key in opts.fields:
                        block, change = set_list(block, key, sorted(values))
                        if change:
                            changes.append(change)
            e.final_block = block
            e.extra_lines = transitive_lines(e, root) if e.sym is not None else []
            edits.append((e.a, e.b, block))
        report.append({"name": e.name, "changes": changes,
                       "status": e.status or ("updated" if changes else "ok")})
    out, pos = [], 0
    for first, last, new_lines in sorted(edits, key=lambda t: t[0]):
        out.extend(lines[pos:first])
        out.extend(new_lines)
        pos = last
    out.extend(lines[pos:])
    head_text = "".join(out)

    # diagrams: edges come from the lists as they are in the updated blocks
    live_final = [e for e in entries if e.sym is not None and not e.duplicate]
    diagram_text, inline_changed = None, False
    if opts.diagrams != "off":
        edges = collect_relations(live_final, new, warnings)
        groups: dict[int, list[str]] = {}
        for e in live_final:
            groups.setdefault(e.section, []).append(e.ref)
        ids: dict = {}
        per_section = {k: render_section_diagram(
                           list(dict.fromkeys(m)), edges, opts.diagram_external, ids,
                           sec_titles[k] if k >= 0 else "(no section)", k)
                       for k, m in groups.items()}
        if opts.diagrams == "file":
            diagram_text = render_diagram_file(
                [(sec_titles[k] if k >= 0 else "(no section)", d) for k, d in per_section.items()], eol)
        else:
            new_head = apply_inline(head_text, {k: d for k, d in per_section.items() if d},
                                    opts.section_level, eol)
            inline_changed, head_text = new_head != head_text, new_head
    agent_text = (render_agent(live_final, opts.agent_file, eol)
                  if opts.agent_file is not None else None)

    section_enabled = graph_on and opts.new_depth >= 1
    dot_style = any(e.file_value.startswith("./") for e in entries)
    slim_mode = opts.slim or any(e.form != "full" for e in entries)
    rendered = (render_section(new, md_path, root, eol, dot_style, slim_mode)
                if section_enabled else old_section)
    if not section_enabled or rendered.rstrip() == old_section.rstrip():
        text, section_changed = head_text + old_section, False      # keep byte-identical
    else:
        base = head_text.rstrip("\r\n \t")
        text = (base + eol if base else "") + ((eol + rendered) if rendered else "")
        section_changed = True
    return Result(text, report, warnings, new if section_enabled else [], section_changed,
                  agent_text, diagram_text, inline_changed)


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


def same_content(path: Path, text: str) -> bool:
    try:
        return path.read_bytes() == text.encode("utf-8")
    except OSError:
        return False


def write_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_bytes(text.encode("utf-8"))
    os.replace(tmp, path)


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
                 f"(backup copy: {next_backup_path(md).name}) and to regenerate "
                 f"agent_index.yaml and the diagrams y/n ")
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
                    help="comma list of: lines, used_in (default: all; 'dependencies' is an old alias of used_in)")
    ap.add_argument("--ref", choices=("id", "name"), default="id",
                    help="what to write into used_in (default: component_id)")
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
    ap.add_argument("--agent-file", default="agent_index.yaml", metavar="PATH",
                    help="agent-only index, relative to the index folder; 'none' = off "
                         "(default: agent_index.yaml; a .md name writes fenced yaml blocks)")
    ap.add_argument("--diagrams", choices=("file", "inline", "off"), default="inline",
                    help="Mermaid diagram per section: inside the index, own file, or off (default: inline)")
    ap.add_argument("--diagram-file", metavar="PATH",
                    help="diagram file, relative to the index folder (default: <index>_diagrams.md)")
    ap.add_argument("--section-level", type=int, default=3, metavar="N",
                    help="heading level that defines a section (default: 3 = '###')")
    ap.add_argument("--diagram-external", choices=("one-hop", "off"), default="one-hop",
                    help="show direct neighbours from other sections as dashed nodes (default: one-hop)")
    ap.add_argument("--slim", action="store_true",
                    help="convert full blocks and symbol links to the anchor form "
                         "([Readable name](path#L4-10 \"component_id\"), block keeps only tags); "
                         "one-time, a backup is made")
    ap.add_argument("--strict", action="store_true",
                    help="exit 5 if the agent index is incomplete (unindexed or unresolved entries)")
    args = ap.parse_args(argv)

    fields = {f.strip() for f in args.fields.split(",") if f.strip()}
    if "dependencies" in fields:                       # key removed from the schema: old alias
        fields = (fields - {"dependencies"}) | {"used_in"}
    if not fields or not fields <= ALL_FIELDS:
        ap.error(f"--fields must be a comma list of {sorted(ALL_FIELDS)}")
    if args.new_depth < 0:
        ap.error("--new-depth must be >= 0")
    if not 1 <= args.section_level <= 6:
        ap.error("--section-level must be between 1 and 6")

    md_path = args.index.resolve()
    root = (args.root or md_path.parent).resolve()

    def out_path(value: str) -> Path:
        p = Path(value)
        return (p if p.is_absolute() else md_path.parent / p).resolve()

    agent_file = None if args.agent_file.strip().lower() in ("", "none", "off") else out_path(args.agent_file)
    diagram_file = (out_path(args.diagram_file) if args.diagram_file
                    else md_path.with_name(f"{md_path.stem}_diagrams.md"))
    targets = [p for p in (agent_file, diagram_file if args.diagrams == "file" else None) if p]
    if md_path in targets or len(set(targets)) != len(targets):
        ap.error("index, agent file and diagram file must be three different files")

    opts = Options(fields=fields, ref_mode=args.ref, new_depth=args.new_depth, scan=args.scan,
                   ignore=set(args.ignore), exclude_dirs=set(args.exclude_dir),
                   reverse=args.reverse, include_tests=args.include_tests,
                   agent_file=agent_file, diagrams=args.diagrams, section_level=args.section_level,
                   diagram_external=args.diagram_external, slim=args.slim)
    res = sync(md_path, root, opts)
    generated = [(path, text) for path, text in
                 ((agent_file, res.agent_text), (diagram_file, res.diagram_text)) if text is not None]
    stale_gen = [(path, text) for path, text in generated if not same_content(path, text)]

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
    index_changed = n_upd > 0 or res.section_changed or res.inline_changed
    changed = index_changed or bool(stale_gen)
    print(f"\n{len(report)} entries: {n_upd} stale, {n_ok} ok, {n_bad} unresolved; "
          f"{len(res.new)} unindexed" + (" (section will change)" if res.section_changed else "")
          + (" (inline diagrams will change)" if res.inline_changed else ""))
    print(f"index file: {md_path}")
    for path, text in generated:
        state = "ok" if same_content(path, text) else ("new" if not path.exists() else "updated")
        print(f"{state:<14} {path.name} (generated)")

    written: list[str] = []
    if not changed:
        print("INDEX is up to date.") # Nothing to write: no stale entry found
    elif args.dry_run or args.check:
        print("NOT written (--dry-run / --check given).")
    else:
        if index_changed:
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
            written.append(md_path.name)
        for path, text in stale_gen:
            try:
                write_atomic(path, text)
            except OSError as exc:
                print(f"WRITE FAILED: {path.name}: {exc}")
                return 3
            written.append(path.name)
        again = sync(md_path, root, opts)  # verify by re-reading from disk
        left = (sum(r["status"] == "updated" for r in again.report) + int(again.section_changed)
                + int(again.inline_changed)
                + sum(not same_content(path, text) for path, text in
                      ((agent_file, again.agent_text), (diagram_file, again.diagram_text))
                      if text is not None))
        if left == 0:
            print(f"wrote {', '.join(written)} (verified by re-reading the files).")
        else:
            print(f"wrote, but {left} items are still stale on re-read: "
                  "another process or an editor may have overwritten a file.")
            return 3

    incomplete = agent_file is not None and (bool(res.new) or n_bad > 0)
    if incomplete:
        would = (args.dry_run or args.check) and res.section_changed
        print("\n*** THE AGENT INDEX IS INCOMPLETE ***")
        if res.new:
            print(f"  {len(res.new)} unindexed component(s) "
                  + ("would be listed" if would else "are listed")
                  + f" at the end of {md_path.name}.")
        if n_bad:
            print(f"  {n_bad} index entr{'y' if n_bad == 1 else 'ies'} could not be resolved "
                  f"and {'is' if n_bad == 1 else 'are'} left out of {agent_file.name}.")
        todo = ([f"move the unindexed blocks into their sections"] if res.new else []) \
            + (["fix the unresolved entries"] if n_bad else [])
        print(f"  -> Finalize {md_path.name} ({', '.join(todo)}) and run update_index.py again.")
    if args.check and changed:
        return 1
    if n_bad:
        return 2
    return 5 if (args.strict and incomplete) else 0


if __name__ == "__main__":
    sys.exit(main())