#!/usr/bin/env python3
"""Check a drill before it becomes a QR code.

The app validates a drill on arrival and rejects the whole thing if any part of it is wrong. Until
this existed the author found that out from whoever scanned the code, which is a slow and
embarrassing way to learn that a zone name is misspelt.

So this refuses the same drills the app refuses, and it does it without a second copy of the rules.
Every list, limit and zone it works from comes out of `rules.json`, which the app generates from the
validator that will judge the drill - rename a zone or move a limit and this file follows on the next
`npm run skill:format`. What it deliberately does not carry is the validator's *logic*: anything that
cannot be decided from the generated data is a warning, or is left to the phone.

The one failure that would make this worse than nothing is refusing a drill the app would have
accepted, so the rule throughout is: refuse only what the data makes certain, and warn about
everything else. The phone remains the authority.

Usage:
    python3 drill_check.py drill.json
    python3 drill_check.py drill.json --quiet     # errors only, no advice
    cat drill.json | python3 drill_check.py -
"""

import argparse
import json
import math
import os
import re
import sys

RULES_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, "rules.json")

_UNITS = {
    1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven",
    8: "eight", 9: "nine", 10: "ten", 11: "eleven", 12: "twelve", 13: "thirteen",
    14: "fourteen", 15: "fifteen", 16: "sixteen", 17: "seventeen", 18: "eighteen",
    19: "nineteen",
}
_TENS = {2: "twenty", 3: "thirty", 4: "forty", 5: "fifty", 6: "sixty", 7: "seventy",
         8: "eighty", 9: "ninety"}


def number_word(n):
    """A shirt number as narration says it. Hyphenated, because that is how it is read aloud."""
    if n in _UNITS:
        return _UNITS[n]
    tens, unit = divmod(n, 10)
    if tens not in _TENS:
        return str(n)
    return _TENS[tens] + ("-" + _UNITS[unit] if unit else "")


# A number word followed by one of these is counting, measuring, or standing in for a noun, rather
# than calling a shirt. "Everybody has one job", "the front of the six-yard box", "four attackers
# against two defenders", "the one the marker is leaving" - every one of those was reported as a
# mistake on a reviewed drill before this list existed. A shirt reference is followed by punctuation
# or a verb instead.
NOT_A_SHIRT = re.compile(
    r"^[\s-]*(?:"
    r"job|jobs|yard|yards|metre|metres|meter|meters|minute|minutes|second|seconds|touch|touches|"
    r"pass|passes|player|players|attacker|attackers|defender|defenders|striker|strikers|"
    r"keeper|keepers|team|teams|side|sides|goal|goals|ball|balls|cone|cones|net|nets|"
    r"queue|queues|station|stations|phase|phases|group|groups|pair|pairs|time|times|"
    r"v|vs|against|more|of|"
    # Used as a pronoun rather than as a name
    r"the|that|this|those|these|he|him|his|they|them|it|its|who|whom|which|where"
    r")\b",
    re.IGNORECASE,
)


def numbers_said(text):
    """Every shirt number a line names, in digits or in words.

    Largest first, and each match struck out as it is found, because "twenty-four" contains "four"
    with a word boundary on both sides of it. Scanning for the small number first found a four in
    every line that correctly said twenty-four, and reported each one as the mistake it was not.

    A word followed by a counted noun is skipped, because football narration is full of numbers that
    are not shirts - one job, a six-yard box, two touches - and reporting those made the check
    useless on drills that were right.
    """
    said = set()
    for match in re.finditer(r"\b\d{1,2}\b", text):
        said.add(int(match.group()))
    remaining = text.lower()
    for n in range(99, 0, -1):
        pattern = r"\b" + re.escape(number_word(n)).replace(r"\-", "[- ]") + r"\b"
        match = re.search(pattern, remaining)
        if not match:
            continue
        # Struck out either way: a counted "six" must not be left for "six" to find again.
        remaining = remaining[: match.start()] + " " + remaining[match.end() :]
        if not NOT_A_SHIRT.match(text[match.end() : match.end() + 24].lower()):
            said.add(n)
    return said

