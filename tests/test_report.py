import json

import pytest

from cost_sentinel.models import Finding
from cost_sentinel.report import render, render_json, render_markdown, total_cost

FINDINGS = [
    Finding("ebs-unattached", "vol-1", "eu-west-1", "500 GiB gp2, unattached", 50.0),
    Finding("ebs-unattached", "vol-2", "eu-west-1", "100 GiB gp3, unattached", 8.0),
    Finding("eip-unassociated", "eipalloc-1", "eu-west-1", "203.0.113.10, not associated", 3.65),
]


def test_total_cost():
    assert total_cost(FINDINGS) == pytest.approx(61.65)


def test_markdown_has_summary_and_section_per_check():
    md = render_markdown(FINDINGS)

    assert "**3 findings, estimated $61.65/month**" in md
    assert "| `ebs-unattached` | 2 | $58.00 |" in md
    assert "## eip-unassociated" in md
    assert "| `vol-1` | eu-west-1 | 500 GiB gp2, unattached | $50.00 |" in md


def test_json_is_machine_readable():
    doc = json.loads(render_json(FINDINGS))

    assert doc["count"] == 3
    assert doc["total_monthly_cost"] == pytest.approx(61.65)
    assert doc["findings"][0]["resource_id"] == "vol-1"


def test_empty_report():
    assert render([], "text").endswith("0 findings, estimated $0.00/month")
    assert json.loads(render([], "json"))["findings"] == []
