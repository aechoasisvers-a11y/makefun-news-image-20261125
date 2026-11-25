#!/usr/bin/env python3
"""The world on Wednesday 25 November 2026 -- one image, six stories.

Pure Python 3.13 standard library only: no Pillow, no numpy. The program
draws a 1024x1024 poster with its own 5x7 bitmap font and writes it as a
PNG with its own minimal encoder (zlib + struct). Output is deterministic:
the same bytes on every run.

Usage: python3 main.py [output_path]   (default: /output/entry.png)

Stories (all first reported on Wednesday 25 November 2026):
  1. China launches Shenzhou 24 -- AP
  2. Australia apologises to LGBTQ veterans -- Reuters
  3. Asian stocks tumble on a fresh US tariff threat -- Reuters
  4. Nvidia chief Jensen Huang apologises to staff -- CNBC / CNN
  5. US Army to detonate unstable lead azide in Iowa today -- CNN / USA Today
  6. Australian inflation runs hotter than expected -- Reuters
"""

import os
import struct
import sys
import zlib

W, H = 1024, 1024

# ---------------------------------------------------------------- palette
NAVY = (14, 26, 43)        # page background
PANEL = (22, 40, 63)       # panel background
BANNER = (18, 35, 58)      # banner background
WHITE = (240, 244, 248)
MUTED = (168, 186, 205)
GOLD = (232, 184, 75)
RED = (214, 72, 72)
GREEN = (72, 190, 120)
BLUE = (84, 150, 230)
ORANGE = (240, 140, 60)
PURPLE = (170, 120, 220)
TEAL = (70, 200, 190)
YELLOW = (250, 220, 90)

