#!/usr/bin/env python3
"""Generate the drawn persona avatars in assets/avatars/<slug>.svg.

Shaded, slightly 3D illustrations: every face uses the same neutral features, and
each person is suggested only through hair colour and style, glasses, clothing and
one emblem. They are deliberately not portraits or caricatures of the real person.
Edit STYLES and re-run:  python3 -I make_avatars.py
"""
import pathlib

OUT = pathlib.Path(__file__).resolve().parent.parent / "assets" / "avatars"


def shade(hex_color, f):
    """Lighten (f > 0) or darken (f < 0) a #rrggbb colour."""
    h = hex_color.lstrip("#")
    rgb = [int(h[i:i + 2], 16) for i in (0, 2, 4)]
    rgb = [round(c + (255 - c) * f) if f > 0 else round(c * (1 + f)) for c in rgb]
    return "#" + "".join(f"{max(0, min(255, c)):02x}" for c in rgb)


# ---- clothing -------------------------------------------------------------
SHOULDERS = "M4 100 C4 74 23 60 48 60 C73 60 92 74 92 100 Z"


def suit(jacket, shirt="#f4f3ef", tie=None, tie_long=False):
    s = f'<path d="{SHOULDERS}" fill="url(#cloth)"/>'
    s += f'<path d="M39 60 L48 82 L57 60 Z" fill="{shirt}"/>'
    if tie:
        end = 100 if tie_long else 86
        s += (f'<path d="M46 64 L50 64 L52.2 {end} L48 {end + 3} L43.8 {end} Z" fill="{tie}"/>'
              f'<path d="M45.3 60.5 L50.7 60.5 L50 64.5 L46 64.5 Z" fill="{shade(tie, -0.2)}"/>')
    s += (f'<path d="M39 60 L45.5 78 L40 81 L33 63 Z M57 60 L50.5 78 L56 81 L63 63 Z" '
          f'fill="{shade(jacket, 0.08)}"/>')
    return s


def plain(garment, collar=None):
    s = f'<path d="{SHOULDERS}" fill="url(#cloth)"/>'
    if collar == "crew":
        s += '<path d="M39.5 60.5 Q48 68 56.5 60.5" fill="none" stroke="#000" stroke-opacity=".3" stroke-width="1.6"/>'
    if collar == "open":
        s += ('<path d="M40 60 L48 73 L56 60 Z" fill="url(#skin)"/>'
              f'<path d="M40 60 L46.5 68 L41 71 Z M56 60 L49.5 68 L55 71 Z" fill="{shade(garment, 0.15)}"/>')
    return s


def turtleneck(color):
    return (f'<path d="{SHOULDERS}" fill="url(#cloth)"/>'
            f'<rect x="39.5" y="49" width="17" height="15" rx="6" fill="{shade(color, 0.06)}"/>'
            f'<path d="M41 54 H55 M41 57.5 H55" stroke="#fff" stroke-opacity=".07" stroke-width="1"/>')


