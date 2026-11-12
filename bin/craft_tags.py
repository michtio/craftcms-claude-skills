#!/usr/bin/env python3
"""Craft version tags for the skills pack: symbol map, linter, version table.

Tag grammar (docs/contributing.md, "Version tags"):
  core added          [5.10+]  [5.11.4+]
  core behaviour      [changed 5.12]  [deprecated 5.12]  [removed 5.12]
  third-party plugin  [seomatic 5.1+]  [ckeditor 4.9+]  [changed blitz 5.13]
  older alternative   "Before 5.10: ..." on the same item as the tag

Subcommands:
  map   --changelog FILE   write bin/data/craft-symbols.tsv (symbol -> first 5.x release
                           that "Added" it) and bin/data/craft-releases.txt
  lint  [PATHS...]         check tag grammar, untagged Craft version mentions, and
                           untagged post-5.0 symbols; exit 1 on findings
        --warn-only        report but exit 0
  table                    write skills/craftcms/references/version-table.md from the tags
  floor --changelog FILE   print the minimum safe version (the latest 5.x release with a
                           ### Security section) and its advisory IDs, tab-separated

Python 3.9+, standard library only. Maintainer and CI tooling: the detection
script that runs in users' projects is bin/craft-version.sh (POSIX sh).
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DATA = REPO / "bin" / "data"
SYMBOLS_TSV = DATA / "craft-symbols.tsv"
RELEASES_TXT = DATA / "craft-releases.txt"
ALLOW_TSV = DATA / "tag-lint-allow.tsv"
TABLE_MD = REPO / "skills" / "craftcms" / "references" / "version-table.md"

VERSION = r"\d+\.\d+(?:\.\d+){0,2}"
CORE_TAG = re.compile(rf"\[(?:(changed|deprecated|removed) )?(5\.\d+(?:\.\d+){{0,2}})(\+)?\]")
PLUGIN_TAG = re.compile(rf"\[(?:(?:changed|deprecated|removed) ([a-z][a-z0-9-]*) ({VERSION})|([a-z][a-z0-9-]*) ({VERSION})\+)\]")
# Anything bracketed that looks like an attempt at a tag, for grammar errors.
TAG_LIKE = re.compile(r"\[(?:changed |deprecated |removed )?(?:[A-Za-z][\w-]* )?v?\d+\.\d+[^\]\s]*\]")
BEFORE = re.compile(rf"\bBefore (5\.\d+(?:\.\d+)?):\s*(.+)")

# A bare Craft 5.x version in prose. Lookbehind keeps "PHP 5.6", "^5.6.0" and
# "v5.1" style numbers out; product names are filtered in is_craft_mention().
CRAFT_VERSION = re.compile(r"(?<![\w.^~>=<v/-])5\.\d{1,2}(?:\.\d+){0,2}(?![\w.]*\d)(?![A-Za-z])")
# Provenance, not a version gate: URLs and "craftcms/cms 5.x.y" source citations.
PROVENANCE = re.compile(r"https?://\S+|(?:craftcms/)?cms`?[ @:]v?5\.\d+\.\d+(?:\.\d+)?")
NON_CRAFT_PRODUCTS = re.compile(
    r"\b(mysql|mariadb|php|node(?:\.js)?|postgres(?:ql)?|twig|tailwind(?:css)?|vite|alpine(?:\.js)?|"
    r"pest|phpunit|laravel|symfony|yii2?|jquery|redis|bootstrap|typescript|imager[- ]?x|vue|"
    r"ckeditor|blitz|seomatic|formie|feed ?me|retour|sprig|hyper|navigation|element api|"
    r"image ?optimize|colour swatches|password policy|typogrify|cache igniter|knock knock|"
    r"elements panel|sherlock|amazon ses|embedded assets|timeloop|warp|htmx|datastar|"
    r"servd|fortrabbit|ddev|composer|npm|guzzle|monolog|graphql-php|webonyx|garnish|"
    r"font ?awesome|ubuntu|debian|python|ruby|go|rust|java|ios|android|macos|windows)\b"
    r"[^.\n]{0,25}$",
    re.I,
)


def vkey(v: str) -> tuple:
    return tuple(int(p) for p in v.split(".")) + (0,) * (4 - v.count(".") - 1)


# ----------------------------------------------------------------------------
# map
# ----------------------------------------------------------------------------

def looks_like_code(s: str) -> bool:
    if re.search(r"[\\:()|/$.{-]", s):
        return True
    if re.fullmatch(r"[A-Z][A-Z0-9_]{3,}", s):
        return True
    return bool(re.fullmatch(r"[a-z]+[A-Z]\w*", s))


def variants(sym: str) -> set[str]:
    sym = sym.strip().rstrip(".")
    out = {sym}
    if "\\" in sym:
        short = sym.rsplit("\\", 1)[1]
        if "::" in short or len(re.findall(r"[A-Z]", short)) >= 2:
            out.add(short)
        if "::" in short:
            member = short.split("::", 1)[1]
            if not member.startswith("$"):
                out.add(member)
    return {s for s in out if len(s) >= 6}


def build_map(changelog: str) -> tuple[dict[str, str], list[str]]:
    version = None
    added: dict[str, str] = {}
    releases: list[str] = []
    for line in changelog.splitlines():
        m = re.match(r"^## (5\.\d+\.\d+(?:\.\d+)?) ", line)
        if m:
            version = m.group(1)
            releases.append(version)
            continue
        if line.startswith("## "):
            version = None
            continue
        if not version or not line.startswith("- Added "):
            continue
        # In "Added `x` ... to `y`" only `x` is new.
        head = re.split(r"\b(?:to|for|on|in|of|when|if|which|that)\b", line, maxsplit=1)[0]
        for s in re.findall(r"`([^`]+)`", head):
            if " " in s or s in {"true", "false", "null"} or not looks_like_code(s):
                continue
            for v in variants(s):
                if v not in added or vkey(version) < vkey(added[v]):
                    added[v] = version
    post50 = {s: v for s, v in added.items() if vkey(v)[1] >= 1}
    return post50, sorted(set(releases), key=vkey)


def cmd_map(args) -> int:
    text = Path(args.changelog).read_text(encoding="utf-8")
    symbols, releases = build_map(text)
    DATA.mkdir(parents=True, exist_ok=True)
    with SYMBOLS_TSV.open("w", encoding="utf-8") as fh:
        fh.write("# symbol\tfirst 5.x release that added it. Generated by bin/craft_tags.py map; do not edit.\n")
        for s in sorted(symbols, key=lambda k: (vkey(symbols[k]), k)):
            fh.write(f"{s}\t{symbols[s]}\n")
    RELEASES_TXT.write_text(
        "# Craft 5.x releases. Generated by bin/craft_tags.py map; do not edit.\n" + "\n".join(releases) + "\n",
        encoding="utf-8",
    )
    print(f"{len(symbols)} post-5.0 symbols, {len(releases)} releases")
    return 0


# ----------------------------------------------------------------------------
# lint
# ----------------------------------------------------------------------------

def load_symbols() -> dict[str, str]:
    out = {}
    for line in SYMBOLS_TSV.read_text(encoding="utf-8").splitlines():
        if line and not line.startswith("#"):
            s, v = line.split("\t")
            out[s] = v
    return out


def load_releases() -> set[str]:
    rel = {l for l in RELEASES_TXT.read_text(encoding="utf-8").splitlines() if l and not l.startswith("#")}
    # A minor tag ([5.10+]) is valid when any 5.10.x release exists.
    rel |= {".".join(r.split(".")[:2]) for r in rel}
    return rel


def load_allow() -> tuple[set[str], list[tuple[str, re.Pattern]]]:
    """bin/data/tag-lint-allow.tsv:
         symbol<TAB><symbol><TAB><reason>          never flag this symbol
         line<TAB><path glob><TAB><regex><TAB><reason>   skip matching lines in matching files
    """
    symbols, lines = set(), []
    if not ALLOW_TSV.exists():
        return symbols, lines
    for raw in ALLOW_TSV.read_text(encoding="utf-8").splitlines():
        if not raw.strip() or raw.startswith("#"):
            continue
        parts = raw.split("\t")
        if parts[0] == "symbol" and len(parts) >= 3:
            symbols.add(parts[1])
        elif parts[0] == "line" and len(parts) >= 4:
            lines.append((parts[1], re.compile(parts[2])))
        else:
            raise SystemExit(f"{ALLOW_TSV}: bad row (need a reason column): {raw!r}")
    return symbols, lines


def core_tags(text: str) -> list[tuple[str, str]]:
    """(kind, version) for every core tag; kind is 'added' or changed/deprecated/removed."""
    return [((m.group(1) or "added"), m.group(2)) for m in CORE_TAG.finditer(text)]


def strip_code_spans(line: str) -> str:
    return re.sub(r"`[^`]*`", "", line)


def is_craft_mention(line: str, start: int) -> bool:
    before = line[max(0, start - 40):start]
    return not NON_CRAFT_PRODUCTS.search(before)


def lint_file(path: Path, symbols: dict[str, str], sym_re: list, releases: set[str],
              allow_syms: set[str], allow_lines: list) -> list[str]:
    rel = path.relative_to(REPO).as_posix()
    findings = []
    lines = path.read_text(encoding="utf-8").splitlines()
    in_code = False
    heading_stack: list[tuple[int, list]] = []  # (level, tags) of enclosing headings
    heading_tags: list[tuple[str, str]] = []   # tags of all enclosing headings
    item_tags: list[tuple[str, str]] = []      # tags on the current paragraph/list item
    prose_before_code: list[tuple[str, str]] = []
    last_block_tags: list[tuple[str, str]] = []  # tags of the last non-blank block
    in_frontmatter = lines[:1] == ["---"]

    allow_here = [rx for glob, rx in allow_lines if Path(rel).match(glob)]

    for i, line in enumerate(lines, 1):
        if in_frontmatter:
            if i > 1 and line == "---":
                in_frontmatter = False
            continue
        if line.lstrip().startswith("```"):
            in_code = not in_code
            if in_code:
                prose_before_code = item_tags[:] if item_tags else last_block_tags[:]
            continue
        if any(rx.search(line) for rx in allow_here):
            continue

        if not in_code:
            hm = re.match(r"(#{1,6}) ", line)
            if hm:
                level = len(hm.group(1))
                heading_stack = [h for h in heading_stack if h[0] < level] + [(level, core_tags(line))]
                heading_tags = [t for _, tags in heading_stack for t in tags]
                item_tags = []
                last_block_tags = []
            elif not line.strip():
                if item_tags:
                    last_block_tags = item_tags
                item_tags = []
            elif re.match(r"\s*([-*+]|\d+\.)\s|\|", line):
                item_tags = core_tags(line)          # a new list item or table row
            else:
                item_tags = item_tags + core_tags(line)  # paragraph continuation

            prose = strip_code_spans(PROVENANCE.sub("", line))
            # 1. grammar
            for m in TAG_LIKE.finditer(prose):
                t = m.group(0)
                if CORE_TAG.fullmatch(t) or PLUGIN_TAG.fullmatch(t):
                    cm = CORE_TAG.fullmatch(t)
                    if cm:
                        kind, ver, plus = cm.group(1), cm.group(2), cm.group(3)
                        if kind is None and not plus:
                            findings.append(f"{rel}:{i}: grammar: {t} needs '+' ([{ver}+]) or a kind ([changed {ver}])")
                        elif kind and plus:
                            findings.append(f"{rel}:{i}: grammar: {t} takes no '+' with '{kind}'")
                        if ver not in releases:
                            findings.append(f"{rel}:{i}: grammar: {t} names no Craft release")
                    continue
                findings.append(f"{rel}:{i}: grammar: {t} is not a valid tag")

            # 2. untagged Craft version mention
            line_tags = CORE_TAG.findall(prose) or PLUGIN_TAG.findall(prose)
            if not line_tags:
                for m in CRAFT_VERSION.finditer(prose):
                    if m.group(0) in ("5.0", "5.0.0"):
                        continue  # the whole pack is Craft 5.0+
                    if is_craft_mention(prose, m.start()):
                        findings.append(f"{rel}:{i}: untagged: Craft version '{m.group(0)}' without a tag on the line")
                        break

        # 3. untagged post-5.0 symbols (prose with backticks, and code lines)
        if not in_code and "`" not in line:
            continue
        covering = heading_tags + item_tags + (prose_before_code if in_code else [])
        best = max((vkey(v) for k, v in covering if k == "added"), default=None)
        hit = None
        for s, rx in sym_re:
            if s in allow_syms:
                continue
            if rx.search(line):
                if hit is None or len(s) > len(hit):
                    hit = s
        if hit:
            since = symbols[hit]
            if best is None:
                where = "code block" if in_code else "line"
                findings.append(f"{rel}:{i}: symbol: `{hit}` is new in {since} but its {where} has no [x.y+] tag "
                                f"(on the line, its list item, the paragraph before the code block, or the heading)")
            elif best < vkey(".".join(since.split(".")[:2])):
                tag = ".".join(str(p) for p in best[:2]) + "".join(f".{p}" for p in best[2:] if p)
                findings.append(f"{rel}:{i}: symbol: `{hit}` is new in {since} but the covering tag is [{tag}+]")
    return findings


def cmd_lint(args) -> int:
    symbols = load_symbols()
    releases = load_releases()
    allow_syms, allow_lines = load_allow()
    sym_re = [(s, re.compile(r"(?<![\w\\$])" + re.escape(s) + r"(?![\w])")) for s in symbols]

    targets: list[Path] = []
    for p in (args.paths or ["skills"]):
        p = (REPO / p) if not Path(p).is_absolute() else Path(p)
        targets += [p] if p.is_file() else sorted(p.rglob("*.md"))
    targets = [t for t in targets if t.resolve() != TABLE_MD.resolve()]

    findings = []
    for t in targets:
        findings += lint_file(t.resolve(), symbols, sym_re, releases, allow_syms, allow_lines)
    for f in findings:
        print(f)
    kinds = {}
    for f in findings:
        k = f.split(": ")[1]
        kinds[k] = kinds.get(k, 0) + 1
    print(f"{len(findings)} finding(s) in {len(targets)} file(s)" + (f": {kinds}" if kinds else ""))
    if findings and not args.warn_only:
        return 1
    return 0


# ----------------------------------------------------------------------------
# table
# ----------------------------------------------------------------------------

def cmd_table(args) -> int:
    rows = []
    for md in sorted((REPO / "skills").rglob("*.md")):
        if md.resolve() == TABLE_MD.resolve():
            continue
        rel = md.relative_to(REPO / "skills").as_posix()
        lines = md.read_text(encoding="utf-8").splitlines()
        heading = ""
        in_code = False
        for i, line in enumerate(lines):
            if line.lstrip().startswith("```"):
                in_code = not in_code
                continue
            if in_code:
                continue
            if re.match(r"#{1,6} ", line):
                heading = re.sub(r"^#+\s*", "", line)
            spans = [(m.start(), m.end(), m.group(1)) for m in re.finditer(r"`([^`]+)`", line)]
            for tm in CORE_TAG.finditer(line):
                if any(a <= tm.start() < b for a, b, _ in spans):
                    continue  # a tag quoted inside a code span is an example, not a tag
                kind, ver = (tm.group(1) or "added"), tm.group(2)
                before = [c for a, b, c in spans if b <= tm.start()]
                after = [c for a, b, c in spans if a >= tm.end()]
                if re.match(r"#{1,6} ", line):
                    feature = re.sub(CORE_TAG, "", heading).strip()
                elif before and len(before[-1]) <= 80:
                    feature = f"`{before[-1]}`"
                elif after and len(after[0]) <= 80:
                    feature = f"`{after[0]}`"
                else:
                    feature = re.sub(CORE_TAG, "", heading).strip() or "(see file)"
                alt = ""
                for nxt in [line] + lines[i + 1:i + 3]:
                    bm = BEFORE.search(nxt)
                    if bm:
                        alt = bm.group(2).strip()
                        break
                label = ver + "+" if kind == "added" else f"{kind} {ver}"
                rows.append((vkey(ver), label, feature.replace("|", "\\|"), alt.replace("|", "\\|"), rel))
    seen, out = set(), []
    for r in sorted(rows, key=lambda r: (r[0], r[1], r[2])):
        key = (r[1], r[2], r[4])
        if key not in seen:
            seen.add(key)
            out.append(r)
    with TABLE_MD.open("w", encoding="utf-8") as fh:
        fh.write("# Craft 5 Version Table\n\n")
        fh.write("Generated by `bin/craft_tags.py table` from the version tags in this pack; do not edit by hand. "
                 "One row per tagged feature: the Craft version it needs (or the version that changed it), "
                 "the older-version alternative where the pack gives one, and the file that covers it.\n\n")
        fh.write("Use it to answer \"what can this project use?\" against the version reported under "
                 "\"Craft Version of This Project\" in any skill.\n\n")
        fh.write("| Version | Feature | Before that version | Covered in |\n|---|---|---|---|\n")
        for _, label, feature, alt, rel in out:
            fh.write(f"| `{label}` | {feature} | {alt} | `{rel}` |\n")
    print(f"{len(out)} rows -> {TABLE_MD.relative_to(REPO)}")
    return 0


def cmd_floor(args) -> int:
    version, in_security, best = None, False, None
    advisories: dict[str, list[str]] = {}
    for line in Path(args.changelog).read_text(encoding="utf-8").splitlines():
        m = re.match(r"^## (5\.\d+\.\d+(?:\.\d+)?) ", line)
        if m:
            version, in_security = m.group(1), False
            continue
        if line.startswith("## "):
            version, in_security = None, False
            continue
        if line.startswith("### "):
            in_security = version is not None and line.strip() == "### Security"
            continue
        if in_security and line.startswith("- "):
            advisories.setdefault(version, []).extend(re.findall(r"GHSA(?:-[0-9a-z]{4}){3}", line))
            if best is None or vkey(version) > vkey(best):
                best = version
    if best is None:
        print("no ### Security section found", file=sys.stderr)
        return 1
    print(f"{best}\t{', '.join(dict.fromkeys(advisories.get(best, []))) or 'see CHANGELOG'}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("map")
    m.add_argument("--changelog", required=True)
    m.set_defaults(fn=cmd_map)
    l = sub.add_parser("lint")
    l.add_argument("paths", nargs="*")
    l.add_argument("--warn-only", action="store_true")
    l.set_defaults(fn=cmd_lint)
    t = sub.add_parser("table")
    t.set_defaults(fn=cmd_table)
    fl = sub.add_parser("floor")
    fl.add_argument("--changelog", required=True)
    fl.set_defaults(fn=cmd_floor)
    args = ap.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
