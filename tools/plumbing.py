#!/usr/bin/env python3
"""方案G 喉路：所有盆款共用一個 route() 計去水同供水，寫 data/plumbing.json。
3D（designs/i.html）同施工圖（tools/gen_shop.py）都讀 plumbing.json，唔再各自畫。
單位 mm；x 由浴缸牆、z 由後牆（鏡櫃牆）、y 由地。
用法：python3 tools/plumbing.py        → 寫 data/plumbing.json，並跑 check_design 檢查"""
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
DESIGN = json.loads((ROOT / "data/design.json").read_text(encoding="utf-8"))
S, P, R = DESIGN["site"], DESIGN["products"], DESIGN["rules"]
VX0 = S["vanity_zone"]["x0"]
CT = S["counter_h"]


def basin_drain(key):
    """去水孔 = 盆內中心（統一規則）。"""
    b = P["basin"][key]
    bw = b["bowl"]
    at = b.get("drain_at")  # 斜底盆：去水孔唔喺中心
    return {
        "x": at["x"] if at else VX0 + (bw["x0"] + bw["x1"]) / 2,
        "z": at["z"] if at else (bw["z0"] + bw["z1"]) / 2,
        "y": CT - b["depth"],
        "bowl": {"x0": VX0 + bw["x0"], "x1": VX0 + bw["x1"], "z0": bw["z0"], "z1": bw["z1"]},
    }


def route(key):
    """盆去水 → 樽型隔氣 → 出水臂向後 → 橫去落地白喉 → 落地。全部盆款用同一條規則。"""
    d = basin_drain(key)
    t = P["trap"]["bottle"]
    st = S["drain_stack"]
    top = min(d["y"], P["basin"][key].get("underside", d["y"]))  # 厚石檯面：尾喉穿石，隔氣喺石底下
    arm_y = top - t["outlet_drop"]
    pts = [
        ("drain", d["x"], d["y"], d["z"]),
        ("trap_top", d["x"], top, d["z"]),
        ("trap_bottom", d["x"], top - t["h"], d["z"]),
        ("arm_start", d["x"], arm_y, d["z"]),
        ("arm_corner", d["x"], arm_y, st["z"]),
        ("stack_top", st["x"], arm_y, st["z"]),
        ("stack_floor", st["x"], 0, st["z"]),
    ]
    tap = S["wall_tap_existing"]
    tp = P["tap"]["wall2hole"]
    return {
        "drain": d,
        "trap": {"x": d["x"], "z": d["z"], "top": top, "bottom": top - t["h"], "body_d": t["body_d"]},
        "waste_path": [{"at": n, "x": round(x, 1), "y": round(y, 1), "z": round(z, 1)} for n, x, y, z in pts],
        "pipe_od": t["pipe_od"],
        "stack_od": st["od"],
        # 龍頭「盆中」= 對準呢款盆嘅去水孔 x；「現有入牆位」固定
        "tap": {
            "design": {"x": d["x"], "y": CT + tp["design_above_counter"], "reach_z": tp["spout_l"]},
            "site": {"x": tap["spout_cx"], "y": tap["spout_y"], "reach_z": tp["spout_l"]},
        },
        # 上格櫃桶要避嘅位：隔氣身 ± 間隙，由後牆伸到隔氣前面
        "drawer_cut": {
            "x0": round(d["x"] - t["body_d"] / 2 - R["drawer_clearance"]),
            "x1": round(d["x"] + t["body_d"] / 2 + R["drawer_clearance"]),
            "z_to": round(d["z"] + t["body_d"] / 2 + R["drawer_clearance"]),
            "y0": round(top - t["h"]),
        },
    }


def supply():
    """淡水：盆位冷水三通 → 角掣 → 軟喉 → TOTO 入水（偏左 115、離地 175）。"""
    to = P["toilet"]["toto"]
    cx = S["toilet_drain"]["cx"]
    inlet = {"x": cx + to["inlet"]["dx"], "y": to["inlet"]["y"], "z": 0}
    tee = S["cold_supply"]
    return {
        "toto_inlet": inlet,
        "angle_valve": {"x": inlet["x"], "y": inlet["y"], "z": 30},
        "tee": {"x": tee["tee_x"], "y": tee["tee_y"], "z": tee["tee_z"]},
        "path": [
            {"at": "tee", "x": tee["tee_x"], "y": tee["tee_y"], "z": tee["tee_z"]},
            {"at": "wall_run", "x": inlet["x"], "y": tee["tee_y"], "z": tee["tee_z"]},
            {"at": "angle_valve", "x": inlet["x"], "y": inlet["y"], "z": 30},
            {"at": "toto_inlet", **inlet},
        ],
        "_note": "三通後嘅喉暗藏入牆，淨係角掣同軟喉睇到",
    }


def build():
    basins = DESIGN["options"]["basin"]
    tops = [t for t in DESIGN["options"].get("ocean_top", []) if t != "ceramic"]  # 海洋盆櫃配石檯面＋底盆
    keys = list(basins) + [t for t in tops if t in P["basin"]]
    return {
        "_note": "由 tools/plumbing.py 生成，唔好手改。改 data/design.json 再跑。",
        "basins": {k: route(k) for k in keys},
        "supply": supply(),
        "floor_drain": S["floor_drain"],
        "drain_stack": S["drain_stack"],
        "socket_toto": S["socket_toto"],
    }


if __name__ == "__main__":
    out = build()
    (ROOT / "data/plumbing.json").write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("wrote data/plumbing.json:", ", ".join(out["basins"]))
    import check_design  # noqa: E402  (same folder)
    raise SystemExit(check_design.main())
