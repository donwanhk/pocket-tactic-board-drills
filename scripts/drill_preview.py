#!/usr/bin/env python3
"""Draw a drill as text, one phase at a time.

Whoever writes a drill is working blind. They pick a zone by name, and nothing says whether the
recovering defender ended up goal-side or halfway to the corner flag, whether the queue is standing
in the passing lane, or whether the ball is anywhere near the player meant to be carrying it. Until
this existed the only way to find out was to make a code, scan it, and watch the animation.

A picture would be better and is not available: this runs wherever the skill was unzipped, with
nothing but Python. A grid is what can be read back and checked.

Every cell is three characters wide, so a label like `a24` cannot run into its neighbour. The first
version used one character per cell, which rendered a queue of away players as `a1a13a1a15` and then
cheerfully reported that nothing was overlapping.

Deliberately coarse: it answers "is this roughly right", not "is this correct to the metre". Four
things it cannot show at all, because the app works them out when the drill arrives -

  * the zoom, which frames the whole drill and is why tight spacing usually reads fine;
  * which side of a player's feet the ball sits on;
  * a player stepping clear of a cone he was placed on;
  * anything drawn - arrows, areas and circles are listed rather than plotted.

It makes no judgements either. `drill_check.py` does that.

Usage:
    python3 drill_preview.py drill.json
    python3 drill_preview.py drill.json --phase 3
"""

import argparse
import json
import sys

import drill_check
from drill_check import resolve_zone, row_points

COLS = 21
ROWS = 24
CELL = 3

BLANK = " " * CELL
RULE = "-" * CELL
SIDE = " | "

# Where the pitch markings go, as a fraction of the way down
HALFWAY = 0.5
BOX_DEPTH = 0.17
BOX_HALF_WIDTH = 0.29


def pad(label):
    return label[:CELL] if len(label) >= CELL else label + " " * (CELL - len(label))


def blank_pitch():
    grid = [[BLANK for _ in range(COLS)] for _ in range(ROWS)]

    for c in range(COLS):
        grid[0][c] = RULE
        grid[ROWS - 1][c] = RULE
        grid[round((ROWS - 1) * HALFWAY)][c] = RULE
    for r in range(ROWS):
        grid[r][0] = SIDE
        grid[r][COLS - 1] = SIDE

    box_rows = round((ROWS - 1) * BOX_DEPTH)
    left = round((COLS - 1) * (0.5 - BOX_HALF_WIDTH))
    right = round((COLS - 1) * (0.5 + BOX_HALF_WIDTH))
    for edge, inward in ((0, 1), (ROWS - 1, -1)):
        far = edge + inward * box_rows
        for c in range(left, right + 1):
            grid[far][c] = RULE
        for r in range(min(edge, far), max(edge, far) + 1):
            grid[r][left] = SIDE
            grid[r][right] = SIDE

    grid[round((ROWS - 1) * HALFWAY)][round((COLS - 1) / 2)] = " + "
    return grid


def to_cell(point):
    return (
        min(ROWS - 2, max(1, round(point["y"] * (ROWS - 1)))),
        min(COLS - 2, max(1, round(point["x"] * (COLS - 1)))),
    )


def fold(phases, upto, field, rules):
    """The board as it stands at the end of a phase.

    Players, cones, nets and the ball carry forward and each phase lists only what changed, so the
    picture for phase 3 is every phase up to 3 laid over each other - the same fold the importer
    does. Cones and nets are keyed by `id` where they have one, which is what makes a moved cone one
    cone rather than two.
    """
    players, cones, nets = {}, {}, {}
    ball = None

    for index, phase in enumerate(phases[: upto + 1]):
        if not isinstance(phase, dict):
            continue
        for player in phase.get("players") or []:
            if not isinstance(player, dict) or not isinstance(player.get("number"), int):
                continue
            for n, point in enumerate(row_points(player, field, rules)):
                number = player["number"] + n
                drawn = number + rules["awayNumberOffset"] if player.get("team") == "away" else number
                players[(player.get("team"), number)] = {
                    "at": point,
                    "label": ("a%d" % drawn) if player.get("team") == "away" else ("h%d" % drawn),
                    "name": player.get("name") if (player.get("count") or 1) == 1 else None,
                }
        for i, cone in enumerate(phase.get("cones") or []):
            if not isinstance(cone, dict):
                continue
            for n, point in enumerate(row_points(cone, field, rules)):
                key = (cone.get("id") or "cone-%d-%d" % (index, i), n)
                cones[key] = point
        for i, net in enumerate(phase.get("nets") or []):
            if not isinstance(net, dict):
                continue
            point = resolve_zone(net.get("at"), rules)
            if point:
                nets[net.get("id") or "net-%d-%d" % (index, i)] = point
        if phase.get("ball") is not None:
            ball = phase["ball"]

    return players, cones, nets, ball