# Said of a team, these describe a board the coach may not have. Said of a cone they are fine, which
# is why the pattern needs the team word beside them rather than just the colour.
TEAM_COLOUR = re.compile(
    r"\b(?:the\s+)?(red|blue|grey|gray|white|black|green|orange|yellow)s?\s+(?:team|side|players|shirts)\b"
    r"|\bthe\s+(red|blue|grey|gray)s\b",
    re.IGNORECASE,
)

FULL_PITCH = re.compile(r"\b(?:full|whole|entire)\s+pitch\b|\bfull\s+field\b", re.IGNORECASE)

# Two markers this close are in the same place, and no amount of zooming separates them
SAME_PLACE_METRES = 0.5

# Closer than this to a net and a player is standing in it rather than near it. Deliberately about
# one body wide rather than the two markers' footprints: footprints are quoted at zoom 1 and the
# board zooms in to frame the drill, so a striker two metres off a small goal reads perfectly well.
# Measured against the footprints first, which reported the finisher in 04-two-small-goals.
NET_CLEARANCE_METRES = 1.5

# A never-moving away player this close to the goal his team defends is a goalkeeper, and a
# goalkeeper standing still is doing his job.
KEEPER_RADIUS_METRES = 10


def load_rules(path=RULES_PATH):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


class Report:
    """Two lists, kept apart because they mean different things.

    An error is the app refusing the drill. A warning is this script's opinion, and an author who
    disagrees with it should be able to ship anyway - several of them are judgements about coaching
    rather than facts about the format.
    """

    def __init__(self):
        self.errors = []
        self.warnings = []

    def error(self, path, message):
        self.errors.append((path, message))

    def warn(self, path, message):
        self.warnings.append((path, message))

    @property
    def ok(self):
        return not self.errors


# --- places -----------------------------------------------------------------------------------
# resolve_zone mirrors resolveZone() in utils/drillZones.ts, which is three lookup tables and one
# suffix match. The tables arrive in rules.json, so a renamed zone needs no change here.


def resolve_zone(at, rules):
    """Turn whatever the author wrote into a point on the pitch, or None."""
    if isinstance(at, list):
        if len(at) != 2:
            return None
        x, y = at
        for value in (x, y):
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                return None
            if not math.isfinite(value):
                return None
        if not (0 <= x <= 1) or not (0 <= y <= 1):
            return None
        return {"x": float(x), "y": float(y)}

    if not isinstance(at, str):
        return None
    key = at.strip().lower()

    landmark = rules["landmarks"].get(key)
    if landmark:
        return dict(landmark)

    band = rules["bands"].get(key)
    if band is not None:
        return {"x": rules["lanes"]["centre"], "y": band}

    # "left-centre-middle-third" is lane "left-centre" + band "middle-third", so the band has to be
    # matched off the end rather than the lane off the front.
    for band_name, band_y in rules["bands"].items():
        suffix = "-" + band_name
        if not key.endswith(suffix):
            continue
        lane_x = rules["lanes"].get(key[: -len(suffix)])
        if lane_x is not None:
            return {"x": lane_x, "y": band_y}

    return None


def metres_to_pitch(metres, direction, field, rules):
    pitch = rules["pitchMetres"].get(field) or rules["pitchMetres"]["11-a-side"]
    dx = metres / pitch["width"]
    dy = metres / pitch["length"]
    return {
        "up": {"x": 0.0, "y": -dy},
        "down": {"x": 0.0, "y": dy},
        "left": {"x": -dx, "y": 0.0},
        "right": {"x": dx, "y": 0.0},
    }[direction]


def metres_between(a, b, field, rules):
    pitch = rules["pitchMetres"].get(field) or rules["pitchMetres"]["11-a-side"]
    return math.hypot((a["x"] - b["x"]) * pitch["width"], (a["y"] - b["y"]) * pitch["length"])


def row_points(item, field, rules):
    """Every point a player or cone row occupies, the way foldPhase expands it."""
    start = resolve_zone(item.get("at"), rules)
    if not start:
        return []
    count = item.get("count")
    count = count if isinstance(count, int) and not isinstance(count, bool) and count > 1 else 1
    spacing = item.get("spacing_m")
    if count > 1 and isinstance(spacing, (int, float)) and not isinstance(spacing, bool):
        step = metres_to_pitch(spacing, item.get("direction") or "down", field, rules)
    else:
        step = {"x": 0.0, "y": 0.0}
    points = []
    for n in range(count):
        points.append({
            "x": min(1.0, max(0.0, start["x"] + step["x"] * n)),
            "y": min(1.0, max(0.0, start["y"] + step["y"] * n)),
        })
    return points


