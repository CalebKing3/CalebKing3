"""Builds assets/header.svg and assets/cards/*.svg in the "Regal Drafting" style (see design/philosophy.md).

Text is shaped with HarfBuzz and converted to vector outlines, so the SVGs render identically on
GitHub regardless of installed fonts. Requires: pip install fonttools uharfbuzz
"""
from math import cos, sin, radians, hypot
from pathlib import Path

import uharfbuzz as hb
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parent.parent
FONTS = ROOT / "design" / "fonts"
GOLD, INK, WHITE = "#E6B70C", "#050505", "#F4F1EA"
HEX_W, HEX_H = 24, 20.7846  # triangular lattice: row r sits at y = r*HEX_H, x offset 12 on odd rows


# ── type ────────────────────────────────────────────────────────────────────────
class Face:
    def __init__(self, file):
        path = FONTS / file
        self.tt = TTFont(path)
        self.glyphs = self.tt.getGlyphSet()
        self.order = self.tt.getGlyphOrder()
        self.upm = self.tt["head"].unitsPerEm
        self.hb = hb.Font(hb.Face(hb.Blob.from_file_path(str(path))))

    def shape(self, text, size, tracking=0.0):
        buf = hb.Buffer()
        buf.add_str(text)
        buf.guess_segment_properties()
        hb.shape(self.hb, buf, {"kern": True, "liga": True})
        k = size / self.upm
        out, x = [], 0.0
        for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
            out.append((self.order[info.codepoint], x + pos.x_offset * k, pos.y_offset * k))
            x += pos.x_advance * k + tracking
        return out, k, x - tracking

    def width(self, text, size, tracking=0.0):
        return self.shape(text, size, tracking)[2]

    def path(self, text, size, x, y, tracking=0.0, anchor="start"):
        glyphs, k, w = self.shape(text, size, tracking)
        if anchor == "end":
            x -= w
        elif anchor == "middle":
            x -= w / 2
        pen = SVGPathPen(self.glyphs, ntos=lambda v: f"{v:.1f}".rstrip("0").rstrip("."))
        for name, gx, gy in glyphs:
            self.glyphs[name].draw(TransformPen(pen, (k, 0, 0, -k, x + gx, y - gy)))
        return pen.getCommands()


SERIF, SERIF_IT, MONO = Face("InstrumentSerif-Regular.ttf"), Face("InstrumentSerif-Italic.ttf"), Face("GeistMono-Regular.ttf")


def text(face, s, size, x, y, fill, tracking=0.0, anchor="start", opacity=1, cls=""):
    c = f' class="{cls}"' if cls else ""
    o = f' fill-opacity="{opacity}"' if opacity != 1 else ""
    return f'<path{c} d="{face.path(s, size, x, y, tracking, anchor)}" fill="{fill}"{o}/>'


def label(s, x, y, fill=GOLD, opacity=1, anchor="start", size=10.5, cls=""):
    """Clinical annotation: small, widely tracked monospace."""
    return text(MONO, s.upper(), size, x, y, fill, tracking=size * 0.22, anchor=anchor, opacity=opacity, cls=cls)


# ── geometry helpers ───────────────────────────────────────────────────────────
def lat(col2, row):
    """Lattice point. col2 is in half-steps (12px) and must share parity with row."""
    assert (col2 - row) % 2 == 0, (col2, row)
    return col2 * HEX_W / 2, row * HEX_H


def pts(points):
    return " ".join(f"{x:.2f},{y:.2f}" for x, y in points)


def corner_marks(w, h, inset=18, arm=11, opacity=0.55):
    out = []
    for cx, sx in ((inset, 1), (w - inset, -1)):
        for cy, sy in ((inset, 1), (h - inset, -1)):
            out.append(f'<path d="M{cx},{cy + sy * arm}V{cy}H{cx + sx * arm}" />')
    return f'<g fill="none" stroke="{GOLD}" stroke-opacity="{opacity}" stroke-width="1">{"".join(out)}</g>'