# ---- hair -----------------------------------------------------------------
def hair(style, color):
    hi, lo = shade(color, 0.25), shade(color, -0.25)
    grad = (f'<linearGradient id="hair" x1="0" y1="0" x2="0" y2="1">'
            f'<stop offset="0" stop-color="{hi}"/><stop offset="1" stop-color="{lo}"/></linearGradient>')
    shapes = {
        "short": 'M32.5 33 C31 19 40 14 48 14 C57 14 65 19 63.5 33 C61 26 56 22.5 48 22.5 C40 22.5 35 26 32.5 33 Z',
        "fuller": 'M31.5 34 C29 18 39 12.5 48 12.5 C58 12.5 67 18 64.5 34 C62.5 27 58 21.5 48 21.5 C39 21.5 34 27 31.5 34 Z',
        "wavy": 'M31.5 35 C28.5 22 34 13 44 12.5 C47 11 52 11.5 55 13 C63 15 67.5 22 64.5 35 C63 29 60 24 55.5 23 C52 21.5 46 21.5 42 23 C36 24.5 33 29 31.5 35 Z',
        "receding": 'M32.5 34 C31.5 24 36 17.5 42 16.2 C40.5 19 40 22 41 24.5 C37 26 34 29.5 32.5 34 Z M63.5 34 C64.5 24 60 17.5 54 16.2 C55.5 19 56 22 55 24.5 C59 26 62 29.5 63.5 34 Z',
        "combed": 'M32.5 33.5 C31 20 39 14.5 48.5 14.5 C58 14.5 65 20 63.5 33.5 C61.5 27.5 57 23.5 50 23.2 C44 21.8 37 25 32.5 33.5 Z',
        "sides": 'M32.4 36.5 C31.8 31 32.6 28 34.6 26.6 C34.2 30 34.4 33 35.6 37.5 Z M63.6 36.5 C64.2 31 63.4 28 61.4 26.6 C61.8 30 61.6 33 60.4 37.5 Z',
        "swept": 'M31.8 33.5 C30 19.5 39.5 13.2 49.5 13.6 C58.5 14 66 19.5 64.2 32 C62.2 25.6 57.5 21.6 51.5 21.4 C45 21 38.5 24.5 31.8 33.5 Z',
        "bald": "",
    }
    d = shapes[style]
    return grad, (f'<path d="{d}" fill="url(#hair)"/>' if d else "")


# ---- face -----------------------------------------------------------------
def beard(color):
    return (f'<path d="M34 40 C35 52 41 57.5 48 57.5 C55 57.5 61 52 62 40 C59 47 55 50 48 50 C41 50 37 47 34 40 Z" fill="{color}" fill-opacity=".9"/>'
            f'<path d="M43.5 47.6 Q48 46 52.5 47.6 Q48 49.5 43.5 47.6 Z" fill="{color}"/>')


def jacket_leather(color):
    return (f'<path d="{SHOULDERS}" fill="url(#cloth)"/>'
            '<path d="M39 60 L48 76 L57 60 Z" fill="#2a2a2c"/>'
            f'<path d="M39 60 L45 74 L38 80 L31 64 Z M57 60 L51 74 L58 80 L65 64 Z" fill="{shade(color, 0.12)}"/>'
            '<path d="M26 70 Q30 68 33 72 M70 70 Q66 68 63 72" stroke="#fff" stroke-opacity=".18" stroke-width="1.2" fill="none"/>')


def face(skin, brow, stubble=False, bald_shine=False):
    s = (f'<ellipse cx="33.4" cy="38" rx="3" ry="4.6" fill="{shade(skin, -0.12)}"/>'
         f'<ellipse cx="62.6" cy="38" rx="3" ry="4.6" fill="{shade(skin, -0.12)}"/>'
         '<ellipse cx="48" cy="35.5" rx="15" ry="18" fill="url(#skin)"/>')
    if bald_shine:
        s += '<ellipse cx="43" cy="22.5" rx="6" ry="3" fill="#fff" fill-opacity=".28"/>'
    if stubble:
        s += f'<path d="M34.5 41 C36 50 42 54 48 54 C54 54 60 50 61.5 41 C58 48 53 50.5 48 50.5 C43 50.5 38 48 34.5 41 Z" fill="{brow}" fill-opacity=".22"/>'
    s += (f'<path d="M39.5 32.6 Q43 30.8 46 32.2" fill="none" stroke="{brow}" stroke-width="1.5" stroke-linecap="round"/>'
          f'<path d="M50 32.2 Q53 30.8 56.5 32.6" fill="none" stroke="{brow}" stroke-width="1.5" stroke-linecap="round"/>'
          '<ellipse cx="42.8" cy="36.6" rx="2.5" ry="1.65" fill="#fbfaf8"/><ellipse cx="53.2" cy="36.6" rx="2.5" ry="1.65" fill="#fbfaf8"/>'
          '<circle cx="42.9" cy="36.7" r="1.25" fill="#3b2f2a"/><circle cx="53.3" cy="36.7" r="1.25" fill="#3b2f2a"/>'
          '<circle cx="43.3" cy="36.3" r=".4" fill="#fff"/><circle cx="53.7" cy="36.3" r=".4" fill="#fff"/>'
          f'<path d="M48.2 37.5 C47.2 40.5 46.4 42.5 47.2 43.6 C48 44.2 49.3 44 50 43.4" fill="none" stroke="{shade(skin, -0.28)}" stroke-width="1" stroke-linecap="round"/>'
          f'<path d="M44.2 47.4 Q48 49.6 51.8 47.4" fill="none" stroke="{shade(skin, -0.4)}" stroke-width="1.15" stroke-linecap="round"/>'
          f'<ellipse cx="39.5" cy="43" rx="2.6" ry="1.5" fill="#e07a6a" fill-opacity=".14"/><ellipse cx="56.5" cy="43" rx="2.6" ry="1.5" fill="#e07a6a" fill-opacity=".14"/>')
    return s


