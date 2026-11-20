#!/usr/bin/env python3
"""Draw the entry picture for the make.fun news-image-20261120 bounty.

The design is a meridian broadsheet, deliberately different from the
atlas grid of 19 November: a light masthead, one full-width world map,
a full-width lead strip with the day's numbers beside it, and then
six horizontal continent strips stacked down the page — one strip
per continent, each with its own coloured tab on the left and its
headlines flowing in two columns on the right. No grid of boxes.

Everything on the page comes from ``stories.json`` in this same
folder. Run ``python3 render.py`` and it writes ``entry.png`` next
to itself: 1024x1024, well under 1 MiB. It needs nothing from the
network — the Merriweather faces it sets the page in are bundled
under ``fonts/`` (SIL Open Font License 1.1) — and the only
third-party import is Pillow. Given the same ``stories.json`` it
always writes the same bytes; if a headline ever overflows its
strip the script fails loudly instead of clipping text silently.
"""

import json
import os

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
TYPE_DIR = os.path.join(HERE, "fonts")
PAGE_W, PAGE_H = 1024, 1024

CUTS = {
    "regular": "merriweather-v33-latin-regular.ttf",
    "bold": "merriweather-v33-latin-700.ttf",
    "black": "merriweather-v33-latin-900.ttf",
}

PAPER = (247, 244, 232)
CARD = (255, 255, 255)
SEA = (205, 224, 232)
LAND = (226, 214, 178)
LAND_LINE = (96, 118, 130)
RULE_RED = (165, 30, 25)
NAVY = (22, 35, 61)
BODY = (24, 24, 24)
SOFT = (88, 84, 76)
FAINT = (120, 115, 105)
PIN = (178, 34, 34)

# Schematic continent outlines in (longitude, latitude) — recognisable
# shapes for a newspaper map, not a survey chart.
CONTINENTS = {
    "north_america": [(-168, 66), (-150, 70), (-130, 71), (-110, 73),
                      (-95, 80), (-82, 73), (-68, 62), (-55, 47),
                      (-65, 44), (-75, 36), (-81, 26), (-90, 21),
                      (-97, 16), (-104, 20), (-112, 26), (-122, 37),
                      (-125, 49), (-135, 58), (-152, 58), (-168, 66)],
    "south_america": [(-79, 9), (-62, 8), (-52, 4), (-44, -3),
                      (-35, -8), (-39, -15), (-41, -23), (-49, -29),
                      (-58, -35), (-65, -41), (-70, -50), (-68, -54),
                      (-71, -45), (-73, -32), (-72, -20), (-78, -8),
                      (-81, 1), (-79, 9)],
    "europe": [(-10, 36), (-9, 43), (-2, 48), (0, 51), (4, 53),
               (8, 57), (12, 56), (18, 56), (21, 55), (25, 60),
               (28, 62), (30, 70), (40, 68), (44, 66), (42, 58),
               (40, 50), (35, 45), (30, 46), (28, 41), (23, 36),
               (19, 40), (12, 44), (3, 43), (-2, 37), (-10, 36)],
    "africa": [(-17, 15), (-12, 27), (-6, 35), (10, 37), (20, 32),
               (32, 31), (35, 28), (43, 12), (51, 11), (48, 2),
               (41, -9), (36, -18), (32, -26), (26, -34), (19, -35),
               (15, -27), (12, -18), (9, -2), (9, 4), (-8, 5),
               (-17, 15)],
    "asia": [(40, 68), (52, 69), (60, 70), (70, 72), (80, 73),
             (100, 77), (120, 73), (140, 72), (158, 71), (178, 66),
             (170, 60), (162, 56), (158, 52), (142, 50), (140, 40),
             (130, 35), (127, 34), (122, 31), (120, 23), (110, 20),
             (108, 12), (104, 8), (100, 6), (97, 16), (91, 22),
             (88, 22), (80, 13), (77, 8), (73, 16), (66, 25),
             (61, 25), (57, 26), (52, 26), (50, 30), (48, 30),
             (44, 39), (41, 42), (39, 46), (40, 56), (40, 68)],
    "oceania": [(113, -22), (114, -30), (115, -35), (122, -34),
                (129, -32), (135, -35), (140, -38), (146, -39),
                (150, -37), (153, -32), (153, -27), (150, -22),
                (146, -19), (142, -11), (137, -12), (132, -11),
                (126, -14), (122, -17), (117, -20), (113, -22)],
}

TAB_COLOURS = {
    "Europe": (165, 30, 25),
    "Asia": (0, 90, 160),
    "North America": (0, 120, 60),
    "Africa": (150, 60, 0),
    "South America": (110, 40, 130),
    "Oceania": (0, 120, 120),
}


