# Pocket Tactic Board — drill and team skill

Ask an AI assistant for a soccer or futsal drill. It writes the drill and shows you a QR code.
Scan that code with the **Pocket Tactic Board** app and the drill appears on your board, ready to
animate and export as a narrated video.

It does the same for your squad. Paste your player list in whatever shape you have it, and the
assistant hands back a **team code** — scan that under **My Team** and the whole squad arrives at
once, instead of being typed in one player at a time.

**[⬇ Download the latest release](https://github.com/donwanhk/pocket-tactic-board-drills/releases/latest)**
— `pocket-tactic-board-drills.zip`

You will also need the app itself: **<https://pocket-tactic-board.vercel.app/>**

Python 3 is the only requirement. There is nothing to install: the QR encoder ships inside.

---

## Install it

Pick whichever assistant you use. You only do this once.

### Claude Code

Unzip it into your skills folder:

```bash
unzip pocket-tactic-board-drills.zip -d ~/.claude/skills/
```

That gives you `~/.claude/skills/pocket-tactic-board-drills/`. Claude finds it on the next session.
Use `.claude/skills/` inside a project instead if you only want it there.

### Claude.ai

1. Open **Settings → Capabilities → Skills**
2. **Upload skill**, choose the zip, and enable it

Skills need a paid plan. The menu has moved before — if it is not under Capabilities, look under
Features.

### ChatGPT

ChatGPT has no skills system, so the files travel with the conversation.

1. Start a chat where the **code interpreter / Data Analysis** tool is available
2. Attach `pocket-tactic-board-drills.zip`
3. Say: *"Unzip this, read SKILL.md and FORMAT.md, and follow them."*

A Custom GPT with these files as Knowledge also works and saves re-attaching, but there are standing
reports of code interpreter failing for non-creator accounts once knowledge files are added. If you
hit that, attach the zip in a normal chat instead.

### DeepSeek Harness

Unzip it into the shared agents root:

```bash
unzip pocket-tactic-board-drills.zip -d ~/.agents/skills/
```

The harness scans `~/.agents/skills` for directory bundles, so it is picked up without a restart —
its watcher notices the new folder. `~/.dsh/skills` works too, and `.agents/skills` or `.dsh/skills`
inside a project limits it to that repo.

Note that `~/.agents/skills` is a shared root rather than a DeepSeek-specific one, so a skill unzipped
there can serve more than one tool.

### Anything else

The requirements are only: read a folder, run a Python script, show an image. Point your assistant at
`SKILL.md`.

---

## Use it

> *"A 1v1 to goal for futsal, with a defender who recovers."*

The assistant writes the drill, checks it, runs `scripts/make_qr.py`, and shows you a QR code. In
the app: **☰ → Scan a Drill Code**, point the camera at it, then **Load drill**.

Each revision is a new code. Say what is wrong, scan again — it takes a couple of seconds.

For a squad:

> *"Here is my team list, turn it into a team code."* — then paste it.

Same idea, different code. In the app: **My Team → the scan button beside Add Player**.

The code holds your players' names, and whatever you paste reaches whichever assistant you are
using. First names or initials are usually enough for a tactics board, and the skill will suggest
them — but it is your squad, so it writes the list the way you ask.

---

## What is in here

```
SKILL.md        what the assistant reads first
FORMAT.md       the drill format, generated from the app's own validator
TEAM-FORMAT.md  the team format, generated the same way
rules.json      the same limits and place names, for the scripts rather than the reader
team-rules.json the team limits, likewise
examples/       nine worked drills, all validated
examples/teams/ two worked squads
scripts/        make_qr.py       - drill or team JSON to a scannable code
                drill_check.py   - refuses what the app would refuse, before a code is made
                team_check.py    - the same, for a squad
                drill_preview.py - draws each phase as a grid, to look at before anyone scans it
vendor/segno/   the QR encoder, vendored so there is no install step
```

`FORMAT.md` and `rules.json` are generated rather than written by hand, so neither can drift from the
validator that judges the drills — and the checker works from the generated file rather than from a
copy of the rules, which is what lets it refuse a drill without ever disagreeing with the app.

The encoder is [segno](https://github.com/heuer/segno) by Lars Heuer, BSD-3-Clause — see
`vendor/segno/LICENSE`. It is vendored because some sandboxes have no network, so `pip install`
cannot be relied on.
