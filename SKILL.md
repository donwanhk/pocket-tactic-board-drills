---
name: pocket-tactic-board-drills
description: Write a coaching drill for the Pocket Tactic Board phone app and turn it into a QR code the app scans. Use when someone asks for a soccer or futsal drill, a training exercise, a tactical animation, or a drill video for that app.
---

# Writing drills for Pocket Tactic Board

The app is a tactic board that animates a drill and exports it as a narrated video. It runs on a
phone; nothing here can drive it. The job is to write a drill the app will accept, render it as a QR
code, and let the person scan it with the app's own scanner.

If they do not have the app yet, it is at **https://pocket-tactic-board.vercel.app/** — say so before
handing them a code they have no way to read.

**Read [FORMAT.md](FORMAT.md) before writing anything.** It is generated from the app's validator, so
it is the authority on limits, place names and vocabulary. Do not rely on what is remembered here.

## Ask before you write

"Give me a passing drill" is not enough to write one with. The same request produces a different
session for nine-year-olds and for a men's first team, and almost every choice in the drill — how far
apart to put the stations, how many players are involved, how many phases it runs for, which pitch it
is drawn on — follows from answers nobody has given yet.

So if the first message does not say, ask. Once, in one short message, for the handful that change
the drill:

- **The theme.** Passing, pressing, finishing, defending a cross: the one thing the session is for.
- **How many players**, and whether they come in pairs, threes or a full squad. This decides whether
  a drill is a 2v1 or a 3v3, and whether there are queues waiting their turn.
- **Their age and level.** A U9 session and an adult one share a diagram and nothing else: the
  distances, the number of things happening at once, and how much the opposition is allowed to do.
- **How long the session is**, and whether this is the whole thing or one exercise inside it.
- **The space and the equipment** — half a pitch, a futsal court, a corner of a gym; cones, balls,
  small goals. This picks `field` and decides whether there are goals to score in.

Then write the drill. Do not hold it hostage to the answers: if they say "just give me something",
make the ordinary choices — eight to twelve players, a club session of an hour, a small-sided grid —
**say which choices you made in one line**, and let the drill be the question. A drill they can see
and correct is worth more than an interview they have to sit through.

Ask again when the answers would change what you write and you still do not have them: a finishing
drill with no goal to shoot at, or a 3v3 for a group of five.

## The loop

1. Write the drill as JSON. Work from [examples/](examples/) — they are real drills, validated.
2. `python3 scripts/drill_preview.py drill.json` — look at it before anybody else does.
3. `python3 scripts/make_qr.py drill.json -o drill-code.png`, which checks it and refuses to encode
   a drill the app would reject.
4. Show the person the PNG and tell them: **Menu → Scan a Drill Code**, then point the phone at it.
5. **Write out what is on the code**, phase by phase — see below.
6. They look at the board and say what is wrong. Change the JSON and make a new code.

Step 2 is the cheap one and it is worth doing every time. It draws each phase as a grid, which is
enough to see that the recovering defender went goal-side rather than sideways, that the queue is not
standing in the passing lane, and that the ball is with the player the narration says has it. Finding
that out from whoever scanned the code costs them a scan and a forty-second video.

## Always list the phases with the code

A QR code is unreadable to a person. Handing one over on its own asks them to scan, watch a
forty-second animation, and only then discover the narration is wrong. So print the contents
alongside it, read from the JSON you just wrote rather than from memory:

```
Phase 3 of 6 - execution
  Subtitle:  Past him, but not clear
  Narration: "Nine is past him on the left. The defender turns and runs - he is not finished yet."
  Movement:  9 carries the ball from the centre out to the left; 4 turns to chase; the keeper
             shifts across to cover the near post.
```

Give every phase, then the total length and the phase count.

**Name every player by the number the board draws**, which for the away team is not the number you
wrote — see FORMAT.md. Writing the listing is where that gets caught: if the movement line says 24
and the narration says "four", one of them is wrong, and it is almost always the narration.

**Movement describes the change into this phase**, because that is what its own narration is spoken
over. Writing it out this way is also the best check on the thing most easily got backwards: if a
phase's movement and its narration describe different moments, the drill is wrong and this is where
it shows.

