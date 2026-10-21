# 價值股第一階段篩選（全市場自動篩選），規則見 RULES.md「價值股篩選規則」
# 步驟：合併各資料 → 算市值、52 週高低點、TTM EPS、負債比/ROE → 依條件過濾 → 綜合評分排序
# 輸出：results/<本週最後交易日>/value_candidates.json（通過第一階段的股票，依價值評分排序）
#       第二階段（現金流、單季 EPS、近三個月營收）由 stage2_prep.py → 逐檔查 → finalize.py 處理
import statistics, datetime
from common import *

load = load_raw
W = week_end()

stocks = {}   # 代號 → 這檔股票的所有欄位

# ---------- 1. 基本資料：名稱、市場、發行股數 ----------
for r in load("L_info"):
    stocks[r["公司代號"]] = dict(code=r["公司代號"], name=r["公司簡稱"], mkt="上市",
                                shares=num(r["已發行普通股數或TDR原股發行股數"]))
for r in load("O_info"):
    par = num(r["ParValueOfCommonStock"].replace("新台幣", "").replace("元", "")) or 10
    stocks[r["SecuritiesCompanyCode"]] = dict(code=r["SecuritiesCompanyCode"], name=r["CompanyAbbreviation"],
                                mkt="上櫃", shares=num(r["Paidin.Capital.NTDollars"]) / par)

# ---------- 2. 收盤價、估值（本益比/淨值比/殖利率）----------
for r in load("L_quote"):
    if r["Code"] in stocks: stocks[r["Code"]]["close"] = num(r["ClosingPrice"])
for r in load("O_quote"):
    if r["SecuritiesCompanyCode"] in stocks: stocks[r["SecuritiesCompanyCode"]]["close"] = num(r["Close"])
for r in load("L_val"):
    if r["Code"] in stocks: stocks[r["Code"]].update(pe=num(r["PEratio"]), pb=num(r["PBratio"]), dy=num(r["DividendYield"]))
for r in load("O_val"):
    c = r["SecuritiesCompanyCode"]
    if c in stocks: stocks[c].update(pe=num(r["PriceEarningRatio"]), pb=num(r["PriceBookRatio"]), dy=num(r["YieldRatio"]))

# ---------- 3. 月營收（產業別也從這裡拿）----------
for n in ["L_rev", "O_rev"]:
    for r in load(n):
        c = r.get("公司代號") or r.get("SecuritiesCompanyCode") or r.get("公司代號")
        if c not in stocks: continue
        g = lambda k: r.get(k) if k in r else None
        stocks[c].update(ind=r.get("產業別"), rev_ym=r.get("資料年月"),
                         rev_yoy=num(r.get("營業收入-去年同月增減(%)")),
                         rev_cum_yoy=num(r.get("累計營業收入-前期比較增減(%)")))

# ---------- 4. 營益分析：最近一季毛利率、稅後純益率 ----------
for r in load("L_margin"):
    c = r["公司代號"]
    if c in stocks: stocks[c].update(gm=num(r["毛利率(%)(營業毛利)/(營業收入)"]), nm=num(r["稅後純益率(%)(稅後純益)/(營業收入)"]))
for r in load("O_margin"):
    c = r["SecuritiesCompanyCode"]
    if c in stocks: stocks[c].update(gm=num(r["毛利率"]), nm=num(r["稅後純益率"]))

# ---------- 5. 財報：負債比（一般業）或 ROE（金融業），以及上半年 EPS ----------
FIN = {"basi", "bd", "fh", "ins"}           # 金融類財報格式
for m in ["L", "O"]:
    for ind in ["ci", "mim", "basi", "bd", "fh", "ins"]:
        bs = {(r.get("公司代號") or r.get("SecuritiesCompanyCode")): r for r in load(f"{m}_ap07_{ind}")}
        for r in load(f"{m}_ap06_{ind}"):
            c = r.get("公司代號") or r.get("SecuritiesCompanyCode")
            if c not in stocks: continue
            s = stocks[c]; b = bs.get(c, {})
            s["fin"] = ind in FIN
            s["eps_h1"] = num(r.get("基本每股盈餘（元）"))
            s["fs_period"] = f"{r.get('年度') or r.get('Year')}Q{r.get('季別') or r.get('Season')}"
            assets = num(b.get("資產總計") or b.get("資產總額"))
            liab = num(b.get("負債總計") or b.get("負債總額"))
            if assets and liab is not None: s["debt"] = liab / assets * 100
            eq = num(b.get("歸屬於母公司業主之權益合計"))
            ni = num(r.get("淨利（淨損）歸屬於母公司業主"))
            if eq and ni is not None: s["roe"] = ni * 2 / eq * 100   # 上半年 ×2 年化

