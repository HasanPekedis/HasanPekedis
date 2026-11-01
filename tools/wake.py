#!/usr/bin/env python3
"""Nudge a git-koi snapshot so the koi plays a swimming animation.

git-koi picks one movement per run from the account's recent activity
(`select_behavior` in src/behavior.rs):

    quiet days >= 60  -> DeepRest   (sits low, barely moves)
    quiet days >= 14  -> Rest       (hovers in place)
    first contribution of the week -> SurfaceFeeding (hovers and gulps)
    milestone / busy week          -> Dart  (two fast laps)
    otherwise                      -> Cruise (one slow lap)

An account with no contributions therefore renders a fish that never travels: that is
what "deep rest" looks like, not a broken animation. This script only touches the
snapshot's own contribution counts for the last two weeks, which is all
`quiet_day_count` reads, so the renderer's own lap animation runs. Colors, language
pigments and growth still come from the untouched history apart from those days.

    python3 tools/wake.py snapshot.json [--days 13]

Say what it does in the commit message; it is a presentation choice, not data.
"""
import argparse
import json


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("snapshot")
    ap.add_argument("--days", type=int, default=13,
                    help="trailing days to mark active (git-koi rests after 14 quiet days)")
    args = ap.parse_args()

    with open(args.snapshot, encoding="utf-8") as handle:
        snapshot = json.load(handle)

    days = snapshot["contribution_history"]["days"]
    if not days:
        raise SystemExit("the snapshot has no contribution days")

    touched = 0
    for day in days[-args.days:]:
        if day["contribution_count"] == 0:
            day["contribution_count"] = 1
            touched += 1

    with open(args.snapshot, "w", encoding="utf-8") as handle:
        json.dump(snapshot, handle)

    print(f"wake: marked {touched} trailing day(s) active; "
          f"the renderer should now choose a lap behavior")


if __name__ == "__main__":
    main()
