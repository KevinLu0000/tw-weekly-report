# 計算週報第一節（盤勢）、第四節（產業）、第五節（美股與宏觀）的數字，以及第九節風險偏好計分
# 需要先跑：update_prices.py、fetch_basic.py、fetch_week.py、fetch_us.py、screen_momentum.py（本週與上週）
# 輸出：results/<W>/market.json
import statistics
from common import *

W = week_end()
P = prev_week_end(W)
OUT = results_dir(W)
mw, mp = load_json(f"data/market/{W}.json", {}), load_json(f"data/market/{P}.json", {})
missing = []                                    # 缺資料的項目，報告裡要寫明


def chg(a, b):
    """b 相對 a 的變動百分比；任一個沒有資料就回傳 None"""
    return None if a in (None, 0) or b is None else (b / a - 1) * 100


def pair(a, b, key=None):
    """整理成 {上週, 本週, 變動%}"""
    return {"上週": a, "本週": b, "變動%": chg(a, b)}


# ---------- 1. 指數 ----------
twse = load_json("data/market/twse_daily.json", {})      # {日期: [上市成交金額(元), 加權指數]}
tpex = load_json("data/market/tpex_daily.json", {})      # {日期: [上櫃成交金額(元), 櫃買指數]}
tdays = sorted(d for d in twse if d <= W)
taiex = [twse[d][1] for d in tdays]
sec1 = {"W": W, "P": P}
sec1["加權指數"] = pair(twse.get(P, [None, None])[1], twse.get(W, [None, None])[1])
sec1["加權指數65日線"] = statistics.mean(taiex[-65:]) if len(taiex) >= 65 else None
sec1["加權指數22日前"] = {"日期": tdays[-23], "收盤": taiex[-23]} if len(taiex) > 23 else None
sec1["櫃買指數"] = pair(tpex.get(P, [None, None])[1], tpex.get(W, [None, None])[1])
if sec1["櫃買指數"]["本週"] is None:
    missing.append("櫃買指數")

# 類股指數：證交所 MI_INDEX 的所有價格指數，算週漲跌
iw, ip = mw.get("index", {}), mp.get("index", {})
sec1["類股指數週漲跌%"] = {k: chg(ip.get(k), v) for k, v in iw.items() if k in ip and "類指數" in k}
if not iw:
    missing.append("類股指數")

# ---------- 2. 成交值（日平均，億元）----------
def avg_turnover(table, d):
    days = [x for x in week_days(d) if x in table]
    return (statistics.mean(table[x][0] for x in days) / 1e8 if days else None), len(days)

for name, table in [("上市日均成交值億", twse), ("上櫃日均成交值億", tpex)]:
    (a, na), (b, nb) = avg_turnover(table, P), avg_turnover(table, W)
    sec1[name] = {"上週": a, "上週天數": na, "本週": b, "本週天數": nb, "變動%": chg(a, b)}

# 類股日均成交值（BFIAMU，億元）
def bfiamu_avg(d):
    tot, n = {}, 0
    for x in week_days(d):
        rec = load_json(f"data/market/bfiamu/{x}.json")
        if rec:
            n += 1
            for k, v in rec.items():
                tot[k] = tot.get(k, 0) + (v or 0)
    return {k: v / n / 1e8 for k, v in tot.items()} if n else {}

ba, bb = bfiamu_avg(P), bfiamu_avg(W)
sec1["類股日均成交值億"] = {k: pair(ba.get(k), v) for k, v in bb.items()}

# ---------- 3. 期貨、融資融券、借券 ----------
def get_in(rec, *keys):
    for k in keys:
        if not isinstance(rec, dict) or k not in rec:
            return None
        rec = rec[k]
    return rec

for who in ["外資", "投信", "自營商"]:
    a, b = get_in(mp, "taifex", "未平倉淨額口", who), get_in(mw, "taifex", "未平倉淨額口", who)
    sec1[f"{who}台指期未平倉淨額口"] = {"上週": a, "本週": b, "增減口": None if a is None or b is None else b - a}
