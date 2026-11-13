import argparse
import sys
from pathlib import Path

from .core import InputError, compare, load_symbols
from .report import render


def main(argv=None):
    parser = argparse.ArgumentParser(description="Review exported ELF symbols from readelf -Ws output")
    sub = parser.add_subparsers(dest="command")
    compare_cmd = sub.add_parser("compare")
    compare_cmd.add_argument("before", type=Path)
    compare_cmd.add_argument("after", type=Path)
    compare_cmd.add_argument("--format", choices=("json", "markdown", "html"), default="json")
    compare_cmd.add_argument("--output", type=Path)
    compare_cmd.add_argument("--fail-on", choices=("breaking", "any-change", "none"), default="breaking")
    demo = sub.add_parser("demo")
    demo.add_argument("--format", choices=("json", "markdown", "html"), default="html")
    demo.add_argument("--output", type=Path, default=Path("abi-report.html"))
    args = parser.parse_args(argv)
    if args.command is None:
        parser.error("a command is required")
    try:
        if args.command == "demo":
            root = Path(__file__).parent / "fixtures"
            before, after = root / "before.readelf", root / "after.readelf"
            output = args.output
            report = compare(load_symbols(before), load_symbols(after), "breaking")
        else:
            output = args.output
            if output and output.resolve() in {args.before.resolve(), args.after.resolve()}:
                raise InputError("output must differ from input")
            report = compare(load_symbols(args.before), load_symbols(args.after), args.fail_on)
        content = render(report, args.format)
        if output:
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(content, encoding="utf-8")
        else:
            sys.stdout.write(content)
        return 0 if report["ok"] else 1
    except (OSError, UnicodeError, InputError, ValueError) as exc:
        print("error: " + str(exc), file=sys.stderr)
        return 2
