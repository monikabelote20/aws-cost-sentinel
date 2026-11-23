"""Command line entry point: `cost-sentinel scan --region <region>`."""

import argparse
import sys

import boto3

from cost_sentinel import __version__
from cost_sentinel.checks import ALL_CHECKS
from cost_sentinel.settings import Settings


def run_checks(session, region: str, checks: list[str], settings: Settings | None = None):
    settings = settings or Settings()
    findings = []
    for name in checks:
        findings.extend(ALL_CHECKS[name](session, region, settings))
    return sorted(findings, key=lambda f: f.monthly_cost, reverse=True)


def render_text(findings) -> str:
    lines = [
        f"{f.check:<15} {f.resource_id:<22} {f.region:<10} {f.summary:<28} "
        f"${f.monthly_cost:,.2f}/mo"
        for f in findings
    ]
    total = sum(f.monthly_cost for f in findings)
    lines.append("")
    lines.append(f"{len(findings)} findings, estimated ${total:,.2f}/month")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cost-sentinel", description=__doc__)
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)
    scan = sub.add_parser("scan", help="scan a region for idle resources")
    scan.add_argument("--region", required=True)
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
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    session = boto3.Session(profile_name=args.profile)
    settings = Settings(snapshot_age_days=args.snapshot_age_days)
    findings = run_checks(session, args.region, args.check or sorted(ALL_CHECKS), settings)
    print(render_text(findings))
    return 0


if __name__ == "__main__":
    sys.exit(main())