The first phase has nothing moving into it - the board holds still while its words are read - so say
so rather than inventing movement for it.

Revising means a new code and another scan. That is the cost of needing no setup, and scanning takes
about two seconds, so do not hesitate to iterate — a drill is usually wrong the first time.

The camera is the only way into the app, so a code that will not scan has to be made easier to
read rather than worked around: show it larger, or shorten the narration so the code is less dense.
`--text-only` prints the payload, which is for checking your own work rather than for the person.

## What is checked, and what is not

`make_qr.py` checks the drill before it encodes it, and writes no code if the app would refuse one.
It works from `rules.json`, which the app generates from the validator itself, so what it refuses is
what the phone refuses: unknown place names, a colour outside the palette, a caption over length, a
ball given to a player who is not on the pitch, a player asked to cover more ground in two seconds
than anyone can run. The message is the app's own. Fix the JSON and run it again.

It also offers advice, which never stops a code being made: a key it does not recognise (the app
ignores those rather than rejecting them, so a misspelt `players` renders a phase with nobody in it),
narration naming an away player by the number on the drill rather than the one on his shirt, a team
called by a colour, "full pitch" over a drill that uses a corner of one, opposition that never moves.
Each of those got through review on a real drill.

What is still not checked is whether the drill is any good. Nothing here can see the board, and the
grid from `drill_preview.py` is coarse on purpose — it cannot show the zoom, which side of a player's
feet the ball sits on, or anything drawn. **The phone is the authority and the coach is the judge.**
If the person reports that the app rejected a drill anyway, ask them to read the message out and fix
the JSON rather than guessing.

Two limits worth respecting without being told: at most 19 phases, and a code that will not fit in a
QR is refused with a list of the longest phases.

## Writing a drill that is worth watching

### How a phase plays

**Each phase says only what changed.** Players, cones, nets and the ball carry forward, so a player
written once stays put until a later phase moves him - there is no need to repeat everyone every
time. Nothing can be taken off the board either: walk a player to the touchline rather than trying to
remove him. Moving a cone or a net needs the same `id` in both phases, or the second phase adds a
second cone beside the first.

**`say` belongs to the movement that arrives at it.** A phase's narration is spoken while the board
changes *into* that phase, so the words and the movement they describe play together. Put "he drives
at the defender" on the phase whose positions show him having driven, not on the one where he is
still standing still. This is the single easiest thing to get backwards, and when it is backwards
every line is a phase early, describing something the viewer has not reached yet.

The first phase is the exception, because nothing moves into it: the board holds while its words are
read. That is what makes it the right place for the title, the aim and the setup.

**Everything in a phase happens at once.** A phase is a moment, not a step in a queue: every player it
lists moves over the same seconds, while its narration plays. So things that happen together belong
in one phase — a defender pressing the ball and his partner sliding across to cover is one movement
by two players, and splitting it over two phases makes a defence shuffle like falling dominoes. Start
a new phase when the next thing genuinely waits on this one: the pass cannot leave until the run has
been made.

**Everyone travels in a straight line.** Between two phases a marker moves straight from one position
to the next at a steady pace, so the position you give it is the whole shape of its run. A recovering
defender needs the point he would really run to — goal-side and inside, cutting off where the ball is
going — because sending him to where the winger is standing walks him sideways across the pitch
instead. If a run genuinely has to bend, that is either a phase boundary or a curved arrow drawn over
it.

**And not far.** That straight line is always covered in two seconds, whatever the narration on it
says, so the distance between two positions is a speed. Twelve metres is a convincing run; anything
past eighteen is rejected outright, because it is quicker than a sprinter from a standing start. On a
full pitch that is about an eighth of its length — so a player crossing from one third to another
needs two or three phases, and a drill whose action covers real ground is a longer drill rather than
a faster one. FORMAT.md has the figures.

### Who is on the board

**Defenders have to move.** A drill where the opposition stands still while the attack runs around
them looks broken, and any coaching point about committing a defender or beating a press is hollow
without one that reacts. Give them a recovery run, a step across, a drop. It is the difference
between a diagram and a drill.

