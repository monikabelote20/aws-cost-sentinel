# aws-cost-sentinel

[![ci](https://github.com/monikabelote20/aws-cost-sentinel/actions/workflows/ci.yml/badge.svg)](https://github.com/monikabelote20/aws-cost-sentinel/actions/workflows/ci.yml)

_Built and maintained with an AI coding agent (Claude, by Anthropic) under the direction of [@monikabelote20](https://github.com/monikabelote20)._

Find idle and wasteful AWS resources and estimate what they cost each month.

`cost-sentinel` is a small, read-only CLI. It calls the EC2 describe APIs, flags resources that are
costing money without doing anything useful, and prints an estimated monthly cost for each finding.

## Checks

| Check | What it flags |
|-------|---------------|
| `ebs-unattached` | EBS volumes in the `available` state (not attached to any instance) |
| `eip-unassociated` | Elastic IPs that are allocated but not associated with an instance or ENI |
| `snapshot-old` | Snapshots older than `--snapshot-age-days` (default 90) that no AMI of yours uses |

## Install

```bash
pip install -e .
```

Requires Python 3.11+ and AWS credentials with read-only EC2 access. The minimum IAM
permissions are:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ec2:DescribeRegions",
        "ec2:DescribeVolumes",
        "ec2:DescribeAddresses",
        "ec2:DescribeSnapshots",
        "ec2:DescribeImages"
      ],
      "Resource": "*"
    }
  ]
}
```

## Usage

```bash
cost-sentinel scan --region eu-west-1
cost-sentinel scan --region eu-west-1,ap-south-1   # several regions
cost-sentinel scan --all-regions                    # every enabled region
```

Write a Markdown or JSON report instead of the console table:

```bash
cost-sentinel scan --region eu-west-1 --format markdown -o cost-report.md
cost-sentinel scan --region eu-west-1 --format json | jq '.total_monthly_cost'
```

Example console output:

```
ebs-unattached  vol-0a1b2c3d4e5f67890  eu-west-1  100 GiB gp3, unattached   $8.00/mo
ebs-unattached  vol-0f9e8d7c6b5a43210  eu-west-1  500 GiB gp2, unattached   $50.00/mo

2 findings, estimated $58.00/month
```

Snapshot costs use the full volume size, so they are an upper bound (snapshots are incremental).
Cost estimates use us-east-1 on-demand list prices. They are meant for prioritising clean-up, not
for billing.

## Development

```bash
pip install -e '.[dev]'
pytest
```

Tests use [moto](https://github.com/getmoto/moto), so no AWS account is needed.

## License

MIT