def defs(w, h, glow_cx, glow_cy, glow_r, extra=""):
    return f"""<defs>
    <clipPath id="frame"><rect width="{w}" height="{h}" rx="16"/></clipPath>
    <pattern id="lattice" width="24" height="41.5692" patternUnits="userSpaceOnUse">
      <circle cx="0" cy="0" r="1"/><circle cx="24" cy="0" r="1"/><circle cx="12" cy="20.7846" r="1"/>
      <circle cx="0" cy="41.5692" r="1"/><circle cx="24" cy="41.5692" r="1"/>
    </pattern>
    <radialGradient id="lamp" gradientUnits="userSpaceOnUse" cx="{glow_cx}" cy="{glow_cy}" r="{glow_r}">
      <stop offset="0" stop-color="#fff"/><stop offset=".55" stop-color="#fff" stop-opacity=".35"/><stop offset="1" stop-color="#fff" stop-opacity="0"/>
    </radialGradient>
    <mask id="lampMask"><rect width="{w}" height="{h}" fill="url(#lamp)"/></mask>
    <radialGradient id="warmth" gradientUnits="userSpaceOnUse" cx="{glow_cx}" cy="{glow_cy}" r="{glow_r * 0.8}">
      <stop offset="0" stop-color="{GOLD}" stop-opacity=".13"/><stop offset="1" stop-color="{GOLD}" stop-opacity="0"/>
    </radialGradient>
    {extra}
  </defs>"""


def ground(w, h):
    # base lattice barely there; a second pass lit only where construction happens
    return f"""<rect width="{w}" height="{h}" fill="{INK}"/>
    <rect width="{w}" height="{h}" fill="url(#warmth)"/>
    <rect width="{w}" height="{h}" fill="url(#lattice)" opacity=".1"/>
    <g mask="url(#lampMask)"><rect width="{w}" height="{h}" fill="url(#lattice)" opacity=".42"/></g>"""


BASE_STYLE = f"""
    #lattice circle {{ fill: {GOLD}; }}
    .spin {{ transform-box: view-box; animation: spin 90s linear infinite; }}
    @keyframes spin {{ to {{ transform: rotate(360deg); }} }}
    .breathe {{ animation: breathe 6s ease-in-out infinite; }}
    @keyframes breathe {{ 0%,100% {{ opacity: 1; }} 50% {{ opacity: .55; }} }}
    @media (prefers-reduced-motion: reduce) {{ * {{ animation: none !important; }} }}"""


def node(x, y, r=3.2):
    return f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{r}" fill="{INK}" stroke="{GOLD}" stroke-width="1.2"/>'


