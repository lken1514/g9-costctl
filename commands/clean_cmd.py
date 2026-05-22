"""clean — (stretch) bulk terminate resources matching a tag.

WARNING — DESIGN-FOR-SAFETY
---------------------------
This is the most dangerous command in the CLI. Get the contract right:

  1. DEFAULT IS DRY-RUN. Without --apply the command MUST NOT touch resources.
     It only lists what WOULD be deleted.
  2. Even with --apply, you should consider printing a summary count first
     ("about to terminate N EC2 + M volumes — proceed?"), though for this
     starter a hard `--apply` flag is enough.
  3. Never use this with a tag you don't fully own. Reflection prompt in
     README covers the blast-radius scenario.

WHAT YOU MUST BUILD
-------------------
1. `_find_targets(tag_key, tag_val)` — return a dict like:
     {"ec2": [<instance ids in non-terminal state>],
      "volume": [<volume ids in 'available' state only>]}
   Skip terminated/shutting-down instances (already gone).
   Skip in-use volumes (can't delete while attached — would error anyway).

2. `run(args)` — call _find_targets, print the plan, then either:
     - bail with "(dry-run — pass --apply to ...)"  (default)
     - or actually terminate (when --apply)

HELPERS YOU CAN USE
-------------------
From commands._common:
  parse_kv(s) -> (k, v)

AWS APIS YOU'LL NEED
--------------------
- ec2.describe_instances() + describe_volumes() — same as list_cmd
- ec2.terminate_instances(InstanceIds=[...])
- ec2.delete_volume(VolumeId=...)  (per volume, no bulk API)

VERIFY
------
    pytest tests/test_clean.py -v
"""
import boto3

from commands._common import parse_kv, tags_to_dict


def _find_targets(tag_key, tag_val):
    """Return {"ec2": [...], "volume": [...]} matching tag in non-terminal state."""
    ec2 = boto3.client("ec2")
    targets = {"ec2": [], "volume": []}

    paginator = ec2.get_paginator("describe_instances")
    for page in paginator.paginate():
        for reservation in page.get("Reservations", []):
            for inst in reservation.get("Instances", []):
                state = inst.get("State", {}).get("Name")
                if state in ("terminated", "shutting-down"):
                    continue
                tags = tags_to_dict(inst.get("Tags"))
                if tags.get(tag_key) == tag_val:
                    targets["ec2"].append(inst["InstanceId"])

    vol_pages = ec2.get_paginator("describe_volumes")
    for page in vol_pages.paginate():
        for vol in page.get("Volumes", []):
            if vol.get("State") != "available":
                continue
            tags = tags_to_dict(vol.get("Tags"))
            if tags.get(tag_key) == tag_val:
                targets["volume"].append(vol["VolumeId"])

    return targets


def run(args):
    """Entry point.

    Args set by argparse:
        args.tag    — "key=value" string (REQUIRED)
        args.apply  — bool, must be True to actually delete (default False = dry-run)
    """
    tag_key, tag_val = parse_kv(args.tag)
    targets = _find_targets(tag_key, tag_val)
    ec2_ids = targets.get("ec2", [])
    vol_ids = targets.get("volume", [])

    if not ec2_ids and not vol_ids:
        print("Nothing to clean.")
        return

    if not args.apply:
        print(
            f"dry-run — would terminate {len(ec2_ids)} EC2 and delete {len(vol_ids)} volume(s)."
        )
        print("(dry-run — pass --apply to execute)")
        return

    ec2 = boto3.client("ec2")
    if ec2_ids:
        ec2.terminate_instances(InstanceIds=ec2_ids)
    for vid in vol_ids:
        ec2.delete_volume(VolumeId=vid)
    print(f"Terminated {len(ec2_ids)} EC2, deleted {len(vol_ids)} volume(s).")
