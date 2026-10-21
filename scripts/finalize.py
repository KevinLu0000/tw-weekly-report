# 套用第二階段規則、產生前 10 名、整理所有表格與圖表資料
# 需要：value_candidates.json、momentum_all.json、market.json、stage2_input.json（都在 results/<W>/）
# 輸出（results/<W>/）：
#   value_top10.json、momentum_top10.json：最終名單（含融資 5 日增減、券資比）
#   tables.md：週報要用的所有數字表格（Markdown，直接貼進文件）
#   widget_weekly.jsx、widget_industry.jsx：兩張圖表的程式碼
#   台股週報資料_<W>.xlsx：完整名單與計分（給人看的試算表）
# 結束代碼：0＝完成；2＝價值股還不到 11 檔通過、需要再逐檔查下一批（會列出代號）
import sys, statistics
from common import *

W = week_end()
D5 = days_back(W, 5)
OUT = results_dir(W)
vc = load_json(f"{OUT}/value_candidates.json")
ma = load_json(f"{OUT}/momentum_all.json")
mk = load_json(f"{OUT}/market.json")
inp = load_json(f"{OUT}/stage2_input.json", {})
months = load_json(f"{OUT}/stage2_todo.json")["rev_months"]       # [最新月, 前一月, 前兩月]


# ---------- 共用：格式化 ----------
def f(x, d=1, sign=False, pct=False, comma=False):
    """數字轉文字：d 位小數、sign 加正負號、pct 加 %、comma 千分位；None → 「—」"""
    if x is None:
        return "—"
    s = f"{x:{'+' if sign else ''}{',' if comma else ''}.{d}f}"
    s = s.replace("-", "−")                                      # 用全形減號，比較好讀
    return s + ("%" if pct else "")


def yoy(pair):
    """[當月, 去年同月] → 年增率 %；如果查到的只有年增率（一個數字），就直接用"""
    if isinstance(pair, (int, float)):
        return float(pair)
    if not pair or not pair[0] or not pair[1]:
        return None
    return (pair[0] / pair[1] - 1) * 100


def eps_pair(eps, i):
    """eps＝[[季別, EPS], ...]（最新在前）；回傳第 i 新的一季與「去年同季」(季別, 本季, 去年同季)
    用季別文字對應（例如 2026Q2 對 2025Q2），就算網頁漏列某一季也不會對錯"""
    if not eps or len(eps) <= i:
        return None
    q, v = eps[i]
    last = f"{int(q[:4]) - 1}{q[4:]}"
    ly = next((x[1] for x in eps if x[0] == last), None)
    return None if ly is None or v is None else (q, v, ly)


def unavailable(rec, item):
    """排程中的 Claude 實際查過但查不到的項目，會寫在 unavailable 清單"""
    return item in (rec.get("unavailable") or [])


# ---------- 融資 5 日增減、券資比 ----------
margin = {}
for m in "LO":
    now, old = load_json(f"data/margin/{m}_{W}.json", {}), load_json(f"data/margin/{m}_{D5}.json", {})
    for c, v in now.items():
        o = old.get(c)
        margin[c] = {"融資張": v[0], "融券張": v[1],
                     "融資5日增減%": (v[0] / o[0] - 1) * 100 if o and o[0] and v[0] is not None else None,
                     "券資比%": v[1] / v[0] * 100 if v[0] and v[1] is not None else None}

