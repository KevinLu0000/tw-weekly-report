# 產生週報兩張圖表的程式碼（Claude 文件的 claude.Visualize 元件，畫成橫條圖）
#   widget_weekly.jsx  ：第一節「本週漲跌幅」——台股指數、類股、美股、匯率、商品
#   widget_industry.jsx：第四節「產業強弱」——各產業等權重週報酬與上漲家數
# 標題預設是根據數字自動寫的一句話，排程中的 Claude 可以改寫成更精確的結論（只改 title／sub 文字）
import json


def _round_axis(v):
    """把最大漲跌幅往上取整，留一點空間放數字標籤"""
    return max(3, int(abs(v)) + 2)


def weekly_rows(mk):
    """整理第一張圖的資料：每列 {key, grp, name, chg}"""
    s1, s5 = mk["盤勢"], mk["美股宏觀"]
    rows = []

    def add(key, grp, name, chg):
        if chg is not None:
            rows.append({"key": key, "grp": grp, "name": name, "chg": round(chg, 2)})

    add("taiex", "台股", "加權指數", s1["加權指數"]["變動%"])
    add("tpex", "台股", "櫃買指數", s1["櫃買指數"]["變動%"])
    if s1.get("台指期近月"):
        add("tx", "台股", "台指期（近月）", s1["台指期近月"]["變動%"])
    for k, name in [("電子工業類指數", "電子工業類指數"), ("半導體類指數", "半導體類指數"),
                    ("電子零組件類指數", "電子零組件類指數"), ("金融保險類指數", "金融保險類指數"),
                    ("航運類指數", "航運類指數")]:
        add(k, "台股", name, s1["類股指數週漲跌%"].get(k))
    for sym, key in [("^SOX", "sox"), ("^IXIC", "ndx"), ("^GSPC", "spx"), ("NVDA", "nvda"), ("TSM", "tsm"),
                     ("DX-Y.NYB", "dxy"), ("GC=F", "gold"), ("CL=F", "wti"), ("BZ=F", "brent")]:
        v = s5.get(sym)
        if v:
            add(key, "國際", v["名稱"].replace("台積電ADR", "台積電 ADR").replace("原油", " 原油"), v.get("週變動%"))
    rows.sort(key=lambda r: -r["chg"])
    return rows


def weekly_code(mk, title=None):
    rows = weekly_rows(mk)
    lim = _round_axis(max(abs(r["chg"]) for r in rows))
    W, P = mk["W"], mk["P"]
    s5 = mk["美股宏觀"].get("^SOX", {})
    up = [r["name"] for r in rows[:2]]
    dn = [r["name"] for r in rows[-2:]]
    title = title or f"本週{up[0]}、{up[1]}漲最多，{dn[1]}、{dn[0]}跌最多"
    sub = (f"週漲跌幅（%）：台股 {P[4:6]}/{P[6:]} → {W[4:6]}/{W[6:]} 收盤；美股、匯率、商品 "
           f"{(s5.get('上週日期') or '')[4:6]}/{(s5.get('上週日期') or '')[6:]} → "
           f"{(s5.get('本週日期') or '')[4:6]}/{(s5.get('本週日期') or '')[6:]} 美國收盤；藍色＝加權指數與費半")
    data = json.dumps(rows, ensure_ascii=False)
    return ("export default () => <claude.Visualize data-claude-component='weekly-change' sources={{rows:{kind:'data', data:" + data + "}}}>"
            "{({rows, datum}) => { const L = 190, R = 700, lo = -" + str(lim) + ", hi = " + str(lim) + ", y0 = 78, step = 24; "
            "const X = v => L + (v - lo) / (hi - lo) * (R - L); const H = y0 + rows.length * step + 30; "
            "return <svg viewBox={`0 0 760 ${H}`} role='img' aria-label='" + title + "' fontSize='12'>"
            "<text data-claude-text-id='title' x='8' y='26' fontSize='16' fill='var(--cds-text-primary)'>" + title + "</text>"
            "<text data-claude-text-id='sub' x='8' y='48' fill='var(--cds-text-secondary)'>" + sub + "</text>"
            "<line x1={X(0)} x2={X(0)} y1={y0 - 10} y2={y0 + rows.length * step} stroke='var(--cds-chart-axis)' />"
            "<g data-claude-anchor='bars'>{rows.map((r, i) => { const yy = y0 + i * step; const accent = r.key === 'taiex' || r.key === 'sox'; "
            "return <g key={r.key}><text x='8' y={yy + 12} fill='var(--cds-text-primary)'>{r.name}</text>"
            "<text x='150' y={yy + 12} fill='var(--cds-text-secondary)' fontSize='11'>{r.grp}</text>"
            "<rect x={Math.min(X(0), X(r.chg))} y={yy} width={Math.abs(X(r.chg) - X(0))} height='16' "
            "fill={accent ? 'var(--cds-chart-categorical-1)' : 'var(--cds-chart-muted)'} {...datum(r, 'chg')}>"
            "<title>{`${r.name}：${r.chg > 0 ? '+' : ''}${r.chg.toFixed(2)}%`}</title></rect>"
            "<text x={r.chg >= 0 ? X(r.chg) + 4 : X(r.chg) - 4} y={yy + 12} textAnchor={r.chg >= 0 ? 'start' : 'end'} "
            "fill='var(--cds-text-primary)' {...datum(r, 'chg')}>{`${r.chg > 0 ? '+' : ''}${r.chg.toFixed(1)}%`}</text></g>; })}</g></svg>; }}"
            "</claude.Visualize>;")


