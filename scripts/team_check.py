#!/usr/bin/env python3
"""Refuse a team roster the app would refuse, before a code is made for it.

Usage:
    python3 team_check.py team.json
    cat team.json | python3 team_check.py -

The same arrangement as `drill_check.py` and for the same reason: the limits come out of
`team-rules.json`, generated from the app's own validator, so this cannot drift from what the phone
will accept. There is no copy of the rules here - only the logic that applies them.

A roster is a much smaller format than a drill, so most of this file is the difference between an
error and a piece of advice. An error is the app refusing the code. A warning is this script's
opinion, and a coach who disagrees should be able to hand the list over anyway.
"""

import json
import os
import sys

RULES_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, "team-rules.json")


def load_rules(path=RULES_PATH):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


class Report:
    def __init__(self):
        self.errors = []
        self.warnings = []

    def error(self, path, message):
        self.errors.append((path, message))

    def warn(self, path, message):
        self.warnings.append((path, message))


def format_report(report):
    lines = []
    if report.errors:
        lines.append("The app will reject this team:")
        lines += ["  %s: %s" % (path, message) if path else "  " + message
                  for path, message in report.errors]
    if report.warnings:
        if lines:
            lines.append("")
        lines.append("Worth a look before you hand it over:")
        lines += ["  %s: %s" % (path, message) if path else "  " + message
                  for path, message in report.warnings]
    if not lines:
        lines.append("No problems found. The app is still the one that decides.")
    return "\n".join(lines)


def check(roster, rules):
    report = Report()

    if not isinstance(roster, dict):
        report.error("", "A team is a JSON object.")
        return report

    if roster.get("format") != rules["format"]:
        report.error(
            "format",
            'Expected "%s", got %s.' % (rules["format"], json.dumps(roster.get("format"))),
        )
        return report

    players = roster.get("players")
    if not isinstance(players, list) or not players:
        report.error("players", "Expected a non-empty array.")
        return report

    if len(players) > rules["maxPlayers"]:
        report.error("players", "%d players; the most this holds is %d."
                     % (len(players), rules["maxPlayers"]))
        return report

    positions = rules["positions"]
    seen = {}
    unknown_position = 0

    for index, player in enumerate(players):
        at = "players[%d]" % index

        if not isinstance(player, dict):
            report.error(at, "Expected an object.")
            continue

        number = player.get("number")
        if not isinstance(number, int) or isinstance(number, bool) \
                or number < rules["minJersey"] or number > rules["maxJersey"]:
            report.error("%s.number" % at, "Expected a whole number from %d to %d, got %s."
                         % (rules["minJersey"], rules["maxJersey"], json.dumps(number)))
        elif number in seen:
            report.error("%s.number" % at, "Shirt %d is already taken by %s."
                         % (number, json.dumps(seen[number])))
        else:
            seen[number] = player.get("name")

        name = player.get("name")
        if not isinstance(name, str) or not name.strip():
            report.error("%s.name" % at, "Expected a name.")
        elif len(name.strip()) > rules["maxNameLength"]:
            report.error("%s.name" % at, "Longer than %d characters."
                         % rules["maxNameLength"])

        position = player.get("position")
        if not isinstance(position, str) or position not in positions:
            report.error("%s.position" % at, "Expected one of %s, got %s."
                         % (", ".join(positions), json.dumps(position)))
        elif position == "NA":
            unknown_position += 1

    # Advice rather than errors. Each of these is a judgement about the list, not a fact about the
    # format, and every one of them has a legitimate answer of "yes, that is what I meant".
    if unknown_position and unknown_position == len(players):
        report.warn("players", "Every player is NA. If the source list named positions, they were "
                               "not carried across.")

    keepers = [p for p in players if isinstance(p, dict) and p.get("position") == "GK"]
    if not keepers:
        report.warn("players", "No goalkeeper. Fine for a futsal rotation, worth checking otherwise.")

    long_names = [
        "players[%d]" % i
        for i, p in enumerate(players)
        if isinstance(p, dict) and isinstance(p.get("name"), str) and len(p["name"].split()) > 2
    ]
    if long_names:
        report.warn(
            ", ".join(long_names[:3]) + (" and others" if len(long_names) > 3 else ""),
            "Full names are drawn wider than the shirt they sit under. A first name, or initials "
            "and a surname, reads better on the board - and keeps a squad list proportionate.",
        )

    return report


def main():
    source = sys.argv[1] if len(sys.argv) > 1 else "-"
    text = sys.stdin.read() if source == "-" else open(source, encoding="utf-8").read()
    try:
        roster = json.loads(text)
    except json.JSONDecodeError as error:
        print("That is not valid JSON: %s" % error, file=sys.stderr)
        return 1

    report = check(roster, load_rules())
    print(format_report(report))
    return 1 if report.errors else 0


if __name__ == "__main__":
    sys.exit(main())