# ---------- 1. 價值股第二階段 ----------
passed, dropped, need_more = [], [], []
for s in vc["stocks"]:
    if len(passed) >= 11:                       # 前 10 名＋1 檔候補
        break
    c = s["code"]
    rec = inp.get(c, {})
    lack = [k for k in ["eps", "ocf"] if k not in rec and not unavailable(rec, k)]
    lack += [f"rev_{ym}" for ym in months if ym not in rec.get("rev", {}) and not unavailable(rec, f"rev_{ym}")]
    if lack:
        need_more.append((c, s["name"], lack))
        break                                   # 要照分數順序檢查，前面沒查完不能跳過
    notes, why = [], []
    # 規則 1：近四季營業現金流或自由現金流 > 0
    if "ocf" in rec:
        s["ocf4"], s["fcf4"] = sum(rec["ocf"][:4]) / 1e5, sum(rec.get("fcf", [0])[:4]) / 1e5   # 仟元 → 億元
        if not (s["ocf4"] > 0 or s["fcf4"] > 0):
            why.append(f"近四季營業 CF {s['ocf4']:.1f} 億、自由 CF {s['fcf4']:.1f} 億都 ≤ 0")
    else:
        notes.append("現金流查不到")
    # 規則 2：最近兩季單季 EPS 都比去年同季少 → 剔除（eps 最新在前：0 vs 4、1 vs 5）
    a, b = eps_pair(rec.get("eps"), 0), eps_pair(rec.get("eps"), 1)
    if a and b:
        s["eps_q"] = rec["eps"]
        e = [x[1] for x in rec["eps"]]
        s["eps4"] = sum(e[:4]) if len(e) >= 4 else None
        if a[1] < a[2] and b[1] < b[2]:
            why.append(f"連兩季 EPS 年減（{a[0]} {a[1]} vs 去年 {a[2]}；{b[0]} {b[1]} vs 去年 {b[2]}）")
    else:
        notes.append("單季 EPS 查不到（無法比較去年同季）")
    # 規則 3：最近三個月有兩個月營收年減超過 10% → 剔除
    ys = {ym: yoy(rec.get("rev", {}).get(ym)) for ym in months}
    s["rev3"] = ys
    bad = [ym for ym, v in ys.items() if v is not None and v < -10]
    if len(bad) >= 2:
        why.append("近三個月有兩個月營收年減逾 10%（" + "、".join(f"{ym[4:]}月 {ys[ym]:.1f}%" for ym in bad) + "）")
    if any(v is None for v in ys.values()):
        notes.append("部分月份營收查不到")
    s["stage2_notes"] = notes
    s["sources"] = rec.get("sources", [])
    s.update(margin.get(c, {}))
    if why:
        s["drop_reason"] = "；".join(why)
        dropped.append(s)
    else:
        passed.append(s)

if need_more:
    print("價值股還需要逐檔查：", need_more)
    print(f"目前通過 {len(passed)} 檔、剔除 {len(dropped)} 檔")
    save_json(f"{OUT}/stage2_need.json", [{"code": c, "name": n, "need": l} for c, n, l in need_more])
    if "--allow-partial" not in sys.argv:
        sys.exit(2)

v_top, v_backup = passed[:10], passed[10:11]
save_json(f"{OUT}/value_top10.json", {"top10": v_top, "backup": v_backup, "dropped": dropped,
                                      "candidates": vc["count"], "universe": vc.get("universe")})

# ---------- 2. 動量股前 10 名：分類與標示 ----------
m_top = ma["stocks"][:10]
for s in m_top:
    c = s["code"]
    rec = inp.get(c, {})
    s.update(margin.get(c, {}))
    revs = rec.get("rev", {})
    c1 = s.get("rev_yoy") is not None and s["rev_yoy"] > 0
    have3 = all(isinstance(revs.get(ym), list) and revs[ym][0] and revs[ym][1] for ym in months)
    cum3 = (sum(revs[ym][0] for ym in months) / sum(revs[ym][1] for ym in months) - 1) * 100 if have3 else None
    s["rev_cum3"] = cum3
    e = [x[1] for x in rec.get("eps", [])]
    s["eps_q"] = rec.get("eps")
    a = eps_pair(rec.get("eps"), 0)                          # 最近一季與去年同季
    s["eps_latest"] = a
    c3 = bool(a) and a[1] > 0 and a[1] > a[2]
    if s.get("rev_yoy") is None or cum3 is None or not a:
        s["class"] = "資料不足"
    else:
        s["class"] = "基本面支持" if (c1 and cum3 > 0 and c3) else "題材／籌碼型"
    tags = []
    if s["punish"]: tags.append("處置股")
    if s["notice"]: tags.append("注意股")
    if s["strong_inst"]: tags.append("法人強力買超")
    if s["spike_up"]: tags.append("最後一天放量上攻")
    if s["spike_down"]: tags.append("放量收黑")
    if e and e[0] < 0: tags.append("仍虧損")
    s["tags"] = tags
    s["sources"] = rec.get("sources", [])
