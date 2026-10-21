# 準備「第二階段逐檔檢查」清單：價值股候選（依價值評分排序）與動量股前 10 名
# 程式能自動取得的先填好，剩下要逐檔上網查的列在 need 欄位，查完寫進 stage2_input.json
#   自動：上市股（.TW）近四季營業／投資現金流 → Yahoo 財經 fundamentals-timeseries API
#         （與 Yahoo 股市網頁同一資料源；自由現金流＝營業現金流＋投資現金流，與 Yahoo 股市定義相同）
#         月營收 → data/rev/ 每月快照（fetch_basic.py 每週累積）
#   人工（排程中的 Claude 用 WebFetch）：單季 EPS（Yahoo 股市 EPS 頁）、上櫃股現金流、快照沒有的月份營收（HiStock）
# 輸出：results/<W>/stage2_todo.json；若 stage2_input.json 不存在，建立一份含自動資料的初稿
import datetime
from common import *

W = week_end()
OUT = results_dir(W)
val = load_json(f"{OUT}/value_candidates.json")["stocks"]
mom = load_json(f"{OUT}/momentum_all.json")["stocks"][:10]

# ---------- 1. 要檢查的三個月份：最新公布月與前兩個月 ----------
latest = max(s.get("rev_ym") or "0" for s in val + mom)          # 民國年月，例如 11509
y, m = int(latest[:-2]) + 1911, int(latest[-2:])
months = []
for k in range(3):
    mm = (y * 12 + m - 1 - k)
    months.append(f"{mm // 12}{mm % 12 + 1:02d}")                 # 西元年月，例如 202609、202608、202607
revsnap = {mk: {ym: load_json(f"data/rev/{mk}_{ym}.json", {}) for ym in months} for mk in "LO"}


def yahoo_symbol(code, mkt):
    return f"{code}.TW" if mkt == "上市" else f"{code}.TWO"


def yahoo_cf(code):
    """從 Yahoo 財經 API 取上市股近四季營業、投資現金流（仟元），最新在前；取不到回傳 None"""
    p2 = int(time.time())
    p1 = p2 - 800 * 86400
    u = (f"https://query1.finance.yahoo.com/ws/fundamentals-timeseries/v1/finance/timeseries/{code}.TW"
         f"?type=quarterlyOperatingCashFlow,quarterlyInvestingCashFlow&period1={p1}&period2={p2}")
    try:
        j = get(u, tries=2, wait=5)
    except RuntimeError:
        return None
    ser = {}
    for r in j["timeseries"]["result"]:
        t = r["meta"]["type"][0]
        ser[t] = {x["asOfDate"]: x["reportedValue"]["raw"] / 1000 for x in (r.get(t) or []) if x}
    ocf, icf = ser.get("quarterlyOperatingCashFlow", {}), ser.get("quarterlyInvestingCashFlow", {})
    qs = sorted(set(ocf) & set(icf), reverse=True)[:4]
    if len(qs) < 4:
        return None
    q = lambda d: f"{d[:4]}Q{(int(d[5:7]) - 1) // 3 + 1}"
    return {"ocf": [round(ocf[d]) for d in qs], "fcf": [round(ocf[d] + icf[d]) for d in qs],
            "cf_quarters": [q(d) for d in qs],
            "cf_source": f"https://finance.yahoo.com/quote/{code}.TW/cash-flow/（Yahoo 財經 API，{datetime.date.today()} 取得）"}


# ---------- 2. 每家公司「最新財報期別」（例如 115Q2），用來判斷舊的 EPS／現金流還能不能沿用 ----------
fs_period = {}
for mk in "LO":
    for ind in ["ci", "basi", "bd", "fh", "ins", "mim"]:
        for r in load_json(f"data/raw/{mk}_ap06_{ind}.json", []):
            c = r.get("公司代號") or r.get("SecuritiesCompanyCode")
            fs_period[c] = f"{r.get('年度') or r.get('Year')}Q{r.get('季別') or r.get('Season')}"

