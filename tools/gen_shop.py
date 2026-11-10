#!/usr/bin/env python3
"""Generate shop drawings (施工圖) for Design H as a static HTML page with SVG drawings. All units mm."""
import math

import os
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "designs", "h-shop.html")

# ---------- drawing helpers ----------
class SVG:
    def __init__(s, w, h, pad=260):
        s.w, s.h, s.p = w, h, pad
        s.el = []
    def add(s, x): s.el.append(x)
    def rect(s, x, y, w, h, cls="o", rx=0):
        s.add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" class="{cls}"/>')
    def line(s, x1, y1, x2, y2, cls="o"):
        s.add(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" class="{cls}"/>')
    def path(s, d, cls="o"):
        s.add(f'<path d="{d}" class="{cls}"/>')
    def circle(s, cx, cy, r, cls="o"):
        s.add(f'<circle cx="{cx}" cy="{cy}" r="{r}" class="{cls}"/>')
    def text(s, x, y, t, cls="t", anchor="middle", rot=0):
        tr = f' transform="rotate({rot} {x} {y})"' if rot else ""
        s.add(f'<text x="{x}" y="{y}" class="{cls}" text-anchor="{anchor}"{tr}>{t}</text>')
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
        p = s.p
        return (f'<svg viewBox="{x0-p} {y0-p} {s.w+2*p} {s.h+2*p}" xmlns="http://www.w3.org/2000/svg">'
                + "".join(s.el) + "</svg>")

def rr_path(x0, y0, x1, y1, r):
    return (f"M{x0+r},{y0} H{x1-r} A{r},{r} 0 0 1 {x1},{y0+r} V{y1-r} A{r},{r} 0 0 1 {x1-r},{y1} "
            f"H{x0+r} A{r},{r} 0 0 1 {x0},{y1-r} V{y0+r} A{r},{r} 0 0 1 {x0+r},{y0} Z")

def plan_corner(x0, y0, x1, y1, r):
    """plan rectangle (y down = toward room), rounded front-left corner only"""
    return f"M{x0},{y0} H{x1} V{y1} H{x0+r} A{r},{r} 0 0 1 {x0},{y1-r} Z"

# ---------- room constants (mm) ----------
W, D, H, CT = 2000, 1485, 2300, 900
TUB_X1 = 730
VX0, VX1, VD = 1400, 2000, 500
MCX0, MCX1, MC_H, MC_D = 780, 1980, 970, 130
TOILET_CX = 1075

drawings = []

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
s.rect(1450, 200, 220, 220, "dash"); s.text(1560, 180, "櫃底維修口", "sm")
# remote
s.line(VX0 - 8, 125, VX0 - 8, 359, "red"); s.text(VX0 - 30, 242, "遙控", "sm", "end")
# floor drain
s.circle(1520, 380, 50, "o2"); s.text(1520, 470, "地台去水", "sm")
# door
s.line(W, 707, W, 1462, "wall2"); s.path(f"M{W},{1455} L{W-740},{1455}", "o"); s.path(f"M{W-740},{1455} A740,740 0 0 1 {W},{715}", "arc")
s.text(W - 380, 1420, "門 770（向內開，鉸近全身鏡）", "sm")
# mirror cabinet on back wall, full mirror on front wall
s.rect(MCX0, -130, MCX1 - MCX0, 130, "dash"); s.text((MCX0 + MCX1) / 2, -40, "鏡櫃 1200 兩門（離地 1250）", "sm")
s.rect(810, D - 15, 600, 15, "o2"); s.text(1110, D + 60, "全身鏡 600＋電視 270×180", "sm")
s.dimH(1410, W, D + 300, "590")
# dims
s.dimH(0, W, -200, f"房闊 {W}")
s.dimH(0, TUB_X1, D + 160); s.dimH(TUB_X1, VX0, D + 160); s.dimH(VX0, VX1, D + 160)
s.dimV(-160, 0, D, f"房深 {D}"); s.dimV(W + 180, 0, 707, "707"); s.dimV(W + 180, 707, 1462, "755 門口")
s.dimV(VX1 + 60, 0, VD, None)
s.dimH(TUB_X1, TOILET_CX - tw / 2, 820, None); s.dimH(TOILET_CX + tw / 2, VX0, 820, None)
drawings.append(("1. 平面圖", "由上望落。上面係鏡櫃牆（後牆），右邊係門。", s.svg(0, -200)))

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
    s.circle(960, Y(175), 18, "red"); s.text(870, Y(175) + 10, "淡水入水 Rc½ 離地 175", "sm", "end")
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
    s.rect(1670, Y(1040), 60, 100, "o2"); s.text(1700, Y(1060), "入牆龍頭", "sm")
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

drawings.append(("2. 後牆立面（鏡櫃牆）· 最終方案", "TOTO＋海洋盆落地櫃＋兩門鏡櫃底離地 1250（頂 2220，離假天花 80）＋窄枱。TOTO 說明書建議後牆 1400 以下唔放櫃（遙控訊號），1250 要同 TOTO 確認；窄枱同開蓋位要喺陳列室實試。", elev(1250)))

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
    s.path(f"M{sx+250},{top} v120 q0,60 -60,60 h-190", "red")
    s.rect(sx + 160, top + 30, 180, 220, "dash"); s.text(sx + 250, top + 290, "U 位 160 闊", "sm")
    s.dimH(sx, sx + 500, Hh + 90, "500")
    s.text(sx + 250, Hh + 260, "側面剖面（去水入牆）", "lbl")
    return s.svg()

drawings.append(("3a. 洗手盆櫃 · 陶瓷海洋盆（上半，盆面離地 900）", "三格拉櫃（落地版）：上格面板 196 高、內箱 80 高，後面 U 位 140 闊伸到離牆 360 避開去水尾喉；中格面板 201、內箱 140（喺存水彎橫喉 620 之下）；下格面板 316、內箱 240。拉櫃深 400，全部三節路軌。圓角未揀：R25 拉櫃約 570 闊；R60 約 535 闊。", vanity("ocean", 25)))

# floor-standing option
s = SVG(700, 950, 200)
s.rect(0, 0, 600, 63, "o"); s.rect(0, 63, 600, 787 - 63, "o")
s.line(0, 470, 600, 470, "o2"); s.line(0, 270, 600, 270, "o2")
s.rect(20, 850, 550, 100, "hatch"); s.line(0, 950, 700, 950, "floor")
s.text(300, 900, "石材防水腳 高 100（退入 50，中空）", "sm"); s.rect(80, 830, 220, 20, "red"); s.text(190, 815, "維修口", "sm"); s.text(300, 380, "拉櫃", "sm"); s.text(300, 650, "落地加多格拉櫃", "sm")
s.dimV(-80, 0, 950, "900"); s.dimV(680, 850, 950, "100"); s.dimH(570, 600, 990, "50")
drawings.append(("3b. 盆櫃落地（側面）", "櫃身唔掂地；石腳中空，櫃底留 220×220 維修口通地台去水；石腳同地之間打防霉膠。", s.svg()))

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

drawings.append(("4. 鏡櫃 · 兩門", "底離地 1250。牆身要打底板，唔好只靠細木條。", mcab(2)))

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
drawings.append(("5. 座廁位置", "紅點＝淡水入水（偏左 115，離地 175）。坑距要拆舊廁實量，INAX 只有 305；TOTO 有 305／400 去水件。座廁兩邊離障礙 ≥70。遙控 234×78 裝盆櫃側面離地 ~750。", s.svg()))

# =============== BOM ===============
bom = [
    ("座廁", "TOTO CES8E810GCN（NEOREST AS）", "692 × 386 × 512；去水件 HP102T3 (305) 或 HP102T4 (400)", "1", "坑距拆廁實量先揀去水件；淡水 Rc½ 離地 175 偏左 115"),
    ("洗手盆", "陶瓷海洋盆 8260", "600 × 500，盆深 130，前邊厚 63，無龍頭孔", "1", "淘寶 MF937；確認實闊 600／605"),
    ("洗手盆櫃", "訂造落地櫃＋石材防水腳", "600 × 500，盆面離地 900；石腳 550 × 440 × 100 退入 50", "1", "上格 U 位避去水；櫃底 220×220 維修口；圓角／木色未定"),
    ("入牆龍頭", "入牆式", "出水嘴長 ~200（要過 120 後平台）", "1", "出水對準盆中"),
    ("鏡櫃", "訂造鏡櫃 兩門", "1200 × 970 × 130，R70，四邊透光燈帶", "1", "底離地 1250；內置防水插蘇；玻璃層板 ×2；打底板"),
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
.scroll{overflow-x:auto}.note{background:#fff7ea;border-left:4px solid var(--gold);padding:10px 12px;border-radius:6px;font-size:13px;margin-bottom:16px}
@media print{header{background:none;color:#000}header p{color:#333}body{background:#fff}.card{border:none;padding:0}@page{size:A3 landscape;margin:12mm}}
"""
html = f"""<!DOCTYPE html><html lang="zh-HK"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>浴室裝修 施工圖 · 方案 H</title><style>{css}</style></head><body>
<header><a href="h.html">← 返 3D 方案 H</a> · <a href="../">主頁</a><h1>施工圖 · 方案 H</h1><p>俾廠家／師傅報價用 · 單位 mm · 所有尺寸以現場實量為準</p></header>
<main>
<div class="note"><b>已實量：</b>房闊 2000、房深 1485、地到假天花 2300、浴缸高 450 闊 730、門 770、全身鏡 600。<br><b>仍要現場確認：</b>坑距（拆舊廁後量；舊廁背離牆 250 係暗水箱）、入水同去水位、牆身平直、TOTO 開蓋同窄枱／鏡櫃有冇撞。</div>
<div class="card"><h2>物料清單</h2><div class="scroll"><table><tr><th>項目</th><th>型號／做法</th><th>尺寸 (mm)</th><th>數量</th><th>備註</th></tr>{bom_html}</table></div></div>
{''.join(f'<div class="card"><h2>{t}</h2><p>{n}</p>{svg}</div>' for t, n, svg in drawings)}
</main></body></html>"""
open(OUT, "w").write(html)
print("ok", len(html))