# --- the refusals -----------------------------------------------------------------------------
# Each of these mirrors a check in parseDrillScript(). Nothing here is this script's own opinion.


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def check_repeat(item, path, rules, report):
    max_repeat = rules["maxRepeat"]
    count = item.get("count")
    if count is not None:
        if not _is_int(count) or count < 1 or count > max_repeat:
            report.error(path + ".count", "Must be a whole number between 1 and %d." % max_repeat)
    spacing = item.get("spacing_m")
    if spacing is not None:
        if not _is_number(spacing) or spacing <= 0 or spacing > rules["maxSpacingMetres"]:
            report.error(
                path + ".spacing_m",
                "Must be a distance in metres, greater than 0 and at most %d."
                % rules["maxSpacingMetres"],
            )
    direction = item.get("direction")
    if direction is not None and direction not in rules["directions"]:
        report.error(path + ".direction", "Must be one of: %s." % ", ".join(rules["directions"]))
    if _is_int(count) and count > 1 and spacing is None:
        report.error(path + ".spacing_m", "Needed when count is more than 1, so the row has a known gap.")


def check_zone(at, path, rules, report):
    point = resolve_zone(at, rules)
    if point:
        return point
    if isinstance(at, list):
        report.error(path, "A coordinate pair must be two finite numbers between 0 and 1.")
    else:
        report.error(path, "Unknown place %s. Use a named zone or a [x, y] pair in 0-1."
                     % json.dumps(at))
    return None


def check_phase(phase, path, rules, report):
    if not isinstance(phase, dict):
        report.error(path, "Each phase must be an object.")
        return

    role = phase.get("role")
    if role is not None and role not in rules["roles"]:
        report.error(path + ".role", "Must be one of: %s." % ", ".join(rules["roles"]))

    for key, limit in (("say", rules["maxSayLength"]), ("caption", rules["maxCaptionLength"])):
        value = phase.get(key)
        if value is None:
            continue
        if not isinstance(value, str):
            report.error("%s.%s" % (path, key), "Must be a string.")
        elif len(value) > limit:
            report.error("%s.%s" % (path, key),
                         "At most %d characters (this one has %d)." % (limit, len(value)))

    at = phase.get("at")
    if at is not None and at not in rules["captionPositions"]:
        report.error(path + ".at",
                     "Caption position must be one of: %s." % ", ".join(rules["captionPositions"]))

    check_players(phase, path, rules, report)
    check_cones(phase, path, rules, report)
    check_nets(phase, path, rules, report)
    check_ball(phase, path, rules, report)
    check_shapes(phase, path, rules, report)
    check_arrows(phase, path, rules, report)


def check_players(phase, path, rules, report):
    players = phase.get("players")
    if players is None:
        return
    if not isinstance(players, list):
        report.error(path + ".players", "Must be an array.")
        return

    low, high = rules["playerNumbers"]["min"], rules["playerNumbers"]["max"]
    # interpolatePlayers keys a Map by number, so a repeat silently loses one of the two
    seen = set()
    for i, player in enumerate(players):
        p = "%s.players[%d]" % (path, i)
        if not isinstance(player, dict):
            report.error(p, "Must be an object.")
            continue
        if player.get("team") not in rules["teams"]:
            report.error(p + ".team", 'Must be "home" or "away".')
        check_repeat(player, p, rules, report)
        count = player.get("count") if _is_int(player.get("count")) else 1
        number = player.get("number")
        if not _is_int(number) or number < low or number > high:
            report.error(p + ".number", "Must be a whole number between %d and %d." % (low, high))
        elif number + count - 1 > high:
            report.error(p + ".number",
                         "A queue of %d from %d runs past shirt %d." % (count, number, high))
        else:
            for n in range(count):
                key = "%s-%d" % (player.get("team"), number + n)
                if key in seen:
                    report.error(p + ".number",
                                 "%s %d appears twice in this phase." % (player.get("team"), number + n))
                seen.add(key)
        check_zone(player.get("at"), p + ".at", rules, report)

        name = player.get("name")
        if name is not None:
            if not isinstance(name, str) or not name.strip():
                report.error(p + ".name", "Must be a non-empty string when present.")
            elif len(name) > rules["maxPlayerName"]:
                report.error(
                    p + ".name",
                    "At most %d characters (this one has %d); the board cuts anything longer."
                    % (rules["maxPlayerName"], len(name)),
                )
            elif count > 1:
                report.error(p + ".name", "A row of players cannot share one label; name them separately.")