def glasses(r=4.6, w=1.1, color="#3a3a3a", square=False):
    if square:
        frames = (f'<rect x="{42.8 - r}" y="{36.6 - r * .78}" width="{2 * r}" height="{1.56 * r}" rx="1.4"/>'
                  f'<rect x="{53.2 - r}" y="{36.6 - r * .78}" width="{2 * r}" height="{1.56 * r}" rx="1.4"/>')
    else:
        frames = f'<circle cx="42.8" cy="36.6" r="{r}"/><circle cx="53.2" cy="36.6" r="{r}"/>'
    return (f'<g fill="#ffffff" fill-opacity=".12" stroke="{color}" stroke-width="{w}">{frames}</g>'
            f'<path d="M{42.8 + r} 36.4 Q48 35 {53.2 - r} 36.4 M{42.8 - r} 36 L33.6 35 M{53.2 + r} 36 L62.4 35" '
            f'fill="none" stroke="{color}" stroke-width="{w}"/>')


EMBLEMS = {
    "rocket": '<g transform="translate(60 70)"><path d="M6 0 C10 4 10 12 8 16 H4 C2 12 2 4 6 0 Z" fill="#f4f4f2"/><circle cx="6" cy="7" r="1.6" fill="#2b2f36"/><path d="M4 13 L1 18 L4 16 Z M8 13 L11 18 L8 16 Z" fill="#f4f4f2"/><path d="M5 16 L6 20 L7 16 Z" fill="#f0a24a"/></g>',
    "question": '<g transform="translate(58 70)"><path d="M0 4 a4 4 0 0 1 4 -4 h10 a4 4 0 0 1 4 4 v6 a4 4 0 0 1 -4 4 h-7 l-4 3 v-3 a4 4 0 0 1 -3 -4 Z" fill="#f4f4f2"/><text x="9" y="11" font-family="Georgia,serif" font-size="10" text-anchor="middle" fill="#7a6f62">?</text></g>',
    "diagram": '<g transform="translate(57 74)" fill="none" stroke="#f4f4f2" stroke-width="1.4" stroke-linecap="round"><path d="M0 0 L5 6 L0 12"/><path d="M5 6 q1.5 -3 3 0 t3 0 t3 0 t3 0"/><path d="M17 6 L22 0 M17 6 L22 12"/></g>',
    "chip": '<g transform="translate(59 72)"><rect x="3" y="3" width="12" height="12" rx="1.5" fill="#cfd8e3"/><rect x="6" y="6" width="6" height="6" fill="#39424a"/><path d="M5 0 V3 M9 0 V3 M13 0 V3 M5 15 V18 M9 15 V18 M13 15 V18 M0 5 H3 M0 9 H3 M0 13 H3 M15 5 H18 M15 9 H18 M15 13 H18" stroke="#cfd8e3" stroke-width="1.2"/></g>',
    "newspaper": '<g transform="translate(58 72)"><rect width="18" height="14" rx="1" fill="#f4f1e8"/><path d="M3 3.5 H15 M3 6.5 H9 M3 9 H9 M3 11.5 H9" stroke="#8a8478" stroke-width="1"/><rect x="11" y="6" width="4" height="6" fill="#bdb6a8"/></g>',
    "books": '<g transform="translate(58 72)"><rect x="0" y="10" width="18" height="5" rx="1" fill="#8a3b3b"/><rect x="2" y="5" width="15" height="5" rx="1" fill="#3f5d7a"/><rect x="1" y="0" width="16" height="5" rx="1" fill="#c9a24a"/></g>',
    "football": '<g transform="translate(67 80)"><circle r="8" fill="#f4f4f2"/><path d="M0 -3.4 L3.2 -1 L2 2.8 L-2 2.8 L-3.2 -1 Z" fill="#23262b"/><path d="M0 -3.4 V-8 M3.2 -1 L7.6 -2.4 M2 2.8 L4.7 6.5 M-2 2.8 L-4.7 6.5 M-3.2 -1 L-7.6 -2.4" stroke="#23262b" stroke-width="1"/></g>',
    "box": '<g transform="translate(58 72)"><path d="M0 4 L9 0 L18 4 V14 L9 18 L0 14 Z" fill="#c79a5b"/><path d="M0 4 L9 8 L18 4 M9 8 V18" fill="none" stroke="#8a6534" stroke-width="1"/></g>',
    "shield": '<g transform="translate(59 71)"><path d="M8 0 L16 3 V9 C16 14 12 17 8 18 C4 17 0 14 0 9 V3 Z" fill="#e9e4d8"/><path d="M4.5 9 L7.2 11.7 L12 6.5" fill="none" stroke="#6a7f5e" stroke-width="1.6" stroke-linecap="round"/></g>',
    "gpu": '<g transform="translate(57 73)"><rect width="20" height="12" rx="2" fill="#3a3d42"/><circle cx="6.5" cy="6" r="4" fill="#5b6068"/><circle cx="6.5" cy="6" r="1.3" fill="#2a2c30"/><circle cx="14.5" cy="6" r="4" fill="#5b6068"/><circle cx="14.5" cy="6" r="1.3" fill="#2a2c30"/><rect x="2" y="12" width="12" height="2" fill="#c9a24a"/></g>',
    "cycle": '<g transform="translate(59 71)" fill="none" stroke="#f4f4f2" stroke-width="1.8" stroke-linecap="round"><path d="M14 5 A7 7 0 0 0 2.5 7"/><path d="M2 13 A7 7 0 0 0 13.5 11"/><path d="M14 1 V5 H10 M2 17 V13 H6"/></g>',
    "check": '<g transform="translate(59 72)"><circle cx="8" cy="8" r="8" fill="#3f8f5a"/><path d="M4.2 8.3 L7 11 L12 5.5" fill="none" stroke="#fff" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></g>',
    "bolt": '<g transform="translate(61 70)"><path d="M8 0 L0 11 H6 L4 20 L13 7 H7 Z" fill="#f2c14e"/></g>',
    "angle": '<g transform="translate(57 73)"><rect width="21" height="13" rx="3" fill="#3f6fb5"/><text x="10.5" y="9.6" font-family="Menlo,monospace" font-size="8" font-weight="700" text-anchor="middle" fill="#fff">&lt;T&gt;</text></g>',
}