save_json(f"{OUT}/momentum_top10.json", {"top10": m_top, "count": ma["count"]})

# ---------- 3. 表格（Markdown）----------
sec1, sec4, sec5, risk = mk["盤勢"], mk["產業"], mk["美股宏觀"], mk["風險"]
P = mk["P"]
md = []
add = md.append
dP, dW = f"{P[4:6]}/{P[6:]}", f"{W[4:6]}/{W[6:]}"
mlabel = f"{int(months[0][4:])}月營收年增"

add(f"# 表格資料（{W}，由 scripts/finalize.py 產生）\n")
add("## 一、盤勢：籌碼與量能\n")
add(f"| 指標 | 上週（{dP}） | 本週（{dW}） | 變化 |\n| --- | --- | --- | --- |")


def row(name, d, dec=0, unit_chg="pct"):
    a, b = d.get("上週"), d.get("本週")
    if unit_chg == "pct":
        c = f(d.get("變動%"), 1, True, True)
    else:
        c = unit_chg
    add(f"| {name} | {f(a, dec, comma=True)} | {f(b, dec, comma=True)} | {c} |")


row("加權指數", sec1["加權指數"], 0)
row("櫃買指數", sec1["櫃買指數"], 2)
t = sec1["上市日均成交值億"]
add(f"| 上市日均成交值（億元） | {f(t['上週'], 0, comma=True)}（{t['上週天數']} 天） | {f(t['本週'], 0, comma=True)}（{t['本週天數']} 天） | {f(t['變動%'], 1, True, True)} |")
t = sec1["上櫃日均成交值億"]
add(f"| 上櫃日均成交值（億元） | {f(t['上週'], 0, comma=True)}（{t['上週天數']} 天） | {f(t['本週'], 0, comma=True)}（{t['本週天數']} 天） | {f(t['變動%'], 1, True, True)} |")
for who in ["外資", "投信"]:
    t = sec1[f"{who}台指期未平倉淨額口"]
    add(f"| {who}台指期未平倉淨額（口） | {f(t['上週'], 0, True, comma=True)} | {f(t['本週'], 0, True, comma=True)} | {f(t['增減口'], 0, True, comma=True)} 口 |")
t = sec1["上市融資金額億"]
add(f"| 上市融資餘額（億元） | {f(t['上週'], 1, comma=True)} | {f(t['本週'], 1, comma=True)} | {f(t['變動%'], 2, True, True)} |")
row("上市融資餘額（張）", sec1["上市融資張"], 0)
row("上市融券餘額（張）", sec1["上市融券張"], 0)
row("上市借券賣出餘額（張）", sec1["上市借券賣出餘額張"], 0)
t = sec1["上櫃融資金額億"]
add(f"| 上櫃融資餘額（億元） | {f(t['上週'], 1, comma=True)} | {f(t['本週'], 1, comma=True)} | {f(t['變動%'], 2, True, True)} |")
row("上櫃融券餘額（張）", sec1["上櫃融券張"], 0)
add(f"| 券資比（上市／上櫃） | — | {f(sec1['上市券資比%'], 2, pct=True)}／{f(sec1['上櫃券資比%'], 2, pct=True)} | — |")
t = sec1["美元兌新台幣"]
add(f"| 美元兌新台幣 | {f(t['上週'], 2)} | {f(t['本週'], 2)} | {'台幣貶值' if (t['變動%'] or 0) > 0 else '台幣升值'} {f(abs(t['變動%'] or 0), 1, pct=True)} |")
t = sec1["美國10年期殖利率%"]
bp = None if t["上週"] is None or t["本週"] is None else (t["本週"] - t["上週"]) * 100
add(f"| 美國 10 年期公債殖利率 | {f(t['上週'], 2, pct=True)} | {f(t['本週'], 2, pct=True)} | {f(bp, 0, True)} 個基點 |")