def check_cones(phase, path, rules, report):
    cones = phase.get("cones")
    if cones is None:
        return
    if not isinstance(cones, list):
        report.error(path + ".cones", "Must be an array.")
        return
    for i, cone in enumerate(cones):
        p = "%s.cones[%d]" % (path, i)
        if not isinstance(cone, dict):
            report.error(p, "Must be an object.")
            continue
        check_zone(cone.get("at"), p + ".at", rules, report)
        colour = cone.get("color")
        if colour is not None and (
            not isinstance(colour, str) or colour.strip().lower() not in rules["coneColors"]
        ):
            report.error(p + ".color", "Use one of: %s." % ", ".join(rules["coneColors"]))
        stand = cone.get("stand")
        if stand is not None and stand not in rules["coneStands"]:
            report.error(p + ".stand", "Must be one of: %s." % ", ".join(rules["coneStands"]))
        check_repeat(cone, p, rules, report)


def check_nets(phase, path, rules, report):
    nets = phase.get("nets")
    if nets is None:
        return
    if not isinstance(nets, list):
        report.error(path + ".nets", "Must be an array.")
        return
    for i, net in enumerate(nets):
        p = "%s.nets[%d]" % (path, i)
        if not isinstance(net, dict):
            report.error(p, "Must be an object.")
            continue
        check_zone(net.get("at"), p + ".at", rules, report)
        facing = net.get("facing")
        if facing is not None and facing not in rules["netOrientations"]:
            report.error(p + ".facing",
                         "Must be one of: %s (degrees the opening faces)."
                         % ", ".join(str(o) for o in rules["netOrientations"]))


def check_ball(phase, path, rules, report):
    ball = phase.get("ball")
    if ball is None:
        return
    p = path + ".ball"
    if not isinstance(ball, dict):
        report.error(p, "Must be an object: { carriedBy: n }, { passTo: n } or { at: place }.")
        return
    if "carriedBy" in ball or "passTo" in ball:
        key = "carriedBy" if "carriedBy" in ball else "passTo"
        if not _is_int(ball.get(key)):
            report.error("%s.%s" % (p, key), "Must be a player number.")
        if ball.get("team") is not None and ball.get("team") not in rules["teams"]:
            report.error(p + ".team", 'Must be "home" or "away".')
    elif "at" in ball:
        check_zone(ball.get("at"), p + ".at", rules, report)
    else:
        report.error(p, "Needs one of: carriedBy, passTo, at.")


def _drawing_colour(value, rules):
    return isinstance(value, str) and value.strip().lower() in rules["drawingColors"]


def check_shapes(phase, path, rules, report):
    minimum = rules["minShapeMetres"]
    colours = ", ".join(rules["drawingColors"])

    areas = phase.get("areas")
    if areas is not None:
        if not isinstance(areas, list):
            report.error(path + ".areas", "Must be an array.")
        else:
            for i, area in enumerate(areas):
                p = "%s.areas[%d]" % (path, i)
                if not isinstance(area, dict):
                    report.error(p, "Must be an object.")
                    continue
                check_zone(area.get("at"), p + ".at", rules, report)
                for side in ("width_m", "height_m"):
                    value = area.get(side)
                    if not _is_number(value) or value < minimum:
                        report.error("%s.%s" % (p, side),
                                     "Must be a number of metres, at least %s." % minimum)
                if area.get("color") is not None and not _drawing_colour(area["color"], rules):
                    report.error(
                        p + ".color",
                        "Must be one of: %s. Those are the two the pen draws, so a shape from a "
                        "drill looks like one drawn by hand." % colours,
                    )

    circles = phase.get("circles")
    if circles is not None:
        if not isinstance(circles, list):
            report.error(path + ".circles", "Must be an array.")
        else:
            for i, circle in enumerate(circles):
                p = "%s.circles[%d]" % (path, i)
                if not isinstance(circle, dict):
                    report.error(p, "Must be an object.")
                    continue
                check_zone(circle.get("at"), p + ".at", rules, report)
                radius = circle.get("radius_m")
                if not _is_number(radius) or radius < minimum:
                    report.error(p + ".radius_m",
                                 "Must be a number of metres, at least %s." % minimum)
                if circle.get("color") is not None and not _drawing_colour(circle["color"], rules):
                    report.error(p + ".color", "Must be one of: %s." % colours)