# ---------------------------------------------------------------- 5x7 font
# Each glyph: 7 rows, each a 5-bit mask, MSB = leftmost pixel.
FONT = {
    "A": [0b01110, 0b10001, 0b10001, 0b11111, 0b10001, 0b10001, 0b10001],
    "B": [0b11110, 0b10001, 0b10001, 0b11110, 0b10001, 0b10001, 0b11110],
    "C": [0b01110, 0b10001, 0b10000, 0b10000, 0b10000, 0b10001, 0b01110],
    "D": [0b11110, 0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b11110],
    "E": [0b11111, 0b10000, 0b10000, 0b11110, 0b10000, 0b10000, 0b11111],
    "F": [0b11111, 0b10000, 0b10000, 0b11110, 0b10000, 0b10000, 0b10000],
    "G": [0b01110, 0b10001, 0b10000, 0b10111, 0b10001, 0b10001, 0b01111],
    "H": [0b10001, 0b10001, 0b10001, 0b11111, 0b10001, 0b10001, 0b10001],
    "I": [0b01110, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100, 0b01110],
    "J": [0b00111, 0b00010, 0b00010, 0b00010, 0b00010, 0b10010, 0b01100],
    "K": [0b10001, 0b10010, 0b10100, 0b11000, 0b10100, 0b10010, 0b10001],
    "L": [0b10000, 0b10000, 0b10000, 0b10000, 0b10000, 0b10000, 0b11111],
    "M": [0b10001, 0b11011, 0b10101, 0b10101, 0b10001, 0b10001, 0b10001],
    "N": [0b10001, 0b11001, 0b10101, 0b10011, 0b10001, 0b10001, 0b10001],
    "O": [0b01110, 0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b01110],
    "P": [0b11110, 0b10001, 0b10001, 0b11110, 0b10000, 0b10000, 0b10000],
    "Q": [0b01110, 0b10001, 0b10001, 0b10001, 0b10101, 0b10010, 0b01101],
    "R": [0b11110, 0b10001, 0b10001, 0b11110, 0b10100, 0b10010, 0b10001],
    "S": [0b01111, 0b10000, 0b10000, 0b01110, 0b00001, 0b00001, 0b11110],
    "T": [0b11111, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100],
    "U": [0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b01110],
    "V": [0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b01010, 0b00100],
    "W": [0b10001, 0b10001, 0b10001, 0b10101, 0b10101, 0b11011, 0b10001],
    "X": [0b10001, 0b10001, 0b01010, 0b00100, 0b01010, 0b10001, 0b10001],
    "Y": [0b10001, 0b10001, 0b01010, 0b00100, 0b00100, 0b00100, 0b00100],
    "Z": [0b11111, 0b00001, 0b00010, 0b00100, 0b01000, 0b10000, 0b11111],
    "0": [0b01110, 0b10001, 0b10011, 0b10101, 0b11001, 0b10001, 0b01110],
    "1": [0b00100, 0b01100, 0b00100, 0b00100, 0b00100, 0b00100, 0b01110],
    "2": [0b01110, 0b10001, 0b00001, 0b00110, 0b01000, 0b10000, 0b11111],
    "3": [0b11111, 0b00010, 0b00100, 0b00010, 0b00001, 0b10001, 0b01110],
    "4": [0b00010, 0b00110, 0b01010, 0b10010, 0b11111, 0b00010, 0b00010],
    "5": [0b11111, 0b10000, 0b11110, 0b00001, 0b00001, 0b10001, 0b01110],
    "6": [0b00110, 0b01000, 0b10000, 0b11110, 0b10001, 0b10001, 0b01110],
    "7": [0b11111, 0b00001, 0b00010, 0b00100, 0b01000, 0b01000, 0b01000],
    "8": [0b01110, 0b10001, 0b10001, 0b01110, 0b10001, 0b10001, 0b01110],
    "9": [0b01110, 0b10001, 0b10001, 0b01111, 0b00001, 0b00010, 0b01100],
    " ": [0, 0, 0, 0, 0, 0, 0],
    ".": [0, 0, 0, 0, 0, 0b01100, 0b01100],
    ",": [0, 0, 0, 0, 0b01100, 0b00100, 0b01000],
    "'": [0b00100, 0b00100, 0b01000, 0, 0, 0, 0],
    "-": [0, 0, 0, 0b01110, 0, 0, 0],
    ":": [0, 0b01100, 0b01100, 0, 0b01100, 0b01100, 0],
    "/": [0b00001, 0b00010, 0b00010, 0b00100, 0b01000, 0b01000, 0b10000],
    "(": [0b00010, 0b00100, 0b01000, 0b01000, 0b01000, 0b00100, 0b00010],
    ")": [0b01000, 0b00100, 0b00010, 0b00010, 0b00010, 0b00100, 0b01000],
    "&": [0b01100, 0b10010, 0b10100, 0b01000, 0b10101, 0b10010, 0b01101],
    "%": [0b11001, 0b11010, 0b00010, 0b00100, 0b01000, 0b01011, 0b10011],
    "+": [0, 0b00100, 0b00100, 0b11111, 0b00100, 0b00100, 0],
    "!": [0b00100, 0b00100, 0b00100, 0b00100, 0b00100, 0, 0b00100],
    "?": [0b01110, 0b10001, 0b00001, 0b00110, 0b00100, 0, 0b00100],
    "$": [0b00100, 0b01111, 0b10100, 0b01110, 0b00101, 0b11110, 0b00100],
}
CHAR_W = 6  # 5 px glyph + 1 px gap