def industry_code(mk, title=None, hot=None):
    s4 = mk["產業"]
    rows = [{"key": f"i{i}", "name": x["產業"].replace("/", "／"), "n": x["檔數"], "up": x["上漲"], "w": round(x["週報酬%"], 2)}
            for i, x in enumerate(s4["產業"]) if x["週報酬%"] is not None]
    ref = [{"key": "taiex", "name": "加權指數", "v": round(s4["加權指數週報酬%"], 2), "dy": 36},
           {"key": "ew", "name": "全市場等權重", "v": round(s4["全市場等權重週報酬%"], 2), "dy": 20}]
    vals = [r["w"] for r in rows] + [r["v"] for r in ref]
    lo, hi = min(min(vals) - 1, -1), max(max(vals) + 1, 1)
    hot = hot or [rows[-1]["key"], rows[-2]["key"], rows[-3]["key"]]        # 預設標出最弱的三個產業
    W, P = mk["W"], mk["P"]
    title = title or f"本週{rows[0]['name']}最強（{rows[0]['w']:+.1f}%），{rows[-1]['name']}最弱（{rows[-1]['w']:+.1f}%）"
    sub = f"產業籃子等權重週報酬（%，{P[4:6]}/{P[6:]} → {W[4:6]}/{W[6:]}）；藍色＝本週最弱三個產業"
    return ("export default () => <claude.Visualize data-claude-component='industry-week' sources={{rows:{kind:'data', data:"
            + json.dumps(rows, ensure_ascii=False) + "}, ref:{kind:'data', data:" + json.dumps(ref, ensure_ascii=False) + "}}}>"
            "{({rows, ref, datum}) => { const L = 170, R = 600, lo = " + f"{lo:.1f}" + ", hi = " + f"{hi:.1f}" + ", y0 = 108, step = 24; "
            "const X = v => L + (v - lo) / (hi - lo) * (R - L); const H = y0 + rows.length * step + 24; "
            "const hot = k => " + json.dumps(hot) + ".includes(k); "
            "return <svg viewBox={`0 0 760 ${H}`} role='img' aria-label='" + title + "' fontSize='12'>"
            "<text data-claude-text-id='title' x='8' y='26' fontSize='16' fill='var(--cds-text-primary)'>" + title + "</text>"
            "<text data-claude-text-id='sub' x='8' y='48' fill='var(--cds-text-secondary)'>" + sub + "</text>"
            "<text data-claude-text-id='col-w' x='670' y={y0 - 10} textAnchor='end' fontSize='11' fill='var(--cds-text-secondary)'>週報酬</text>"
            "<text data-claude-text-id='col-up' x='748' y={y0 - 10} textAnchor='end' fontSize='11' fill='var(--cds-text-secondary)'>上漲／檔數</text>"
            "<g data-claude-anchor='reference'>{ref.map(r => <g key={r.key}><line x1={X(r.v)} x2={X(r.v)} y1={y0 - r.dy + 4} "
            "y2={y0 + rows.length * step} stroke='var(--cds-chart-reference)' strokeDasharray='4 3' {...datum(r, 'v')} />"
            "<text x={X(r.v) + 4} y={y0 - r.dy} fontSize='11' fill='var(--cds-text-secondary)' {...datum(r, 'v')}>{`${r.name} ${r.v.toFixed(1)}%`}</text></g>)}</g>"
            "<line x1={X(0)} x2={X(0)} y1={y0 - 6} y2={y0 + rows.length * step} stroke='var(--cds-chart-axis)' />"
            "<g data-claude-anchor='bars'>{rows.map((r, i) => { const yy = y0 + i * step; "
            "return <g key={r.key}><text x='8' y={yy + 12} fill='var(--cds-text-primary)'>{r.name}</text>"
            "<rect x={Math.min(X(0), X(r.w))} y={yy} width={Math.abs(X(r.w) - X(0))} height='16' "
            "fill={hot(r.key) ? 'var(--cds-chart-categorical-1)' : 'var(--cds-chart-muted)'} {...datum(r, 'w')}>"
            "<title>{`${r.name}：${r.w > 0 ? '+' : ''}${r.w.toFixed(2)}%，上漲 ${r.up}/${r.n} 檔`}</title></rect>"
            "<text x='670' y={yy + 12} textAnchor='end' fill='var(--cds-text-primary)' {...datum(r, 'w')}>{`${r.w > 0 ? '+' : ''}${r.w.toFixed(1)}%`}</text>"
            "<text x='748' y={yy + 12} textAnchor='end' fill='var(--cds-text-secondary)' {...datum(r, 'up')}>{`${r.up}/${r.n}`}</text></g>; })}</g></svg>; }}"
            "</claude.Visualize>;")


def write_all(out_dir, mk):
    open(f"{out_dir}/widget_weekly.jsx", "w").write(weekly_code(mk))
    open(f"{out_dir}/widget_industry.jsx", "w").write(industry_code(mk))