def check_arrows(phase, path, rules, report):
    arrows = phase.get("arrows")
    if arrows is None:
        return
    if not isinstance(arrows, list):
        report.error(path + ".arrows", "Must be an array.")
        return
    for i, arrow in enumerate(arrows):
        p = "%s.arrows[%d]" % (path, i)
        if not isinstance(arrow, dict):
            report.error(p, "Must be an object.")
            continue
        for end in ("from", "to"):
            value = arrow.get(end)
            if _is_number(value) and not isinstance(value, str):
                if not _is_int(value):
                    report.error("%s.%s" % (p, end), "A player number must be a whole number.")
            else:
                check_zone(value, "%s.%s" % (p, end), rules, report)
        style = arrow.get("style")
        if style is not None and style not in rules["arrowStyles"]:
            report.error(p + ".style", "Must be one of: %s." % ", ".join(rules["arrowStyles"]))
        if arrow.get("color") is not None and not _drawing_colour(arrow["color"], rules):
            report.error(p + ".color", "Must be one of: %s." % ", ".join(rules["drawingColors"]))
        curve = arrow.get("curve")
        if curve is not None:
            if not _is_number(curve):
                report.error(p + ".curve", "Must be a number.")
            elif abs(curve) > 1:
                report.error(p + ".curve", "Between -1 and 1; past that the arrow loops back on itself.")


def check_ball_carriers(phases, rules, report):
    """The ball can only be given to a player who is on the pitch.

    `team` defaults to home, so a drill meaning away 5 asks for home 5 instead - and if home 5 does
    not exist the importer finds nobody and leaves the ball where it was, which renders perfectly and
    contradicts its own narration.
    """
    on_pitch = set()
    for index, phase in enumerate(phases):
        for player in phase.get("players") or []:
            count = player.get("count") if _is_int(player.get("count")) else 1
            for n in range(max(1, count)):
                on_pitch.add("%s-%d" % (player.get("team"), player.get("number") + n))
        ball = phase.get("ball")
        if not ball or "at" in ball:
            continue
        team = ball.get("team") or "home"
        wanted = ball.get("carriedBy") if "carriedBy" in ball else ball.get("passTo")
        if "%s-%s" % (team, wanted) in on_pitch:
            continue
        other = "away" if team == "home" else "home"
        hint = ""
        if "%s-%s" % (other, wanted) in on_pitch:
            hint = ' There is an %s %s; add "team": "%s" if that is who you meant.' % (other, wanted, other)
        report.error(
            "phases[%d].ball" % index,
            "No %s player %s is on the pitch, so nobody can %s the ball.%s"
            % (team, wanted, "carry" if "carriedBy" in ball else "receive", hint),
        )


def check_player_movement(phases, field, rules, report):
    """Nobody may cross more ground between two phases than a player could run."""
    limit = rules["maxPlayerMoveMetres"]
    seconds = rules["movementSeconds"]
    previous = {}
    for index, phase in enumerate(phases):
        for player_index, player in enumerate(phase.get("players") or []):
            points = row_points(player, field, rules)
            for n, at in enumerate(points):
                number = player.get("number") + n
                key = "%s-%d" % (player.get("team"), number)
                was = previous.get(key)
                previous[key] = at
                if not was:
                    continue
                metres = metres_between(at, was, field, rules)
                if metres <= limit:
                    continue
                board = number + rules["awayNumberOffset"] if player.get("team") == "away" else number
                report.error(
                    "phases[%d].players[%d]" % (index, player_index),
                    "%s%d would cover %dm in the %s seconds a movement takes, which is faster than "
                    "anyone runs. Keep it under %gm, or split the run across more phases."
                    % ("Away " if player.get("team") == "away" else "", board, round(metres),
                       number_word(int(seconds)) if float(seconds).is_integer() else seconds, limit),
                )


