import html
import json


def render(report, format="json"):
    if format == "json":
        return json.dumps(report, indent=2, ensure_ascii=True, allow_nan=False) + "\n"
    if format == "markdown":
        lines = ["# ELF ABI diff", "", "Policy: **%s**" % ("PASS" if report["ok"] else "FAIL"), "",
                 "| Kind | Symbol | Details |", "|---|---|---|"]
        for item in report["removed"]:
            lines.append("| removed | `%s` | exported symbol disappeared |" % item["name"].replace("|", "\\|"))
        for item in report["added"]:
            lines.append("| added | `%s` | new export |" % item["name"].replace("|", "\\|"))
        for item in report["changed"]:
            details = ", ".join("%s: %s → %s" % (key, value["before"], value["after"])
                                for key, value in item["differences"].items())
            lines.append("| changed | `%s` | %s |" % (item["name"].replace("|", "\\|"), details.replace("|", "\\|")))
        return "\n".join(lines) + "\n"
    if format != "html":
        raise ValueError("format must be json, markdown or html")
    esc = lambda value: html.escape(str(value), quote=True)
    rows = []
    for item in report["removed"]:
        rows.append("<tr><td>removed</td><td>" + esc(item["name"]) + "</td><td>export disappeared</td></tr>")
    for item in report["added"]:
        rows.append("<tr><td>added</td><td>" + esc(item["name"]) + "</td><td>new export</td></tr>")
    for item in report["changed"]:
        details = ", ".join("%s: %s → %s" % (key, value["before"], value["after"])
                            for key, value in item["differences"].items())
        rows.append("<tr><td>changed</td><td>" + esc(item["name"]) + "</td><td>" + esc(details) + "</td></tr>")
    return ("<!doctype html><meta charset='utf-8'><title>ELF ABI diff</title>"
            "<style>body{font:16px system-ui;margin:2rem;color:#172b4d}table{border-collapse:collapse;width:100%}"
            "td,th{padding:.5rem;border:1px solid #ccd}th{background:#edf2f7}</style>"
            "<h1>ELF ABI diff</h1><p>Policy: <strong>" + ("PASS" if report["ok"] else "FAIL") +
            "</strong> · gate: " + esc(report["fail_on"]) + "</p><table><tr><th>Kind</th><th>Symbol</th>"
            "<th>Details</th></tr>" + "".join(rows) + "</table>\n")
