#!/usr/bin/env python3
"""Check the Craft PHP symbols the skills pack names against the craftcms/cms source.

Subcommands:
  index SRC_DIR            write bin/data/craft-source-index.tsv from a craftcms/cms
                           checkout or extracted tarball (its src/ directory is read)
  verify [PATHS...]        check every Craft symbol named in the pack (default: skills/)
                           against the index; exit 1 on a symbol that does not exist

What `verify` checks (inline code spans and fenced PHP/shell blocks):
  - fully qualified craft\\... classes, and craft\\...::member
  - Short::member where Short is a Craft class (imported in the block or a unique
    Craft short name), resolved through parents, interfaces and traits
  - Craft::$app->getX()->method() service chains
  - bare EVENT_* constants
  - console commands: craft <controller>/<action>
A symbol whose class chain leaves Craft (yii\\, Twig, PHP) and is not found in the
Craft part is not reported: only provably missing symbols fail. Plugin namespaces
(craft\\commerce, craft\\ckeditor, ...) are skipped. Deliberate mentions of symbols
that don't exist go in bin/data/symbol-allow.tsv with a reason.

Python 3.9+, standard library only.
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DATA = REPO / "bin" / "data"
INDEX_TSV = DATA / "craft-source-index.tsv"
TAG_TXT = DATA / "craft-source-tag.txt"
ALLOW_TSV = DATA / "symbol-allow.tsv"

IDENT = r"[A-Za-z_][A-Za-z0-9_]*"
QNAME = rf"\\?{IDENT}(?:\\{IDENT})*"

# Members every PHP/Yii object has; never reported.
UNIVERSAL_MEMBERS = {"class", "__construct", "__toString", "__get", "__set", "__call", "__callStatic", "__invoke"}
# Event constants Yii defines on classes Craft extends (yii\\base, web, db, mail, queue).
YII_EVENTS = {
    "EVENT_INIT", "EVENT_BEFORE_REQUEST", "EVENT_AFTER_REQUEST", "EVENT_BEFORE_ACTION", "EVENT_AFTER_ACTION",
    "EVENT_BEFORE_VALIDATE", "EVENT_AFTER_VALIDATE", "EVENT_BEFORE_INSERT", "EVENT_AFTER_INSERT",
    "EVENT_BEFORE_UPDATE", "EVENT_AFTER_UPDATE", "EVENT_BEFORE_DELETE", "EVENT_AFTER_DELETE", "EVENT_AFTER_FIND",
    "EVENT_AFTER_REFRESH", "EVENT_INIT", "EVENT_BEFORE_SEND", "EVENT_AFTER_SEND", "EVENT_AFTER_PREPARE",
    "EVENT_BEFORE_RENDER", "EVENT_AFTER_RENDER", "EVENT_BEGIN_PAGE", "EVENT_END_PAGE", "EVENT_BEGIN_BODY",
    "EVENT_END_BODY", "EVENT_BEFORE_LOGIN", "EVENT_AFTER_LOGIN", "EVENT_BEFORE_LOGOUT", "EVENT_AFTER_LOGOUT",
    "EVENT_BEFORE_PUSH", "EVENT_AFTER_PUSH", "EVENT_BEFORE_EXEC", "EVENT_AFTER_EXEC", "EVENT_AFTER_ERROR",
    "EVENT_WORKER_START", "EVENT_WORKER_STOP", "EVENT_BEFORE_RUN", "EVENT_AFTER_RUN", "EVENT_AFTER_OPEN",
    "EVENT_BEGIN_TRANSACTION", "EVENT_COMMIT_TRANSACTION", "EVENT_ROLLBACK_TRANSACTION", "EVENT_FLUSH",
}
# Yii console controller options and the help pseudo-command.
YII_CONSOLE_OPTIONS = {"interactive", "color", "help", "silent-exit-on-exception", "verbose", "quiet"}


# ----------------------------------------------------------------------------
# index
# ----------------------------------------------------------------------------

def strip_php_comments(src: str) -> str:
    src = re.sub(r"/\*.*?\*/", lambda m: "\n" * m.group(0).count("\n"), src, flags=re.S)
    return re.sub(r"(?m)(?<![:\"'])//[^\n]*|^\s*#[^\n\[]*", "", src)


def resolve(name: str, ns: str, uses: dict[str, str]) -> str:
    name = name.strip()
    if name.startswith("\\"):
        return name[1:]
    head, _, rest = name.partition("\\")
    if head in uses:
        return uses[head] + ("\\" + rest if rest else "")
    return f"{ns}\\{name}" if ns else name


def parse_php(path: Path) -> list[tuple]:
    """Return index rows for one PHP file."""
    raw = path.read_text(encoding="utf-8", errors="replace")
    src = strip_php_comments(raw)
    m = re.search(rf"^\s*namespace\s+({QNAME})\s*;", src, re.M)
    ns = m.group(1) if m else ""
    uses: dict[str, str] = {}
    for um in re.finditer(rf"^use\s+(?:function\s+|const\s+)?({QNAME})(?:\s+as\s+({IDENT}))?\s*;", src, re.M):
        full = um.group(1).lstrip("\\")
        uses[um.group(2) or full.rsplit("\\", 1)[-1]] = full

    decl = re.search(
        rf"^\s*(?:(?:abstract|final|readonly)\s+)*(class|interface|trait|enum)\s+({IDENT})"
        rf"(?:\s*:\s*{IDENT})?([^{{]*)\{{",
        src, re.M,
    )
    if not decl:
        return []
    kind, short, header = decl.group(1), decl.group(2), decl.group(3)
    fqcn = f"{ns}\\{short}" if ns else short
    parents: list[str] = []
    em = re.search(rf"\bextends\s+((?:{QNAME}\s*,?\s*)+?)(?=\bimplements\b|$)", header)
    if em:
        parents += [resolve(p, ns, uses) for p in re.split(r"\s*,\s*", em.group(1).strip()) if p]
    im = re.search(rf"\bimplements\s+((?:{QNAME}\s*,?\s*)+)", header)
    if im:
        parents += [resolve(p, ns, uses) for p in re.split(r"\s*,\s*", im.group(1).strip()) if p]

    body = src[decl.end():]
    for tm in re.finditer(rf"^\s*use\s+((?:{QNAME}\s*,\s*)*{QNAME})\s*[;{{]", body, re.M):
        parents += [resolve(t, ns, uses) for t in re.split(r"\s*,\s*", tm.group(1))]

    rows = [("class", fqcn, kind, ",".join(parents))]
    for fm in re.finditer(
        rf"^\s*((?:(?:public|protected|private|static|abstract|final)\s+)*)function\s+&?({IDENT})\s*\(",
        body, re.M,
    ):
        name = fm.group(2)
        # Return type: the text after the matching ")" up to "{" or ";".
        depth, i = 1, fm.end()
        while i < len(body) and depth:
            depth += {"(": 1, ")": -1}.get(body[i], 0)
            i += 1
        rt = re.match(rf"\s*:\s*\??({QNAME})", body[i:i + 200])
        ret = resolve(rt.group(1), ns, uses) if rt and rt.group(1)[0].isupper() or (rt and "\\" in rt.group(1)) else ""
        if ret in {"self", "static"} or ret.endswith("\\static") or ret.endswith("\\self"):
            ret = fqcn
        rows.append(("method", fqcn, name, ret))
    for cm in re.finditer(rf"^\s*(?:(?:public|protected|final)\s+)*const\s+(?:{IDENT}\s+)?({IDENT})\s*=", body, re.M):
        rows.append(("const", fqcn, cm.group(1), ""))
    for cm in re.finditer(rf"^\s*case\s+({IDENT})\s*[=;]", body, re.M):
        if kind == "enum":
            rows.append(("const", fqcn, cm.group(1), ""))
    for pm in re.finditer(
        rf"^\s*(?:public|protected)(?:\s+(?:static|readonly))*(?:\s+\??{QNAME}(?:\|{QNAME})*)?\s+\$({IDENT})",
        body, re.M,
    ):
        rows.append(("prop", fqcn, pm.group(1), ""))
    # @property / @property-read / @method docblock members (Craft uses them on ApplicationTrait etc.)
    for dm in re.finditer(rf"@property(?:-read|-write)?\s+(\S+)\s+\$({IDENT})", raw):
        typ = dm.group(1).lstrip("?").split("|")[0]
        rows.append(("prop", fqcn, dm.group(2), resolve(typ, ns, uses) if typ[:1].isupper() or "\\" in typ else ""))
    for dm in re.finditer(rf"@method\s+(?:static\s+)?(\S+)\s+({IDENT})\s*\(", raw):
        typ = dm.group(1).lstrip("?").split("|")[0]
        rows.append(("method", fqcn, dm.group(2), resolve(typ, ns, uses) if typ[:1].isupper() or "\\" in typ else ""))
    return rows


def kebab(name: str) -> str:
    return re.sub(r"(?<=[a-z0-9])([A-Z])", r"-\1", name).lower()


def console_rows(src_dir: Path, rows: list[tuple]) -> list[tuple]:
    """Console commands, with actions resolved through the controller's class chain.

    A controller is "dynamic" (any action accepted) when its chain leaves Craft
    (yii's BaseMigrateController), when a class in the chain other than the base
    craft\\console\\Controller overrides defineActions() (clear-caches,
    invalidate-tags, users), or for resave, which plugins extend through
    EVENT_DEFINE_ACTIONS.
    """
    parents = {r[1]: [p for p in r[3].split(",") if p] for r in rows if r[0] == "class"}
    methods: dict[str, list[str]] = defaultdict(list)
    for r in rows:
        if r[0] == "method":
            methods[r[1]].append(r[2])
    base = "craft\\console\\Controller"
    out = []
    ns = "craft\\console\\controllers\\"
    mapped = {"migrate": ns + "MigrateController"}
    controllers = {kebab(php.stem[: -len("Controller")]): ns + php.stem
                   for php in (src_dir / "console" / "controllers").glob("*Controller.php")}
    controllers.update(mapped)
    for cid, fq in sorted(controllers.items()):
        chain, todo, closed = [], [fq], True
        while todo:
            c = todo.pop()
            if c in chain or c == base:
                continue
            if c not in parents:
                if not c.startswith("craft\\") or "Controller" in c:
                    closed = closed and not c.endswith("Controller")
                continue
            chain.append(c)
            todo += parents[c]
        dynamic = not closed or cid == "resave"
        for c in chain:
            if "defineActions" not in methods[c]:
                continue
            path = src_dir / Path(*c.split("\\")[1:]).with_suffix(".php")
            text = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
            body = text[text.find("function defineActions"):]
            body = body[: body.find("\n    }\n") + 1]
            literal = re.findall(r"'([a-z0-9-]+)'\s*=>\s*\[", body)
            if literal and "foreach" not in body:
                out += [("command", f"{cid}/{a}", "", "") for a in literal]
            else:
                dynamic = True
        out.append(("command", cid, "", "dynamic" if dynamic else ""))
        for c in chain:
            for m in methods[c]:
                if m.startswith("action") and len(m) > 6 and m[6].isupper():
                    out.append(("command", f"{cid}/{kebab(m[6:])}", "", ""))
    return out


def cmd_index(args) -> int:
    src_dir = Path(args.src).resolve()
    if (src_dir / "src").is_dir():
        src_dir = src_dir / "src"
    rows: list[tuple] = []
    files = sorted(src_dir.rglob("*.php"))
    for php in files:
        if "/templates/" in php.as_posix() or "/translations/" in php.as_posix():
            continue
        rows += parse_php(php)
    rows += console_rows(src_dir, rows)
    # Libraries Craft classes extend (yii2, yii2-queue): indexed so a member that is
    # missing from the whole chain is provably missing, not "left Craft".
    for lib in args.lib or []:
        lib_dir = Path(lib).resolve()
        for php in sorted(lib_dir.rglob("*.php")):
            if re.search(r"/(tests?|views|messages|requirements|migrations|gii|debug)/", php.as_posix()):
                continue
            files.append(php)
            rows += parse_php(php)
    rows = sorted(set(rows))
    tag = args.tag or (TAG_TXT.read_text().strip() if TAG_TXT.exists() else "unknown")
    with INDEX_TSV.open("w") as f:
        libs = f" + {args.lib_versions}" if args.lib_versions else ""
        f.write(f"# craftcms/cms {tag} src/{libs}. Generated by bin/craft_source.py index; do not edit.\n")
        for r in rows:
            f.write("\t".join(r) + "\n")
    TAG_TXT.write_text(tag + "\n")
    print(f"indexed {len(files)} files: {len(rows)} rows -> {INDEX_TSV.relative_to(REPO)} ({tag})")
    return 0


# ----------------------------------------------------------------------------
# verify
# ----------------------------------------------------------------------------

class Index:
    def __init__(self, path: Path = INDEX_TSV):
        self.classes: dict[str, tuple[str, list[str]]] = {}
        self.members: dict[str, dict[str, str]] = defaultdict(dict)  # fqcn -> name -> return type
        self.consts: dict[str, set[str]] = defaultdict(set)
        self.props: dict[str, dict[str, str]] = defaultdict(dict)
        self.commands: dict[str, str] = {}
        self.all_consts: set[str] = set()
        for line in path.read_text().splitlines():
            if line.startswith("#") or not line:
                continue
            kind, a, b, c = (line.split("\t") + ["", "", ""])[:4]
            if kind == "class":
                self.classes[a] = (b, [p for p in c.split(",") if p])
            elif kind == "method":
                self.members[a][b.lower()] = c
            elif kind == "const":
                self.consts[a].add(b)
                self.all_consts.add(b)
            elif kind == "prop":
                self.props[a][b] = c
            elif kind == "command":
                self.commands[a] = c
        self.by_short: dict[str, list[str]] = defaultdict(list)
        for fq in self.classes:
            self.by_short[fq.rsplit("\\", 1)[-1]].append(fq)
        self.top_ns = {fq.split("\\")[1] for fq in self.classes if fq.startswith("craft\\") and fq.count("\\") >= 2}

    def is_core_ns(self, fq: str) -> bool:
        """craft\\<top>\\... where <top> is a namespace cms itself ships (not a plugin)."""
        parts = fq.split("\\")
        if parts[0] != "craft":
            return parts[0] == "Craft" and len(parts) == 1
        return len(parts) == 2 or parts[1] in self.top_ns

    def chain(self, fq: str) -> tuple[list[str], bool]:
        """All ancestor classes in Craft, and whether the chain is closed (never leaves Craft)."""
        seen, todo, closed = [], [fq], True
        while todo:
            c = todo.pop()
            if c in seen:
                continue
            if c not in self.classes:
                closed = False
                continue
            seen.append(c)
            todo += self.classes[c][1]
        return seen, closed

    def has_member(self, fq: str, member: str) -> bool | None:
        """True / False (provably missing) / None (unknown: chain leaves Craft)."""
        if member in UNIVERSAL_MEMBERS:
            return True
        classes, closed = self.chain(fq)
        for c in classes:
            if member.startswith("$"):
                if member[1:] in self.props[c]:
                    return True
            elif member.lower() in self.members[c] or member in self.consts[c]:
                return True
            elif member in self.props[c]:
                return True
        return False if closed else None

    def method_return(self, fq: str, method: str) -> str:
        for c in self.chain(fq)[0]:
            if method.lower() in self.members[c]:
                return self.members[c][method.lower()]
            if method in self.props[c]:
                return self.props[c][method]
        return ""


def load_allow() -> tuple[set[str], set[str]]:
    syms, lines = set(), set()
    if ALLOW_TSV.exists():
        for line in ALLOW_TSV.read_text().splitlines():
            if not line.strip() or line.startswith("#"):
                continue
            key = line.split("\t")[0].strip()
            (lines if re.search(r"\.md:\d+$", key) else syms).add(key)
    return syms, lines


FENCE = re.compile(r"^(\s*)(`{3,}|~{3,})\s*([\w+-]*)")
SPAN = re.compile(r"`([^`\n]+)`")
FQ_MEMBER = re.compile(rf"(?<![\w\\$])(\\?craft\\{IDENT}(?:\\{IDENT})*)(?![\w*])(?:::(\$?{IDENT}))?")
SHORT_MEMBER = re.compile(rf"(?<![\w\\$>])([A-Z]{IDENT})::(\$?{IDENT})")
APP_CHAIN = re.compile(rf"Craft::\$app->(get{IDENT})\(\)(?:->({IDENT})\()?")
EVENT = re.compile(r"(?<![\w:$>])(EVENT_[A-Z0-9_]+)\b")
COMMAND = re.compile(r"(?:^|[\s`(])(?:ddev\s+|php\s+|\./)?craft\s+([a-z][a-z0-9-]*(?:/[a-z][a-z0-9-]*)?)(?![\w/.-])")
USE_STMT = re.compile(rf"^\s*use\s+(\\?craft\\{IDENT}(?:\\{IDENT})*)(?:\s+as\s+({IDENT}))?\s*;", re.M)


def iter_chunks(text: str):
    """Yield (line_no, text, is_code_block, lang) for inline lines and fenced blocks."""
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        m = FENCE.match(lines[i])
        if m:
            fence, lang, start = m.group(2), m.group(3).lower(), i
            i += 1
            block = []
            while i < len(lines) and not lines[i].strip().startswith(fence[:3]):
                block.append(lines[i])
                i += 1
            yield start + 2, "\n".join(block), True, lang
            i += 1
            continue
        yield i + 1, lines[i], False, ""
        i += 1


def check_text(rel: str, text: str, idx: Index, allow_syms: set[str], allow_lines: set[str]) -> list[str]:
    findings: list[str] = []

    def report(line_no: int, sym: str, why: str):
        if sym in allow_syms or f"{rel}:{line_no}" in allow_lines:
            return
        findings.append(f"{rel}:{line_no}: {sym}: {why}")

    for start, chunk, is_block, lang in iter_chunks(text):
        if is_block and lang not in {"php", "bash", "sh", "shell", "console", "", "text", "yaml"}:
            continue
        if is_block:
            pieces = [(start + k, ln) for k, ln in enumerate(chunk.splitlines())]
            imports = {(m.group(2) or m.group(1).rsplit("\\", 1)[-1]): m.group(1).lstrip("\\") for m in USE_STMT.finditer(chunk)}
            php = lang == "php"
        else:
            pieces = [(start, s) for s in SPAN.findall(chunk)]
            imports = {}
            php = True
        for line_no, s in pieces:
            if "[removed " in (chunk if not is_block else s):
                continue
            if php:
                findings_for_piece(line_no, s, idx, imports, report)
            for cm in COMMAND.finditer(s if not is_block or lang != "php" else ""):
                check_command(line_no, cm.group(1), idx, report)
    return findings


def findings_for_piece(line_no, s, idx: Index, imports, report):
    for m in FQ_MEMBER.finditer(s):
        fq, member = m.group(1).lstrip("\\"), m.group(2)
        if not idx.is_core_ns(fq):
            continue
        if fq not in idx.classes:
            # Maybe a namespace mention (craft\elements) rather than a class.
            if any(c.startswith(fq + "\\") for c in idx.classes):
                continue
            report(line_no, fq, "no such class in craftcms/cms")
            continue
        if member and idx.has_member(fq, member) is False:
            report(line_no, f"{fq}::{member}", "no such member")
    for m in SHORT_MEMBER.finditer(s):
        short, member = m.group(1), m.group(2)
        if short in {"Craft"} and member == "$app":
            continue
        if short in imports:
            cands = [imports[short]] if idx.is_core_ns(imports[short]) else []
            if cands and cands[0] not in idx.classes:
                report(line_no, cands[0], "no such class in craftcms/cms")
                continue
        else:
            cands = idx.by_short.get(short, [])
        if not cands or (short in {"Craft"} and member.startswith("$")):
            continue
        if member.endswith("_"):
            continue
        results = [idx.has_member(c, member) for c in cands]
        if all(r is False for r in results):
            report(line_no, f"{short}::{member}", f"no such member on {', '.join(cands[:3])}")
    for m in APP_CHAIN.finditer(s):
        getter, method = m.group(1), m.group(2)
        ret = idx.method_return("craft\\web\\Application", getter) or idx.method_return("craft\\console\\Application", getter)
        if idx.has_member("craft\\web\\Application", getter) is False and idx.has_member("craft\\console\\Application", getter) is False:
            report(line_no, f"Craft::$app->{getter}()", "no such service getter")
            continue
        # Declared return types can be a parent of the runtime class (getQueue() is
        # typed yii\\queue\\Queue, the instance is craft\\queue\\Queue): judge Craft types only.
        if method and ret.startswith("craft\\") and ret in idx.classes and idx.has_member(ret, method) is False:
            report(line_no, f"Craft::$app->{getter}()->{method}()", f"no such method on {ret}")
    for m in EVENT.finditer(s):
        name = m.group(1)
        if name.endswith("_") or name in YII_EVENTS:
            continue
        if name not in idx.all_consts:
            report(line_no, name, "no Craft class defines this event constant")


def check_command(line_no, cmd, idx: Index, report):
    cid, _, action = cmd.partition("/")
    if cid not in idx.commands:
        # Plugin commands (craft blitz/cache/refresh) and app aliases can't be checked.
        return
    if not action or idx.commands[cid] == "dynamic":
        return
    if f"{cid}/{action}" not in idx.commands:
        report(line_no, f"craft {cmd}", "no such console action")


def cmd_verify(args) -> int:
    if not INDEX_TSV.exists():
        print("no index: run bin/craft_source.py index <cms-src>", file=sys.stderr)
        return 2
    idx = Index()
    allow_syms, allow_lines = load_allow()
    targets: list[Path] = []
    for p in (args.paths or ["skills"]):
        p = Path(p) if Path(p).is_absolute() else REPO / p
        targets += [p] if p.is_file() else sorted(p.rglob("*.md"))
    # Generated from the other files' tags (bin/craft_tags.py table): checked at its source.
    table = REPO / "skills" / "craftcms" / "references" / "version-table.md"
    targets = [t for t in targets if t.resolve() != table.resolve()]
    findings = []
    for t in targets:
        try:
            rel = str(t.resolve().relative_to(REPO))
        except ValueError:
            rel = str(t)
        findings += check_text(rel, t.read_text(encoding="utf-8"), idx, allow_syms, allow_lines)
    for f in findings:
        print(f)
    tag = TAG_TXT.read_text().strip() if TAG_TXT.exists() else "?"
    print(f"{len(findings)} unknown symbol(s) in {len(targets)} file(s) (craftcms/cms {tag})")
    return 1 if findings else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    i = sub.add_parser("index")
    i.add_argument("src")
    i.add_argument("--tag", help="the craftcms/cms tag the source is from")
    i.add_argument("--lib", action="append", help="extra source dir to index (yii2 framework, yii2-queue src)")
    i.add_argument("--lib-versions", default="", help="recorded in the index header, e.g. 'yii2 2.0.55, yii2-queue 2.3.8'")
    v = sub.add_parser("verify")
    v.add_argument("paths", nargs="*")
    args = ap.parse_args()
    return {"index": cmd_index, "verify": cmd_verify}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