# --- the advice -------------------------------------------------------------------------------
# None of this is enforced anywhere. It is the set of mistakes that got through review on real
# drills, each of which took a person watching a video to notice.


def advise(script, phases, field, rules, report):
    advise_unknown_keys(script, phases, rules, report)
    advise_same_place(phases, field, rules, report)
    advise_player_on_net(phases, field, rules, report)
    advise_away_numbers(phases, rules, report)
    advise_team_colours(phases, report)
    advise_full_pitch(phases, field, rules, report)
    advise_idle_opposition(phases, field, rules, report)


# Which key list each phase collection is checked against
COLLECTIONS = {"players": "player", "cones": "cone", "nets": "net",
               "arrows": "arrow", "areas": "area", "circles": "circle"}


def advise_unknown_keys(script, phases, rules, report):
    """A misspelt key is not refused, it is ignored - which is the worst of the two.

    `"playrs"` passes the validator untouched and renders a phase with nobody in it. Warned rather
    than refused because that is exactly what the app does with it: ignoring unknown keys is how the
    format will add one without breaking older drills, so a drill refused here could be a drill the
    phone is perfectly happy with.
    """
    keys = rules["keys"]

    def look(kind, value, path):
        if not isinstance(value, dict):
            return
        for key in value:
            if key not in keys[kind]:
                report.warn(path, 'Unknown %s key "%s", which the app ignores. Did you mean one of: '
                                  "%s?" % (kind, key, ", ".join(keys[kind])))

    look("script", script, "")
    for index, phase in enumerate(phases):
        path = "phases[%d]" % index
        look("phase", phase, path)
        if not isinstance(phase, dict):
            continue
        look("ball", phase.get("ball"), path + ".ball")
        for collection, kind in COLLECTIONS.items():
            items = phase.get(collection)
            if not isinstance(items, list):
                continue
            for i, item in enumerate(items):
                look(kind, item, "%s.%s[%d]" % (path, collection, i))


def _markers(phase, field, rules):
    """Everything a phase places, as (label, point) pairs."""
    out = []
    for player in phase.get("players") or []:
        if not isinstance(player, dict) or not _is_int(player.get("number")):
            continue
        for n, point in enumerate(row_points(player, field, rules)):
            number = player["number"] + n
            board = number + rules["awayNumberOffset"] if player.get("team") == "away" else number
            out.append(("%s %d" % (player.get("team"), board), point, "player"))
    for i, cone in enumerate(phase.get("cones") or []):
        if not isinstance(cone, dict):
            continue
        for point in row_points(cone, field, rules):
            out.append(("cone %s" % (cone.get("id") or i + 1), point, "cone"))
    for i, net in enumerate(phase.get("nets") or []):
        if not isinstance(net, dict):
            continue
        point = resolve_zone(net.get("at"), rules)
        if point:
            out.append(("net %s" % (net.get("id") or i + 1), point, "net"))
    return out


def advise_same_place(phases, field, rules, report):
    """Two things in the same place stay in the same place however far the board zooms in.

    Ordinary crowding is not reported. The board frames the drill and markers keep their size on
    screen, so spacing that looks tight at zoom 1 is usually fine once the drill is framed - and
    SKILL.md's answer to a tight drill is to zoom in rather than to space players further apart than
    they stand in life. This is only the case no zoom can help.
    """
    for index, phase in enumerate(phases):
        markers = _markers(phase, field, rules)
        for i in range(len(markers)):
            for j in range(i + 1, len(markers)):
                a_label, a_point, a_kind = markers[i]
                b_label, b_point, b_kind = markers[j]
                # A player given a cone's position is stepped clear of it by the importer, so that
                # pair is not a collision - it is the documented way to place a player at a station.
                if {a_kind, b_kind} == {"player", "cone"}:
                    continue
                if metres_between(a_point, b_point, field, rules) <= SAME_PLACE_METRES:
                    report.warn("phases[%d]" % index,
                                "%s and %s are in the same place." % (a_label, b_label))