inp_path = f"{OUT}/stage2_input.json"
inp = load_json(inp_path, {})

# ---------- 3. 沿用前幾週已查到的資料（省下重複上網查）----------
#   月營收：公布後不會變，同一個月份可以直接沿用
#   EPS、現金流：只有在公司「最新財報期別」沒變時才沿用（公布新一季財報後要重查）
prev_inputs = []
for d in sorted(glob.glob("results/*/stage2_input.json"), reverse=True):
    if d != inp_path and d < inp_path:
        prev_inputs.append(load_json(d, {}))
for c in {s["code"] for s in val + mom}:
    rec = inp.setdefault(c, {})
    for old in prev_inputs:
        o = old.get(c)
        if not o:
            continue
        for ym, v in (o.get("rev") or {}).items():
            if ym in months and ym not in rec.setdefault("rev", {}):
                rec["rev"][ym] = v
        if o.get("fs_period") and o.get("fs_period") == fs_period.get(c):
            for k in ["eps", "ocf", "fcf", "cf_quarters"]:
                if k in o and k not in rec:
                    rec[k] = o[k]
            rec.setdefault("sources", [])
            rec["sources"] += [u for u in o.get("sources", []) if u not in rec["sources"]]
    rec["fs_period"] = fs_period.get(c)
todo = {"W": W, "rev_months": months,
        "format": {
            "eps": "最近 6 季單季 EPS，最新在前，例 [[\"2026Q2\", 2.02], [\"2026Q1\", 1.18], ...]（Yahoo 股市 /quote/代號.TW 或 .TWO/eps）",
            "ocf": "近四季單季營業現金流（仟元），最新在前", "fcf": "近四季自由現金流＝營業＋投資現金流（仟元）",
            "cf_quarters": "現金流對應季別，例 [\"2026Q2\", ...]（Yahoo 股市 /cash-flow-statement）",
            "rev": "{西元年月: [當月營收, 去年同月營收]}（仟元；HiStock /stock/代號/每月營收）",
            "sources": "實際打開的網址清單", "note": "查不到時寫試了哪些來源"},
        "value": [], "momentum": []}

for group, lst in [("value", val), ("momentum", mom)]:
    for rank, s in enumerate(lst, 1):
        c = s["code"]
        rec = inp.setdefault(c, {})
        rec.setdefault("rev", {})
        for ym in months:                                           # 月營收：快照有的先填
            snap = revsnap["L" if s["mkt"] == "上市" else "O"][ym]
            if c in snap and ym not in rec["rev"]:
                rec["rev"][ym] = snap[c][:2]
        if group == "value" and "ocf" not in rec and s["mkt"] == "上市":
            cf = yahoo_cf(c)                                        # 現金流只有價值股需要
            if cf:
                rec.update(cf)
                rec.setdefault("sources", []).append(cf["cf_source"])
            time.sleep(0.5)
        need = []
        if "eps" not in rec:
            need.append("eps")
        if group == "value" and "ocf" not in rec:
            need.append("cf")
        need += [f"rev_{ym}" for ym in months if ym not in rec["rev"]]
        need = [x for x in need if x not in (rec.get("unavailable") or [])]   # 已查過確定查不到的不再列
        todo[group].append({"rank": rank, "code": c, "name": s["name"], "mkt": s["mkt"],
                            "yahoo": f"https://tw.stock.yahoo.com/quote/{yahoo_symbol(c, s['mkt'])}",
                            "histock": f"https://histock.tw/stock/{c}/%E6%AF%8F%E6%9C%88%E7%87%9F%E6%94%B6",
                            "score": round(s["score"], 1), "need": need})

save_json(inp_path, inp)
save_json(f"{OUT}/stage2_todo.json", todo)
print(f"檢查月份：{months}")
for g in ["value", "momentum"]:
    print(f"== {g}（前 15 筆）")
    for t in todo[g][:15]:
        print(f"  {t['rank']:>2} {t['code']} {t['name']} {t['mkt']} 還要查：{t['need'] or '無'}")