add("\n## 一、盤勢：三大法人（上市，本週買賣金額，億元）\n")
add("| 法人 | 買進 | 賣出 | 買賣超 |\n| --- | --- | --- | --- |")
names = {"外資及陸資(不含外資自營商)": "外資及陸資", "投信": "投信", "自營商(自行買賣)": "自營商（自行買賣）",
         "自營商(避險)": "自營商（避險）", "合計": "合計"}
for k, n in names.items():
    v = sec1["三大法人本週億元"].get(k)
    if v:
        add(f"| {n} | {f(v[0], 0, comma=True)} | {f(v[1], 0, comma=True)} | {f(v[2], 0, True, comma=True)} |")

add("\n## 一、盤勢：類股指數週漲跌（%）與類股日均成交值（億元）\n")
add("| 類股 | 週漲跌 | 上週日均成交值 | 本週日均成交值 | 成交值變化 |\n| --- | --- | --- | --- | --- |")
bf = sec1["類股日均成交值億"]
for k, v in sorted(sec1["類股指數週漲跌%"].items(), key=lambda x: -(x[1] or -99)):
    alias = {"電子工業類指數": "電子類指數", "航運類指數": "航運業類指數"}   # 兩個資料表的名稱不同
    b = bf.get(alias.get(k, k), {})
    add(f"| {k} | {f(v, 2, True, True)} | {f(b.get('上週'), 0, comma=True)} | {f(b.get('本週'), 0, comma=True)} | {f(b.get('變動%'), 1, True, True)} |")
w10 = sec1["權值集中度"]
add(f"\n權值集中度（自行計算，{dW} 收盤）：台積電佔上市普通股市值 {f(w10['台積電%'], 1, pct=True)}，前 10 大合計 {f(w10['前10大%'], 1, pct=True)}。")

# 價值股
add(f"\n## 二、價值股 Top 10（第一階段通過 {vc['count']} 檔；第二階段剔除 {len(dropped)} 檔）\n")
add(f"| # | 代號 | 公司 | 產業 | 市值(億) | 收盤 | 52週低 | 距低點 | 52週高 | 距高點 | TTM P/E | P/B | 殖利率 | {mlabel} | 近四季EPS | 近四季營業CF(億) | 近四季自由CF(億) | 負債比／ROE | 融資5日增減 | 券資比 |")
add("|" + " --- |" * 20)
for i, s in enumerate(v_top, 1):
    dr = f"{f(s.get('debt'), 0, pct=True)}／{f(s.get('roe'), 1, pct=True)}" if not s.get("fin") else f"金融股／{f(s.get('roe'), 1, pct=True)}"
    add(f"| {i} | {s['code']} | {s['name']} | {s.get('ind') or '—'} | {f(s['mcap'], 0, comma=True)} | {f(s['close'], 2)} | "
        f"{f(s['low52'], 2)} | {f(s['dist'], 1, pct=True)} | {f(s['high52'], 2)} | {f(s['from_hi'], 1, True, True)} | "
        f"{f(s['pe'], 1)} | {f(s['pb'], 2)} | {f(s['dy'], 1, pct=True)} | {f(s.get('rev_yoy'), 1, True, True)} | "
        f"{f(s.get('eps4'), 2)} | {f(s.get('ocf4'), 1)} | {f(s.get('fcf4'), 1)} | {dr} | "
        f"{f(s.get('融資5日增減%'), 1, True, True)} | {f(s.get('券資比%'), 1, pct=True)} |")
