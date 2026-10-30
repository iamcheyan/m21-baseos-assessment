#!/usr/bin/env python3
"""Parse and validate docs/m21-round2/SPEC.md.

Two independent YAML readers are used on purpose:

  * PyYAML, when importable (full YAML);
  * a bundled narrow reader that understands exactly the subset SPEC.md uses.

Both must produce the same object graph, and the result must satisfy the
profile schema below.  That catches "the file parses for one reader only",
which is the failure mode a hand-written spec usually has.

Usage:
    parse_spec.py                       validate docs/m21-round2/SPEC.md
    parse_spec.py --spec PATH           validate another file
    parse_spec.py --emit-pocketjs OUT   also write the PocketJS runtime profile
    parse_spec.py --quiet               exit status only
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
DEFAULT_SPEC = REPO / "docs" / "m21-round2" / "SPEC.md"

# ---------------------------------------------------------------- narrow reader

TRUE = {"true", "yes", "on"}
FALSE = {"false", "no", "off"}
NULL = {"null", "~", ""}


class NarrowError(ValueError):
    pass


def _strip_comment(line: str) -> str:
    out, quote, i = [], None, 0
    while i < len(line):
        ch = line[i]
        if quote:
            out.append(ch)
            if ch == quote:
                quote = None
        elif ch in "\"'":
            quote = ch
            out.append(ch)
        elif ch == "#" and (i == 0 or line[i - 1] in " \t"):
            break
        else:
            out.append(ch)
        i += 1
    return "".join(out).rstrip()


def _scalar(text: str):
    text = text.strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in "\"'":
        return text[1:-1]
    low = text.lower()
    if low in NULL:
        return None
    if low in TRUE:
        return True
    if low in FALSE:
        return False
    if re.fullmatch(r"-?\d+", text):
        return int(text)
    if re.fullmatch(r"-?\d+\.\d+", text):
        return float(text)
    if text.startswith("[") and text.endswith("]"):
        body = text[1:-1].strip()
        if not body:
            return []
        return [_scalar(part) for part in _split_flow(body)]
    if text.startswith("{") and text.endswith("}"):
        body = text[1:-1].strip()
        if not body:
            return {}
        items = {}
        for part in _split_flow(body):
            key, _, value = part.partition(":")
            if not _:
                raise NarrowError(f"bad flow mapping entry: {part!r}")
            items[_scalar(key)] = _scalar(value)
        return items
    return text


def _split_flow(body: str):
    parts, buf, depth, quote = [], [], 0, None
    for ch in body:
        if quote:
            buf.append(ch)
            if ch == quote:
                quote = None
        elif ch in "\"'":
            quote = ch
            buf.append(ch)
        elif ch in "[{":
            depth += 1
            buf.append(ch)
        elif ch in "]}":
            depth -= 1
            buf.append(ch)
        elif ch == "," and depth == 0:
            parts.append("".join(buf).strip())
            buf = []
        else:
            buf.append(ch)
    if "".join(buf).strip():
        parts.append("".join(buf).strip())
    return parts


def _split_inline_map(text: str):
    items, buf, depth, quote = {}, [], 0, None
    fields = []
    for ch in text:
        if quote:
            buf.append(ch)
            if ch == quote:
                quote = None
        elif ch in "\"'":
            quote = ch
            buf.append(ch)
        elif ch in "[{":
            depth += 1
            buf.append(ch)
        elif ch in "]}":
            depth -= 1
            buf.append(ch)
        elif ch == "," and depth == 0:
            fields.append("".join(buf).strip())
            buf = []
        else:
            buf.append(ch)
    if "".join(buf).strip():
        fields.append("".join(buf).strip())
    for field in fields:
        key, sep, value = field.partition(":")
        if not sep:
            raise NarrowError(f"bad inline mapping entry: {field!r}")
        items[key.strip()] = _scalar(value)
    return items


def read_yaml_narrow(text: str):
    lines = []
    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        body = _strip_comment(raw[indent:])
        if body:
            lines.append((indent, body))

    pos = 0

    def block(indent: int):
        nonlocal pos
        if pos >= len(lines):
            return None
        if lines[pos][1].startswith("- "):
            return sequence(indent)
        return mapping(indent)

    def mapping(indent: int):
        nonlocal pos
        out = {}
        while pos < len(lines):
            cur_indent, body = lines[pos]
            if cur_indent < indent:
                break
            if cur_indent > indent:
                raise NarrowError(f"unexpected indent {cur_indent} at {body!r}")
            if body.startswith("- "):
                break
            key, sep, rest = body.partition(":")
            if not sep:
                raise NarrowError(f"expected 'key: value', got {body!r}")
            key = key.strip().strip("\"'")
            rest = rest.strip()
            pos += 1
            if rest:
                if rest.startswith("{") and rest.endswith("}"):
                    out[key] = _split_inline_map(rest[1:-1])
                else:
                    out[key] = _scalar(rest)
            else:
                nxt = lines[pos][0] if pos < len(lines) else -1
                if nxt > cur_indent:
                    out[key] = block(nxt)
                elif nxt == cur_indent and pos < len(lines) and lines[pos][1].startswith("- "):
                    out[key] = sequence(cur_indent)
                else:
                    out[key] = None
        return out

    def sequence(indent: int):
        nonlocal pos
        out = []
        while pos < len(lines):
            cur_indent, body = lines[pos]
            if cur_indent != indent or not body.startswith("- "):
                break
            item = body[2:].strip()
            pos += 1
            if item.startswith("{") and item.endswith("}"):
                out.append(_split_inline_map(item[1:-1]))
            elif item:
                key, sep, rest = item.partition(":")
                if sep and re.fullmatch(r"[A-Za-z_][\w.-]*", key.strip()):
                    entry = {}
                    if rest.strip():
                        entry[key.strip()] = _scalar(rest)
                    else:
                        nxt = lines[pos][0] if pos < len(lines) else -1
                        entry[key.strip()] = block(nxt) if nxt > indent else None
                    nxt_indent = lines[pos][0] if pos < len(lines) else -1
                    if nxt_indent > indent:
                        entry.update(mapping(nxt_indent))
                    out.append(entry)
                else:
                    out.append(_scalar(item))
            else:
                nxt = lines[pos][0] if pos < len(lines) else -1
                out.append(block(nxt) if nxt >= 0 else None)
        return out

    value = block(lines[0][0]) if lines else None
    if pos != len(lines):
        raise NarrowError(f"unconsumed input at {lines[pos]!r}")
    return value


# ------------------------------------------------------------------- structure

def split_frontmatter(text: str):
    if not text.startswith("---\n"):
        raise SystemExit("SPEC.md must start with a '---' frontmatter fence")
    end = text.find("\n---\n", 3)
    if end < 0:
        raise SystemExit("SPEC.md frontmatter is not closed with '---'")
    return text[4:end], text[end + 5:]


def read_yaml_pyyaml(text: str):
    import yaml  # noqa: F401  (optional dependency)
    return yaml.safe_load(text)


REQUIRED_TOP = [
    "schema", "revision", "identity", "soc", "kernel", "boot", "display",
    "input", "audio", "power", "storage", "network", "capabilities",
    "pocketjs", "verified_on_device", "risks",
]
CAPABILITY_STATES = {"yes", "no", "unknown"}
POCKET_CAPABILITY_IDS = {
    "input.analog.left", "input.analog.right", "input.buttons", "input.cursor",
    "input.ime", "input.pointer", "input.text", "input.touch",
    "input.touch.auxiliary", "ui.compositor-surfaces", "ui.physics",
    "audio.pcm", "media.playback", "io.offload", "net.http", "link.companion",
    "system.wifi", "camera.qr", "system.agent", "data.sqlite", "data.fs",
    "host.clipboard", "display.viewport.live", "display.auxiliary",
    "text.glyphs.baked", "text.glyphs.streamed", "text.glyphs.runtime",
    "text.layout.native", "text.layout.offload", "camera.photo",
}
TARGET_FORMS = {"takeover", "window", "widget", "kiosk", "embedded"}
PRESENTATIONS = {"fill", "fit", "integer-fit", "native", "stretch"}


def validate(spec: dict) -> list[str]:
    errors: list[str] = []

    def need(cond, msg):
        if not cond:
            errors.append(msg)

    for key in REQUIRED_TOP:
        need(key in spec, f"missing top-level key: {key}")

    need(spec.get("schema") == "pjos.device-profile/2",
         "schema must be 'pjos.device-profile/2'")
    need(spec.get("identity", {}).get("id") == "m21", "identity.id must be 'm21'")

    display = spec.get("display", {})
    need(display.get("physical_width") == 750, "display.physical_width must be 750")
    need(display.get("physical_height") == 1334, "display.physical_height must be 1334")
    need(display.get("backend") in {"drm", "fbdev"}, "display.backend must be drm|fbdev")
    need(display.get("refresh_hz") == 60, "display.refresh_hz must be 60")

    kernel = spec.get("kernel", {})
    need(kernel.get("source") in {"vendor", "mainline", "custom"},
         "kernel.source must be vendor|mainline|custom")
    need(isinstance(kernel.get("version"), str), "kernel.version must be a string")

    caps = spec.get("capabilities", {})
    need(isinstance(caps, dict) and caps, "capabilities must be a non-empty mapping")
    for name, state in caps.items():
        need(state in CAPABILITY_STATES,
             f"capabilities.{name} must be one of {sorted(CAPABILITY_STATES)}")

    touch = spec.get("input", {}).get("touch", {})
    if caps.get("input.touch") == "yes":
        need(touch.get("present") is True, "input.touch=yes requires input.touch.present=true")
        need(touch.get("protocol") == "evdev_mt_b",
             "input.touch.protocol must be evdev_mt_b")

    verified = spec.get("verified_on_device", {})
    need(isinstance(verified.get("items"), list) and verified["items"],
         "verified_on_device.items must be a non-empty list")
    for item in verified["items"]:
        need(isinstance(item.get("done"), bool),
             f"verified_on_device item {item.get('item')!r} needs a boolean 'done'")

    risks = spec.get("risks", [])
    need(isinstance(risks, list) and risks, "risks must be a non-empty list")
    for risk in risks:
        need(risk.get("level") in {"low", "medium", "high"},
             f"risk {risk.get('id')} level must be low|medium|high")
        need(bool(risk.get("text")), f"risk {risk.get('id')} needs text")

    profile = spec.get("pocketjs", {})
    need(profile.get("form") in TARGET_FORMS, "pocketjs.form must be a PocketJS target form")
    need(isinstance(profile.get("tick_hz"), int) and 1 <= profile["tick_hz"] <= 240,
         "pocketjs.tick_hz must be 1..240")
    view = profile.get("display", {})
    physical = view.get("physical_viewport")
    need(physical == [750, 1334], "pocketjs.display.physical_viewport must be [750, 1334]")
    logicals = view.get("logical_viewports") or []
    need(bool(logicals), "pocketjs.display.logical_viewports must not be empty")
    density = view.get("raster_density")
    need(isinstance(density, int) and 1 <= density <= 255,
         "pocketjs.display.raster_density must be 1..255")
    for mode in view.get("presentations") or []:
        need(mode in PRESENTATIONS, f"unknown presentation mode {mode!r}")
    p_caps = profile.get("capabilities") or []
    need(bool(p_caps), "pocketjs.capabilities must not be empty")
    for cap in p_caps:
        need(cap in POCKET_CAPABILITY_IDS, f"unregistered PocketJS capability {cap!r}")
    if "input.touch" in p_caps:
        for size in logicals:
            need(size[0] <= 1024 and size[1] <= 1024,
                 f"logical viewport {size} exceeds the 10-bit touch frame encoding (max 1024)")
    for size in logicals:
        need(size[0] <= physical[0] and size[1] <= physical[1],
             f"logical viewport {size} exceeds the physical viewport")
        need(physical[0] % size[0] == 0 and physical[1] % size[1] == 0,
             f"logical viewport {size} does not divide the physical viewport evenly")

    return errors


def to_pocketjs_profile(spec: dict) -> dict:
    profile = spec["pocketjs"]
    view = profile["display"]
    return {
        "id": profile.get("runtime_target_suggested", spec["identity"]["id"]),
        "platform": "linux",
        "form": profile["form"],
        "tickHz": profile["tick_hz"],
        "display": {
            "physicalViewport": view["physical_viewport"],
            "logicalViewports": view["logical_viewports"],
            "rasterDensity": view["raster_density"],
            "presentations": view["presentations"],
        },
        "capabilities": profile["capabilities"],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--spec", type=Path, default=DEFAULT_SPEC)
    ap.add_argument("--emit-pocketjs", type=Path,
                    help="write the PocketJS runtime profile (JSON) here")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    text = args.spec.read_text(encoding="utf-8")
    front, body = split_frontmatter(text)

    narrow = read_yaml_narrow(front)
    readers = {"narrow": narrow}
    try:
        readers["pyyaml"] = read_yaml_pyyaml(front)
    except ImportError:
        readers["pyyaml"] = None

    print(f"spec      : {args.spec}")
    print(f"frontmatter: {len(front.splitlines())} lines, body: {len(body.splitlines())} lines")
    for name, value in readers.items():
        label = "not installed" if value is None else ("ok" if value == narrow else "MISMATCH")
        print(f"reader {name:<8}: {label}")
    if readers["pyyaml"] is not None and readers["pyyaml"] != narrow:
        print("readers disagree; refusing to continue", file=sys.stderr)
        return 2

    errors = validate(narrow)
    if errors:
        print(f"\n{len(errors)} schema error(s):")
        for err in errors:
            print(f"  - {err}")
        return 1

    spec = narrow
    caps = spec["capabilities"]
    counts = {state: sum(1 for v in caps.values() if v == state) for state in sorted(CAPABILITY_STATES)}
    print(f"profile   : {spec['identity']['model']} ({spec['identity']['id']})"
          f"  soc={spec['soc']['name']}  kernel={spec['kernel']['version']}")
    print(f"display   : {spec['display']['physical_width']}x{spec['display']['physical_height']}"
          f"@{spec['display']['refresh_hz']}Hz backend={spec['display']['backend']}")
    print(f"pocketjs  : form={spec['pocketjs']['form']}"
          f" logical={spec['pocketjs']['display']['logical_viewports']}"
          f" density={spec['pocketjs']['display']['raster_density']}")
    print(f"capabilities: {counts['yes']} yes / {counts['no']} no / {counts['unknown']} unknown")
    todo = [i["item"] for i in spec["verified_on_device"]["items"] if not i["done"]]
    print(f"unverified: {len(todo)} item(s) still need hardware")
    print("schema    : OK")

    if args.emit_pocketjs:
        args.emit_pocketjs.write_text(
            json.dumps(to_pocketjs_profile(spec), indent=2) + "\n", encoding="utf-8")
        print(f"pocketjs profile written to {args.emit_pocketjs}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
