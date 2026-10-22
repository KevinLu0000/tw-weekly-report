# 動量股篩選與排名，規則見 RULES.md「動量股篩選規則」
# 用法：python3 scripts/screen_momentum.py [結束日 YYYYMMDD]
#   不給日期＝本週最後交易日 W；給上週日期可以算「上週有幾檔通過」（市場廣度用）
# 輸出：results/<結束日>/momentum_all.json（全部通過門檻的股票，依總分排序）
import sys, statistics, datetime
from common import *

END = sys.argv[1] if len(sys.argv) > 1 else week_end()

# ---------- 1. 每日行情：每檔股票的時間序列（只用到 END 為止）----------
series = {}
for c, rows in load_prices(END).items():
    s = [r for r in rows if r[1] is not None and r[4]]      # 去掉沒成交的日子
    if s:
        series[c] = s

# 加權指數收盤：優先用證交所 FMTQIK 累積檔，沒有就用舊的 data/raw/taiex.json
twse_daily = load_json("data/market/twse_daily.json", {})
taiex = {d: v[1] for d, v in twse_daily.items() if d <= END} or \
        {d: v for d, v in load_raw("taiex").items() if d <= END}
tdays = sorted(taiex)
if tdays[-1] != END:
    raise SystemExit(f"加權指數資料只到 {tdays[-1]}，還沒有 {END}，請先跑 fetch_week.py")


def tret(n):
    """加權指數近 n 個交易日報酬（%）"""
    return (taiex[tdays[-1]] / taiex[tdays[-1 - n]] - 1) * 100


idx = {5: tret(5), 22: tret(22), 65: tret(65)}

# ---------- 2. 基本資料：名稱、市場、股數、產業、最新月營收 ----------
info = {}
for r in load_raw("L_info"):
    info[r["公司代號"]] = dict(name=r["公司簡稱"], mkt="上市", shares=num(r["已發行普通股數或TDR原股發行股數"]))
for r in load_raw("O_info"):
    par = num(r["ParValueOfCommonStock"].replace("新台幣", "").replace("元", "")) or 10   # 每股面額，通常 10 元
    info[r["SecuritiesCompanyCode"]] = dict(name=r["CompanyAbbreviation"], mkt="上櫃",
                                           shares=num(r["Paidin.Capital.NTDollars"]) / par)
for n in ["L_rev", "O_rev"]:
    for r in load_raw(n):
        c = r.get("公司代號")
        if c in info:
            info[c].update(ind=r.get("產業別"), rev_ym=r.get("資料年月"),
                           rev_yoy=num(r.get("營業收入-去年同月增減(%)")),
                           rev_cur=num(r.get("營業收入-當月營收")), rev_ly=num(r.get("營業收入-去年當月營收")))

# ---------- 3. 外資、投信近 5 個交易日買賣超（股）----------
inst_days = last_n_days(END, 5)
lack = [f"{m}_{d}" for d in inst_days for m in "LO" if not os.path.exists(f"data/inst/{m}_{d}.json")]
if lack:
    raise SystemExit(f"缺少法人資料 {lack}，請先跑 fetch_week.py")
fi, it = {}, {}
for d in inst_days:
    # 上市 T86 欄位：r[4] 外資(不含自營)買賣超、r[7] 外資自營商買賣超、r[10] 投信買賣超
    for r in load_json(f"data/inst/L_{d}.json")["data"]:
        fi[r[0]] = fi.get(r[0], 0) + num(r[4]) + num(r[7])
        it[r[0]] = it.get(r[0], 0) + num(r[10])
    # 上櫃 dailyTrade 欄位：r[10] 外資及陸資合計買賣超、r[13] 投信買賣超
    for r in load_json(f"data/inst/O_{d}.json")["tables"][0]["data"]:
        fi[r[0]] = fi.get(r[0], 0) + num(r[10])
        it[r[0]] = it.get(r[0], 0) + num(r[13])

# ---------- 4. 處置、注意、全額交割名單（OpenAPI 最新公告）----------
punish = {r["Code"] for r in load_raw("L_punish")} | {r["SecuritiesCompanyCode"] for r in load_raw("O_punish")}
notice = {r["Code"] for r in load_raw("L_notice") if r.get("Code")} | \
         {r["SecuritiesCompanyCode"] for r in load_raw("O_notice")}
fulldel = {r["Code"] for r in load_raw("L_change")}

start52 = (ymd(END) - datetime.timedelta(days=364)).strftime("%Y%m%d")   # 52 週起點

# ---------- 5. 逐檔檢查門檻、計分 ----------
out, why = [], {}


def fail(k):
    why[k] = why.get(k, 0) + 1