txw, txp = get_in(mw, "taifex", "TX"), get_in(mp, "taifex", "TX")
if txw and txp:
    near = txw[0]["月份"]                                     # 本週的近月合約，上週用同一個合約比較
    old = next((x["收盤"] for x in txp if x["月份"] == near), None)
    sec1["台指期近月"] = {"合約": near, **pair(old, txw[0]["收盤"])}
else:
    missing.append("台指期行情")

for mk in ["L", "O"]:
    for k in ["融資金額億", "融資張", "融券張"]:
        sec1[f"{'上市' if mk == 'L' else '上櫃'}{k}"] = pair(get_in(mp, f"margin_{mk}", k), get_in(mw, f"margin_{mk}", k))
    a = get_in(mw, f"margin_{mk}", "融券張"), get_in(mw, f"margin_{mk}", "融資張")
    sec1[f"{'上市' if mk == 'L' else '上櫃'}券資比%"] = a[0] / a[1] * 100 if all(a) else None
sec1["上市借券賣出餘額張"] = pair(get_in(mp, "sbl_L", "借券賣出餘額張"), get_in(mw, "sbl_L", "借券賣出餘額張"))
for k in ["上市融資金額億", "上櫃融資金額億", "上市借券賣出餘額張", "外資台指期未平倉淨額口"]:
    if sec1[k]["本週"] is None:
        missing.append(k)

# 三大法人一週買賣金額（億元）
def bfi(d):
    return load_json(f"data/market/week_{week_days(d)[0]}.json", {}).get("億元", {})

bw, bp = bfi(W), bfi(P)
sec1["三大法人本週億元"] = bw          # {單位: [買進, 賣出, 買賣差額]}
sec1["三大法人上週億元"] = bp
if not bw:
    missing.append("三大法人週報")

# ---------- 4. 美股、匯率、利率、商品 ----------
us = load_json("data/raw/us.json", {})


def us_at(sym, d, strict_prev_week=False):
    """某代號在日期 d（含）之前最後一個收盤；strict_prev_week=True 時取「上一週」最後一個收盤"""
    rows = us.get(sym, {}).get("rows", [])
    if strict_prev_week:
        rows = [r for r in rows if iso_week(r[0]) < iso_week(d)]
    else:
        rows = [r for r in rows if r[0] <= d]
    return (rows[-1][0], rows[-1][1]) if rows else (None, None)


sec5 = {}
start_1m = tdays[-23] if len(tdays) > 23 else None            # 「近 1 月」起點：與加權指數同一天（22 個交易日前）
for sym, v in us.items():
    d1, c1 = us_at(sym, W)
    d0, c0 = us_at(sym, W, strict_prev_week=True)
    dm, cm = us_at(sym, start_1m) if start_1m else (None, None)
    rows = [r for r in v["rows"] if r[0] <= W]
    ma65 = statistics.mean(r[1] for r in rows[-65:]) if len(rows) >= 65 else None
    sec5[sym] = {"名稱": v["name"], "本週日期": d1, "本週": c1, "上週日期": d0, "上週": c0,
                 "週變動%": chg(c0, c1), "1月起點日期": dm, "1月變動%": chg(cm, c1), "65日線": ma65,
                 "週變動點": None if c0 is None or c1 is None else c1 - c0}
# 第一節用台股日期比較（上週最後交易日 P → 本週 W）
sec1["美元兌新台幣"] = pair(us_at("TWD=X", P)[1], us_at("TWD=X", W)[1])
sec1["美國10年期殖利率%"] = pair(us_at("^TNX", P)[1], us_at("^TNX", W)[1])
sec5["TAIEX"] = {"名稱": "加權指數", "週變動%": sec1["加權指數"]["變動%"],
                 "1月變動%": chg(taiex[-23], taiex[-1]) if len(taiex) > 23 else None}
if "^SOX" not in us:
    missing.append("美股資料（fetch_us）")

# 台積電 ADR 溢價：ADR 價格 × 匯率 ÷ 5（1 ADR＝5 股）相對台股收盤
prices_w = load_json(f"data/prices/L/{W}.json", {})
prices_p = load_json(f"data/prices/L/{P}.json", {})