# skin, hair (style, colour), brow, clothing (kind, colour, extras), glasses, emblem, background
EMBLEMS.update({
    "pager": '<g transform="translate(58 72)"><rect width="18" height="13" rx="2.5" fill="#2f3338"/><rect x="2.5" y="2.5" width="13" height="5" rx="1" fill="#9fd3a8"/><path d="M4 5 L6 3.5 L8 6 L10 3.5 L12 5.5 L14 4.5" fill="none" stroke="#2f3338" stroke-width=".9"/><circle cx="5" cy="10.3" r="1" fill="#e2574c"/></g>',
    "blocks": '<g transform="translate(58 71)"><rect x="0" y="10" width="9" height="8" rx="1" fill="#7f9bb8"/><rect x="9" y="10" width="9" height="8" rx="1" fill="#a9bccf"/><rect x="4.5" y="2" width="9" height="8" rx="1" fill="#d3dbe4"/></g>',
    "sprout": '<g transform="translate(60 70)"><path d="M8 20 V9" stroke="#5c8f4f" stroke-width="1.8" stroke-linecap="round"/><path d="M8 11 C3 11 1 7 1 4 C5 4 8 6 8 11 Z" fill="#7fb36b"/><path d="M8 9 C12 9 15 6 15 2 C11 2 8 5 8 9 Z" fill="#9ccc84"/><rect x="2" y="17" width="12" height="4" rx="1.5" fill="#b8865b"/></g>',
    "target": '<g transform="translate(58 71)"><circle cx="9" cy="9" r="8.5" fill="#f4f4f2"/><circle cx="9" cy="9" r="5.6" fill="#e2574c"/><circle cx="9" cy="9" r="2.8" fill="#f4f4f2"/><circle cx="9" cy="9" r="1.2" fill="#e2574c"/></g>',
    "phone": '<g transform="translate(60 70)"><rect width="12" height="19" rx="2.5" fill="#2f3338"/><rect x="1.5" y="2.5" width="9" height="13" rx="1" fill="#dfe7ef"/><text x="6" y="12.5" font-family="Arial,sans-serif" font-size="9" font-weight="700" text-anchor="middle" fill="#e2574c">!</text></g>',
    "magnifier": '<g transform="translate(58 70)" fill="none" stroke="#f4f4f2" stroke-width="2.2" stroke-linecap="round"><circle cx="8" cy="8" r="6"/><path d="M12.5 12.5 L18 18"/></g>',
    "cross": '<g transform="translate(59 71)"><circle cx="8.5" cy="8.5" r="8.5" fill="#f4f4f2"/><path d="M6.5 3.5 H10.5 V6.5 H13.5 V10.5 H10.5 V13.5 H6.5 V10.5 H3.5 V6.5 H6.5 Z" fill="#3f9a8a"/></g>',
    "coin": '<g transform="translate(59 71)"><circle cx="8.5" cy="8.5" r="8.5" fill="#d9ad4a"/><circle cx="8.5" cy="8.5" r="6.3" fill="none" stroke="#b88c2e" stroke-width="1"/><text x="8.5" y="12" font-family="Georgia,serif" font-size="9.5" font-weight="700" text-anchor="middle" fill="#8a6522">$</text></g>',
    "clipboard": '<g transform="translate(60 69)"><rect y="2" width="15" height="19" rx="2" fill="#c79a5b"/><rect x="2" y="5" width="11" height="14" rx="1" fill="#f4f1e8"/><rect x="4.5" width="6" height="4" rx="1" fill="#8a8478"/><path d="M4 9.5 L5.5 11 L8 8.5 M4 14.5 L5.5 16 L8 13.5" fill="none" stroke="#3f8f5a" stroke-width="1.1" stroke-linecap="round"/><path d="M9.5 10 H11.5 M9.5 15 H11.5" stroke="#8a8478" stroke-width="1"/></g>',
    "mug": '<g transform="translate(58 72)"><path d="M1 2 H14 V13 a4 4 0 0 1 -4 4 H5 a4 4 0 0 1 -4 -4 Z" fill="#f4f4f2"/><path d="M14 5 h2 a3 3 0 0 1 0 6 h-2" fill="none" stroke="#f4f4f2" stroke-width="1.8"/><path d="M5 -1 q1.5 -2 0 -4 M9 -1 q1.5 -2 0 -4" fill="none" stroke="#f4f4f2" stroke-opacity=".7" stroke-width="1" stroke-linecap="round"/></g>',
    "flip": '<g transform="translate(58 72)" fill="none" stroke="#f4f4f2" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M2 4 H16 M12 0 L16 4 L12 8"/><path d="M16 13 H2 M6 9 L2 13 L6 17"/></g>',
    "chart": '<g transform="translate(58 71)"><rect width="19" height="17" rx="2" fill="#f4f4f2"/><rect x="3" y="10" width="3" height="4" fill="#7f9bb8"/><rect x="8" y="7" width="3" height="7" fill="#5f81a6"/><rect x="13" y="4" width="3" height="10" fill="#3f6fb5"/></g>',
})

