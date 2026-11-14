#!/usr/bin/env python3
"""Generate shop drawings (施工圖) for Design H: a static HTML page with SVG drawings, plus DXF files for CAD.
All units mm. Main dimensions come from data/dims.json (shared with designs/h.html).
DXF output needs ezdxf (pip install ezdxf); without it only the HTML is written."""
import json
import math
import os
import re

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
OUT = os.path.join(ROOT, "designs", "h-shop.html")
DXF_DIR = os.path.join(ROOT, "files", "dxf")
DIMS = json.load(open(os.path.join(ROOT, "data", "dims.json"), encoding="utf-8"))
# 喉位、地台去水、TOTO 入水由 tools/plumbing.py 計（同 3D 共用），唔好喺度手寫
PL = json.load(open(os.path.join(ROOT, "data", "plumbing.json"), encoding="utf-8"))
FD = PL["floor_drain"]; OC = PL["basins"]["ocean"]; INLET = PL["supply"]["toto_inlet"]
_hatch = DIMS_HATCH = (1450, 200, 1670, 420)
FD_UNDER_HATCH = False  # 櫃底維修口唔做（Gino 2026-11-14）：地台去水喺盆櫃左邊外面

# ---------- drawing helpers ----------
class SVG:
    last = None
    def __init__(s, w, h, pad=260):
        s.w, s.h, s.p = w, h, pad
        s.el = []
        s.cad = []  # same primitives for DXF: (kind, cls, data)
    def add(s, x): s.el.append(x)
    def rect(s, x, y, w, h, cls="o", rx=0):
        s.add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" class="{cls}"/>')
        s.cad.append(("poly", cls, ([(x, y), (x + w, y), (x + w, y + h), (x, y + h)], True)))
    def line(s, x1, y1, x2, y2, cls="o"):
        s.add(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" class="{cls}"/>')
        s.cad.append(("poly", cls, ([(x1, y1), (x2, y2)], False)))
    def path(s, d, cls="o"):
        s.add(f'<path d="{d}" class="{cls}"/>')
        for pts, closed in flatten_path(d): s.cad.append(("poly", cls, (pts, closed)))
    def circle(s, cx, cy, r, cls="o"):
        s.add(f'<circle cx="{cx}" cy="{cy}" r="{r}" class="{cls}"/>')
        s.cad.append(("circle", cls, (cx, cy, r)))
    def text(s, x, y, t, cls="t", anchor="middle", rot=0):
        tr = f' transform="rotate({rot} {x} {y})"' if rot else ""
        s.add(f'<text x="{x}" y="{y}" class="{cls}" text-anchor="{anchor}"{tr}>{t}</text>')
        s.cad.append(("text", cls, (x, y, str(t), anchor, rot)))
    def dimH(s, x1, x2, y, label=None, off=0):
        """horizontal dimension at height y (ext lines drawn from y-off)"""
        if off: s.line(x1, y - off, x1, y + 20, "e"); s.line(x2, y - off, x2, y + 20, "e")
        s.line(x1, y, x2, y, "d")
        for x in (x1, x2): s.line(x - 12, y + 12, x + 12, y - 12, "d")
        s.text((x1 + x2) / 2, y - 14, label if label is not None else f"{round(abs(x2-x1))}", "dt")
    def dimV(s, x, y1, y2, label=None, off=0):
        if off: s.line(x - off, y1, x + 20, y1, "e"); s.line(x - off, y2, x + 20, y2, "e")
        s.line(x, y1, x, y2, "d")
        for y in (y1, y2): s.line(x - 12, y + 12, x + 12, y - 12, "d")
        s.text(x - 16, (y1 + y2) / 2, label if label is not None else f"{round(abs(y2-y1))}", "dt", rot=-90)
    def svg(s, x0=0, y0=0):
        SVG.last = s
        p = s.p
        return (f'<svg viewBox="{x0-p} {y0-p} {s.w+2*p} {s.h+2*p}" xmlns="http://www.w3.org/2000/svg">'
                + "".join(s.el) + "</svg>")

def rr_path(x0, y0, x1, y1, r):
    return (f"M{x0+r},{y0} H{x1-r} A{r},{r} 0 0 1 {x1},{y0+r} V{y1-r} A{r},{r} 0 0 1 {x1-r},{y1} "
            f"H{x0+r} A{r},{r} 0 0 1 {x0},{y1-r} V{y0+r} A{r},{r} 0 0 1 {x0+r},{y0} Z")

def plan_corner(x0, y0, x1, y1, r):
    """plan rectangle (y down = toward room), rounded front-left corner only"""
    return f"M{x0},{y0} H{x1} V{y1} H{x0+r} A{r},{r} 0 0 1 {x0},{y1-r} Z"

def flatten_path(d, seg_deg=6, q_steps=12):
    """SVG path (M L H V A Q Z, absolute or relative; circular arcs only) -> list of (points, closed)."""
    tok = re.findall(r"[MLHVAQZmlhvaqz]|-?\d*\.?\d+(?:e-?\d+)?", d)
    out, pts, i, cmd = [], [], 0, None
    x = y = sx = sy = 0.0
    def num():
        nonlocal i
        v = float(tok[i]); i += 1; return v
    while i < len(tok):
        if tok[i].isalpha(): cmd = tok[i]; i += 1
        rel, c = cmd.islower(), cmd.upper()
        ox, oy = (x, y) if rel else (0.0, 0.0)
        if c == "Z":
            if pts: out.append((pts, True))
            pts, x, y = [], sx, sy
            continue
        if c == "M":
            if pts: out.append((pts, False))
            x, y = ox + num(), oy + num(); sx, sy = x, y; pts = [(x, y)]
            cmd = "l" if rel else "L"
        elif c == "L": x, y = ox + num(), oy + num(); pts.append((x, y))
        elif c == "H": x = (x if rel else 0) + num(); pts.append((x, y))
        elif c == "V": y = (y if rel else 0) + num(); pts.append((x, y))
        elif c == "Q":
            cx, cy, ex, ey = ox + num(), oy + num(), ox + num(), oy + num()
            for k in range(1, q_steps + 1):
                t = k / q_steps
                pts.append(((1-t)**2*x + 2*(1-t)*t*cx + t*t*ex, (1-t)**2*y + 2*(1-t)*t*cy + t*t*ey))
            x, y = ex, ey
        elif c == "A":
            r = num(); num(); num(); large = num(); sweep = num(); ex, ey = ox + num(), oy + num()
            dx, dy = (ex - x) / 2, (ey - y) / 2
            half = math.hypot(dx, dy)
            r = max(r, half)
            k = math.sqrt(max(r * r - half * half, 0)) / half * (1 if large != sweep else -1)
            cx, cy = (x + ex) / 2 - k * dy, (y + ey) / 2 + k * dx
            a0, a1 = math.atan2(y - cy, x - cx), math.atan2(ey - cy, ex - cx)
            da = a1 - a0
            if sweep and da < 0: da += 2 * math.pi
            if not sweep and da > 0: da -= 2 * math.pi
            n = max(2, int(abs(math.degrees(da)) / seg_deg))
            for k2 in range(1, n + 1):
                a = a0 + da * k2 / n; pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
            x, y = ex, ey
    if len(pts) > 1: out.append((pts, False))
    return out

# ---------- room constants (mm), from data/dims.json ----------
W, D, H, CT = DIMS["room"]["w"], DIMS["room"]["d"], DIMS["room"]["h"], DIMS["counter_h"]
TUB_X1 = DIMS["tub"]["x1"]
VX0, VX1, VD = DIMS["vanity"]["x0"], DIMS["vanity"]["x1"], DIMS["vanity"]["d"]
_mc = DIMS["mirror_cabinet"]
MCX0, MCX1, MC_H, MC_D, MC_BOTTOM, MC_DOORS = _mc["x0"], _mc["x1"], _mc["h"], _mc["d"], _mc["bottom"], _mc["doors"]
TOILET_CX = DIMS["toilet"]["cx"]
DOOR_Z0, DOOR_Z1 = DIMS["door"]["z0"], DIMS["door"]["z1"]
DOORS_ZH = {1: "單", 2: "兩", 3: "三"}.get(MC_DOORS, str(MC_DOORS))

drawings = []
def dxf_name(title):
    return f"h-shop-{title.split('.')[0].strip()}.dxf"

# ---------- DXF export (same geometry as the SVGs; SVG y-down -> DXF y-up) ----------
LAYERS = {  # svg class -> (layer, ACI colour, linetype)
    "wall": ("WALL", 7, "CONTINUOUS"), "wall2": ("OPENING", 8, "CONTINUOUS"), "o": ("OUTLINE", 7, "CONTINUOUS"),
    "o2": ("DETAIL", 8, "CONTINUOUS"), "dash": ("HIDDEN", 8, "DASHED"), "arc": ("DOOR_SWING", 8, "DASHED"),
    "glass": ("GLASS", 4, "CONTINUOUS"), "red": ("SERVICES", 1, "CONTINUOUS"), "glow": ("LIGHT", 2, "CONTINUOUS"),
    "hatch": ("STONE", 8, "CONTINUOUS"), "floor": ("FLOOR", 7, "CONTINUOUS"), "d": ("DIM", 30, "CONTINUOUS"),
    "e": ("DIM", 30, "CONTINUOUS"), "dt": ("DIM", 30, "CONTINUOUS"), "lbl": ("TEXT", 7, "CONTINUOUS"),
    "sm": ("TEXT", 7, "CONTINUOUS"), "t": ("TEXT", 7, "CONTINUOUS"),
}
TEXT_H = {"dt": 30, "lbl": 32, "sm": 24, "t": 24}

def _dxf_doc():
    import ezdxf
    doc = ezdxf.new("R2010", setup=True)
    doc.units = ezdxf.units.MM
    doc.header["$INSUNITS"] = 4
    doc.styles.add("CJK", font="msjh.ttc")  # Microsoft JhengHei; CAD falls back if missing
    for name, col, lt in {v[0]: v for v in LAYERS.values()}.values():
        if name not in doc.layers: doc.layers.add(name, color=col, linetype=lt)
    return doc

def _dxf_put(msp, svg, dx=0.0, dy=0.0):
    from ezdxf.enums import TextEntityAlignment
    al = {"middle": TextEntityAlignment.CENTER, "start": TextEntityAlignment.LEFT, "end": TextEntityAlignment.RIGHT}
    for kind, cls, d in svg.cad:
        layer = LAYERS.get(cls, ("OUTLINE",))[0]
        if kind == "poly":
            pts, closed = d
            msp.add_lwpolyline([(x + dx, -y + dy) for x, y in pts], close=closed, dxfattribs={"layer": layer})
        elif kind == "circle":
            cx, cy, r = d
            msp.add_circle((cx + dx, -cy + dy), r, dxfattribs={"layer": layer})
        else:
            x, y, t, anchor, rot = d
            t = re.sub(r"<[^>]+>", "", t)
            msp.add_text(t, height=TEXT_H.get(cls, 24), rotation=-rot,
                         dxfattribs={"layer": layer, "style": "CJK"}).set_placement((x + dx, -y + dy), align=al[anchor])

def write_dxf():
    try:
        import ezdxf  # noqa: F401
    except ImportError:
        print("DXF skipped: pip install ezdxf"); return
    os.makedirs(DXF_DIR, exist_ok=True)
    allDoc = _dxf_doc(); allMsp = allDoc.modelspace(); ox = 0.0
    for title, _, _, svg in drawings:
        doc = _dxf_doc(); _dxf_put(doc.modelspace(), svg)
        doc.saveas(os.path.join(DXF_DIR, dxf_name(title)))
        _dxf_put(allMsp, svg, dx=ox)
        allMsp.add_text(title, height=60, dxfattribs={"layer": "TEXT", "style": "CJK"}).set_placement((ox, svg.p + 120))
        ox += svg.w + 2 * svg.p + 600
    allDoc.saveas(os.path.join(DXF_DIR, "h-shop-all.dxf"))
    print("dxf", len(drawings) + 1, "files ->", os.path.relpath(DXF_DIR, ROOT))
def add_drawing(title, note, svg):
    drawings.append((title, note, svg, SVG.last))

# =============== 1. PLAN ===============
s = SVG(W, D)
s.rect(0, 0, W, D, "wall")
# tub
s.rect(0, 0, TUB_X1, D, "o"); s.path(rr_path(50, 50, 650, D - 50, 80), "o2")
s.text(350, D / 2, "浴缸 730 × 1485（盆內 600）", "lbl")
s.dimH(650, 730, D - 200, "邊 80"); s.dimH(50, 650, D - 300, "600")
# glass
s.line(690, 0, 690, 735, "glass"); s.text(690 + 40, 400, "玻璃屏 735（企浴缸前邊）", "lbl", "start", -90)
# toilet INAX
tw, td = 386, 692
s.path(f"M{TOILET_CX-tw/2},0 H{TOILET_CX+tw/2} V{td-175} A175,175 0 0 1 {TOILET_CX+tw/2-175},{td} H{TOILET_CX-tw/2+175} A175,175 0 0 1 {TOILET_CX-tw/2},{td-175} Z", "o")
s.text(TOILET_CX, 420, "座廁", "lbl"); s.text(TOILET_CX, 470, "TOTO 386×692", "sm")
s.circle(TOILET_CX, 305, 50, "o2"); s.text(TOILET_CX, 250, "去水（坑距待拆廁實量）", "sm")
# ledge
s.path(plan_corner(750, 0, 1400, 100, 40), "o"); s.text(1075, 60, "窄枱 650×100（可選）", "sm")
# vanity
s.path(plan_corner(VX0, 0, VX1, VD, 60), "o"); s.text(1700, 230, "洗手盆櫃 600×500（落地）", "lbl")
if FD_UNDER_HATCH: s.rect(1450, 200, 220, 220, "dash"); s.text(1560, 180, "櫃底維修口", "sm")
# basin waste: drain -> trap -> back -> right to the white floor pipe (plan view)
_wp = OC["waste_path"]; s.path("M" + " L".join(f"{p['x']},{p['z']}" for p in _wp[2:5]), "red"); s.circle(_wp[0]["x"], _wp[0]["z"], 36, "red")
s.circle(PL["drain_stack"]["x"], PL["drain_stack"]["z"], 20, "red"); s.text(PL["drain_stack"]["x"], PL["drain_stack"]["z"] + 60, "落地白喉", "sm")
# remote
s.line(VX0 - 8, 125, VX0 - 8, 359, "red"); s.text(VX0 - 30, 242, "遙控", "sm", "end")
# floor drain
s.circle(FD["x"], FD["z"], FD["d"] / 2, "o2"); s.text(FD["x"], FD["z"] + 95, "地台去水" + ("" if FD_UNDER_HATCH else "（櫃左邊外）"), "sm")
s.dimH(FD["x"], W, FD["z"] + 160, f"{W-FD['x']}"); s.dimV(FD["x"] - 90, 0, FD["z"], f"{FD['z']}")
# door
s.line(W, DOOR_Z0, W, DOOR_Z1, "wall2"); s.path(f"M{W},{1455} L{W-740},{1455}", "o"); s.path(f"M{W-740},{1455} A740,740 0 0 1 {W},{715}", "arc")
s.text(W - 380, 1420, "門 770（向內開，鉸近全身鏡）", "sm")
# mirror cabinet on back wall, full mirror on front wall
s.rect(MCX0, -130, MCX1 - MCX0, 130, "dash"); s.text((MCX0 + MCX1) / 2, -40, f"鏡櫃 {MCX1-MCX0} {DOORS_ZH}門（離地 {MC_BOTTOM}）", "sm")
s.rect(810, D - 15, 600, 15, "o2"); s.text(1110, D + 60, "全身鏡 600＋電視 270×180", "sm")
s.dimH(1410, W, D + 300, "590")
# dims
s.dimH(0, W, -200, f"房闊 {W}")
s.dimH(0, TUB_X1, D + 160); s.dimH(TUB_X1, VX0, D + 160); s.dimH(VX0, VX1, D + 160)
s.dimV(-160, 0, D, f"房深 {D}"); s.dimV(W + 180, 0, DOOR_Z0); s.dimV(W + 180, DOOR_Z0, DOOR_Z1, f"{DOOR_Z1-DOOR_Z0} 門口")
s.dimV(VX1 + 60, 0, VD, None)
s.dimH(TUB_X1, TOILET_CX - tw / 2, 820, None); s.dimH(TOILET_CX + tw / 2, VX0, 820, None)
add_drawing("1. 平面圖", "由上望落。上面係鏡櫃牆（後牆），右邊係門。", s.svg(0, -200))

# =============== 2. BACK WALL ELEVATION ===============
def elev(mc_bottom, ledge=True, toilet="TOTO", doors=2, floor=True):
    s = SVG(W, H)
    Y = lambda h: H - h
    s.rect(0, 0, W, H, "wall")
    s.line(0, H, W, H, "floor")
    # tub
    s.rect(0, Y(450), TUB_X1, 450, "o"); s.text(365, Y(225), "浴缸 高 450", "lbl")
    s.line(690, Y(450 + 1800), 690, Y(450), "glass"); s.text(660, Y(1400), "玻璃 1800", "sm", "end")
    # shower
    s.rect(280, Y(680), 140, 60, "o2"); s.line(350, Y(950), 350, Y(1650), "o"); s.circle(350, Y(1570), 55, "o2")
    s.text(350, Y(1730), "花灑", "sm")
    # backsplash
    s.rect(750, Y(CT + 160), 1250, 160, "hatch"); s.text(1075, Y(CT + 80), "坑紋背牆 160", "sm")
    # ledge
    if ledge: s.rect(750, Y(CT), 650, 30, "o"); s.text(1075, Y(CT) + 70, "窄枱 650（厚 30）", "sm")
    # toilet
    th = 472 if toilet == "INAX" else 512
    s.path(f"M{TOILET_CX-192},{H} V{Y(th-40)} Q{TOILET_CX-192},{Y(th)} {TOILET_CX-150},{Y(th)} H{TOILET_CX+150} Q{TOILET_CX+192},{Y(th)} {TOILET_CX+192},{Y(th-40)} V{H}", "o")
    s.text(TOILET_CX, Y(th / 2), f"座廁 {toilet}", "lbl"); s.dimV(TOILET_CX + 260, Y(0), Y(th), f"{th}")
    # inlet + socket
    s.circle(INLET["x"], Y(INLET["y"]), 18, "red"); s.text(INLET["x"] - 90, Y(INLET["y"]) + 10, f"淡水入水 Rc½ 離地 {INLET['y']}（角掣同位）", "sm", "end")
    s.rect(1485, Y(335), 70, 70, "red"); s.text(1590, Y(300), "TOTO 插蘇（盆櫃下格內）離地 ~300", "sm", "start")
    # vanity
    base = 103 if floor else 430
    s.rect(VX0, Y(CT), 600, 63, "o"); s.rect(VX0, Y(CT - 63), 600, CT - 63 - base, "o")
    s.line(VX0 + 60, Y(CT - 63), VX0 + 60, Y(base), "o2"); s.line(VX0 + 60, Y(634), VX1, Y(634), "o2")
    s.text(1700, Y(740), "盆櫃", "lbl")
    if floor:
        s.line(VX0 + 60, Y(430), VX1, Y(430), "o2"); s.rect(VX0 + 30, Y(100), 550, 100, "hatch"); s.text(1700, Y(50) + 12, "石腳 100", "sm")
        s.dimV(VX0 - 60, Y(0), Y(100), "100")
    else:
        s.rect(VX0 + 5, Y(212), 590, 25, "o2"); s.text(1700, Y(150), "置物板 離地 ~190", "sm")
    # tap
    # basin waste in elevation: tail + bottle, arm to the white floor pipe, down to the floor
    _wp = OC["waste_path"]; s.path("M" + " L".join(f"{p['x']},{Y(p['y'])}" for p in _wp), "red")
    s.rect(OC["trap"]["x"] - 36, Y(OC["trap"]["top"] - 55), 72, OC["trap"]["top"] - 55 - OC["trap"]["bottom"], "red")
    s.rect(1485, Y(335), 70, 70, "red")
    _t = OC["tap"]["design"]; s.rect(_t["x"] - 90, Y(_t["y"] + 35), 180, 70, "o2"); s.text(_t["x"], Y(_t["y"] + 60), "入牆龍頭（對準盆中）", "sm")
    # mirror cabinet
    s.path(rr_path(MCX0, Y(mc_bottom + MC_H), MCX1, Y(mc_bottom), 70), "o")
    for i in range(1, doors): s.line(MCX0 + i * 1200 / doors, Y(mc_bottom + MC_H) + 10, MCX0 + i * 1200 / doors, Y(mc_bottom) - 10, "o2")
    s.text((MCX0 + MCX1) / 2, Y(mc_bottom + MC_H / 2), "鏡櫃 1200 × 970 × 130", "lbl")
    # dims
    s.dimV(VX1 + 120, Y(0), Y(CT), f"{CT}")
    s.dimV(VX1 + 120, Y(CT), Y(mc_bottom), f"{mc_bottom-CT}")
    s.dimV(VX1 + 120, Y(mc_bottom), Y(mc_bottom + MC_H), f"{MC_H}")
    s.dimV(VX1 + 240, Y(0), Y(mc_bottom), f"鏡櫃底離地 {mc_bottom}")
    s.dimV(VX1 + 240, Y(mc_bottom + MC_H), Y(H), f"{H-mc_bottom-MC_H}")
    s.dimV(VX0 - 60, Y(base), Y(CT), f"{CT-base}")
    s.dimH(MCX0, MCX1, Y(mc_bottom + MC_H) - 80)
    s.dimH(VX0, VX1, Y(0) + 120)
    s.dimH(0, 780, Y(mc_bottom + MC_H) - 80, "780")
    s.dimV(-120, Y(0), Y(H), f"地到假天花 {H}")
    return s.svg()

add_drawing("2. 後牆立面（鏡櫃牆）· 最終方案", f"TOTO＋海洋盆落地櫃＋{DOORS_ZH}門鏡櫃底離地 {MC_BOTTOM}（頂 {MC_BOTTOM+MC_H}，離假天花 {H-MC_BOTTOM-MC_H}）＋窄枱。TOTO 說明書建議後牆 1400 以下唔放櫃（遙控訊號），{MC_BOTTOM} 要同 TOTO 確認；窄枱同開蓋位要喺陳列室實試。", elev(MC_BOTTOM))

# =============== 3. VANITY DETAIL ===============
def vanity(kind, R):
    s = SVG(2300, 1100, 200)
    # plan (left)
    ox, oy = 0, 0
    s.path(plan_corner(ox, oy, ox + 600, oy + 500, R), "o")
    if kind == "ocean":
        s.path(rr_path(ox + 15, oy + 120, ox + 585, oy + 490, 50), "o2"); s.text(ox + 300, oy + 330, "盆內 570×370 深 130", "sm")
        s.text(ox + 300, oy + 70, "後平台 120（無龍頭孔）", "sm")
    else:
        s.rect(ox + 60, oy + 130, 470, 310, "o2"); s.text(ox + 300, oy + 300, "盆 470×310 斜底", "sm")
    s.dimH(ox, ox + 600, oy - 80); s.dimV(ox - 80, oy, oy + 500)
    s.text(ox + 300, oy + 620, "平面", "lbl"); s.text(ox + R + 40, oy + 470, f"R{R}", "dt", "start")
    # front elevation (middle)
    ex, Hh = 800, 470
    top = 63 if kind == "ocean" else 180
    s.rect(ex, 0, 600, top, "o")
    s.rect(ex, top, 600, Hh - top, "o")
    split = ex + R + 4
    s.line(split, top, split, Hh, "o2")
    if kind == "ocean":
        s.line(split, top + 200, ex + 600, top + 200, "o2"); s.text(ex + 330, top + 110, "拉櫃 1（U 位避去水）", "sm"); s.text(ex + 330, top + 310, "拉櫃 2", "sm")
    else:
        s.text(ex + 330, top + 150, "大拉櫃（U 位避去水）", "sm")
    s.text(ex + 300, top / 2 + 15, "陶瓷海洋盆 8260" if kind == "ocean" else "岩板 180 厚", "sm")
    s.dimV(ex - 70, 0, top, f"{top}"); s.dimV(ex - 70, top, Hh, f"{Hh-top}"); s.dimV(ex + 680, 0, Hh, "470")
    s.dimH(ex, split, Hh + 90, f"{R+4}"); s.dimH(split, ex + 600, Hh + 90, f"拉櫃 {600-R-4}")
    s.text(ex + 300, Hh + 260, "正面（盆面離地 900，櫃底離地 430）", "lbl")
    # side section (right)
    sx = 1650
    s.rect(sx, 0, 500, top, "o"); s.rect(sx, top, 500, Hh - top, "o")
    # same route as the 3D (data/plumbing.json): drain -> bottle trap -> arm back -> white floor pipe -> floor
    r = PL["basins"]["ocean"]; Yc = lambda y: CT - y
    s.path("M" + " L".join(f"{sx+p['z']},{Yc(p['y'])}" for p in r["waste_path"] if p["at"] not in ("stack_top", "stack_floor")) + f" L{sx+r['waste_path'][-1]['z']},{Hh}", "red")
    s.rect(sx + r["trap"]["z"] - 36, Yc(r["trap"]["top"] - 55), 72, r["trap"]["top"] - 55 - r["trap"]["bottom"], "red")
    c = r["drawer_cut"]; s.rect(sx, top + 20, c["z_to"], Yc(c["y0"]) - top - 20, "dash"); s.text(sx + c["z_to"] / 2, Yc(c["y0"]) + 40, f"U 位 {c['x1']-c['x0']} 闊，到離牆 {c['z_to']}", "sm")
    s.text(sx + r["waste_path"][-1]["z"] + 30, Hh - 20, "落地白喉 ↓", "sm", "start")
    s.dimH(sx, sx + 500, Hh + 90, "500")
    s.text(sx + 250, Hh + 260, "側面剖面（去水經隔氣入落地白喉）", "lbl")
    return s.svg()

add_drawing("3a. 洗手盆櫃 · 陶瓷海洋盆（上半，盆面離地 900）", "三格拉櫃（落地版）：上格面板 196 高、內箱 80 高，後面 U 位 " + f"{OC['drawer_cut']['x1']-OC['drawer_cut']['x0']} 闊伸到離牆 {OC['drawer_cut']['z_to']}" + " 避開隔氣（去水經隔氣、橫喉入落地白喉，離後牆 90／右牆 140）；中格面板 201、內箱 140（喺存水彎橫喉 620 之下）；下格面板 316、內箱 240。拉櫃深 400，全部三節路軌。圓角未揀：R25 拉櫃約 570 闊；R60 約 535 闊。", vanity("ocean", 25))

# floor-standing option
s = SVG(700, 950, 200)
s.rect(0, 0, 600, 63, "o"); s.rect(0, 63, 600, 787 - 63, "o")
s.line(0, 470, 600, 470, "o2"); s.line(0, 270, 600, 270, "o2")
s.rect(20, 850, 550, 100, "hatch"); s.line(0, 950, 700, 950, "floor")
s.text(300, 900, "石材防水腳 高 100（退入 50，中空）", "sm"); (s.rect(80, 830, 220, 20, "red"), s.text(190, 815, "維修口", "sm")) if FD_UNDER_HATCH else None; s.text(300, 380, "拉櫃", "sm"); s.text(300, 650, "落地加多格拉櫃", "sm")
s.dimV(-80, 0, 950, "900"); s.dimV(680, 850, 950, "100"); s.dimH(570, 600, 990, "50")
add_drawing("3b. 盆櫃落地（側面）", ("櫃身唔掂地；石腳中空，櫃底留 220×220 維修口通地台去水；石腳同地之間打防霉膠。" if FD_UNDER_HATCH else f"櫃身唔掂地；石腳中空；石腳同地之間打防霉膠。地台去水喺盆櫃左邊外面（離後牆 {FD['z']}、右牆 {W-FD['x']}），唔使櫃底維修口。"), s.svg())

# =============== 4. MIRROR CABINET ===============
def mcab(n):
    s = SVG(2100, 1100, 200)
    s.path(rr_path(0, 0, 1200, 970, 70), "o"); s.path(rr_path(14, 14, 1186, 956, 56), "glow")
    dw = (1200 - 28) / n
    for i in range(1, n): s.line(14 + i * dw, 20, 14 + i * dw, 950, "o")
    s.text(600, 1030, f"{n} 道鏡門 · 每道約 {round(dw)}", "sm")
    s.dimH(0, 1200, -90); s.dimV(-90, 0, 970); s.text(80, 120, "R70", "dt", "start")
    s.text(600, 1100, "正面（四邊透光燈帶 14 闊）", "lbl")
    # section
    sx = 1500
    s.rect(sx, 0, 130, 970, "o"); s.line(sx, 970 - 320, sx + 120, 970 - 320, "o2"); s.line(sx, 970 - 640, sx + 120, 970 - 640, "o2")
    s.rect(sx - 12, 0, 12, 970, "dash")
    s.rect(sx + 20, 970 - 120, 30, 50, "red"); s.text(sx + 160, 970 - 90, "防水插蘇", "sm", "start")
    s.dimH(sx, sx + 130, -90, "130"); s.dimV(sx + 200, 970, 970 - 320, "320"); s.dimV(sx + 200, 970 - 320, 970 - 640, "320")
    s.text(sx + 65, 1080, "側面剖面（玻璃層板 ×2）", "lbl")
    return s.svg()

add_drawing(f"4. 鏡櫃 · {DOORS_ZH}門", f"底離地 {MC_BOTTOM}。牆身要打底板，唔好只靠細木條。", mcab(MC_DOORS))

# =============== 5. TOILET POSITION ===============
s = SVG(1600, 900, 200)
# plan
s.rect(0, 0, 385, 710, "dash"); s.path(f"M0,0 H385 V560 A150,150 0 0 1 235,710 H150 A150,150 0 0 1 0,560 Z", "o")
s.circle(192, 305, 40, "o2"); s.circle(192 - 115, 0, 15, "red")
s.dimH(0, 385, -80); s.dimV(-80, 0, 710); s.dimV(470, 0, 305, "坑距 305")
s.text(192, 820, "INAX SARAS 平面", "lbl")
# TOTO
tx = 900
s.rect(tx, 0, 386, 692, "dash"); s.path(f"M{tx},0 H{tx+386} V{692-175} A175,175 0 0 1 {tx+386-175},692 H{tx+175} A175,175 0 0 1 {tx},{692-175} Z", "o")
s.circle(tx + 193, 305, 40, "o2"); s.circle(tx + 193 - 115, 0, 15, "red")
s.dimH(tx, tx + 386, -80); s.dimV(tx - 80, 0, 692); s.dimV(tx + 470, 0, 305, "305 / 400")
s.text(tx + 193, 820, "TOTO CES8E810GCN 平面", "lbl")
add_drawing("5. 座廁位置", "紅點＝淡水入水（偏左 115，離地 175）。坑距要拆舊廁實量，INAX 只有 305；TOTO 有 305／400 去水件。座廁兩邊離障礙 ≥70。遙控 234×78 裝盆櫃側面離地 ~750。", s.svg())

# =============== BOM ===============
bom = [
    ("座廁", "TOTO CES8E810GCN（NEOREST AS）", "692 × 386 × 512；去水件 HP102T3 (305) 或 HP102T4 (400)", "1", "坑距拆廁實量先揀去水件；淡水 Rc½ 離地 175 偏左 115"),
    ("洗手盆", "陶瓷海洋盆 8260", "600 × 500，盆深 130，前邊厚 63，無龍頭孔", "1", "淘寶 MF937；確認實闊 600／605"),
    ("洗手盆櫃", "訂造落地櫃＋石材防水腳", "600 × 500，盆面離地 900；石腳 550 × 440 × 100 退入 50", "1", "上格 U 位避隔氣；" + ("櫃底 220×220 維修口；" if FD_UNDER_HATCH else "地台去水喺櫃左邊外，唔使維修口；") + "圓角／木色未定"),
    ("入牆龍頭", "入牆式", "出水嘴長 ~200（要過 120 後平台）", "1", "出水對準盆中"),
    ("鏡櫃", f"訂造鏡櫃 {DOORS_ZH}門", f"{MCX1-MCX0} × {MC_H} × {MC_D}，R70，四邊透光燈帶", "1", f"底離地 {MC_BOTTOM}；內置防水插蘇；玻璃層板 ×2；打底板"),
    ("窄枱（可選）", "白色陶瓷／石", "650 × 100 × 30，面離地 900", "1", "陳列室試 TOTO 開蓋會唔會撞先決定"),
    ("浴缸玻璃屏", "固定透明玻璃", "735 × 1800，企浴缸前邊（離浴缸外邊牆 ~690）", "1", "由鏡櫃牆伸出"),
    ("全身鏡＋電視", "現有", "鏡闊 600，離門牆 590；電視 270 × 180", "—", "保留"),
]
bom_html = "".join(f"<tr><td>{a}</td><td>{b}</td><td>{c}</td><td>{d}</td><td>{e}</td></tr>" for a, b, c, d, e in bom)

css = """
:root{--ink:#222;--mute:#666;--line:#ddd;--gold:#a8823f}
*{box-sizing:border-box}body{margin:0;font-family:"Noto Sans TC",-apple-system,"PingFang HK",sans-serif;color:var(--ink);background:#f4f2ee;line-height:1.55}
header{background:#1f1e1c;color:#f3efe8;padding:22px 18px}header a{color:#c9a46a;text-decoration:none;font-size:13px}
header h1{margin:6px 0 4px;font-size:22px}header p{margin:0;color:#c9c3b9;font-size:13px}
main{max-width:1100px;margin:0 auto;padding:16px}
.card{background:#fff;border:1px solid var(--line);border-radius:10px;padding:14px;margin:0 0 16px;break-inside:avoid;page-break-inside:avoid}
.card h2{font-size:17px;margin:0 0 4px}.card p{margin:0 0 8px;color:var(--mute);font-size:13px}
svg{width:100%;height:auto;display:block;background:#fff}
svg .wall{fill:none;stroke:#111;stroke-width:14}svg .wall2{stroke:#fff;stroke-width:18}
svg .o{fill:#fff;stroke:#222;stroke-width:5}svg .o2{fill:none;stroke:#555;stroke-width:3}
svg .dash{fill:none;stroke:#777;stroke-width:3;stroke-dasharray:16 10}svg .arc{fill:none;stroke:#888;stroke-width:3;stroke-dasharray:10 8}
svg .glass{stroke:#3a9fb5;stroke-width:8}svg .red{fill:none;stroke:#c0392b;stroke-width:5}
svg .glow{fill:none;stroke:#e8b85c;stroke-width:10;opacity:.7}svg .hatch{fill:#e9e6e0;stroke:#999;stroke-width:3}
svg .floor{stroke:#111;stroke-width:8}
svg .d{stroke:#b5651d;stroke-width:3}svg .e{stroke:#b5651d;stroke-width:2;opacity:.6}
svg text{font-family:inherit}svg .dt{font-size:40px;fill:#b5651d;font-weight:600}
svg .lbl{font-size:42px;fill:#222;font-weight:600}svg .sm{font-size:32px;fill:#444}
table{width:100%;border-collapse:collapse;font-size:13px}th,td{border:1px solid var(--line);padding:7px;text-align:left;vertical-align:top}th{background:#efebe4}
.scroll{overflow-x:auto}a.dxf{color:var(--gold);font-weight:600;white-space:nowrap}.note{background:#fff7ea;border-left:4px solid var(--gold);padding:10px 12px;border-radius:6px;font-size:13px;margin-bottom:16px}
@media print{header{background:none;color:#000}header p{color:#333}body{background:#fff}.card{border:none;padding:0}@page{size:A3 landscape;margin:12mm}}
"""
html = f"""<!DOCTYPE html><html lang="zh-HK"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>浴室裝修 施工圖 · 方案 H</title><style>{css}</style></head><body>
<header><a href="h.html">← 返 3D 方案 H</a> · <a href="../">主頁</a><h1>施工圖 · 方案 H</h1><p>俾廠家／師傅報價用 · 單位 mm · 所有尺寸以現場實量為準</p></header>
<main>
<div class="note"><b>CAD 檔：</b><a href="../files/dxf/h-shop-all.dxf" download>⬇ 全部圖則 DXF</a>（AutoCAD／SketchUp／LibreCAD 開得，單位 mm）；每張圖下面都有單獨 DXF。<br><b>已實量：</b>房闊 2000、房深 1485、地到假天花 2300、浴缸高 450 闊 730、門 770、全身鏡 600。<br><b>仍要現場確認：</b>坑距（拆舊廁後量；舊廁背離牆 250 係暗水箱）、入水同去水位、牆身平直、TOTO 開蓋同窄枱／鏡櫃有冇撞。</div>
<div class="card"><h2>物料清單</h2><div class="scroll"><table><tr><th>項目</th><th>型號／做法</th><th>尺寸 (mm)</th><th>數量</th><th>備註</th></tr>{bom_html}</table></div></div>
{''.join(f'<div class="card"><h2>{t}</h2><p>{n} <a class="dxf" href="../files/dxf/{dxf_name(t)}" download>⬇ DXF</a></p>{svg}</div>' for t, n, svg, _ in drawings)}
</main></body></html>"""
open(OUT, "w").write(html)
print("ok", len(html))
write_dxf()