def adr_premium(d, tw_close):
    _, tsm = us_at("TSM", d)
    _, fx = us_at("TWD=X", d)
    if not (tsm and fx and tw_close):
        return None
    return {"ADR美元": tsm, "匯率": fx, "換算台幣": tsm * fx / 5, "台股收盤": tw_close,
            "溢價%": (tsm * fx / 5 / tw_close - 1) * 100}


sec5["台積電ADR溢價"] = {"本週": adr_premium(W, (prices_w.get("2330") or [None])[0]),
                     "上週": adr_premium(P, (prices_p.get("2330") or [None])[0])}

# ---------- 5. 產業強弱（非凡概念成分股，等權重）----------
concepts = {c["concept"]: c["stocks"] for c in load_json("data/concepts/ustv_concepts.json")["concepts"]}
imap = {k: v for k, v in load_json("data/concepts/industry_map.json").items() if not k.startswith("_")}
rev = {}
for n in ["L_rev", "O_rev"]:
    for r in load_raw(n):
        rev[r.get("公司代號")] = num(r.get("營業收入-去年同月增減(%)"))
rev_month = next((r.get("資料年月") for r in load_raw("L_rev")), None)
price = {}
for m in "LO":
    pw, pp = load_json(f"data/prices/{m}/{W}.json", {}), load_json(f"data/prices/{m}/{P}.json", {})
    pm = load_json(f"data/prices/{m}/{start_1m}.json", {}) if start_1m else {}
    for c, v in pw.items():
        price[c] = (v[0], (pp.get(c) or [None])[0], (pm.get(c) or [None])[0])
sec4 = {"營收月份": rev_month, "產業": []}
for ind, names in imap.items():
    members = sorted({s[0] for n in names for s in concepts.get(n, [])})
    if not any(n in concepts for n in names):
        missing.append(f"產業 {ind} 的概念名稱在快照中找不到")
    wk = [chg(price[c][1], price[c][0]) for c in members if c in price and price[c][0] and price[c][1]]
    mo = [chg(price[c][2], price[c][0]) for c in members if c in price and price[c][0] and price[c][2]]
    rv = [rev[c] for c in members if rev.get(c) is not None]
    sec4["產業"].append({"產業": ind, "檔數": len(wk), "上漲": sum(1 for x in wk if x > 0),
                       "週報酬%": statistics.mean(wk) if wk else None, "週中位數%": statistics.median(wk) if wk else None,
                       "1月報酬%": statistics.mean(mo) if mo else None,
                       "營收年增中位數%": statistics.median(rv) if rv else None,
                       "營收年增家數": sum(1 for x in rv if x > 0), "營收家數": len(rv)})
sec4["產業"].sort(key=lambda x: -(x["週報酬%"] or -99))
allw = [chg(v[1], v[0]) for c, v in price.items() if len(c) == 4 and c[0] != "0" and v[0] and v[1]]
sec4["全市場等權重週報酬%"] = statistics.mean(allw) if allw else None
sec4["加權指數週報酬%"] = sec1["加權指數"]["變動%"]

# 權值集中度：台積電與前 10 大佔上市普通股市值（用 OpenAPI 股數 × W 收盤）
shares = {r["公司代號"]: num(r["已發行普通股數或TDR原股發行股數"]) for r in load_raw("L_info")}
mcap = {c: prices_w[c][0] * shares[c] for c in shares if c in prices_w and prices_w[c][0] and shares[c]}
tot = sum(mcap.values())
top = sorted(mcap.items(), key=lambda x: -x[1])[:10]
sec1["權值集中度"] = {"台積電%": mcap.get("2330", 0) / tot * 100 if tot else None,
                  "前10大%": sum(v for _, v in top) / tot * 100 if tot else None,
                  "前10大": [c for c, _ in top]}

