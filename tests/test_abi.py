import json
import tempfile
import unittest
from pathlib import Path

from elf_abi_diff.cli import main
from elf_abi_diff.core import InputError, compare, parse_symbols
from elf_abi_diff.report import render


HEADER = """Symbol table '.dynsym' contains 3 entries:\n   Num:    Value          Size Type    Bind   Vis      Ndx Name\n"""


def row(num, value, size, typ, bind, vis, ndx, name):
    return f"{num:6d}: {value:08x} {size:5d} {typ:<7} {bind:<6} {vis:<8} {ndx:>3} {name}\n"


class AbiTests(unittest.TestCase):
    def test_parse_exported_symbols(self):
        symbols = parse_symbols(HEADER + row(1, 1, 4, "FUNC", "GLOBAL", "DEFAULT", 1, "api"))
        self.assertEqual(symbols["api"].size, 4)

    def test_undefined_and_local_are_ignored(self):
        text = HEADER + row(1, 0, 0, "NOTYPE", "GLOBAL", "DEFAULT", "UND", "imp") + row(2, 1, 4, "FUNC", "LOCAL", "DEFAULT", 1, "local")
        self.assertEqual(parse_symbols(text), {})

    def test_empty_table_rejected(self):
        with self.assertRaises(InputError):
            parse_symbols("header only")

    def test_duplicate_export_rejected(self):
        text = HEADER + row(1, 1, 4, "FUNC", "GLOBAL", "DEFAULT", 1, "api") + row(2, 2, 4, "FUNC", "GLOBAL", "DEFAULT", 1, "api")
        with self.assertRaisesRegex(InputError, "duplicate"):
            parse_symbols(text)

    def test_removed_and_added_are_reported(self):
        before = parse_symbols(HEADER + row(1, 1, 4, "FUNC", "GLOBAL", "DEFAULT", 1, "old"))
        after = parse_symbols(HEADER + row(1, 1, 4, "FUNC", "GLOBAL", "DEFAULT", 1, "new"))
        report = compare(before, after)
        self.assertEqual(report["summary"], {"added": 1, "removed": 1, "changed": 0})
        self.assertFalse(report["ok"])

    def test_address_relocation_is_not_abi_change(self):
        before = parse_symbols(HEADER + row(1, 1, 4, "FUNC", "GLOBAL", "DEFAULT", 1, "api"))
        after = parse_symbols(HEADER + row(1, 0x1000, 4, "FUNC", "GLOBAL", "DEFAULT", 1, "api"))
        self.assertTrue(compare(before, after)["ok"])

    def test_size_change_is_breaking(self):
        before = parse_symbols(HEADER + row(1, 1, 4, "FUNC", "GLOBAL", "DEFAULT", 1, "api"))
        after = parse_symbols(HEADER + row(1, 1, 8, "FUNC", "GLOBAL", "DEFAULT", 1, "api"))
        report = compare(before, after)
        self.assertEqual(report["summary"]["changed"], 1)
        self.assertFalse(report["ok"])

    def test_any_change_gate_includes_additions(self):
        before = parse_symbols(HEADER + row(1, 1, 4, "FUNC", "GLOBAL", "DEFAULT", 1, "api"))
        after = parse_symbols(HEADER + row(1, 1, 4, "FUNC", "GLOBAL", "DEFAULT", 1, "api") + row(2, 2, 4, "FUNC", "GLOBAL", "DEFAULT", 1, "new"))
        self.assertFalse(compare(before, after, "any-change")["ok"])

    def test_report_escapes_html(self):
        report = {"ok": False, "fail_on": "breaking", "removed": [{"name": "a<&"}], "added": [], "changed": []}
        self.assertIn("a&lt;&amp;", render(report, "html"))

    def test_cli_status_and_output(self):
        root = Path(__file__).parents[1] / "elf_abi_diff" / "fixtures"
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "report.json"
            self.assertEqual(main(["compare", str(root / "before.readelf"), str(root / "after.readelf"), "--output", str(output)]), 1)
            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(payload["summary"]["changed"], 1)


if __name__ == "__main__":
    unittest.main()
