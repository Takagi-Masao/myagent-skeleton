from __future__ import annotations

import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

DRAWING = {"circle", "path", "ellipse", "rect", "line", "polygon", "polyline"}


def local(tag: str) -> str:
    return tag.split("}")[-1]


def fail(message: str) -> int:
    print(f"FAIL quest02: {message}")
    return 1


def size_of(root: ET.Element) -> tuple[float, float] | None:
    view_box = root.get("viewBox")
    if view_box:
        parts = view_box.replace(",", " ").split()
        if len(parts) == 4:
            try:
                return float(parts[2]), float(parts[3])
            except ValueError:
                return None
    try:
        width = float(re.sub(r"[^0-9.]", "", root.get("width", "")) or 0)
        height = float(re.sub(r"[^0-9.]", "", root.get("height", "")) or 0)
    except ValueError:
        return None
    return (width, height) if width and height else None


def main() -> int:
    path = Path("pelican.svg")
    if not path.is_file():
        return fail("pelican.svg not found")
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError as exc:
        return fail(f"invalid SVG/XML: {exc}")

    if local(root.tag) != "svg":
        return fail("root element must be <svg>")

    size = size_of(root)
    if size is None or size[0] < 400 or size[1] < 300:
        return fail("SVG needs a viewBox/width/height of at least 400x300")

    elements = list(root.iter())
    drawings = [e for e in elements if local(e.tag) in DRAWING]
    circles = [e for e in elements if local(e.tag) == "circle"]
    frame_like = [e for e in elements if local(e.tag) in {"path", "line", "rect", "polygon"}]

    if len(circles) < 2:
        return fail("need at least two wheels (two <circle> elements)")
    if len(drawings) < 8:
        return fail("too few drawing elements; draw a bike + pelican, not just text")
    if len(frame_like) < 3:
        return fail("need a frame/body (path/line/rect/polygon)")

    colors: set[str] = set()
    style_text: list[str] = []
    for element in elements:
        for attr in ("fill", "stroke"):
            value = element.get(attr)
            if value and value.lower() not in {"none", "transparent", "currentcolor"}:
                colors.add(value.lower())
        if local(element.tag) == "style" and element.text:
            style_text.append(element.text)
    colors.update(re.findall(r"#[0-9a-fA-F]{3,8}", " ".join(style_text)))

    if len(colors) < 3:
        return fail("need at least three colors (fill/stroke)")

    text = " ".join(
        element.text or ""
        for element in elements
        if local(element.tag) in {"title", "text", "desc"}
    ).lower()
    if not any(word in text for word in ("pelican", "bicycle", "鹈鹕", "自行车")):
        return fail('add a <title> containing "Pelican riding a bicycle"')

    if any(local(element.tag) == "image" for element in elements):
        return fail("do not use external images; draw it with SVG shapes")

    print("PASS quest02")
    print("open pelican.svg in a browser to see it")
    return 0


if __name__ == "__main__":
    sys.exit(main())