**Away numbers are not what they look like.** An away player written as 4 is drawn as 24, so
narration that says "four" is describing a disc nobody can see. The ball is the same trap from the
other side: `carriedBy` defaults to the home team, so `{ "carriedBy": 4 }` gives the ball to home 4
even when the only 4 you placed was an away one. Say `{ "carriedBy": 4, "team": "away" }`. The app
rejects a ball given to a player who is not on the pitch, so the common version of this mistake comes
back as an error rather than a drill that quietly contradicts itself — but the version where both
teams have that number does not, and only reading the listing will catch it.

**Do not put a player on a net.** Nets draw underneath players, so a keeper placed on
`attacking-goal` makes the goal vanish. Offset one of them.

**Label only what cannot be said without one, and keep it short.** A name is drawn under the disc and
is wider than it, so two labelled players who look well apart can still have their words overlapping -
three labels on a board is usually plenty and five is a crowd. A keeper in his goal and the only
defender in the picture do not need telling apart; the two runners whose timing is the whole drill do.
Eight characters is the hard limit and nowhere near tight enough to save you: "Near" and "Far" stay
legible beside each other where "Target" and "Keeper" do not.

**Never name a team by its colour.** The coach picks the team colours in the app, so a drill that
says "the blues" is describing a board you cannot see. Out of the box the home team is red and the
away team is **grey** — the only blue on the pitch is the away goalkeeper — so a guess is usually
wrong twice over. A drill is written from the home team's point of view, so "ours" and "theirs" read
naturally and stay true whatever the coach has chosen; numbers work too. Cone colours are different:
the drill sets those itself, so naming them is telling the truth.

**Describe the ground the drill actually uses.** The board zooms to fit the drill, so a viewer
watching a 3v3 in a grid never sees the rest of the pitch. A setup line that says "full pitch" over a
view of one channel contradicts what is on screen. Say the working area — "a thirty by twenty-five
grid", "the right-hand channel between the halfway line and the box" — and leave `field` to decide
which pitch is drawn underneath it. Say "full pitch" only when the drill really does span one, which
the zoom will then confirm by staying at 1.

**Send the queue outwards.** The players waiting their turn are scenery with legs: they must not
stand in a passing lane, crowd the cones, or be mistaken for someone in the drill. Point each queue's
`direction` away from the shape the cones make — down from a station at the bottom, up from one at
the top — so the working area is the players, the cones mark its edge, and the queues sit beyond
that. The board frames the whole drill, queues included, so a queue pointed the wrong way does not
just look crowded, it zooms the drill out to fit.

**Spacing that is accurate can still look wrong.** Markers hold a constant size on screen, so on a
full pitch a player disc covers nearly eight metres. A queue three metres apart is correctly placed
and visually a single blob. FORMAT.md has the figures per field; the answer is to zoom in, not to
space players further apart than real life.

**Keep narration short.** It is spoken aloud, and phase length is derived from how long the words
take to say. Two sentences per phase is usually plenty.

### What the voice says

**Narrate the drill, not the board.** Say what the players are being asked to do and why it works,
not what the picture contains. "Twenty-eight is the nearest defender and twenty-four is the cover
inside him" describes two discs; "don't let the press set — play inside before he arrives" coaches
the exercise. The viewer can see where everyone is standing. Numbers still belong in the narration,
but inside a coaching sentence rather than as a roll call.

## Drawing on the board

A drill can draw as well as place. Everything drawn belongs to the phase that drew it and is gone as
soon as the board moves on, so the way to use it is: draw the plan, let it be read, then run the move
on a clean board. Put a shape on every phase only when it marks the working area for the whole drill.

**Draw it on the setup phase.** Nothing moves into the opening phase, so its board - drawings
included - is held for both the title and the first instruction, which is two captions' worth of
reading time. A shape put on a later phase appears only as that phase arrives, which is usually one
beat after the words that referred to it.

**Solid arrow is the ball, dotted is a player.** A pass, a shot or a clearance is solid; a run made
off the ball is dotted. Two different things sharing one symbol is the fastest way to make a board
unreadable.

