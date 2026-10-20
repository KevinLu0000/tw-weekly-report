# 產生「台股動量股初步名單」試算表（資料截至 2026/10/16 收盤）
# 藍字＝來源數字；黑字＝公式
import json
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.comments import Comment

M = json.load(open("mom_passed.json"))
TOP = M[:10]
IDX = {"r5": -4.47, "r22": 2.01, "r65": 5.30}   # 加權指數 1週／1月／3月報酬（%），由 FMTQIK 計算

# 逐檔查到的資料：7、8 月營收（當月, 去年同月, 千元）、單季 EPS（26Q2, 25Q2, 26Q1, 25Q1）
# 來源：HiStock 每月營收頁、Yahoo 股市 EPS 頁；7711 永擎 8 月營收與 25Q2 比較取自 winvest 營收快訊
X = {
 "6505": dict(jul=(74820784,56534424), aug=(81905672,54499632), eps=(2.18,-0.79,2.14,0.39)),
 "6278": dict(jul=(4667997,4161114), aug=(4628384,4174612), eps=(2.76,1.64,2.17,2.88)),
 "3265": dict(jul=(421419,395506), aug=(401868,388792), eps=(2.09,0.66,1.76,1.54)),
 "1569": dict(jul=(207224,241532), aug=(208971,279673), eps=(-0.94,-2.28,-0.73,-1.33)),
 "7711": dict(jul=(5143796,1332030), aug=(2154000,2118828), eps=(9.76,6.64,7.68,None),
              note="8 月營收 21.54 億、年增 1.66% 取自 winvest 營收快訊，去年同月由年增率反推；25Q2 EPS 由「26Q2 EPS 9.76 元、年增 47%」反推（同一來源）；Yahoo 只列 2025Q3 以後"),
 "8039": dict(jul=(847235,901908), aug=(806704,936162), eps=(0.91,0.13,0.65,0.32)),
 "1815": dict(jul=(854379,508238), aug=(912400,509132), eps=(1.45,-0.06,0.79,0.33)),
 "6269": dict(jul=(2045178,1967149), aug=(1997131,1970931), eps=(-1.68,-1.41,-2.60,-1.76)),
 "6715": dict(jul=(154589,125326), aug=(164842,77384), eps=(-0.12,0.45,1.02,0.69)),
 "2603": dict(jul=(48079100,33605172), aug=(48985696,32956840), eps=(7.41,5.06,3.84,12.64)),
}
# 營收／獲利催化劑（分析判斷，只根據表內數字）
CAT = {
 "6505": "7～9 月營收年增 32%～66%；26Q2 EPS 2.18 元，去年同季虧損",
 "6278": "7～9 月營收年增 11%～16%；26Q2 EPS 年增 68%",
 "3265": "7～9 月營收年增 3%～11%；26Q2 EPS 年增 217%",
 "1569": "9 月營收年增 39%，但 7、8 月年減；仍在虧損，26Q2 EPS -0.94 元（虧損比去年縮小）",
 "7711": "9 月營收年增 42%；26Q2 EPS 9.76 元、年增 47%（winvest）",
 "8039": "9 月營收年減 19%，近三月營收都年減；股價走勢與營收背離",
 "1815": "7～9 月營收年增 68%～82%；26Q2 EPS 1.45 元，去年同季虧損",
 "6269": "9 月營收年減 3%；26Q2 仍虧損 1.68 元，且虧損比去年擴大",
 "6715": "7～9 月營收大增，但 26Q2 由盈轉虧（-0.12 元）",
 "2603": "7～9 月營收年增 43%～64%；26Q2 EPS 年增 46%",
}

wb = Workbook(); F = "Arial"
blue, black = Font(name=F, color="0000FF"), Font(name=F)
hdr = Font(name=F, bold=True, color="FFFFFF"); fill = PatternFill("solid", fgColor="1F3864")
red_fill = PatternFill("solid", fgColor="FCE4D6"); green_fill = PatternFill("solid", fgColor="E2EFDA")
thin = Side(style="thin", color="BFBFBF"); box = Border(left=thin, right=thin, top=thin, bottom=thin)
wrap = Alignment(wrap_text=True, vertical="top")

# ================= 工作表 2：營收與EPS =================
q = wb.active; q.title = "營收與EPS"
q.append(["代號","公司","7月營收","去年7月","8月營收","去年8月","9月營收","去年9月",
          "近3月營收年增率","9月營收年增率","26Q2 EPS","25Q2 EPS","26Q1 EPS","25Q1 EPS","備註"])