# ---------- 6. 風險偏好計分（8 個訊號，規則見 RULES.md）----------
def fmt(x, d=0, sign=False):
    """數字轉成好讀的文字（千分位、d 位小數）；None → 缺資料"""
    return "缺資料" if x is None else f"{x:{'+' if sign else ''},.{d}f}"


def sgn(x, pos, neg):
    return None if x is None else (pos if x else neg)


mom_w = load_json(f"{OUT}/momentum_all.json", {})
pdir = f"results/{P[:4]}-{P[4:6]}-{P[6:]}"
mom_p = load_json(f"{pdir}/momentum_all.json", {})
fx_w, fx_p = sec1["美元兌新台幣"]["本週"], sec1["美元兌新台幣"]["上週"]
sox = sec5.get("^SOX", {})
foreign_net = (bw.get("外資及陸資(不含外資自營商)") or [None] * 3)[2]
trust_net = (bw.get("投信") or [None] * 3)[2]
oi = sec1["外資台指期未平倉淨額口"]
margin = sec1["上市融資金額億"]
cnt_w, cnt_p = mom_w.get("count"), mom_p.get("count")
signals = [
    ("趨勢：加權指數 vs 65 日線", f"{fmt(sec1['加權指數']['本週'])} vs {fmt(sec1['加權指數65日線'])}（{fmt(chg(sec1['加權指數65日線'], sec1['加權指數']['本週']), 1, True)}%）",
     sgn(None if sec1["加權指數65日線"] is None else sec1["加權指數"]["本週"] > sec1["加權指數65日線"], 1, -1)),
    ("外資現貨（本週買賣超，億元）", fmt(foreign_net, 0, True), sgn(None if foreign_net is None else foreign_net > 0, 1, -1)),
    ("外資台指期淨額（口，上週→本週）", f"{fmt(oi['上週'], 0, True)} → {fmt(oi['本週'], 0, True)}（{fmt(oi['增減口'], 0, True)} 口）",
     sgn(None if oi["增減口"] is None else oi["增減口"] > 0, 1, -1)),      # 淨額增加＝淨空減少＝偏多
    ("上市融資金額週變動%", fmt(margin["變動%"], 2, True), sgn(None if margin["變動%"] is None else margin["變動%"] < 3, 1, -1)),
    ("費半 vs 65 日線", f"{fmt(sox.get('本週'))} vs {fmt(sox.get('65日線'))}（{fmt(chg(sox.get('65日線'), sox.get('本週')), 1, True)}%）",
     sgn(None if not sox.get("65日線") else sox["本週"] > sox["65日線"], 1, -1)),
    ("美元兌台幣（上週→本週）", f"{fmt(fx_p, 2)} → {fmt(fx_w, 2)}", sgn(None if not (fx_w and fx_p) else fx_w < fx_p, 1, -1)),
    ("投信（本週買賣超，億元；只扣分）", fmt(trust_net, 0, True), sgn(None if trust_net is None else trust_net < 0, -1, 0)),
    ("市場廣度：通過動量門檻檔數（上週→本週）", f"{cnt_p} → {cnt_w}",
     None if cnt_w is None or cnt_p is None else (1 if cnt_w > cnt_p else -1 if cnt_w < cnt_p else 0)),
]
total = sum(s[2] or 0 for s in signals)
risk = {"訊號": [{"訊號": a, "數字": b, "得分": c} for a, b, c in signals], "總分": total,
        "判斷": "偏多" if total >= 3 else "偏保守" if total <= -3 else "中性",
        "缺資料訊號": [a for a, b, c in signals if c is None]}
missing += [f"風險訊號缺資料：{a}" for a in risk["缺資料訊號"]]

result = {"W": W, "P": P, "盤勢": sec1, "產業": sec4, "美股宏觀": sec5, "風險": risk,
          "缺資料": missing, "抓取失敗": load_json("data/market/fetch_status.json", {}).get("failed", [])}
save_json(f"{OUT}/market.json", result)
print(json.dumps({"加權指數": sec1["加權指數"], "65日線": sec1["加權指數65日線"], "風險": risk, "缺資料": missing},
                 ensure_ascii=False, indent=1, default=str))
