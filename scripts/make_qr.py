#!/usr/bin/env python3
"""Turn a drill JSON file into a QR code the Pocket Tactic Board app can scan.

Usage:
    python3 make_qr.py drill.json [-o drill.png] [--text-only]
    cat drill.json | python3 make_qr.py - -o drill.png

The drill is checked first, by `drill_check.py`, which refuses what the app would refuse. That used
to be left to the phone on the grounds that a second copy of the rules would drift from the
validator - which was right about the danger and wrong about the only cure. The checker carries no
copy: it reads `rules.json`, generated from the validator itself. What it cannot decide from that it
reports as advice, or leaves to the phone, which remains the authority.

`--no-check` skips it. The one limit nothing else can help with is still enforced here: how much a
QR code physically holds.

The payload format must match utils/drillLink.ts exactly:
    PTB1: + base64url( raw DEFLATE( json ) )
Raw DEFLATE means no zlib header, which is what fflate's deflateSync produces and what the app's
inflateSync expects. Hence wbits=-15.
"""

import argparse
import base64
import json
import os
import sys
import zlib

# segno is vendored beside this script rather than installed. Agents run in sandboxes that often have
# no network at all - ChatGPT's code interpreter is one - so `pip install` is not a step that can be
# relied on, and an install step is the thing most likely to stop someone using this at all. Putting
# the vendored copy first also means every agent runs the same encoder.
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, os.pardir, 'vendor'))
# And this script's own folder, so drill_check is importable however make_qr was invoked
sys.path.insert(0, HERE)

import drill_check

PREFIX = "PTB1:"
# Capacity of the largest QR version in byte mode at error correction L. Past this there is no
# bigger code to move up to, so the only honest answer is to refuse.
QR_BYTE_CEILING = 2953


def encode(script: dict) -> str:
    """JSON -> raw DEFLATE -> base64url -> prefixed code. Mirrors encodeDrillCode()."""
    raw = json.dumps(script, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    compressor = zlib.compressobj(9, zlib.DEFLATED, -15)
    packed = compressor.compress(raw) + compressor.flush()
    # The app's decoder tolerates missing padding, and '=' would only cost QR density.
    return PREFIX + base64.urlsafe_b64encode(packed).decode("ascii").rstrip("=")


def too_big_message(script: dict, code: str) -> str:
    """Say which phases to cut, rather than that it is too big."""
    phases = script.get("phases") or []
    weights = sorted(
        (
            (len(json.dumps(phase, separators=(",", ":"), ensure_ascii=False)), i + 1)
            for i, phase in enumerate(phases)
        ),
        reverse=True,
    )
    lines = [
        f"This drill encodes to {len(code)} characters and a QR code holds about {QR_BYTE_CEILING}.",
        "",
        "Largest phases, uncompressed:",
    ]
    lines += [f"  phase {number}: {size} characters" for size, number in weights[:5]]
    lines += [
        "",
        "Shorten the longest `say` text, or split the drill in two. Truncating the payload would",
        "produce a code that scans and then fails to read, which is worse.",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Make a scannable drill code")
    parser.add_argument("drill", help="path to the drill JSON, or - for stdin")
    parser.add_argument("-o", "--out", default="drill-code.png", help="where to write the PNG")
    parser.add_argument(
        "--text-only",
        action="store_true",
        help="print the code and skip the image, for pasting into the app instead",
    )
    parser.add_argument(
        "--no-check",
        action="store_true",
        help="encode without checking the drill first, leaving every mistake to the phone",
    )
    args = parser.parse_args()

    text = sys.stdin.read() if args.drill == "-" else open(args.drill, encoding="utf-8").read()
    try:
        script = json.loads(text)
    except json.JSONDecodeError as error:
        print(f"That is not valid JSON: {error}", file=sys.stderr)
        return 1
    if not isinstance(script, dict) or not isinstance(script.get("phases"), list):
        print("A drill is a JSON object with a `phases` array.", file=sys.stderr)
        return 1

    if not args.no_check:
        report = drill_check.check(script, drill_check.load_rules())
        if report.errors:
            # No code is written. Handing over one the app will refuse wastes a scan and the trust
            # that goes with it.
            print(drill_check.format_report(report), file=sys.stderr)
            print("\nNo code written. Fix the drill, or pass --no-check to encode it anyway.",
                  file=sys.stderr)
            return 1
        if report.warnings:
            print(drill_check.format_report(report))
            print()

    code = encode(script)
    if len(code) > QR_BYTE_CEILING:
        print(too_big_message(script, code), file=sys.stderr)
        return 1

    print(f"{len(code)} characters, {len(script['phases'])} phase(s).")

    if args.text_only:
        print(code)
        return 0

    try:
        import segno
    except ImportError:
        print(
            "Could not load the QR encoder. It lives in skill/vendor/segno, beside this script -\n"
            "if the skill was copied without that folder, copy it across and try again.\n"
            "Meanwhile --text-only prints the code itself.",
            file=sys.stderr,
        )
        return 1

    # error='l' for the most room; scale and border chosen so the code survives being photographed
    # off a laptop screen, which is how this is actually used.
    segno.make(code, error="l").save(args.out, scale=10, border=4)
    print(f"Wrote {args.out} - show it on screen and scan it from the app.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
