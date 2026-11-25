"""Generate portal/img/llama.svg: a pixel-art llama in a nursing cap.

The sprite is drawn as the left half of a 12 x 28 grid and mirrored, then outlined
automatically, so it is perfectly symmetric. Run:  python scripts/make_llama.py
"""
from pathlib import Path

W, H = 12, 28
g = [["."] * W for _ in range(H)]


def rect(r0, r1, c0, c1, ch):
    for r in range(r0, r1 + 1):
        for c in range(c0, c1 + 1):
            g[r][c] = ch


rect(0, 7, 6, 11, "w")          # cap
rect(1, 6, 11, 11, "t")         # cross, vertical (mirrors to 2 wide)
rect(3, 4, 9, 11, "t")          # cross, horizontal
rect(8, 8, 4, 11, "t")          # cap band
rect(2, 2, 3, 3, "c"); rect(3, 3, 2, 4, "c"); rect(4, 9, 2, 4, "c")   # ear
rect(5, 8, 3, 3, "p")           # ear inner
rect(9, 18, 3, 11, "c")         # head
rect(14, 18, 7, 11, "l")        # snout
rect(14, 15, 4, 5, "p")         # cheek
rect(12, 13, 6, 7, "e"); g[12][6] = "h"   # eye + highlight
rect(14, 14, 10, 11, "n")       # nose
rect(15, 15, 8, 9, "m"); rect(16, 16, 10, 11, "m")  # smile
rect(19, 27, 6, 11, "c")        # neck
rect(22, 27, 9, 11, "l")        # chest
rect(22, 22, 9, 10, "r"); rect(23, 23, 9, 11, "r"); rect(24, 24, 10, 11, "r"); g[25][11] = "r"  # heart pin

full = [row + row[::-1] for row in g]
PAD = 1
FW, FH = W * 2 + PAD * 2, H + PAD * 2
canvas = [["."] * FW for _ in range(FH)]
for r in range(H):
    for c in range(W * 2):
        canvas[r + PAD][c + PAD] = full[r][c]
solid = [[canvas[r][c] != "." for c in range(FW)] for r in range(FH)]
for r in range(FH):
    for c in range(FW):
        if canvas[r][c] == "." and any(
            0 <= r + dr < FH and 0 <= c + dc < FW and solid[r + dr][c + dc]
            for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1))
        ):
            canvas[r][c] = "o"

COL = {"o": "#0A1B2B", "c": "#F1E1C8", "l": "#FFF8EC", "p": "#F4B9B2", "w": "#FFFFFF",
       "t": "#007C91", "n": "#0A1B2B", "m": "#0A1B2B", "e": "#0A1B2B", "h": "#FFFFFF", "r": "#E5484D"}


def runs(ch):
    out = []
    for r in range(FH):
        c = 0
        while c < FW:
            if canvas[r][c] == ch:
                s = c
                while c < FW and canvas[r][c] == ch:
                    c += 1
                out.append(f"M{s} {r}h{c - s}v1h-{c - s}z")
            else:
                c += 1
    return "".join(out)


parts = []
for ch in "oclpwtnmr":   # eyes handled separately so they can blink
    d = runs(ch)
    if d:
        parts.append(f'<path fill="{COL[ch]}" d="{d}"/>')
eyes = runs("e"); hl = runs("h")
svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {FW} {FH}" width="{FW * 4}" height="{FH * 4}" shape-rendering="crispEdges" role="img" aria-label="Pixel-art llama wearing a nursing cap">
<style>
.eye{{transform-box:fill-box;transform-origin:50% 50%;animation:blink 4.8s steps(1) infinite}}
.heart{{animation:beat 1.4s steps(1) infinite}}
@keyframes blink{{0%,93%,100%{{transform:scaleY(1)}}95%{{transform:scaleY(.25)}}}}
@keyframes beat{{0%,100%{{opacity:1}}50%{{opacity:.7}}}}
@media (prefers-reduced-motion:reduce){{.eye,.heart{{animation:none}}}}
</style>
{"".join(p for p in parts if '#E5484D' not in p)}
<path class="heart" fill="#E5484D" d="{runs('r')}"/>
<path class="eye" fill="#0A1B2B" d="{eyes}"/>
<path fill="#FFFFFF" d="{hl}"/>
</svg>
'''
out = Path(__file__).resolve().parent.parent / "portal" / "img" / "llama.svg"
out.write_text(svg)
print("wrote", out, len(svg), "bytes", FW, "x", FH)