class Canvas:
    def __init__(self, w, h, bg):
        self.w, self.h = w, h
        self.px = bytearray(bg * (w * h))

    def set(self, x, y, color):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i:i + 3] = bytes(color)

    def rect(self, x, y, w, h, color):
        for yy in range(y, y + h):
            for xx in range(x, x + w):
                self.set(xx, yy, color)

    def hline(self, x0, x1, y, color):
        for xx in range(x0, x1 + 1):
            self.set(xx, y, color)

    def vline(self, x, y0, y1, color):
        for yy in range(y0, y1 + 1):
            self.set(x, yy, color)

    def line(self, x0, y0, x1, y1, color, thick=1):
        dx, dy = abs(x1 - x0), abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy
        while True:
            for ty in range(thick):
                for tx in range(thick):
                    self.set(x0 + tx, y0 + ty, color)
            if x0 == x1 and y0 == y1:
                return
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x0 += sx
            if e2 < dx:
                err += dx
                y0 += sy

    def circle(self, cx, cy, r, color, fill=True):
        for yy in range(cy - r, cy + r + 1):
            for xx in range(cx - r, cx + r + 1):
                d = (xx - cx) ** 2 + (yy - cy) ** 2
                if fill:
                    if d <= r * r:
                        self.set(xx, yy, color)
                else:
                    if r * r - 2 * r <= d <= r * r:
                        self.set(xx, yy, color)

    def ring(self, cx, cy, r, color, thick=3):
        for yy in range(cy - r - thick, cy + r + thick + 1):
            for xx in range(cx - r - thick, cx + r + thick + 1):
                d = ((xx - cx) ** 2 + (yy - cy) ** 2) ** 0.5
                if abs(d - r) <= thick / 2:
                    self.set(xx, yy, color)

    def arc_top(self, cx, cy, r, color, thick=4):
        # upper half of a ring (a rainbow arc)
        for yy in range(cy - r - thick, cy + 1):
            for xx in range(cx - r - thick, cx + r + thick + 1):
                d = ((xx - cx) ** 2 + (yy - cy) ** 2) ** 0.5
                if abs(d - r) <= thick / 2:
                    self.set(xx, yy, color)

    def triangle(self, x0, y0, x1, y1, x2, y2, color):
        # filled triangle via scanline
        pts = sorted([(x0, y0), (x1, y1), (x2, y2)], key=lambda p: p[1])
        (ax, ay), (bx, by), (cx, cy) = pts
        for y in range(ay, cy + 1):
            if y < by:
                t1 = (y - ay) / (by - ay) if by != ay else 0
                xa = ax + (bx - ax) * t1
            else:
                t1 = (y - by) / (cy - by) if cy != by else 0
                xa = bx + (cx - bx) * t1
            t2 = (y - ay) / (cy - ay) if cy != ay else 0
            xb = ax + (cx - ax) * t2
            for x in range(int(min(xa, xb)), int(max(xa, xb)) + 1):
                self.set(x, y, color)

    def starburst(self, cx, cy, r_out, r_in, spikes, color):
        import math
        pts = []
        for i in range(spikes * 2):
            r = r_out if i % 2 == 0 else r_in
            a = math.pi * i / spikes - math.pi / 2
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
        for i in range(len(pts)):
            x0, y0 = pts[i]
            x1, y1 = pts[(i + 1) % len(pts)]
            self.triangle(int(cx), int(cy), int(x0), int(y0), int(x1), int(y1), color)

    # ------------------------------------------------------------- text
    def text(self, x, y, s, scale, color):
        s = s.upper()
        cx = x
        for ch in s:
            glyph = FONT.get(ch, FONT[" "])
            for row in range(7):
                bits = glyph[row]
                for col in range(5):
                    if bits & (1 << (4 - col)):
                        self.rect(cx + col * scale, y + row * scale,
                                  scale, scale, color)
            cx += CHAR_W * scale
        return cx

    def text_w(self, s, scale):
        return len(s.upper()) * CHAR_W * scale

    def wrap(self, s, scale, max_w):
        words = s.upper().split(" ")
        lines, cur = [], ""
        for w in words:
            trial = (cur + " " + w).strip()
            if self.text_w(trial, scale) <= max_w:
                cur = trial
            else:
                if cur:
                    lines.append(cur)
                cur = w
        if cur:
            lines.append(cur)
        return lines