def advise_player_on_net(phases, field, rules, report):
    """A net draws underneath everything, so a marker on one erases it rather than crowding it."""
    nets = {}
    for index, phase in enumerate(phases):
        for i, net in enumerate(phase.get("nets") or []):
            if not isinstance(net, dict):
                continue
            point = resolve_zone(net.get("at"), rules)
            if point:
                nets[net.get("id") or "net-%d-%d" % (index, i)] = point
        for player in phase.get("players") or []:
            if not isinstance(player, dict) or not _is_int(player.get("number")):
                continue
            for n, point in enumerate(row_points(player, field, rules)):
                number = player["number"] + n
                board = number + rules["awayNumberOffset"] if player.get("team") == "away" else number
                for name, net_point in nets.items():
                    if metres_between(point, net_point, field, rules) < NET_CLEARANCE_METRES:
                        report.warn(
                            "phases[%d]" % index,
                            "%s stands on %s, which draws underneath him and disappears. Offset one "
                            "of them." % (board, name),
                        )


def advise_away_numbers(phases, rules, report):
    """An away 4 is drawn 24, so narration that says "four" names a disc nobody can see.

    Judged over the whole drill rather than line by line. A phase saying "four attackers against two
    defenders" is counting, not naming, and there is no way to tell the two apart in one sentence -
    but a drill that names the drawn number *somewhere* has clearly understood the offset, and one
    that never does has not. That is the mistake worth reporting, and it is the one that shipped.
    """
    offset = rules["awayNumberOffset"]
    away, home = set(), set()
    said = {}
    for index, phase in enumerate(phases):
        for player in phase.get("players") or []:
            if not isinstance(player, dict) or not _is_int(player.get("number")):
                continue
            count = player.get("count") if _is_int(player.get("count")) else 1
            for n in range(max(1, count)):
                (away if player.get("team") == "away" else home).add(player["number"] + n)
        text = phase.get("say")
        if isinstance(text, str):
            for number in numbers_said(text):
                said.setdefault(number, index)

    for number in sorted(away):
        drawn = number + offset
        # With the same number on both sides the narration is ambiguous rather than wrong, and only
        # the author knows which of the two was meant.
        if number in home or drawn in said or number not in said:
            continue
        report.warn(
            "phases[%d].say" % said[number],
            'Says "%s" and never "%s", but away %d is drawn as %d. The narration has to name the '
            "number on the disc." % (number_word(number), number_word(drawn), number, drawn),
        )


def advise_team_colours(phases, report):
    """The coach picks the team colours, so a drill naming them describes a board it cannot see."""
    for index, phase in enumerate(phases):
        for key in ("say", "caption"):
            text = phase.get(key)
            if not isinstance(text, str):
                continue
            match = TEAM_COLOUR.search(text)
            if match:
                report.warn(
                    "phases[%d].%s" % (index, key),
                    'Names a team by its colour ("%s"). The coach sets the colours in the app, so '
                    'say "ours" and "theirs", or use the numbers.' % match.group(0).strip(),
                )


def _bounding_metres(phases, field, rules):
    pitch = rules["pitchMetres"].get(field) or rules["pitchMetres"]["11-a-side"]
    xs, ys = [], []
    for phase in phases:
        for _, point, _kind in _markers(phase, field, rules):
            xs.append(point["x"])
            ys.append(point["y"])
        ball = phase.get("ball")
        if isinstance(ball, dict) and "at" in ball:
            point = resolve_zone(ball["at"], rules)
            if point:
                xs.append(point["x"])
                ys.append(point["y"])
    if not xs:
        return None
    return {
        "width": (max(xs) - min(xs)) * pitch["width"],
        "length": (max(ys) - min(ys)) * pitch["length"],
        "pitch": pitch,
    }


def advise_full_pitch(phases, field, rules, report):
    """The board zooms to fit the drill, so "full pitch" over a zoomed view contradicts the screen."""
    box = _bounding_metres(phases, field, rules)
    if not box:
        return
    spans = max(box["width"] / box["pitch"]["width"], box["length"] / box["pitch"]["length"])
    if spans >= 0.6:
        return
    for index, phase in enumerate(phases):
        for key in ("say", "caption"):
            text = phase.get(key)
            if isinstance(text, str) and FULL_PITCH.search(text):
                report.warn(
                    "phases[%d].%s" % (index, key),
                    'Says "full pitch", but the drill occupies about %dm by %dm and the board zooms '
                    "to fit it. Describe the area the viewer will actually see."
                    % (round(box["width"]), round(box["length"])),
                )