# Archetypes (fictional roles): neutral faces, no ties or beards, varied skin tones; the emblem names the role.
ARCHETYPES = {
    "skeptical-security-architect": dict(bg="#e2e6ec", skin="#c99a78", hair=("short", "#2e2a28"), brow="#2a2523", cloth=("suit", "#3a4049", None), glasses=dict(r=4.5, w=1.2, color="#2f2f2f", square=True), emblem="shield"),
    "pragmatic-staff-engineer": dict(bg="#e3ece1", skin="#e8c6a8", hair=("fuller", "#6b4e3a"), brow="#5a4232", cloth=("plain", "#5f7d6a", "crew"), emblem="blocks"),
    "on-call-sre": dict(bg="#ece4dc", skin="#a77657", hair=("wavy", "#1f1c1b"), brow="#1d1a19", cloth=("plain", "#384b63", "crew"), emblem="pager"),
    "curious-junior-developer": dict(bg="#e6eef6", skin="#f0d2b8", hair=("swept", "#b07a4a"), brow="#946440", cloth=("plain", "#e0a85a", "crew"), emblem="sprout"),
    "outcome-driven-product-manager": dict(bg="#efe6e2", skin="#d9a985", hair=("combed", "#3b302b"), brow="#33281f", cloth=("suit", "#5a6b82", None), emblem="target"),
    "frustrated-end-user": dict(bg="#ece9e2", skin="#8f5f45", hair=("short", "#1a1817"), brow="#171514", cloth=("plain", "#9a5d5d", "crew"), emblem="phone"),
    "ux-researcher": dict(bg="#e7e2ef", skin="#e3bd9c", hair=("wavy", "#7a5a3c"), brow="#62472f", cloth=("plain", "#7d6aa3", "open"), glasses=dict(r=4.4, w=1.0, color="#5a4a6a"), emblem="magnifier"),
    "frontline-clinician": dict(bg="#dfeceb", skin="#c08a66", hair=("short", "#2b2523"), brow="#262120", cloth=("plain", "#5aa39a", "open"), emblem="cross"),
    "cost-conscious-cfo": dict(bg="#ebe7de", skin="#eccbb0", hair=("combed", "#9a948d"), brow="#7f7a74", cloth=("suit", "#2f3a46", None), glasses=dict(r=4.6, w=1.1, color="#3a3a3a"), emblem="coin"),
    "compliance-auditor": dict(bg="#e6e6e1", skin="#b88463", hair=("short", "#3a3431"), brow="#2f2a27", cloth=("suit", "#4b5258", None), glasses=dict(r=4.4, w=1.3, color="#2a2a2a", square=True), emblem="clipboard"),
    "battle-scarred-veteran": dict(bg="#e9e2d7", skin="#e2b998", hair=("receding", "#c9c4bd"), brow="#aca69e", stubble=True, cloth=("plain", "#5a5f66", "crew"), emblem="mug"),
    "devils-advocate": dict(bg="#efe1df", skin="#9d6a4c", hair=("swept", "#24201e"), brow="#201c1a", cloth=("plain", "#7a3b3b", "open"), emblem="flip"),
    "pragmatic-ceo": dict(bg="#e1e7ef", skin="#d8a682", hair=("combed", "#4a3c33"), brow="#3d3129", cloth=("suit", "#26313d", None), emblem="chart"),
}