for c, s in series.items():
    if len(c) != 4 or c[0] == "0" or c not in info:      # 只看普通股（4 碼、不是 0 開頭的 ETF）
        continue
    if s[-1][0] != END:
        fail("當天無成交"); continue
    if len(s) < 70:
        fail("交易日不足"); continue
    cl = [x[1] for x in s]
    vol = [x[4] for x in s]
    close = cl[-1]
    I = info[c]
    mcap = close * I["shares"] / 1e8                     # 市值（億元）
    if mcap < 100:
        fail("市值<100億"); continue
    if c in fulldel:
        fail("全額交割"); continue
    val20 = statistics.mean(x[1] * x[4] for x in s[-20:]) / 1e8          # 近 20 日平均成交值（億元）
    if val20 < 1:
        fail("20日均成交值<1億"); continue
    ma22, ma65 = statistics.mean(cl[-22:]), statistics.mean(cl[-65:])     # 22 日、65 日均線
    if not (close > ma22 and close > ma65):
        fail("未站上22/65日均線"); continue
    r5, r22, r65 = [(close / cl[-1 - n] - 1) * 100 for n in (5, 22, 65)]
    if not (r22 > idx[22] and r65 > idx[65]):
        fail("1月或3月報酬未贏大盤"); continue
    v5, v20 = statistics.mean(vol[-5:]), statistics.mean(vol[-20:])
    if not v5 > v20:
        fail("5日均量未大於20日均量"); continue
    f5, t5 = fi.get(c, 0), it.get(c, 0)
    if not ((f5 > 0 or t5 > 0) and f5 + t5 > 0):
        fail("法人門檻未過"); continue
    # 法人買超佔成交值：同一檔股票 5 天內價格差不多，用股數比近似金額比
    inst_ratio = (f5 + t5) / sum(vol[-5:]) * 100
    strong_inst = inst_ratio >= 20
    last_spike = vol[-1] > 1.5 * v5                       # 最後一天量 > 5 日均量 1.5 倍
    spike_up, spike_down = last_spike and cl[-1] > cl[-2], last_spike and cl[-1] < cl[-2]
    yr = [x for x in s if x[0] >= start52]
    hi52 = max(x[2] or x[1] for x in yr)
    lo52 = min(x[3] or x[1] for x in yr)
    base = (r5 - idx[5]) * 0.2 + (r22 - idx[22]) * 0.3 + (r65 - idx[65]) * 0.5
    score = base + (10 if strong_inst else 0) + (5 if spike_up else 0)
    out.append(dict(code=c, name=I["name"], mkt=I["mkt"], ind=I.get("ind"), mcap=mcap, close=close,
                    r5=r5, r22=r22, r65=r65, ex5=r5 - idx[5], ex22=r22 - idx[22], ex65=r65 - idx[65],
                    hi52=hi52, from_hi=(close / hi52 - 1) * 100, lo52=lo52, from_lo=(close / lo52 - 1) * 100,
                    ma22=ma22, ma65=ma65, v5=v5 / 1000, v20=v20 / 1000, vlast=vol[-1] / 1000, val20=val20,
                    f5=f5 / 1000, t5=t5 / 1000, inst_ratio=inst_ratio, strong_inst=strong_inst,
                    spike_up=spike_up, spike_down=spike_down, punish=c in punish, notice=c in notice,
                    rev_ym=I.get("rev_ym"), rev_yoy=I.get("rev_yoy"), rev_cur=I.get("rev_cur"), rev_ly=I.get("rev_ly"),
                    base=base, score=score))

out.sort(key=lambda x: -x["score"])
print(f"結束日 {END}；法人資料日 {inst_days}")
print("加權指數報酬 1週/1月/3月:", {k: round(v, 2) for k, v in idx.items()})
print("刷掉原因:", json.dumps(why, ensure_ascii=False))
print("通過:", len(out))
for i, x in enumerate(out[:15], 1):
    tag = ("法人強" if x["strong_inst"] else "") + (" 放量紅" if x["spike_up"] else "") + \
          (" 放量黑" if x["spike_down"] else "") + (" 處置" if x["punish"] else "") + (" 注意" if x["notice"] else "")
    print(f"{i:>2} {x['code']} {x['name']:<6} 1週{x['r5']:+.1f} 1月{x['r22']:+.1f} 3月{x['r65']:+.1f} "
          f"距高{x['from_hi']:.1f}% 距低{x['from_lo']:.1f}% 法人比{x['inst_ratio']:.0f}% 分{x['score']:.1f} {tag}")
save_json(f"{results_dir(END)}/momentum_all.json",
          {"end": END, "inst_days": inst_days, "taiex_ret": idx, "fail_reasons": why, "count": len(out), "stocks": out})