if v_backup:
    b = v_backup[0]
    add(f"\n候補：{b['code']} {b['name']}（價值評分 {b['score']}）。")
if dropped:
    add("\n第二階段剔除：" + "；".join(f"{s['code']} {s['name']}：{s['drop_reason']}" for s in dropped) + "。")
notes = [f"{s['code']} {s['name']}：{'、'.join(s['stage2_notes'])}" for s in v_top if s.get("stage2_notes")]
if notes:
    add("\n資料缺口：" + "；".join(notes) + "。")

# 動量股
tr = ma["taiex_ret"]
add(f"\n## 三、動量股 Top 10（通過門檻 {ma['count']} 檔；加權指數同期 1 週 {f(tr['5'] if '5' in tr else tr.get(5), 2, True, True)}、"
    f"1 月 {f(tr['22'] if '22' in tr else tr.get(22), 2, True, True)}、3 月 {f(tr['65'] if '65' in tr else tr.get(65), 2, True, True)}）\n")
add("| # | 代號 | 公司 | 分類 | 1週 | 1月 | 3月 | 52週高 | 距高點 | 52週低 | 距低點 | 外資5日(張) | 投信5日(張) | 法人買超佔成交值 | 22日線(警戒) | 65日線(失效) | 融資5日增減 | 券資比 | 總分 | 標示 |")
add("|" + " --- |" * 20)
for i, s in enumerate(m_top, 1):
    add(f"| {i} | {s['code']} | {s['name']} | {s['class']} | {f(s['r5'], 1, True, True)} | {f(s['r22'], 1, True, True)} | "
        f"{f(s['r65'], 1, True, True)} | {f(s['hi52'], 2)} | {f(s['from_hi'], 1, True, True)} | {f(s['lo52'], 2)} | "
        f"{f(s['from_lo'], 1, True, True)} | {f(s['f5'], 0, True, comma=True)} | {f(s['t5'], 0, True, comma=True)} | "
        f"{f(s['inst_ratio'], 1, pct=True)} | {f(s['ma22'], 1)}（{f((s['close'] / s['ma22'] - 1) * 100, 1, True, True)}） | "
        f"{f(s['ma65'], 1)}（{f((s['close'] / s['ma65'] - 1) * 100, 1, True, True)}） | "
        f"{f(s.get('融資5日增減%'), 1, True, True)} | {f(s.get('券資比%'), 1, pct=True)} | {f(s['score'], 1)} | {'、'.join(s['tags'])} |")
add("\n分類依據（逐檔）：" + "；".join(
    f"{s['code']} 最新月營收年增 {f(s.get('rev_yoy'), 1, True, True)}、近 3 月累計 {f(s.get('rev_cum3'), 1, True, True)}、" +
    (f"{s['eps_latest'][0]} EPS {s['eps_latest'][1]}（去年同季 {s['eps_latest'][2]}）" if s.get("eps_latest") else "單季 EPS 查不到")
    for s in m_top) + "。")

# 產業
add(f"\n## 四、產業強弱（非凡概念成分股，等權重；加權指數週報酬 {f(sec4['加權指數週報酬%'], 2, True, True)}、"
    f"全市場等權重 {f(sec4['全市場等權重週報酬%'], 2, True, True)}）\n")
add(f"| 產業 | 週報酬 | 上漲／檔數 | 近 1 月報酬 | {int(months[0][4:])}月營收年增（中位數） | 營收年增家數 |\n| --- | --- | --- | --- | --- | --- |")
for x in sec4["產業"]:
    add(f"| {x['產業']} | {f(x['週報酬%'], 2, True, True)} | {x['上漲']}/{x['檔數']} | {f(x['1月報酬%'], 1, True, True)} | "
        f"{f(x['營收年增中位數%'], 1, True, True)} | {x['營收年增家數']}/{x['營收家數']} |")