# ── header ─────────────────────────────────────────────────────────────────────
def header():
    W, H = 1200, 400
    HL = 13  # annotation size; GitHub shows the banner at ~0.7x
    # crown vertices, all on lattice points (odd rows, centre column x=924)
    c = 77  # centre column in half-steps → x = 924
    side_top, valley, apex, band_top, band_bot = 5, 9, 3, 13, 15
    L, R = c - 12, c + 12  # x = 780 / 1068
    crown = [lat(L, band_top), lat(L, side_top), lat(c - 6, valley), lat(c, apex), lat(c + 6, valley), lat(R, side_top), lat(R, band_top)]
    (bx0, by0), (bx1, by1) = lat(L, band_top), lat(R, band_bot)
    cx, apex_y = lat(c, apex)
    cy = (apex_y + by1) / 2
    rad = hypot(bx0 - cx, by1 - cy)

    # construction: extended edges, circumscribed circle, centre axis, band diagonals
    def extend(p, q, t=0.35):
        (x0, y0), (x1, y1) = p, q
        return f'<line x1="{x0 - (x1 - x0) * t:.2f}" y1="{y0 - (y1 - y0) * t:.2f}" x2="{x1 + (x1 - x0) * t:.2f}" y2="{y1 + (y1 - y0) * t:.2f}"/>'

    construction = "".join(extend(crown[i], crown[i + 1]) for i in range(1, 5))
    construction += f'<line x1="{cx}" y1="{apex_y - 34:.2f}" x2="{cx}" y2="{by1 + 26:.2f}" stroke-dasharray="2 5"/>'
    construction += f'<line x1="{bx0}" y1="{by0:.2f}" x2="{bx1}" y2="{by1:.2f}"/><line x1="{bx1}" y1="{by0:.2f}" x2="{bx0}" y2="{by1:.2f}"/>'

    # vertical dimension (12 lattice rows, apex → base), ticked per row
    dx = bx1 + 40
    ticks = "".join(f'<line x1="{dx - (6 if r % 3 == 0 else 3)}" y1="{r * HEX_H:.2f}" x2="{dx}" y2="{r * HEX_H:.2f}"/>' for r in range(apex, band_bot + 1))
    dim_v = f'<line x1="{dx}" y1="{apex_y:.2f}" x2="{dx}" y2="{by1:.2f}"/>{ticks}'
    # horizontal dimension under the base
    hy = by1 + 22
    dim_h = f'<line x1="{bx0}" y1="{hy:.2f}" x2="{bx1}" y2="{hy:.2f}"/><line x1="{bx0}" y1="{hy - 5:.2f}" x2="{bx0}" y2="{hy + 5:.2f}"/><line x1="{bx1}" y1="{hy - 5:.2f}" x2="{bx1}" y2="{hy + 5:.2f}"/>'

    gems = "".join(
        f'<circle cx="{x:.2f}" cy="{y:.2f}" r="11" fill="none" stroke="{GOLD}" stroke-opacity=".35" class="breathe" style="animation-delay:{i * 2}s"/>'
        f'<circle cx="{x:.2f}" cy="{y:.2f}" r="4.6" fill="{GOLD}"/>'
        for i, (x, y) in enumerate([crown[1], crown[3], crown[5]])
    )
    nodes = "".join(node(x, y) for x, y in [crown[0], crown[2], crown[4], crown[6], (bx0, by1), (bx1, by1)])

    # left column
    X = 72
    name_size = 128
    caleb_w = SERIF.width("Caleb", name_size, -2)
    name = text(SERIF, "Caleb", name_size, X - 4, 202, WHITE, -2) + text(SERIF_IT, "King", name_size, X - 4 + caleb_w + 30, 202, GOLD, -2)
    rule = (f'<line x1="{X}" y1="236" x2="{X + 56}" y2="236" stroke="{GOLD}" stroke-width="1.5"/>'
            f'<line x1="{X + 64}" y1="236" x2="{X + 520}" y2="236" stroke="{GOLD}" stroke-opacity=".22"/>'
            + "".join(f'<line x1="{X + 64 + i * 32}" y1="233" x2="{X + 64 + i * 32}" y2="239" stroke="{GOLD}" stroke-opacity=".22"/>' for i in range(15)))
    lines = ["Engineer to engineering director by thirty.", "Breaking down AI in plain language.", "Building AI-native products, in public."]
    taglines = "".join(text(SERIF_IT, s, 31, X, 282, "#CFCBC2", cls=f"t t{i + 1}") for i, s in enumerate(lines))

    style = BASE_STYLE + """
    .t1 { animation: first 15s infinite; }
    .t2, .t3 { opacity: 0; animation: next 15s infinite; }
    .t2 { animation-delay: 5s; } .t3 { animation-delay: 10s; }
    @keyframes first { 0%,30% { opacity: 1; } 33%,97% { opacity: 0; } 100% { opacity: 1; } }
    @keyframes next  { 0% { opacity: 0; } 3%,30% { opacity: 1; } 33%,100% { opacity: 0; } }
    .cursor { animation: blink 1.1s steps(1) infinite; }
    @keyframes blink { 50% { opacity: 0; } }
    .scan { animation: scan 9s cubic-bezier(.45,0,.55,1) infinite; }
    @keyframes scan { 0%,100% { transform: translateY(0); } 50% { transform: translateY(SCANpx); } }""".replace("SCAN", f"{by1 - apex_y:.1f}")

    cursor_x = X + MONO.width("~/CALEBKING3", HL, HL * 0.22) + 6
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="Caleb King. Engineer to engineering director by thirty. Educator, engineer, innovator.">
  {defs(W, H, cx, cy, 330)}
  <style>{style}</style>
  <g clip-path="url(#frame)">
    {ground(W, H)}

    <!-- fig. 01 — the crown, drafted -->
    <g fill="none" stroke="{GOLD}" stroke-width="1" stroke-opacity=".2">{construction}</g>
    <g class="spin" style="transform-origin:{cx}px {cy:.2f}px"><circle cx="{cx}" cy="{cy:.2f}" r="{rad:.2f}" fill="none" stroke="{GOLD}" stroke-opacity=".22" stroke-dasharray="1 7"/></g>
    <g fill="none" stroke="{GOLD}" stroke-width="1" stroke-opacity=".5">{dim_v}{dim_h}</g>
    <polygon points="{pts(crown)}" fill="{GOLD}" fill-opacity=".045"/>
    <polyline points="{pts(crown)}" fill="none" stroke="{GOLD}" stroke-width="2" stroke-linejoin="miter"/>
    <rect x="{bx0}" y="{by0:.2f}" width="{bx1 - bx0}" height="{by1 - by0:.2f}" fill="{GOLD}" fill-opacity=".09" stroke="{GOLD}" stroke-width="2"/>
    <g class="scan"><line x1="{bx0 - 30}" y1="{apex_y:.2f}" x2="{bx1 + 30}" y2="{apex_y:.2f}" stroke="{GOLD}" stroke-opacity=".35"/></g>
    {nodes}{gems}
    {label("30", dx + 10, cy + 4, opacity=.7, size=HL)}
    {label(f"{bx1 - bx0:.0f}", cx, hy + 18, opacity=.55, anchor="middle", size=HL)}
    {label("Fig. 01 — Regalia, drafted", bx1 + 40, H - 30, fill="#8C8779", anchor="end", size=HL)}

    <!-- identity -->
    {label("~/calebking3", X, 76, size=HL)}
    <rect class="cursor" x="{cursor_x:.1f}" y="{76 - HL * 0.9:.1f}" width="{HL * 0.62:.1f}" height="{HL * 1.05:.1f}" fill="{GOLD}"/>
    {label("Engineer → Director", X + 470 + 50, 76, fill="#8C8779", anchor="end", size=HL)}
    {name}
    {rule}
    {taglines}
    {label("Educator · Engineer · Innovator · Tech Dad", X, H - 30, fill="#8C8779", size=HL)}

    {corner_marks(W, H)}
    <rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="15.5" fill="none" stroke="{GOLD}" stroke-opacity=".16"/>
  </g>