def ball_point(ball, players, rules):
    """Where the ball roughly is, and whose it is.

    The app places it off the carrier's foot on the side the play came from or is going to, which
    this cannot know and does not try to: on the carrier is close enough to tell whether the right
    player has it.
    """
    if not isinstance(ball, dict):
        return None, None
    if "at" in ball:
        return resolve_zone(ball["at"], rules), None
    key = "carriedBy" if "carriedBy" in ball else "passTo" if "passTo" in ball else None
    if key is None:
        return None, None
    owner = (ball.get("team") or "home", ball.get(key))
    player = players.get(owner)
    return (player["at"] if player else None), owner


def draw(phases, index, field, rules):
    players, cones, nets, ball = fold(phases, index, field, rules)
    grid = blank_pitch()
    taken = {}
    collisions = []

    # Least important first, so a player drawn later wins the cell over the cone he is standing at
    marks = [(point, "N") for point in nets.values()]
    marks += [(point, "c") for point in cones.values()]
    marks += [(p["at"], p["label"]) for p in players.values()]

    ball_at, owner = ball_point(ball, players, rules)
    if ball_at:
        marks.append((ball_at, "o"))

    owner_label = players[owner]["label"] if owner and owner in players else None

    for point, label in marks:
        cell = to_cell(point)
        sitting = taken.get(cell)
        # The ball sharing a cell with the player carrying it is the drill working, not a collision -
        # and the player is the one worth seeing, so the ball gives up the cell rather than drawing
        # over him. Plotted on top first, which hid the carrier and left the picture a player short.
        if sitting and {sitting, label} == {"o", owner_label}:
            continue
        if sitting:
            collisions.append("%s and %s" % (sitting, label))
        taken[cell] = label
        grid[cell[0]][cell[1]] = pad(label)

    lines = ["   (attacking end - home attacks upward)"]
    lines += ["".join(row) for row in grid]
    lines.append("   (own end)")
    return "\n".join(lines), collisions, players, ball, owner_label


def describe(phases, index, field, rules):
    phase = phases[index]
    out = []
    head = "Phase %d of %d" % (index + 1, len(phases))
    if isinstance(phase, dict) and phase.get("role"):
        head += " - %s" % phase["role"]
    out.append(head)
    out.append("=" * len(head))

    if isinstance(phase, dict):
        if phase.get("caption"):
            out.append("Subtitle:  " + phase["caption"].replace("\n", "\n           "))
        if phase.get("say"):
            out.append("Narration: " + phase["say"])
        if phase.get("caption") or phase.get("say"):
            out.append("")

    picture, collisions, players, ball, owner_label = draw(phases, index, field, rules)
    out.append(picture)
    out.append("")

    labelled = sorted(
        "%s is %s" % (p["label"], p["name"]) for p in players.values() if p.get("name")
    )
    if labelled:
        out.append("Labels:    " + ", ".join(labelled))

    if isinstance(ball, dict):
        if "at" in ball:
            out.append("Ball:      at %s" % json.dumps(ball["at"]))
        elif owner_label:
            verb = "carried by" if "carriedBy" in ball else "played to"
            out.append("Ball:      %s %s" % (verb, owner_label))

    if isinstance(phase, dict):
        # Drawings are listed rather than plotted: they are filled shapes, and filling cells with
        # them would hide the players standing in them, which is the one thing the grid is for.
        for kind in ("arrows", "areas", "circles"):
            items = phase.get(kind)
            if items:
                out.append("%-10s %d, cleared when the board next moves"
                           % (kind.capitalize() + ":", len(items)))

    if collisions:
        out.append("Same cell: " + "; ".join(sorted(set(collisions)))
                   + " - too close to tell apart here, which the zoom may well fix")
    return "\n".join(out)


def main():
    parser = argparse.ArgumentParser(description="Draw a drill as text, phase by phase")
    parser.add_argument("drill", help="path to the drill JSON, or - for stdin")
    parser.add_argument("--phase", type=int, help="just this one, counting from 1")
    args = parser.parse_args()

    raw = sys.stdin.read() if args.drill == "-" else open(args.drill, encoding="utf-8").read()
    try:
        script = json.loads(raw)
    except json.JSONDecodeError as problem:
        print("Not valid JSON: %s" % problem, file=sys.stderr)
        return 1

    rules = drill_check.load_rules()
    phases = script.get("phases")
    if not isinstance(phases, list) or not phases:
        print("A drill is a JSON object with a `phases` array.", file=sys.stderr)
        return 1
    field = script.get("field")
    if field not in rules["fields"]:
        print("Unknown field %s, drawing it as %s." % (json.dumps(field), rules["fields"][0]),
              file=sys.stderr)
        field = rules["fields"][0]

    if script.get("title"):
        print("%s - %s, %d phases\n" % (script["title"], field, len(phases)))

    wanted = range(len(phases)) if args.phase is None else [args.phase - 1]
    for index in wanted:
        if not 0 <= index < len(phases):
            print("There is no phase %d." % (index + 1), file=sys.stderr)
            return 1
        print(describe(phases, index, field, rules))
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