# ---------------------------------------------------------------- stories
# (tag, tag colour, headline, summary, pictogram)
STORIES = [
    ("SPACE - CHINA", BLUE,
     "CHINA LAUNCHES SHENZHOU 24",
     "Three astronauts head for the Tiangong station, "
     "including Pakistan's Zeeshan Ali, the first foreign "
     "crew member on board.",
     "rocket"),
    ("AUSTRALIA", PURPLE,
     "AUSTRALIA'S APOLOGY TO LGBTQ VETERANS",
     "Canberra formally apologises for decades of "
     "discrimination against gay and lesbian service "
     "members.",
     "rainbow"),
    ("MARKETS", RED,
     "ASIAN STOCKS TUMBLE ON TARIFF THREAT",
     "Shares fall across Asia as Washington prepares new "
     "duties on China, the EU and 14 other economies.",
     "down"),
    ("TECH - NVIDIA", GREEN,
     "HUANG APOLOGISES TO NVIDIA STAFF",
     "A day after his return as chief, Jensen Huang says "
     "sorry, says he is in therapy and needs no "
     "succession plan.",
     "chip"),
    ("USA - IOWA", ORANGE,
     "IOWA BLASTS 5 TONS OF EXPLOSIVE TODAY",
     "The Army will detonate 68 barrels of unstable lead "
     "azide at 9 a.m.; residents told to leave or stay "
     "indoors.",
     "blast"),
    ("ECONOMY - AUSTRALIA", TEAL,
     "AUSTRALIAN INFLATION RUNS HOT",
     "Prices rose more than expected in October, with "
     "core inflation at 3.8%, piling pressure on the "
     "Reserve Bank.",
     "up"),
]


def draw_pictogram(cv, kind, cx, cy, s):
    """Draw a simple pictogram centred at (cx, cy), size ~s px."""
    if kind == "rocket":
        # body
        cv.rect(cx - 9, cy - 26, 18, 44, WHITE)
        cv.triangle(cx - 9, cy - 26, cx + 9, cy - 26, cx, cy - 42, RED)
        cv.circle(cx, cy - 8, 5, BLUE)
        # fins
        cv.triangle(cx - 9, cy + 6, cx - 9, cy + 18, cx - 20, cy + 18, RED)
        cv.triangle(cx + 9, cy + 6, cx + 9, cy + 18, cx + 20, cy + 18, RED)
        # flame
        cv.triangle(cx - 6, cy + 18, cx + 6, cy + 18, cx, cy + 34, ORANGE)
        cv.triangle(cx - 3, cy + 18, cx + 3, cy + 18, cx, cy + 26, YELLOW)
        # stars
        for sx, sy in ((cx - 34, cy - 30), (cx + 34, cy - 18), (cx - 30, cy + 26)):
            cv.rect(sx - 1, sy - 4, 2, 8, GOLD)
            cv.rect(sx - 4, sy - 1, 8, 2, GOLD)
    elif kind == "rainbow":
        for r, c in ((34, RED), (28, ORANGE), (22, YELLOW),
                     (16, GREEN), (10, BLUE)):
            cv.arc_top(cx, cy + 18, r, c, 5)
        cv.circle(cx, cy + 18, 7, RED)  # heart-ish dot at the foot
    elif kind == "down":
        bars = [34, 26, 18, 10]
        for i, bh in enumerate(bars):
            x = cx - 36 + i * 18
            cv.rect(x, cy + 20 - bh, 12, bh, BLUE)
        cv.line(cx - 40, cy - 26, cx + 38, cy + 26, RED, 5)
        cv.triangle(cx + 38, cy + 26, cx + 22, cy + 22, cx + 34, cy + 10, RED)
    elif kind == "chip":
        cv.rect(cx - 24, cy - 24, 48, 48, GREEN)
        cv.rect(cx - 15, cy - 15, 30, 30, NAVY)
        cv.rect(cx - 7, cy - 7, 14, 14, GREEN)
        for i in range(3):
            off = -16 + i * 16
            cv.rect(cx + off - 2, cy - 34, 4, 10, GREEN)
            cv.rect(cx + off - 2, cy + 24, 4, 10, GREEN)
            cv.rect(cx - 34, cy + off - 2, 10, 4, GREEN)
            cv.rect(cx + 24, cy + off - 2, 10, 4, GREEN)
    elif kind == "blast":
        cv.starburst(cx, cy, 36, 16, 10, YELLOW)
        cv.starburst(cx, cy, 22, 10, 10, ORANGE)
        cv.circle(cx, cy, 8, RED)
    elif kind == "up":
        bars = [10, 18, 26, 34]
        for i, bh in enumerate(bars):
            x = cx - 36 + i * 18
            cv.rect(x, cy + 20 - bh, 12, bh, GREEN)
        cv.line(cx - 40, cy + 26, cx + 38, cy - 26, GREEN, 5)
        cv.triangle(cx + 38, cy - 26, cx + 22, cy - 22, cx + 34, cy - 10, GREEN)