</svg>
"""


# ── cards ──────────────────────────────────────────────────────────────────────
def glyph_launch(cx, cy):
    # a ballistic arc sampled at even intervals; launch point, apex, and landing ticks
    p = [(cx - 78 + t * 156, cy + 52 - 4 * 104 * t * (1 - t)) for t in [i / 24 for i in range(25)]]
    arc = f'<polyline points="{pts(p[:19])}" fill="none" stroke="{GOLD}" stroke-width="2"/>'
    ghost = f'<polyline points="{pts(p[18:])}" fill="none" stroke="{GOLD}" stroke-opacity=".3" stroke-dasharray="3 5"/>'
    ticks = "".join(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="1.3" fill="{GOLD}" fill-opacity=".6"/>' for x, y in p[2:18:2])
    con = (f'<line x1="{p[0][0]}" y1="{p[0][1]}" x2="{p[0][0] + 70}" y2="{p[0][1] - 140}" />'
           f'<line x1="{cx - 96}" y1="{cy + 52}" x2="{cx + 96}" y2="{cy + 52}"/>'
           f'<line x1="{cx}" y1="{cy - 70}" x2="{cx}" y2="{cy + 60}" stroke-dasharray="2 5"/>')
    ring = f'<g class="spin" style="transform-origin:{cx}px {cy}px"><circle cx="{cx}" cy="{cy}" r="96" fill="none" stroke="{GOLD}" stroke-opacity=".2" stroke-dasharray="1 7"/></g>'
    ax, ay = p[12]
    return (f'<g fill="none" stroke="{GOLD}" stroke-opacity=".2">{con}</g>{ring}{ghost}{arc}{ticks}'
            + node(*p[0]) + f'<circle cx="{ax:.2f}" cy="{ay:.2f}" r="11" fill="none" stroke="{GOLD}" stroke-opacity=".35" class="breathe"/><circle cx="{ax:.2f}" cy="{ay:.2f}" r="4.6" fill="{GOLD}"/>'
            + node(*p[18]))


def glyph_play(cx, cy):
    r = 70
    tri = [(cx + r * cos(radians(a)), cy + r * sin(radians(a))) for a in (0, 120, 240)]
    con = "".join(f'<line x1="{cx}" y1="{cy}" x2="{x:.2f}" y2="{y:.2f}"/>' for x, y in tri)
    con += f'<circle cx="{cx}" cy="{cy}" r="{r / 2}" fill="none"/><line x1="{cx - 96}" y1="{cy}" x2="{cx + 96}" y2="{cy}" stroke-dasharray="2 5"/>'
    ring = f'<g class="spin" style="transform-origin:{cx}px {cy}px"><circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{GOLD}" stroke-opacity=".3" stroke-dasharray="1 7"/></g>'
    return (f'<g fill="none" stroke="{GOLD}" stroke-opacity=".2">{con}</g>{ring}'
            f'<polygon points="{pts(tri)}" fill="{GOLD}" fill-opacity=".07" stroke="{GOLD}" stroke-width="2" stroke-linejoin="miter"/>'
            + node(*tri[1]) + node(*tri[2])
            + f'<circle cx="{tri[0][0]:.2f}" cy="{tri[0][1]:.2f}" r="11" fill="none" stroke="{GOLD}" stroke-opacity=".35" class="breathe"/><circle cx="{tri[0][0]:.2f}" cy="{tri[0][1]:.2f}" r="4.6" fill="{GOLD}"/>'
            + f'<path d="M{cx - 4},{cy}h8M{cx},{cy - 4}v8" stroke="{GOLD}" stroke-opacity=".7"/>')


def glyph_letter(cx, cy):
    w, h = 176, 112
    x0, y0, x1, y1 = cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2
    fold = (cx, cy + 10)
    con = (f'<line x1="{x0}" y1="{y1}" x2="{fold[0]}" y2="{fold[1]}"/><line x1="{x1}" y1="{y1}" x2="{fold[0]}" y2="{fold[1]}"/>'
           f'<line x1="{cx}" y1="{y0 - 22}" x2="{cx}" y2="{y1 + 22}" stroke-dasharray="2 5"/>'
           f'<line x1="{x0 - 18}" y1="{y0}" x2="{x0}" y2="{y0}"/><line x1="{x1}" y1="{y1}" x2="{x1 + 18}" y2="{y1}"/>')
    ring = f'<g class="spin" style="transform-origin:{cx}px {cy}px"><circle cx="{cx}" cy="{cy}" r="{hypot(w, h) / 2:.2f}" fill="none" stroke="{GOLD}" stroke-opacity=".2" stroke-dasharray="1 7"/></g>'
    return (f'<g fill="none" stroke="{GOLD}" stroke-opacity=".2">{con}</g>{ring}'
            f'<rect x="{x0}" y="{y0}" width="{w}" height="{h}" fill="{GOLD}" fill-opacity=".05" stroke="{GOLD}" stroke-width="2"/>'
            f'<polyline points="{pts([(x0, y0), fold, (x1, y0)])}" fill="none" stroke="{GOLD}" stroke-width="2" stroke-linejoin="miter"/>'
            + node(x0, y0) + node(x1, y0)
            + f'<circle cx="{fold[0]}" cy="{fold[1]}" r="11" fill="none" stroke="{GOLD}" stroke-opacity=".35" class="breathe"/><circle cx="{fold[0]}" cy="{fold[1]}" r="4.6" fill="{GOLD}"/>')


def glyph_prompt(cx, cy):
    # a prompt chevron and cursor bar set on a 24px module grid
    s = 24
    chev = [(cx - 3 * s, cy - 2 * s), (cx - s, cy), (cx - 3 * s, cy + 2 * s)]
    bar = (cx + 0.5 * s, cy + 2 * s - 3, 2.5 * s, 6)
    grid = "".join(f'<line x1="{cx - 4 * s}" y1="{cy + i * s}" x2="{cx + 4 * s}" y2="{cy + i * s}"/>' for i in range(-2, 3))
    grid += "".join(f'<line x1="{cx + i * s}" y1="{cy - 3 * s}" x2="{cx + i * s}" y2="{cy + 3 * s}"/>' for i in range(-4, 5))
    ring = f'<g class="spin" style="transform-origin:{cx}px {cy}px"><circle cx="{cx}" cy="{cy}" r="{3.6 * s}" fill="none" stroke="{GOLD}" stroke-opacity=".2" stroke-dasharray="1 7"/></g>'
    return (f'<g fill="none" stroke="{GOLD}" stroke-opacity=".1">{grid}</g>{ring}'
            f'<polyline points="{pts(chev)}" fill="none" stroke="{GOLD}" stroke-width="2" stroke-linejoin="miter"/>'
            f'<rect class="cursor" x="{bar[0]}" y="{bar[1]}" width="{bar[2]}" height="{bar[3]}" fill="{GOLD}"/>'
            + node(*chev[0]) + node(*chev[2])
            + f'<circle cx="{chev[1][0]}" cy="{chev[1][1]}" r="11" fill="none" stroke="{GOLD}" stroke-opacity=".35" class="breathe"/><circle cx="{chev[1][0]}" cy="{chev[1][1]}" r="4.6" fill="{GOLD}"/>')


CARDS = [
    ("launchkit", "01", "SaaS starter kit", "LaunchKit", ["Auth, billing, AI and teams, pre-built.", "Ship your SaaS this weekend."], "getlaunchkit.app", glyph_launch),
    ("youtube", "02", "YouTube", "Caleb King", ["AI and engineering in plain", "language, with real examples."], "youtube.com/@CalebKing0", glyph_play),
    ("newsletter", "03", "Newsletter", "Build Different", ["Notes from the road, engineer", "to director, in your inbox."], "newsletter.kingcaleb.com", glyph_letter),
    ("prompts", "04", "Open source", "Prompt Library", ["My favorite AI prompts for", "image, video and product."], "github.com/CalebKing3/promptLibrary", glyph_prompt),
]


def card(idx, kind, title, lines, url, glyph):
    W, H = 800, 280
    gx, gy = 648, 140
    X = 44
    body = "".join(text(SERIF_IT, s, 22, X, 178 + i * 27, "#A9A497") for i, s in enumerate(lines))
    style = BASE_STYLE + """
    .cursor { animation: blink 1.1s steps(1) infinite; }
    @keyframes blink { 50% { opacity: 0; } }"""
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="{title}: {' '.join(lines)}">
  {defs(W, H, gx, gy, 230)}
  <style>{style}</style>
  <g clip-path="url(#frame)">
    {ground(W, H)}
    {glyph(gx, gy)}
    {label(f"{idx} — {kind}", X, 60, size=16)}
    {text(SERIF, title, 62, X - 2, 130, WHITE, -1)}
    {body}
    <line x1="{X}" y1="236" x2="{X + 28}" y2="236" stroke="{GOLD}" stroke-width="1.5"/>
    {label(url + " ↗", X + 40, 242, size=16)}
    {label(f"Fig. {idx}", W - 40, H - 36, fill="#8C8779", anchor="end", size=16)}
    {corner_marks(W, H, inset=16, arm=10)}
    <rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="15.5" fill="none" stroke="{GOLD}" stroke-opacity=".16"/>
  </g>
</svg>
"""


if __name__ == "__main__":
    (ROOT / "assets" / "cards").mkdir(parents=True, exist_ok=True)
    (ROOT / "assets" / "header.svg").write_text(header())
    print("wrote header.svg")
    for slug, idx, kind, title, lines, url, glyph in CARDS:
        (ROOT / "assets" / "cards" / f"{slug}.svg").write_text(card(idx, kind, title, lines, url, glyph))
        print("wrote", slug)