STYLES = {
    "steve-jobs": dict(bg="#dfe5f2", skin="#e6c3a3", hair=("short", "#6a645f"), brow="#4f4945", stubble=True,
                       cloth=("turtleneck", "#1d1d20"), glasses=dict(r=4.7, w=.9, color="#5a5a5a")),
    "daniel-kahneman": dict(bg="#eee6dc", skin="#e8c6a8", hair=("receding", "#e6e3de"), brow="#cfcac2",
                            cloth=("suit", "#7a6f62", None), glasses=dict(r=4.4, w=1.2, color="#4a4038", square=True), emblem="question"),
    "richard-feynman": dict(bg="#e3ece1", skin="#e4bf9e", hair=("wavy", "#5d5753"), brow="#4a4440",
                            cloth=("plain", "#7f9bb8", "open"), emblem="diagram"),
    "andy-grove": dict(bg="#e1e9ee", skin="#e5c1a0", hair=("short", "#8f8a84"), brow="#77726c",
                       cloth=("suit", "#39424a", "#2f5d8a"), glasses=dict(r=5.2, w=1.3, color="#2f2f2f", square=True), emblem="chip"),
    "charlie-munger": dict(bg="#e9e2d7", skin="#e7c1a3", hair=("sides", "#eeece8"), brow="#d2cdc6", bald_shine=True,
                           cloth=("suit", "#2f3338", "#5a2e2e"), glasses=dict(r=5.3, w=2.3, color="#141414"), emblem="books"),
}


