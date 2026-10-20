# 動量股初步篩選（資料截至 2026/10/16 收盤），規則見 RULES.md「動量股篩選規則」
import json, glob, statistics
num = lambda s: float(str(s).replace(",", "").strip() or 0) if str(s).replace(",", "").strip() not in ("", "--", "---") else None
def load(n): return json.load(open(f"data/raw/{n}.json"))
END = "20261016"

# ---------- 1. 每日行情：組成每檔股票的時間序列（只用到 10/16）----------
series = {}
for m in "LO":
    for f in sorted(glob.glob(f"data/prices/{m}/*.json")):
        d = f[-13:-5]
        if d > END: continue
        for c, v in json.load(open(f)).items():
            if v[0] is not None and v[3]: series.setdefault(c, []).append((d, *v))   # (日期, 收盤, 最高, 最低, 量)
taiex = {d: v for d, v in load("taiex").items() if d <= END}
tdays = sorted(taiex)                                   # 加權指數的交易日當作基準
def tret(n):                                            # 加權指數 n 日報酬（%）
    return (taiex[tdays[-1]] / taiex[tdays[-1 - n]] - 1) * 100
idx = {5: tret(5), 22: tret(22), 65: tret(65)}

# ---------- 2. 基本資料、市值、名稱、產業 ----------
info = {}
for r in load("L_info"): info[r["公司代號"]] = dict(name=r["公司簡稱"], mkt="上市", shares=num(r["已發行普通股數或TDR原股發行股數"]))
for r in load("O_info"): info[r["SecuritiesCompanyCode"]] = dict(name=r["CompanyAbbreviation"], mkt="上櫃", shares=num(r["Paidin.Capital.NTDollars"]) / 10)
for n in ["L_rev", "O_rev"]:
    for r in load(n):
        c = r.get("公司代號")
        if c in info: info[c].update(ind=r.get("產業別"), rev_yoy=num(r.get("營業收入-去年同月增減(%)")),
                                     rev_cur=num(r.get("營業收入-當月營收")), rev_ly=num(r.get("營業收入-去年當月營收")))

# ---------- 3. 法人 5 日買賣超（股）----------
fi, it = {}, {}
for d in ["20261012", "20261013", "20261014", "20261015", "20261016"]:
    for r in json.load(open(f"data/inst/L_{d}.json"))["data"]:
        fi[r[0]] = fi.get(r[0], 0) + num(r[4]) + num(r[7]); it[r[0]] = it.get(r[0], 0) + num(r[10])
    for r in json.load(open(f"data/inst/O_{d}.json"))["tables"][0]["data"]:
        fi[r[0]] = fi.get(r[0], 0) + num(r[10]); it[r[0]] = it.get(r[0], 0) + num(r[13])

# ---------- 4. 標示名單 ----------
punish = {r["Code"] for r in load("L_punish")} | {r["SecuritiesCompanyCode"] for r in load("O_punish")}
notice = {r["Code"] for r in load("L_notice") if r["Code"]} | {r["SecuritiesCompanyCode"] for r in load("O_notice")}
fulldel = {r["Code"] for r in load("L_change")}

# ---------- 5. 逐檔檢查 ----------
out, why = [], {}
def fail(k): why[k] = why.get(k, 0) + 1
for c, s in series.items():
    if len(c) != 4 or c[0] == "0" or c not in info: continue
    if s[-1][0] != END: fail("10/16 無成交"); continue
    if len(s) < 70: fail("交易日不足"); continue
    cl = [x[1] for x in s]; vol = [x[4] for x in s]
    close = cl[-1]; I = info[c]
    mcap = close * I["shares"] / 1e8
    if mcap < 100: fail("市值<100億"); continue
    if c in fulldel: fail("全額交割"); continue
    val20 = statistics.mean(x[1] * x[4] for x in s[-20:]) / 1e8          # 20 日平均成交值（億）
    if val20 < 1: fail("20日均成交值<1億"); continue
    ma22, ma65 = statistics.mean(cl[-22:]), statistics.mean(cl[-65:])
    if not (close > ma22 and close > ma65): fail("未站上22/65日均線"); continue
    r5, r22, r65 = [(close / cl[-1 - n] - 1) * 100 for n in (5, 22, 65)]
    if not (r22 > idx[22] and r65 > idx[65]): fail("1月或3月報酬未贏大盤"); continue
    v5, v20 = statistics.mean(vol[-5:]), statistics.mean(vol[-20:])
    if not v5 > v20: fail("5日均量未大於20日均量"); continue
    f5, t5 = fi.get(c, 0), it.get(c, 0)
    if not ((f5 > 0 or t5 > 0) and f5 + t5 > 0): fail("法人門檻未過"); continue
    # 法人買超佔成交值：用每日收盤價把 5 日總量換算金額；股數比 ≈ 金額比
    inst_ratio = (f5 + t5) / sum(vol[-5:]) * 100
    strong_inst = inst_ratio >= 20
    last_spike = vol[-1] > 1.5 * v5
    up = cl[-1] > cl[-2]
    spike_up, spike_down = last_spike and up, last_spike and cl[-1] < cl[-2]
    hi52 = max(x[2] or 0 for x in s if x[0] >= "20251017")
    base = (r5 - idx[5]) * 0.2 + (r22 - idx[22]) * 0.3 + (r65 - idx[65]) * 0.5
    score = base + (10 if strong_inst else 0) + (5 if spike_up else 0)
    out.append(dict(code=c, name=I["name"], mkt=I["mkt"], ind=I.get("ind"), mcap=mcap, close=close,
                    r5=r5, r22=r22, r65=r65, ex5=r5-idx[5], ex22=r22-idx[22], ex65=r65-idx[65],
                    hi52=hi52, from_hi=(close / hi52 - 1) * 100, ma22=ma22, ma65=ma65,
                    v5=v5/1000, v20=v20/1000, vlast=vol[-1]/1000, val20=val20,
                    f5=f5/1000, t5=t5/1000, inst_ratio=inst_ratio, strong_inst=strong_inst,
                    spike_up=spike_up, spike_down=spike_down, punish=c in punish, notice=c in notice,
                    rev_yoy=I.get("rev_yoy"), rev_cur=I.get("rev_cur"), rev_ly=I.get("rev_ly"),
                    base=base, score=score))
out.sort(key=lambda x: -x["score"])
print("加權指數報酬 1週/1月/3月:", {k: round(v, 2) for k, v in idx.items()})
print("刷掉原因:", json.dumps(why, ensure_ascii=False)); print("通過:", len(out))
for i, x in enumerate(out[:25], 1):
    tag = ("法人強" if x["strong_inst"] else "") + (" 放量紅" if x["spike_up"] else "") + (" 放量黑" if x["spike_down"] else "") + (" 處置" if x["punish"] else "") + (" 注意" if x["notice"] else "")
    print(f"{i:>2} {x['code']} {x['name']:<6} {x['ind']} 1週{x['r5']:+.1f} 1月{x['r22']:+.1f} 3月{x['r65']:+.1f} 距高{x['from_hi']:.1f}% 法人比{x['inst_ratio']:.0f}% 月營收YoY{x['rev_yoy']} 分{x['score']:.1f} {tag}")
json.dump(out, open("data/mom_passed.json", "w"), ensure_ascii=False, indent=1)
