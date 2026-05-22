"""idle — (stretch) find idle EC2 instances by N-hour CPU average.

WHAT YOU MUST BUILD
-------------------
A script that:
  1. Iterates running EC2 instances (skip ones tagged `keep=true`)
  2. For each, queries CloudWatch CPUUtilization average over last N hours
  3. Marks as IDLE if avg < threshold
  4. Prints per-instance status + final idle list

AWS APIS YOU'LL NEED
--------------------
cw = boto3.client("cloudwatch")
cw.get_metric_statistics(
    Namespace="AWS/EC2",
    MetricName="CPUUtilization",
    Dimensions=[{"Name": "InstanceId", "Value": iid}],
    StartTime=<datetime>, EndTime=<datetime>,
    Period=3600,            # 1-hour buckets
    Statistics=["Average"],
)
Response: resp["Datapoints"] is a list of dicts with "Average" key.

NOTE: CloudWatch metrics start populating ~5 min after instance launch. New
instances (< 1h running) typically return zero Datapoints — handle that as
"NO DATA", not as idle.

EXPECTED OUTPUT FORMAT
----------------------
    Scanning running EC2 (excluding keep=true) — threshold 5.0% over 24h:
    ------------------------------------------------------------------------------
      i-0abc123def456789a   t3.micro     cpu_24h= 1.20%  <- IDLE
      i-0bbb456ef789012345   t3.small     cpu_24h=42.50%
      i-0ccc789f0123456789   t3.nano      cpu_24h=NO DATA
    ------------------------------------------------------------------------------

    Idle: 1 instance(s): ['i-0abc123def456789a']
    Tip: combo with terminate →  ./costctl.py terminate ec2 --id <id>

VERIFY MANUALLY (no test file for this command)
-----------------------------------------------
    ./costctl.py idle --threshold 5 --hours 24

If nothing idle in your account, lower threshold to e.g. 50 to test the
path: `./costctl.py idle --threshold 50 --hours 1`.

COMBO IDEA FOR W6 EVIDENCE PACK
-------------------------------
1. Run `idle` to find waste
2. `terminate` the idle instances
3. Run `cost --tag Application=<your-app>` 24h later
4. Document the delta in your evidence pack
"""
import boto3
from datetime import datetime, timedelta, timezone
from statistics import mean

from commands._common import tags_to_dict


def _avg_cpu(cw, instance_id, hours):
    """Return average CPU% over last N hours, or None if no datapoints."""
    end = datetime.now(timezone.utc)
    start = end - timedelta(hours=hours)
    resp = cw.get_metric_statistics(
        Namespace="AWS/EC2",
        MetricName="CPUUtilization",
        Dimensions=[{"Name": "InstanceId", "Value": instance_id}],
        StartTime=start,
        EndTime=end,
        Period=3600,
        Statistics=["Average"],
    )
    points = [p.get("Average") for p in resp.get("Datapoints", []) if "Average" in p]
    if not points:
        return None
    return mean(points)


def run(args):
    """Entry point.

    Args set by argparse:
        args.threshold  — float, default 5.0 (% CPU)
        args.hours      — int, default 24
    """
    ec2 = boto3.client("ec2", region_name="us-east-1")
    cw = boto3.client("cloudwatch", region_name="us-east-1")

    print(
        f"Scanning running EC2 (excluding keep=true) — threshold {args.threshold:.1f}% "
        f"over {args.hours}h:"
    )
    print("-" * 78)

    idle_ids = []
    paginator = ec2.get_paginator("describe_instances")
    for page in paginator.paginate(Filters=[{"Name": "instance-state-name", "Values": ["running"]}]):
        for reservation in page.get("Reservations", []):
            for inst in reservation.get("Instances", []):
                tags = tags_to_dict(inst.get("Tags"))
                if tags.get("keep", "").lower() == "true":
                    continue
                iid = inst["InstanceId"]
                itype = inst["InstanceType"]
                avg = _avg_cpu(cw, iid, args.hours)
                if avg is None:
                    print(f"  {iid:20} {itype:12} cpu_{args.hours}h=NO DATA")
                    continue
                flag = "  <- IDLE" if avg < args.threshold else ""
                if avg < args.threshold:
                    idle_ids.append(iid)
                print(f"  {iid:20} {itype:12} cpu_{args.hours}h={avg:6.2f}%{flag}")

    print("-" * 78)
    print(f"\nIdle: {len(idle_ids)} instance(s): {idle_ids}")
    print("Tip: combo with terminate ->  ./costctl.py terminate ec2 --id <id>")