qrow = {}
for x in TOP:
    c = x["code"]; d = X[c]; r = q.max_row + 1
    q.append([c, x["name"], *d["jul"], *d["aug"], x["rev_cur"], x["rev_ly"],
              f"=(C{r}+E{r}+G{r})/(D{r}+F{r}+H{r})-1", f"=G{r}/H{r}-1", *d["eps"], d.get("note", "")])
    qrow[c] = r
for row in q.iter_rows(min_row=2):
    for cell in row:
        cell.border = box; cell.font = black if isinstance(cell.value, str) and cell.value.startswith("=") else blue
    for cell in row[2:8]: cell.number_format = "#,##0"
    row[8].number_format = row[9].number_format = "0.0%"
    row[0].font = row[1].font = black
q.cell(q.max_row + 2, 1, "單位：營收為千元；EPS 為元（單季）。9 月營收來自證交所／櫃買 OpenAPI 月營收彙總表，7、8 月來自 HiStock 每月營收頁，EPS 來自 Yahoo 股市 EPS 頁。").font = Font(name=F, italic=True)
for i, w in enumerate([7,10,13,13,13,13,13,13,11,11,9,9,9,9,60], 1): q.column_dimensions[get_column_letter(i)].width = w

# ================= 工作表 1：動量股 Top 10 =================
t = wb.create_sheet("動量股Top10", 0)
cols = ["排名","代號","公司","市場","產業","分類","標示","收盤價","近1週報酬","近1月報酬","近3月報酬",
        "52週高點","距52週高點","22日均線(警戒)","距22日線","65日均線(失效)","距65日線",
        "5日均量(張)","20日均量(張)","10/16量(張)","外資5日(張)","投信5日(張)","法人買超佔成交值",
        "近3月營收年增率","26Q2 EPS","25Q2 EPS","動量基本分","加分","總分",
        "均線與量價訊號（分析判斷）","營收／獲利催化劑（分析判斷）","支撐位與失效條件"]
t.append(cols)
for i, x in enumerate(TOP, 1):
    c = x["code"]; d = X[c]; r = t.max_row + 1; qr = qrow[c]
    jul, aug = d["jul"], d["aug"]
    rev3 = (jul[0] + aug[0] + x["rev_cur"]) / (jul[1] + aug[1] + x["rev_ly"]) - 1
    fund = x["rev_yoy"] > 0 and rev3 > 0 and d["eps"][0] > d["eps"][1]
    tags = [s for s, ok in [("法人強力買超", x["strong_inst"]), ("最後一天放量上攻", x["spike_up"]),
                            ("放量收黑", x["spike_down"]), ("處置股", x["punish"]), ("注意股", x["notice"]),
                            ("仍虧損", d["eps"][0] < 0)] if ok]
    sig = (f"站上 22、65 日線；5 日均量 {x['v5']:,.0f} 張 > 20 日均量 {x['v20']:,.0f} 張"
           + ("；10/16 放量收紅" if x["spike_up"] else "") + ("；10/16 放量收黑" if x["spike_down"] else "")
           + f"；距 52 週高點 {x['from_hi']:.1f}%")
    t.append([i, c, x["name"], x["mkt"], x["ind"], "基本面支持" if fund else "題材／籌碼型",
              "、".join(tags), x["close"], x["r5"]/100, x["r22"]/100, x["r65"]/100,
              x["hi52"], f"=H{r}/L{r}-1", round(x["ma22"], 2), f"=H{r}/N{r}-1", round(x["ma65"], 2), f"=H{r}/P{r}-1",
              round(x["v5"]), round(x["v20"]), round(x["vlast"]), round(x["f5"]), round(x["t5"]), x["inst_ratio"]/100,
              f"='營收與EPS'!I{qr}", f"='營收與EPS'!K{qr}", f"='營收與EPS'!L{qr}",
              f"=(I{r}-({IDX['r5']}/100))*100*0.2+(J{r}-({IDX['r22']}/100))*100*0.3+(K{r}-({IDX['r65']}/100))*100*0.5",
              (10 if x["strong_inst"] else 0) + (5 if x["spike_up"] else 0), f"=AA{r}+AB{r}",
              sig, CAT[c],
              f"警戒：跌破 22 日線 {x['ma22']:.1f} 元，減碼一部分；失效：跌破 65 日線 {x['ma65']:.1f} 元，出場或大幅降低部位"])
