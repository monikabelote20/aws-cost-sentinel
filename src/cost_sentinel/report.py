"""Render findings as plain text, Markdown or JSON."""

import json
from collections import defaultdict
from dataclasses import asdict

FORMATS = ("text", "markdown", "json")


def total_cost(findings) -> float:
    return round(sum(f.monthly_cost for f in findings), 2)


def render_text(findings) -> str:
    lines = [
        f"{f.check:<17} {f.resource_id:<26} {f.region:<14} {f.summary:<30} "
        f"${f.monthly_cost:,.2f}/mo"
        for f in findings
    ]
    lines.append("")
    lines.append(f"{len(findings)} findings, estimated ${total_cost(findings):,.2f}/month")
    return "\n".join(lines)


def render_markdown(findings) -> str:
    by_check = defaultdict(list)
    for f in findings:
        by_check[f.check].append(f)

    out = [
        "# AWS cost findings",
        "",
        f"**{len(findings)} findings, estimated ${total_cost(findings):,.2f}/month**",
        "",
        "| Check | Findings | Est. monthly cost |",
        "|-------|---------:|------------------:|",
    ]
    for check, items in sorted(by_check.items()):
        out.append(f"| `{check}` | {len(items)} | ${total_cost(items):,.2f} |")

    for check, items in sorted(by_check.items()):
        out += ["", f"## {check}", "", "| Resource | Region | Details | Est. monthly cost |"]
        out.append("|----------|--------|---------|------------------:|")
        for f in items:
            out.append(f"| `{f.resource_id}` | {f.region} | {f.summary} | ${f.monthly_cost:,.2f} |")
    return "\n".join(out) + "\n"


def render_json(findings) -> str:
    doc = {
        "total_monthly_cost": total_cost(findings),
        "count": len(findings),
        "findings": [asdict(f) for f in findings],
    }
    return json.dumps(doc, indent=2, default=str)


def render(findings, fmt: str) -> str:
    renderers = {"text": render_text, "markdown": render_markdown, "json": render_json}
    return renderers[fmt](findings)