def typeface(cut, size):
    """A Merriweather face at the given size, from the bundled fonts."""
    try:
        return ImageFont.truetype(os.path.join(TYPE_DIR, CUTS[cut]), size)
    except OSError:
        return ImageFont.load_default()


def wrap_lines(draw, text, face, width):
    """Greedy word wrap: split text into lines that fit a pixel width."""
    words, lines, current = text.split(), [], ""
    for word in words:
        trial = f"{current} {word}".strip()
        if draw.textlength(trial, font=face) <= width or not current:
            current = trial
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def draw_lines(draw, x, y, text, face, width, colour, spacing=2):
    """Draw wrapped text and return the y coordinate just below it."""
    for line in wrap_lines(draw, text, face, width):
        draw.text((x, y), line, font=face, fill=colour)
        y += face.size + spacing
    return y


class MeridianMap:
    """Equirectangular world map drawn inside a rectangle."""

    def __init__(self, x, y, w, h):
        self.x, self.y, self.w, self.h = x, y, w, h
        self.lat_top, self.lat_bot = 84.0, -58.0

    def project(self, lon, lat):
        px = self.x + (lon + 180.0) / 360.0 * self.w
        py = self.y + (self.lat_top - lat) / (self.lat_top - self.lat_bot) * self.h
        return px, py

    def draw(self, pen):
        pen.rectangle([self.x, self.y, self.x + self.w, self.y + self.h],
                      fill=SEA)
        for lon in range(-180, 181, 30):
            px, _ = self.project(lon, 0)
            pen.line([(px, self.y), (px, self.y + self.h)],
                     fill=(190, 208, 220), width=1)
        for lat in range(-60, 91, 30):
            _, py = self.project(0, lat)
            pen.line([(self.x, py), (self.x + self.w, py)],
                     fill=(190, 208, 220), width=1)
        for shape in CONTINENTS.values():
            pen.polygon([self.project(lon, lat) for lon, lat in shape],
                        fill=LAND, outline=LAND_LINE, width=1)
        for lon, lat in ((167, -45), (174, -41)):
            px, py = self.project(lon, lat)
            pen.ellipse([px - 3, py - 2, px + 3, py + 2],
                        fill=LAND, outline=LAND_LINE)
        cx, cy = self.x + self.w - 26, self.y + 24
        pen.ellipse([cx - 13, cy - 13, cx + 13, cy + 13],
                    outline=LAND_LINE, width=1)
        pen.polygon([(cx, cy - 10), (cx + 4, cy + 6), (cx - 4, cy + 6)],
                    fill=NAVY)
        pen.text((cx - 4, cy - 24), "N", font=typeface("bold", 10),
                 fill=NAVY)


def draw_pin(pen, x, y, label):
    """A numbered red pin with a white numeral."""
    pen.ellipse([x - 10, y - 10, x + 10, y + 10], fill=PIN,
                outline=(255, 255, 255), width=2)
    face = typeface("bold", 10)
    tw = pen.textlength(label, font=face)
    pen.text((x - tw / 2, y - 7), label, font=face, fill=(255, 255, 255))