# ---------- 6. 52 週高低點、近 20 日均量（用每日行情計算，只用到 W 為止）----------
hist = load_prices(W)
start52 = (ymd(W) - datetime.timedelta(days=364)).strftime("%Y%m%d")  # 52 週起點
for c, rows in hist.items():
    if c not in stocks: continue
    rows.sort()
    yr = [r for r in rows if r[0] >= start52 and r[3] is not None]
    if len(yr) < 150: continue               # 交易日太少（新上市）就不算
    s = stocks[c]
    if rows[-1][0] == W and rows[-1][1] is not None:
        s["close"] = rows[-1][1]             # 收盤價以 W 當天的日行情為準
    lo = min(yr, key=lambda r: r[3]); hi = max(yr, key=lambda r: r[2] or 0)
    s.update(low52=lo[3], low52_date=lo[0], high52=hi[2], high52_date=hi[0], days=len(yr))
    vol20 = [r[4] for r in yr[-20:] if r[4]]
    s["vol20"] = statistics.mean(vol20) / 1000 if vol20 else 0   # 單位：張

# ---------- 7. 處置股、全額交割（變更交易）名單 ----------
bad = {r["Code"] for r in load("L_punish")} | {r["SecuritiesCompanyCode"] for r in load("O_punish")} \
      | {r["Code"] for r in load("L_change")}

# ---------- 8. 逐條篩選，記錄每檔被刷掉的原因 ----------
passed, reasons = [], {}
for c, s in stocks.items():
    def fail(why): reasons[why] = reasons.get(why, 0) + 1
    if not (len(c) == 4 and c[0] != "0"): continue                       # 只留普通股
    if s.get("close") is None or s.get("shares") is None: fail("無收盤價/股數"); continue
    s["mcap"] = s["close"] * s["shares"] / 1e8                            # 市值（億元）
    if s["mcap"] < 100: fail("市值<100億"); continue
    if c in bad: fail("處置/全額交割"); continue
    if s.get("low52") is None: fail("股價歷史不足"); continue
    s["dist"] = (s["close"] / s["low52"] - 1) * 100                       # 距 52 週低點 %
    s["from_hi"] = (s["close"] / s["high52"] - 1) * 100                   # 距 52 週高點 %
    if s["dist"] > 15: fail("距52週低>15%"); continue
    if s.get("vol20", 0) < 500: fail("20日均量<500張"); continue
    if not s.get("pe"): fail("本益比空白(近四季EPS≤0或無資料)"); continue
    s["eps_ttm"] = s["close"] / s["pe"]                                   # 近四季 EPS = 股價 ÷ 本益比
    if "fin" not in s: fail("財報資料不足"); continue
    if s["fin"]:
        if (s.get("roe") or 0) <= 8: fail("金融股ROE≤8%"); continue
    else:
        if s.get("debt") is None or s["debt"] > 60: fail("負債比>60%"); continue
    if (s.get("eps_h1") or 0) <= 0: fail("今年上半年EPS≤0"); continue
    if s.get("rev_yoy") is None or s["rev_yoy"] < -10 or (s.get("rev_cum_yoy") or 0) < -10:
        fail("營收年減>10%(月或累計)"); continue
    if not s["fin"] and (s.get("gm") is None or s["gm"] <= 0): fail("毛利率≤0"); continue
    passed.append(s)

# ---------- 9. 綜合評分：本益比低、淨值比低、殖利率高、離低點近，各取百分位平均 ----------
def pct_rank(vals, v, high_good):
    below = sum(1 for x in vals if (x < v if high_good else x > v))
    return below / max(len(vals) - 1, 1)
for key, hg in [("pe", False), ("pb", False), ("dy", True), ("dist", False)]:
    vals = [p.get(key) or 0 for p in passed]
    for p in passed: p[f"r_{key}"] = pct_rank(vals, p.get(key) or 0, hg)
for p in passed: p["score"] = round(sum(p[f"r_{k}"] for k in ["pe", "pb", "dy", "dist"]) / 4 * 100, 1)
passed.sort(key=lambda p: -p["score"])

print("本週最後交易日:", W, "；52 週起點:", start52)
print("刷掉原因統計:", json.dumps(reasons, ensure_ascii=False))
print("通過條件:", len(passed))
for p in passed[:30]:
    print(p["code"], p["name"], p["mkt"], p.get("ind"), f"市值{p['mcap']:.0f}億 收{p['close']} 低{p['low52']} 距{p['dist']:.1f}% PE{p['pe']} PB{p['pb']} 殖{p['dy']} 月營收YoY{p['rev_yoy']:.1f} 負債{p.get('debt') or 0:.0f}% ROE{p.get('roe') or 0:.1f} 分{p['score']}")
save_json(f"{results_dir(W)}/value_candidates.json",
          {"end": W, "fail_reasons": reasons, "universe": sum(reasons.values()) + len(passed),
           "count": len(passed), "stocks": passed})