for row in t.iter_rows(min_row=2):
    for cell in row:
        cell.border = box; cell.alignment = wrap
        v = cell.value; cell.font = black if isinstance(v, str) and v.startswith("=") else blue
    for idx in [1,2,3,4,5,6,7,30,31,32]: row[idx-1].font = black
    row[5].fill = green_fill if row[5].value == "基本面支持" else red_fill
    for idx, fmt in {8:"0.00",9:"0.0%",10:"0.0%",11:"0.0%",12:"0.00",13:"0.0%",14:"0.00",15:"0.0%",16:"0.00",17:"0.0%",
                     18:"#,##0",19:"#,##0",20:"#,##0",21:"#,##0;(#,##0)",22:"#,##0;(#,##0)",23:"0.0%",24:"0.0%",25:"0.00",26:"0.00",27:"0.0",28:"0",29:"0.0"}.items():
        row[idx-1].number_format = fmt
for cell in t[1]:
    cell.font = hdr; cell.fill = fill; cell.border = box
    cell.alignment = Alignment(wrap_text=True, vertical="center", horizontal="center")
for i, w in enumerate([5,7,9,6,12,11,14,8,8,8,8,8,8,9,8,9,8,9,9,9,9,9,9,9,8,8,8,6,7,36,36,40], 1):
    t.column_dimensions[get_column_letter(i)].width = w
t.freeze_panes = "D2"; t.row_dimensions[1].height = 45
t["AA1"].comment = Comment("基本分＝(1週報酬−大盤)×0.2＋(1月報酬−大盤)×0.3＋(3月報酬−大盤)×0.5，單位百分點；大盤＝加權指數 1週 -4.47%、1月 +2.01%、3月 +5.30%", "Claude")
t["W1"].comment = Comment("外資＋投信 5 日合計買超股數 ÷ 5 日總成交股數；≥ 20% 標示「法人強力買超」並加 10 分", "Claude")
n = t.max_row + 2
t.cell(n, 1, "注意：近期強勢不代表未來報酬；題材／籌碼型為高波動動量，需嚴設停損。訊號與催化劑欄為根據數字的分析判斷，尚未查證新聞與法說內容。").font = Font(name=F, bold=True, color="C00000")
t.cell(n+1, 1, "藍字＝來源數字；黑字＝公式。綠底＝基本面支持；橘底＝題材／籌碼型。").font = Font(name=F, italic=True)

# ================= 工作表 3：第 11～30 名 =================
o = wb.create_sheet("第11-30名")
o.append(["排名","代號","公司","產業","近1週","近1月","近3月","距52週高點","法人買超佔成交值","9月營收年增率","總分","標示"])
for i, x in enumerate(M[10:30], 11):
    tags = "、".join(s for s, ok in [("法人強力買超", x["strong_inst"]), ("最後一天放量上攻", x["spike_up"]),
                                    ("放量收黑", x["spike_down"]), ("處置股", x["punish"]), ("注意股", x["notice"])] if ok)
    o.append([i, x["code"], x["name"], x["ind"], x["r5"]/100, x["r22"]/100, x["r65"]/100, x["from_hi"]/100,
              x["inst_ratio"]/100, (x["rev_yoy"] or 0)/100, round(x["score"], 1), tags])
for row in o.iter_rows(min_row=2):
    for cell in row: cell.font = blue; cell.border = box
    for idx in [5,6,7,8,9,10]: row[idx-1].number_format = "0.0%"
for cell in o[1]: cell.font = hdr; cell.fill = fill; cell.alignment = Alignment(wrap_text=True, horizontal="center")
for i, w in enumerate([5,7,10,14,8,8,8,10,10,10,7,24], 1): o.column_dimensions[get_column_letter(i)].width = w
o.cell(o.max_row + 2, 1, "第 11 名以後尚未逐檔查 7、8 月營收與單季 EPS，所以還沒分類。").font = Font(name=F, italic=True)