**Curve the arrow that goes round something.** `curve` bows it as a fraction of its own length,
signed, so `0.3` bends one way and `-0.3` the other. A run that goes outside a defender drawn
straight reads as a pass straight through him.

**Yellow or black, and nothing else.** Those are the pen's two colours, so they are the only two a
drill can draw in; anything else is rejected. Yellow reads on grass, black reads on a futsal floor.

**A box marks a playing area, a ring marks space.** `areas` for a grid, a channel or a zone to stay
inside; `circles` for the space that matters — the room behind a defence, the gap a run is aimed at.
Both are filled shapes rather than outlines, so keep them big enough to read and few enough to look
deliberate.

**Cones mark the things that do not move**: a station, a gate, where a queue starts, where a run
turns. Five colours, and naming them in the narration is fair — the drill set them, so "start at the
blue cone" is true on anybody's board.

**Do not add nets at the far ends.** Every pitch already draws two goals. A net placed there is
furniture on top of a goal that exists, and it hides the one underneath. Add nets only for goals the
pitch does not have: small goals in a grid, a counter-goal, a target gate.

## What the board does for you

Four things are worked out from the drill rather than written into it. Knowing which they are saves
you fighting them.

**The zoom.** The board frames the whole drill — players, cones, nets, ball and drawings, across
every phase — and holds that frame for the length of it. A ten-metre passing square on a futsal court
fills the screen. So write the real distances: three metres is three metres, and the zoom is what
makes them readable.

**Which side of his feet the ball sits on.** A ball just received sits on the side it came from, one
about to be played sits toward whoever gets it next, and one being carried sits ahead of the run. It
follows from the phases either side, and it is what makes a pass look struck rather than drifting.

**Stepping a player off a cone.** Nobody stands on a cone, so a player placed at one steps aside, into
the middle of whatever shape the cones make. `stand: "outside"` on the cone reverses it. Place the
player at the cone and leave the rest alone.

**A label, once given, lasts.** Naming a player in the phase that first places him is enough; moving
him later does not wipe it.

## The subtitle and the voice

`say` is spoken and `caption` is shown. They can differ, and choosing well is most of what makes a
drill watchable.

**The caption is a label, not a second narration.** Three to six words naming the moment — "Inside
to six", "Switch to the free side". Reading a sentence while listening to a different one is reading
twice, and the subtitle is the one the viewer did not ask for.

**Leave `caption` out when the narration is already short.** The subtitle then *is* the narration,
and its words light up one at a time in time with the voice, which is the effect at its best. A
caption that differs from the spoken line does not light up at all — it is shown whole, because the
voice's position in one sentence says nothing about where to be in another.

**Where to put it.** `bottom` is the default and usually right: home attacks up the screen, so the
play lives in the top half and the bottom is the clear end. Use `top` when the drill works in your
own defensive third, which is drawn low. The rule is simply to put the words at the end of the pitch
where nothing is happening.

**`middle` is for the closing coaching points, and little else.** By then the drill has been watched
and the text is the content rather than a label on it. Everywhere else it covers the board — and it
covers it in the middle, where a centre midfielder stands. The opening title phase is the trap worth
naming: it is static, which makes `middle` tempting, but it is also the phase whose whole job is
showing the starting shape, and a caption across the centre circle hides whoever is standing there.

**Coaching points read better as a list.** Line breaks in a caption are kept, and a multi-line
subtitle is ranged left rather than centred. Three bullets of five or six words fit the 120
characters, and they stay on screen whole while the voice reads the same points as a sentence:

```json
{
  "role": "coaching",
  "at": "middle",
  "caption": "Coaching points\n- Scan before it arrives\n- Touch away from the press\n- Switch low and firm",
  "say": "Coaching points. Scan before it arrives, take your touch away from the press, and switch it low and firm."
}
```

## A reasonable shape for a drill

Open with a `setup` phase that places everyone and says what the exercise is. Then two to five
`execution` phases carrying the movement. Close with a `coaching` phase that names the point to take
away. Six phases is a comfortable video; nineteen is the ceiling and far more than anyone watches.
