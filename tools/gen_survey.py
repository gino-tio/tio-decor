#!/usr/bin/env python3
"""方案G 實量清單：讀 data/design.json，寫 designs/i-survey.html（俾 Gino 逐項對數）。"""
import json, html, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
D = json.loads((ROOT / "data/design.json").read_text(encoding="utf-8"))
S, P = D["site"], D["products"]
W = S["room"]["w"]

def rows():
    yield "房間", f"闊 {S['room']['w']} × 深 {S['room']['d']} × 地到假天花 {S['room']['h']}", S["room"].get("_src", "")
    yield "浴缸", f"外闊 {S['tub']['x1']}，高 {S['tub']['h']}", ""
    yield "門", f"闊 {S['door']['w']}，門框離後牆 {S['door']['z0']}", ""
    yield "檯面高", f"{S['counter_h']}", ""
    ds = S["drain_stack"]; yield "落地白去水喉", f"中心離後牆 {ds['z']}、離右牆 {W-ds['x']}，管徑 {ds['od']}", ds["_src"]
    fd = S["floor_drain"]; yield "地台去水", f"中心離後牆 {fd['z']}、離右牆 {W-fd['x']}", fd["_src"]
    t = S["wall_tap_existing"]; yield "現有入牆龍頭", f"出水嘴中心離右牆 {W-t['spout_cx']}，離地 {t['spout_y']}", t["_src"]
    tr = P["trap"]["bottle"]; yield "樽型隔氣", f"高 {tr['h']}，出水臂喺頂下 {tr['outlet_drop']}", tr["_src"]
    to = P["toilet"]["toto"]; yield "TOTO 入水", f"座廁中線偏左 {-to['inlet']['dx']}，離地 {to['inlet']['y']}（x={S['toilet_drain']['cx']+to['inlet']['dx']}）", "TOTO 規格書"
    yield "坑距", "未量（拆舊廁先知）", S["toilet_drain"]["_note"]
    so = S["socket_toto"]; yield "TOTO 插蘇", f"離右牆 {W-so['x']}，離地 {so['y']}", so["_note"]
    for k, b in P["basin"].items():
        if k.startswith("_") or "bowl" not in b: continue
        bw = b["bowl"]; cx = 1400 + (bw["x0"] + bw["x1"]) / 2; cz = (bw["z0"] + bw["z1"]) / 2
        yield f"盆：{b['name']}", f"盆內 {bw['x1']-bw['x0']}×{bw['z1']-bw['z0']} 深 {b['depth']}；去水孔離右牆 {W-cx:.0f}、離後牆 {cz:.0f}", "去水孔一律喺盆內中心"

body = "".join(f"<tr><td>{html.escape(a)}</td><td>{html.escape(b)}</td><td class=s>{html.escape(c)}</td></tr>" for a, b, c in rows())
out = f"""<!DOCTYPE html><html lang="zh-HK"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>方案G 實量清單</title><style>
body{{margin:0;padding:16px;background:#1d1f22;color:#eee;font-family:-apple-system,"PingFang HK","Noto Sans TC",sans-serif}}
h1{{font-size:18px}}p{{color:#a9adb8;font-size:13px}}table{{border-collapse:collapse;width:100%;font-size:14px}}
td{{border-bottom:1px solid #33363c;padding:8px 6px;vertical-align:top}}td:first-child{{color:#c9a46a;white-space:nowrap}}.s{{color:#8b8f99;font-size:12px}}a{{color:#c9a46a}}
</style></head><body><a href="../">← 主頁</a><h1>方案G 實量清單</h1>
<p>單位 mm。由 data/design.json 生成（tools/gen_survey.py），3D 同施工圖都讀同一份數。有錯話我知，改一次全部跟。</p>
<table>{body}</table></body></html>"""
(ROOT / "designs/i-survey.html").write_text(out, encoding="utf-8")
print("wrote designs/i-survey.html")
