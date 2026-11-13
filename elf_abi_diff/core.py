import re
from dataclasses import asdict, dataclass
from pathlib import Path


class InputError(ValueError):
    """Raised when a readelf symbol table is malformed or empty."""


@dataclass(frozen=True)
class Symbol:
    name: str
    value: str
    size: int
    symbol_type: str
    bind: str
    visibility: str
    section: str


_ROW = re.compile(
    r"^\s*(?:\d+):\s+([0-9A-Fa-f]+)\s+(\d+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(.+?)\s*$"
)
_UNDEFINED = {"UND", "UNDEF"}


def parse_symbols(text):
    """Parse the stable symbol-table columns emitted by ``readelf -Ws``.

    Addresses are deliberately ignored during comparison: link layout changes
    move symbols without changing the source-level ABI.  The input is text so
    the tool can run on CI hosts without requiring a target architecture.
    """
    if not isinstance(text, str):
        raise InputError("symbol table must be text")
    symbols = {}
    rows = 0
    for line_number, line in enumerate(text.splitlines(), 1):
        match = _ROW.match(line)
        if not match:
            continue
        rows += 1
        value, size, symbol_type, bind, visibility, section, name = match.groups()
        name = name.strip()
        if not name:
            raise InputError(f"line {line_number}: symbol name is empty")
        if section in _UNDEFINED:
            continue
        if bind not in {"GLOBAL", "WEAK"}:
            continue
        if visibility not in {"DEFAULT", "PROTECTED", "INTERNAL", "HIDDEN"}:
            raise InputError(f"line {line_number}: unsupported visibility {visibility}")
        if name in symbols:
            raise InputError(f"duplicate exported symbol: {name}")
        symbols[name] = Symbol(name, value.lower(), int(size), symbol_type, bind, visibility, section)
    if rows == 0:
        raise InputError("no readelf symbol rows found")
    return symbols


def load_symbols(path):
    try:
        return parse_symbols(Path(path).read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError) as exc:
        raise InputError(str(exc)) from exc


def compare(before, after, fail_on="breaking"):
    if fail_on not in {"breaking", "any-change", "none"}:
        raise ValueError("fail_on must be breaking, any-change or none")
    removed = [asdict(before[name]) for name in sorted(set(before) - set(after))]
    added = [asdict(after[name]) for name in sorted(set(after) - set(before))]
    changed = []
    for name in sorted(set(before) & set(after)):
        left, right = before[name], after[name]
        differences = {
            field: {"before": getattr(left, field), "after": getattr(right, field)}
            for field in ("size", "symbol_type", "bind", "visibility", "section")
            if getattr(left, field) != getattr(right, field)
        }
        if differences:
            changed.append({"name": name, "differences": differences, "before": asdict(left), "after": asdict(right)})
    breaking = bool(removed or changed)
    any_change = bool(removed or added or changed)
    failed = breaking if fail_on == "breaking" else any_change if fail_on == "any-change" else False
    return {
        "ok": not failed,
        "fail_on": fail_on,
        "summary": {"added": len(added), "removed": len(removed), "changed": len(changed)},
        "added": added,
        "removed": removed,
        "changed": changed,
    }