# 美股
add("\n## 五、美股與宏觀\n")
add("| 標的 | 近 1 週 | 近 1 月 | 本週收盤 |\n| --- | --- | --- | --- |")
for sym in ["^SOX", "TSM", "NVDA", "^IXIC", "^GSPC", "TAIEX", "DX-Y.NYB", "TWD=X", "^TNX", "CL=F", "BZ=F", "GC=F"]:
    v = sec5.get(sym)
    if v and sym == "^TNX":                                     # 殖利率用「個基點」表示變動
        w = None if v.get("週變動點") is None else v["週變動點"] * 100
        add(f"| {v['名稱']} | {f(w, 0, True)} 個基點 | — | {f(v.get('本週'), 2, pct=True)} |")
    elif v:
        add(f"| {v['名稱']} | {f(v.get('週變動%'), 1, True, True)} | {f(v.get('1月變動%'), 1, True, True)} | {f(v.get('本週'), 2, comma=True)} |")
sox = sec5.get("^SOX", {})
add(f"\n美股以 {(sox.get('本週日期') or '')[4:6]}/{(sox.get('本週日期') or '')[6:]} 美國收盤計；近 1 週起點 "
    f"{(sox.get('上週日期') or '')[4:6]}/{(sox.get('上週日期') or '')[6:]}，近 1 月起點 {(sox.get('1月起點日期') or '')[4:6]}/{(sox.get('1月起點日期') or '')[6:]}。"
    f"費半 65 日線 {f(sox.get('65日線'), 0, comma=True)}。")
adr = sec5["台積電ADR溢價"]
if adr.get("本週"):
    a = adr["本週"]
    add(f"台積電 ADR 溢價：ADR {f(a['ADR美元'], 2)} 美元 × 匯率 {f(a['匯率'], 2)} ÷ 5 ＝ {f(a['換算台幣'], 0, comma=True)} 元，"
        f"台股收 {f(a['台股收盤'], 0, comma=True)} 元，溢價 {f(a['溢價%'], 1, True, True)}"
        + (f"（上週 {f(adr['上週']['溢價%'], 1, True, True)}）" if adr.get("上週") else "") + "。")

# 風險計分
add(f"\n## 九、風險偏好計分：{risk['判斷']}（總分 {f(risk['總分'], 0, True)}）\n")
add("| # | 訊號 | 本週數字 | 得分 |\n| --- | --- | --- | --- |")
for i, x in enumerate(risk["訊號"], 1):
    v = x["數字"]
    v = f(v, 1, True, comma=True) if isinstance(v, (int, float)) else (v or "—")
    v = v.replace("-", "−") if isinstance(v, str) else v
    score = "缺資料" if x["得分"] is None else ("0" if x["得分"] == 0 else f(x["得分"], 0, True))
    add(f"| {i} | {x['訊號']} | {v} | {score} |")
add(f"|  | **合計** | （≥ +3 偏多；−2～+2 中性；≤ −3 偏保守） | **{f(risk['總分'], 0, True)}** |")
if mk.get("缺資料") or mk.get("抓取失敗"):
    add("\n**缺資料**：" + "；".join(mk.get("缺資料", []) + mk.get("抓取失敗", [])))
open(f"{OUT}/tables.md", "w").write("\n".join(md) + "\n")

# ---------- 4. 圖表程式碼 ----------
import widgets
widgets.write_all(OUT, mk)

# ---------- 5. 試算表 ----------
import build_xlsx
build_xlsx.build(OUT, W, v_top, v_backup, dropped, vc["stocks"], m_top, ma["stocks"], mk)

print(f"完成：價值股 {len(v_top)} 檔（候補 {len(v_backup)}、剔除 {len(dropped)}），動量股 {len(m_top)} 檔，"
      f"風險 {risk['判斷']}（{risk['總分']}）。表格：{OUT}/tables.md")
