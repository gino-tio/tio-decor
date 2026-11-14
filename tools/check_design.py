#!/usr/bin/env python3
"""方案G 自動檢查：讀 data/design.json + data/plumbing.json，逐款盆檢查冇穿崩。
有 FAIL 就 exit 1（push 之前要全部 OK）；WARN 係要人決定嘅嘢。"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent


def main():
    D = json.loads((ROOT / "data/design.json").read_text(encoding="utf-8"))
    PL = json.loads((ROOT / "data/plumbing.json").read_text(encoding="utf-8"))
    S, P, R, O = D["site"], D["products"], D["rules"], D["options"]
    cab = P["cabinet"]
    res = []

    def chk(ok, what, warn=False):
        res.append(("OK" if ok else ("WARN" if warn else "FAIL"), what))

    drawer_back = cab["front_z"] - cab["drawer_depth"]
    inner_x1 = cab["x1"] - cab["panel_t"]
    inner_floor = cab["plinth_h"] + cab["panel_t"]
    for k, r in PL["basins"].items():
        name = P["basin"][k]["name"]
        d, b, t = r["drain"], r["drain"]["bowl"], r["trap"]
        st = PL["drain_stack"]
        chk(b["x0"] >= cab["x0"] and b["x1"] <= cab["x1"] and b["z1"] <= cab["front_z"], f"{name}：盆喺櫃面範圍內")
        path = r["waste_path"]
        cont = all(sum(a[c] != q[c] for c in "xyz") <= 1 for a, q in zip(path, path[1:]))
        chk(cont, f"{name}：去水喉由盆到落地一條過，冇斷（{len(path)-1} 段，每段直行）")
        chk(path[-2]["x"] == st["x"] and path[-2]["z"] == st["z"], f"{name}：駁入落地白喉（離後牆 {st['z']}、右牆 {S['room']['w']-st['x']}）")
        chk(t["bottom"] - inner_floor >= R["trap_clearance"], f"{name}：隔氣底離櫃底板 {t['bottom']-inner_floor:.0f}（要 ≥ {R['trap_clearance']}）")
        arm_back = st["z"] + max(r["pipe_od"], r["stack_od"]) / 2
        chk(drawer_back - arm_back >= R["drawer_clearance"], f"{name}：橫喉同落地喉喺櫃桶後面，隙 {drawer_back-arm_back:.0f}（要 ≥ {R['drawer_clearance']}）")
        chk(st["x"] + r["stack_od"] / 2 <= inner_x1, f"{name}：落地喉喺櫃內（離右側板 {inner_x1-st['x']-r['stack_od']/2:.0f}）")
        c = r["drawer_cut"]
        chk(c["x0"] > cab["x0"] + cab["panel_t"] and c["x1"] < inner_x1, f"{name}：上格櫃桶 U 位 {c['x1']-c['x0']} 闊，伸到離後牆 {c['z_to']}，喺櫃身之內")
        for tk in O.get("tap", ["design"]):
            tp = r["tap"][tk]
            lz, m = tp["reach_z"] - 10, R["tap_land_margin"]
            ok = b["x0"] + m <= tp["x"] <= b["x1"] - m and b["z0"] + m <= lz <= b["z1"] - m
            chk(ok, f"{name}：龍頭（{'盆中' if tk=='design' else '現有入牆位'}）出水落喺盆內，落點離後牆 {lz:.0f}（盆內 {b['z0']:.0f}–{b['z1']:.0f}）")

    sp = PL["supply"]
    to = P["toilet"]["toto"]
    tx0, tx1 = S["toilet_drain"]["cx"] - to["w"] / 2, S["toilet_drain"]["cx"] + to["w"] / 2
    chk(tx0 <= sp["toto_inlet"]["x"] <= tx1, f"TOTO 入水位 x={sp['toto_inlet']['x']:.0f}（座廁中線偏左 {-to['inlet']['dx']}），角掣同一位")
    chk(tx0 - S["tub"]["x1"] >= R["toilet_side_clear"], f"座廁左邊離浴缸 {tx0-S['tub']['x1']:.0f}（要 ≥ {R['toilet_side_clear']}）")
    chk(cab["x0"] - tx1 >= R["toilet_side_clear"], f"座廁右邊離盆櫃 {cab['x0']-tx1:.0f}（要 ≥ {R['toilet_side_clear']}）")

    fd = PL["floor_drain"]
    fx0, fx1, fz0, fz1 = fd["x"] - fd["d"] / 2, fd["x"] + fd["d"] / 2, fd["z"] - fd["d"] / 2, fd["z"] + fd["d"] / 2
    plinth_x0 = cab["x0"] + cab["plinth_setback"]
    # 冇櫃底維修口（Gino 2026-11-14）→ 地台去水一定要喺石腳外面，唔可以被櫃封住
    chk(fx1 <= plinth_x0, f"地台去水（x {fx0:.0f}–{fx1:.0f}）喺盆櫃石腳外面，隙 {plinth_x0-fx1:.0f}；櫃身懸空蓋住 {max(0, fx1-cab['x0']):.0f}")

    for s_, w in res:
        print(f"[{s_:4}] {w}")
    fails = sum(s_ == "FAIL" for s_, _ in res)
    print(f"\n{len(res)} 項：{fails} FAIL，{sum(s_=='WARN' for s_,_ in res)} WARN")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