# ================= 工作表 4：篩選規則與來源 =================
s = wb.create_sheet("篩選規則與來源")
rows = [
 ["台股動量股初步名單：篩選規則、漏斗與資料來源"],
 ["資料截至","2026/10/16（週五）收盤；法人資料 10/12～10/16；處置／注意股名單為 10/19 抓取的最新公告"],
 ["加權指數報酬","近 1 週 -4.47%、近 1 月 +2.01%、近 3 月 +5.30%（1 週＝5 日、1 月＝22 日、3 月＝65 個交易日）"],
 [],
 ["篩選條件（依序檢查）","門檻","刷掉檔數"],
 ["上市櫃普通股、10/16 有成交、交易日足夠","","52"],
 ["市值","≥ 100 億元","1,255"],
 ["全額交割（變更交易）","剔除（待確認）","0"],
 ["流動性","近 20 日平均成交值 ≥ 1 億元","240"],
 ["趨勢","收盤價站上 22 日與 65 日均線","232"],
 ["報酬","近 1 月與近 3 月報酬都高於加權指數","83"],
 ["量能","近 5 日均量 ＞ 近 20 日均量","33"],
 ["法人","外資或投信至少一方 5 日買超，且外資＋投信合計買超","15"],
 ["→ 通過","","73 檔"],
 [],
 ["排名與標示",""],
 ["動量基本分","1 週、1 月、3 月超額報酬 × 20%、30%、50%"],
 ["加分","法人買超佔 5 日成交值 ≥ 20%：+10；10/16 量 ＞ 5 日均量 1.5 倍且收紅：+5"],
 ["警訊標示","10/16 量 ＞ 5 日均量 1.5 倍但收黑：「放量收黑」；處置股、注意股照常保留並標示"],
 ["分類","最新月營收年增、近 3 月累計營收年增、最近一季 EPS ＞ 去年同季，三項都符合＝基本面支持；否則＝題材／籌碼型"],
 ["支撐／失效","22 日均線＝警戒（減碼一部分）；65 日均線＝失效（出場或大幅降低部位）"],
 [],
 ["資料來源",""],
 ["每日行情（上市／上櫃）","https://www.twse.com.tw/rwd/zh/afterTrading/MI_INDEX ； https://www.tpex.org.tw/www/zh-tw/afterTrading/otc"],
 ["加權指數","https://www.twse.com.tw/rwd/zh/afterTrading/FMTQIK"],
 ["三大法人個股買賣超","https://www.twse.com.tw/rwd/zh/fund/T86 ； https://www.tpex.org.tw/www/zh-tw/insti/dailyTrade"],
 ["處置股","https://openapi.twse.com.tw/v1/announcement/punish ； https://www.tpex.org.tw/openapi/v1/tpex_disposal_information"],
 ["注意股","https://openapi.twse.com.tw/v1/announcement/notice ； https://www.tpex.org.tw/openapi/v1/tpex_trading_warning_information"],
 ["月營收（9 月）","https://openapi.twse.com.tw/v1/opendata/t187ap05_L ； https://www.tpex.org.tw/openapi/v1/mopsfin_t187ap05_O"],
 ["月營收（7、8 月）","https://histock.tw/stock/代號/每月營收"],
 ["單季 EPS","https://tw.stock.yahoo.com/quote/代號.TW/eps（上櫃為 .TWO）"],
 ["永擎 8 月營收、Q2 EPS 年增","https://winvest.tw/News/Detail/94943"],
 [],
 ["已知限制",""],
 ["1","股價報酬沒有做除權息還原，除息的股票報酬會略為低估"],
 ["2","處置／注意股名單是 10/19 抓的最新公告，不是 10/16 當天的名單"],
 ["3","第 11 名以後尚未逐檔分類"],
 ["4","濱川（1569）依規則算「基本面支持」，但它仍在虧損，EPS 只是虧損比去年小，已加註「仍虧損」"],
 ["5","均線與量價訊號、催化劑欄為根據數字的分析判斷，尚未查證新聞與法說內容"],
]
for r in rows: s.append(r)
s["A1"].font = Font(name=F, bold=True, size=14)
for r in [5, 16, 23, 34]:
    for c in s[r]: c.font = Font(name=F, bold=True)
for row in s.iter_rows():
    for c in row:
        if not c.font.bold: c.font = Font(name=F)
        c.alignment = Alignment(wrap_text=True, vertical="top")
s.column_dimensions["A"].width = 34; s.column_dimensions["B"].width = 95; s.column_dimensions["C"].width = 12
wb.save("台股動量股初步名單_20261016.xlsx"); print("ok")
