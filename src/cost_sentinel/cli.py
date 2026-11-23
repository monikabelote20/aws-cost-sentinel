"""Command line entry point: `cost-sentinel scan --region <region>`."""

import argparse
import sys

import boto3

from cost_sentinel import __version__
from cost_sentinel.checks import ALL_CHECKS
from cost_sentinel.report import FORMATS, render
from cost_sentinel.settings import Settings


def run_checks(session, region: str, checks: list[str], settings: Settings | None = None):
    settings = settings or Settings()
    findings = []
    for name in checks:
        findings.extend(ALL_CHECKS[name](session, region, settings))
    return sorted(findings, key=lambda f: f.monthly_cost, reverse=True)


def enabled_regions(session) -> list[str]:
    """Regions this account can use (opted-in or not requiring opt-in)."""
    ec2 = session.client("ec2", region_name=session.region_name or "us-east-1")
    resp = ec2.describe_regions(
        Filters=[{"Name": "opt-in-status", "Values": ["opt-in-not-required", "opted-in"]}]
    )
    return sorted(r["RegionName"] for r in resp["Regions"])


def scan_regions(session, regions: list[str], checks: list[str], settings: Settings | None = None):
    findings = []
    for region in regions:
        findings.extend(run_checks(session, region, checks, settings))
    return sorted(findings, key=lambda f: f.monthly_cost, reverse=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cost-sentinel", description=__doc__)
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)
    scan = sub.add_parser("scan", help="scan one or more regions for idle resources")
    where = scan.add_mutually_exclusive_group(required=True)
    where.add_argument(
        "--region",
        action="append",
        dest="regions",
        help="region to scan (repeatable, or comma-separated)",
    )
    where.add_argument("--all-regions", action="store_true", help="scan every enabled region")
    scan.add_argument("--profile", help="AWS named profile")
    scan.add_argument(
        "--check",
        action="append",
        choices=sorted(ALL_CHECKS),
        help="run only this check (repeatable); default is all checks",
    )
    scan.add_argument(
        "--snapshot-age-days",
        type=int,
        default=Settings.snapshot_age_days,
        help="flag snapshots older than this (default: %(default)s)",
    )
    scan.add_argument(
        "--nat-idle-days",
        type=int,
        default=Settings.nat_idle_days,
        help="flag NAT gateways with no traffic for this many days (default: %(default)s)",
    )
    scan.add_argument(
        "--stopped-days",
        type=int,
        default=Settings.stopped_instance_days,
        help="flag instances stopped for longer than this (default: %(default)s)",
    )
    scan.add_argument("--format", choices=FORMATS, default="text", help="output format")
    scan.add_argument("--output", "-o", help="write the report to this file instead of stdout")
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    session = boto3.Session(profile_name=args.profile)
    settings = Settings(
        snapshot_age_days=args.snapshot_age_days,
        nat_idle_days=args.nat_idle_days,
        stopped_instance_days=args.stopped_days,
    )
    if args.all_regions:
        regions = enabled_regions(session)
    else:
        regions = [r.strip() for value in args.regions for r in value.split(",") if r.strip()]
    findings = scan_regions(session, regions, args.check or sorted(ALL_CHECKS), settings)
    report = render(findings, args.format)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(report if report.endswith("\n") else report + "\n")
        print(f"wrote {len(findings)} findings to {args.output}", file=sys.stderr)
    else:
        print(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