def advise_idle_opposition(phases, field, rules, report):
    """Opposition that never moves makes any point about beating them hollow.

    The away goalkeeper is left out of it. He is the one player whose job is to stay where he is, and
    reporting him taught the author to ignore the whole check.
    """
    positions = {}
    moved = set()
    present = set()
    # The away team defends the goal the home team attacks, so that is where its keeper stands
    own_goal = rules["landmarks"]["attacking-goal"]
    for phase in phases:
        for player in phase.get("players") or []:
            if not isinstance(player, dict) or player.get("team") != "away" or not _is_int(player.get("number")):
                continue
            for n, at in enumerate(row_points(player, field, rules)):
                key = player["number"] + n
                present.add(key)
                was = positions.get(key)
                positions[key] = at
                if was and metres_between(at, was, field, rules) > SAME_PLACE_METRES:
                    moved.add(key)
    keepers = {
        number for number, at in positions.items()
        if metres_between(at, own_goal, field, rules) <= KEEPER_RADIUS_METRES
    }
    present -= keepers
    idle = sorted(present - moved)
    if not present or not idle or len(phases) < 2:
        return
    drawn = ", ".join(str(n + rules["awayNumberOffset"]) for n in idle)
    if len(idle) == len(present):
        report.warn("phases", "No opposition player moves at any point (%s). A drill where they "
                              "stand still looks broken, and any coaching point about beating them "
                              "is hollow." % drawn)
    else:
        report.warn("phases", "%s never move. Give them something to do, or leave them out." % drawn)


# --- the whole thing --------------------------------------------------------------------------


def check(script, rules, advice=True):
    report = Report()

    if not isinstance(script, dict):
        report.error("", "A drill script must be a JSON object.")
        return report

    if script.get("format") != rules["format"]:
        report.error("format",
                     'Expected "%s", got %s. This app cannot read other versions.'
                     % (rules["format"], json.dumps(script.get("format"))))

    field = script.get("field")
    if not isinstance(field, str) or field not in rules["fields"]:
        report.error("field", "Must be one of: %s." % ", ".join(rules["fields"]))

    if script.get("title") is not None and not isinstance(script.get("title"), str):
        report.error("title", "Must be a string when present.")

    phases = script.get("phases")
    if not isinstance(phases, list) or not phases:
        report.error("phases", "A drill needs at least one phase.")
        return report
    if len(phases) > rules["maxPhases"]:
        report.error("phases", "At most %d phases (this one has %d)."
                     % (rules["maxPhases"], len(phases)))
        return report

    for index, phase in enumerate(phases):
        check_phase(phase, "phases[%d]" % index, rules, report)

    # Only worth walking once the shapes are known good, exactly as the validator orders it: a
    # half-validated phase would have this reading fields that may not be numbers.
    if report.ok:
        check_ball_carriers(phases, rules, report)
        check_player_movement(phases, field, rules, report)
        if advice:
            advise(script, phases, field, rules, report)

    return report


def main():
    parser = argparse.ArgumentParser(description="Check a drill the way the app will")
    parser.add_argument("drill", help="path to the drill JSON, or - for stdin")
    parser.add_argument("--quiet", action="store_true", help="errors only, no advice")
    parser.add_argument("--json", action="store_true", dest="as_json", help="machine-readable output")
    args = parser.parse_args()

    raw = sys.stdin.read() if args.drill == "-" else open(args.drill, encoding="utf-8").read()
    try:
        script = json.loads(raw)
    except json.JSONDecodeError as problem:
        print("Not valid JSON: %s" % problem, file=sys.stderr)
        return 1

    report = check(script, load_rules(), advice=not args.quiet)

    if args.as_json:
        print(json.dumps({
            "ok": report.ok,
            "errors": [{"path": p, "message": m} for p, m in report.errors],
            "warnings": [{"path": p, "message": m} for p, m in report.warnings],
        }, indent=2))
        return 0 if report.ok else 1

    print(format_report(report))
    return 0 if report.ok else 1


def format_report(report):
    lines = []
    if report.errors:
        lines.append("The app will reject this drill:")
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


if __name__ == "__main__":
    sys.exit(main())