def main():
    with open(os.path.join(HERE, "stories.json"), encoding="utf-8") as fh:
        data = json.load(fh)

    sections = data["sections"]
    total = 1 + sum(len(s["headlines"]) for s in sections)

    page = Image.new("RGB", (PAGE_W, PAGE_H), PAPER)
    pen = ImageDraw.Draw(page)

    # ---- Masthead: light paper, black title, red rule underneath.
    pen.text((28, 12), "THE WORLD IN ONE DAY",
             font=typeface("black", 36), fill=BODY)
    pen.text((28, 58), "FRIDAY 20 NOVEMBER 2026",
             font=typeface("bold", 13), fill=RULE_RED)
    badge = f"{total} STORIES  ·  6 CONTINENTS"
    face = typeface("bold", 13)
    pen.text((PAGE_W - 28 - pen.textlength(badge, font=face), 20), badge,
             font=face, fill=BODY)
    pen.text((PAGE_W - 28 - pen.textlength("ONE IMAGE — THE WHOLE DAY",
             font=typeface("regular", 11)), 46),
             "ONE IMAGE — THE WHOLE DAY",
             font=typeface("regular", 11), fill=SOFT)
    pen.rectangle([28, 88, PAGE_W - 28, 92], fill=RULE_RED)

    # ---- Map band: one full-width map with numbered pins.
    map_x, map_y, map_w, map_h = 24, 102, 976, 176
    world = MeridianMap(map_x, map_y, map_w, map_h)
    world.draw(pen)
    for lon, lat, label, _place in data["map_points"]:
        px, py = world.project(lon, lat)
        draw_pin(pen, px, py, label)
    key = "  ·  ".join(f"{n} {place}" for _lon, _lat, n, place
                       in data["map_points"])
    pen.text((map_x, map_y + map_h + 5), key,
             font=typeface("regular", 10), fill=SOFT)

    # ---- Lead strip: lead story left, day in numbers right.
    lead_y, lead_h = 308, 142
    lead_x, lead_w = 24, 612
    pen.rectangle([lead_x, lead_y, lead_x + lead_w, lead_y + lead_h],
                  fill=CARD, outline=(200, 195, 185), width=1)
    pen.rectangle([lead_x, lead_y, lead_x + lead_w, lead_y + 5], fill=RULE_RED)
    lx = lead_x + 14
    pen.text((lx, lead_y + 14), "TOP STORY",
             font=typeface("bold", 11), fill=RULE_RED)
    y = draw_lines(pen, lx, lead_y + 32, data["lead"]["headline"],
                   typeface("black", 18), lead_w - 28, BODY, spacing=3)
    y = draw_lines(pen, lx, y + 5, data["lead"]["standfirst"],
                   typeface("regular", 12), lead_w - 28, SOFT, spacing=3)
    if y > lead_y + lead_h - 6:
        raise SystemExit("lead strip overflow")

    num_x, num_w = 652, 348
    pen.rectangle([num_x, lead_y, num_x + num_w, lead_y + lead_h],
                  fill=CARD, outline=(200, 195, 185), width=1)
    pen.rectangle([num_x, lead_y, num_x + num_w, lead_y + 5], fill=NAVY)
    nx = num_x + 14
    pen.text((nx, lead_y + 14), data["numbers_title"],
             font=typeface("bold", 11), fill=NAVY)
    y = lead_y + 34
    for label, value, move in data["numbers"]:
        pen.text((nx, y), label, font=typeface("bold", 11), fill=BODY)
        cell = f"{value}  {move}"
        face = typeface("regular", 11)
        pen.text((num_x + num_w - 14 - pen.textlength(cell, font=face), y),
                 cell, font=face, fill=BODY)
        y += 17
    if y > lead_y + lead_h - 6:
        raise SystemExit("numbers strip overflow")

    # ---- Six continent strips: stacked horizontal bands, tab on the left,
    # headlines in two columns on the right. No grid of boxes.
    strip_y = 466
    strip_h, strip_gap = 82, 5
    strip_x, strip_w = 24, 976
    for section in sections:
        top = strip_y
        colour = TAB_COLOURS[section["continent"]]
        pen.rectangle([strip_x, top, strip_x + strip_w, top + strip_h],
                      fill=CARD, outline=(200, 195, 185), width=1)
        pen.rectangle([strip_x, top, strip_x + 118, top + strip_h],
                      fill=colour)
        pen.text((strip_x + 10, top + 12), section["continent"].upper(),
                 font=typeface("bold", 12), fill=(255, 255, 255))
        count = f"{len(section['headlines'])} stories"
        pen.text((strip_x + 10, top + 52), count,
                 font=typeface("regular", 11), fill=(235, 235, 235))
        # Split headlines across two columns, left column first.
        heads = section["headlines"]
        half = (len(heads) + 1) // 2
        columns = [heads[:half], heads[half:]]
        col_w = 408
        for ci, col_heads in enumerate(columns):
            cx = strip_x + 132 + ci * (col_w + 20)
            cy = top + 8
            for hi, headline in enumerate(col_heads):
                face = typeface("bold", 11) if hi == 0 and ci == 0 else typeface("regular", 11)
                cy = draw_lines(pen, cx, cy, "•  " + headline,
                                face, col_w, BODY, spacing=0)
                cy += 1
                if cy > top + strip_h - 4:
                    raise SystemExit(
                        f"strip overflow in {section['continent']}: "
                        "headlines do not fit the strip")
        strip_y = top + strip_h + strip_gap

    # ---- Footer.
    pen.text((28, 1000),
             f"{total} stories  ·  6 continents  ·  Friday 20 November 2026"
             "  ·  Sources: Reuters, BBC, Guardian, AP, FT, IMD",
             font=typeface("regular", 11), fill=FAINT)

    out = os.path.join(HERE, "entry.png")
    page.save(out, format="PNG", optimize=True)
    print(f"wrote {out} ({os.path.getsize(out)} bytes, {PAGE_W}x{PAGE_H})")


if __name__ == "__main__":
    main()
