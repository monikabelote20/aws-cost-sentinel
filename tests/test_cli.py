import json

from cost_sentinel.cli import build_parser, enabled_regions, main, scan_regions


def test_scan_several_regions(session):
    for region in ("us-east-1", "eu-west-1"):
        ec2 = session.client("ec2", region_name=region)
        ec2.allocate_address(Domain="vpc")

    findings = scan_regions(session, ["us-east-1", "eu-west-1"], ["eip-unassociated"])

    assert {f.region for f in findings} == {"us-east-1", "eu-west-1"}


def test_enabled_regions_includes_default_regions(session):
    regions = enabled_regions(session)

    assert "us-east-1" in regions
    assert regions == sorted(regions)


def test_region_flag_accepts_commas_and_repeats():
    args = build_parser().parse_args(
        ["scan", "--region", "us-east-1,eu-west-1", "--region", "ap-south-1"]
    )

    assert args.regions == ["us-east-1,eu-west-1", "ap-south-1"]


def test_main_writes_json_report(session, tmp_path, capsys):
    session.client("ec2", region_name="ap-south-1").allocate_address(Domain="vpc")
    out = tmp_path / "report.json"

    code = main(
        [
            "scan",
            "--region",
            "ap-south-1",
            "--check",
            "eip-unassociated",
            "--format",
            "json",
            "-o",
            str(out),
        ]
    )

    assert code == 0
    assert json.loads(out.read_text())["count"] == 1
    assert "wrote 1 findings" in capsys.readouterr().err