def clothing(spec):
    kind, color = spec[0], spec[1]
    if kind == "turtleneck":
        return color, turtleneck(color)
    if kind == "plain":
        return color, plain(color, spec[2] if len(spec) > 2 else None)
    if kind == "leather":
        return color, jacket_leather(color)
    tie = spec[2] if len(spec) > 2 else None
    long_tie = spec[3] if len(spec) > 3 else False
    return color, suit(color, tie=tie, tie_long=long_tie)


def svg(slug, s):
    cloth_color, cloth = clothing(s["cloth"])
    hair_grad, hair_shape = hair(*s["hair"])
    skin = s["skin"]
    g = s.get("glasses")
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 96 96" role="img" aria-label="Drawn avatar for {slug} (an illustration, not a likeness)">
<defs>
<clipPath id="c"><circle cx="48" cy="48" r="48"/></clipPath>
<radialGradient id="bg" cx=".5" cy=".35" r=".75"><stop offset="0" stop-color="{shade(s["bg"], 0.35)}"/><stop offset="1" stop-color="{shade(s["bg"], -0.06)}"/></radialGradient>
<radialGradient id="skin" cx=".4" cy=".35" r=".75"><stop offset="0" stop-color="{shade(skin, 0.18)}"/><stop offset=".65" stop-color="{skin}"/><stop offset="1" stop-color="{shade(skin, -0.16)}"/></radialGradient>
<linearGradient id="cloth" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{shade(cloth_color, 0.12)}"/><stop offset="1" stop-color="{shade(cloth_color, -0.3)}"/></linearGradient>
{hair_grad}
</defs>
<g clip-path="url(#c)">
<rect width="96" height="96" fill="url(#bg)"/>
<g transform="translate(48 50) scale(1.12) translate(-48 -50)">
<rect x="41.5" y="48" width="13" height="15" rx="4" fill="{shade(skin, -0.12)}"/>
<ellipse cx="48" cy="56" rx="7" ry="3" fill="#000" fill-opacity=".12"/>
{cloth}
{face(skin, s["brow"], s.get("stubble", False), s.get("bald_shine", False))}
{beard(s["beard"]) if s.get("beard") else ""}
{hair_shape}
{glasses(**g) if g else ""}
{EMBLEMS.get(s.get("emblem"), "")}
</g>
</g>
</svg>
'''


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for slug, s in {**STYLES, **ARCHETYPES}.items():
        (OUT / f"{slug}.svg").write_text(svg(slug, s), encoding="utf-8")
    print(f"Wrote {len(STYLES) + len(ARCHETYPES)} avatars to {OUT}")


if __name__ == "__main__":
    main()
