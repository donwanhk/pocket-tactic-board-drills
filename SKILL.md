---
name: pocket-tactic-board-drills
description: Write a coaching drill for the Pocket Tactic Board phone app and turn it into a QR code the app scans. Use when someone asks for a soccer or futsal drill, a training exercise, a tactical animation, or a drill video for that app.
---

# Writing drills for Pocket Tactic Board

The app is a tactic board that animates a drill and exports it as a narrated video. It runs on a
phone; nothing here can drive it. The job is to write a drill the app will accept, render it as a QR
code, and let the person scan it with the app's own scanner.

**Read [FORMAT.md](FORMAT.md) before writing anything.** It is generated from the app's validator, so
it is the authority on limits, place names and vocabulary. Do not rely on what is remembered here.

## The loop

1. Write the drill as JSON. Work from [examples/](examples/) — they are real drills, validated.
2. `python3 scripts/make_qr.py drill.json -o drill-code.png`
3. Show the person the PNG and tell them: **Menu → Scan a Drill Code**, then point the phone at it.
4. They look at the board and say what is wrong. Change the JSON and make a new code.

Revising means a new code and another scan. That is the cost of needing no setup, and scanning takes
about two seconds, so do not hesitate to iterate — a drill is usually wrong the first time.

The camera is the only way into the app, so a code that will not scan has to be made easier to
read rather than worked around: show it larger, or shorten the narration so the code is less dense.
`--text-only` prints the payload, which is for checking your own work rather than for the person.

## What is not checked here

`make_qr.py` does not validate the drill. The real validator lives in the app and judges it on
arrival, so **mistakes surface on the phone, not in this conversation.** If the person reports that
the app rejected a drill, ask them to read the message out — it names the problem precisely — and fix
the JSON rather than guessing.

The two limits worth respecting without being told: at most 19 phases, and a code that will not fit
in a QR is refused with a list of the longest phases.

## Writing a drill that is worth watching

**Each phase is the whole board, not a change to it.** Every player who is still on the pitch must
appear in every phase. A player omitted from a phase has walked off.

**`say` belongs to the movement that follows it.** A phase's narration is spoken while the board
changes into the *next* phase. Put "he drives at the defender" on the phase where he is still
standing still, not on the one where he has arrived. This is the single easiest thing to get
backwards, and when it is backwards every line describes something the viewer has already seen.

**Defenders have to move.** A drill where the opposition stands still while the attack runs around
them looks broken, and any coaching point about committing a defender or beating a press is hollow
without one that reacts. Give them a recovery run, a step across, a drop. It is the difference
between a diagram and a drill.

**Do not put a player on a net.** Nets draw underneath players, so a keeper placed on
`attacking-goal` makes the goal vanish. Offset one of them.

**Spacing that is accurate can still look wrong.** Markers hold a constant size on screen, so on a
full pitch a player disc covers nearly eight metres. A queue three metres apart is correctly placed
and visually a single blob. FORMAT.md has the figures per field; the answer is to zoom in, not to
space players further apart than real life.

**Keep narration short.** It is spoken aloud, and phase length is derived from how long the words
take to say. Two sentences per phase is usually plenty.

## A reasonable shape for a drill

Open with a `setup` phase that places everyone and says what the exercise is. Then two to five
`execution` phases carrying the movement. Close with a `coaching` phase that names the point to take
away. Six phases is a comfortable video; nineteen is the ceiling and far more than anyone watches.