def draw_panel(cv, x, y, w, h, story):
    tag, color, headline, summary, pic = story
    cv.rect(x, y, w, h, PANEL)
    cv.rect(x, y, w, 6, color)
    # pictogram column on the left
    icon_cx, icon_cy = x + 52, y + h // 2 + 8
    draw_pictogram(cv, pic, icon_cx, icon_cy, 90)
    tx = x + 112
    tw = w - 112 - 18
    cv.text(tx, y + 20, tag, 2, color)
    lines = cv.wrap(headline, 3, tw)
    yy = y + 52
    for ln in lines[:2]:
        cv.text(tx, yy, ln, 3, WHITE)
        yy += 26
    yy = y + 112
    for ln in cv.wrap(summary, 2, tw)[:5]:
        cv.text(tx, yy, ln, 2, MUTED)
        yy += 18


def draw():
    cv = Canvas(W, H, NAVY)
    # banner
    cv.rect(0, 0, W, 142, BANNER)
    cv.rect(0, 142, W, 4, GOLD)
    title = "THE WORLD TODAY"
    tw = cv.text_w(title, 6)
    cv.text((W - tw) // 2, 22, title, 6, GOLD)
    date = "WEDNESDAY 25 NOVEMBER 2026"
    dw = cv.text_w(date, 3)
    cv.text((W - dw) // 2, 92, date, 3, WHITE)
    # gold dots flanking the title
    cv.circle(150, 52, 5, GOLD)
    cv.circle(874, 52, 5, GOLD)
    # panels: 2 columns x 3 rows
    px, py = 16, 158
    pw, ph = 488, 262
    gx, gy = 16, 14
    for i, story in enumerate(STORIES):
        col, row = i % 2, i // 2
        draw_panel(cv, px + col * (pw + gx), py + row * (ph + gy),
                   pw, ph, story)
    # footer
    foot1 = "SIX STORIES FIRST REPORTED ON WEDNESDAY 25 NOVEMBER 2026"
    fw = cv.text_w(foot1, 2)
    cv.text((W - fw) // 2, 978, foot1, 2, WHITE)
    foot2 = "SOURCES: AP - REUTERS - CNBC - CNN"
    fw2 = cv.text_w(foot2, 2)
    cv.text((W - fw2) // 2, 1000, foot2, 2, MUTED)
    return cv


# ---------------------------------------------------------------- PNG out
def _chunk(ctype, data):
    out = struct.pack(">I", len(data)) + ctype + data
    return out + struct.pack(">I", zlib.crc32(ctype + data) & 0xFFFFFFFF)


def write_png(path, cv):
    raw = b"".join(
        b"\x00" + bytes(cv.px[y * W * 3:(y + 1) * W * 3])
        for y in range(H)
    )
    ihdr = struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)
    png = (b"\x89PNG\r\n\x1a\n"
           + _chunk(b"IHDR", ihdr)
           + _chunk(b"IDAT", zlib.compress(raw, 9))
           + _chunk(b"IEND", b""))
    parent = os.path.dirname(os.path.abspath(path))
    os.makedirs(parent, exist_ok=True)
    with open(path, "wb") as f:
        f.write(png)
    return len(png)


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "/output/entry.png"
    cv = draw()
    n = write_png(out, cv)
    print(f"wrote {out} ({W}x{H}, {n} bytes)")


if __name__ == "__main__":
    main()
