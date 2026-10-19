# 產生「台股價值股初步名單」試算表（資料截至 2026/10/16 收盤）
# 藍字＝直接從資料來源抄來的數字；黑字＝公式計算
import json
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.comments import Comment
from yahoo import Y

P = {p["code"]: p for p in json.load(open("passed.json"))}
TOP = ["2204","1307","9958","9904","1722","3413","2439","4114","1227","9910"]
BACKUP = ["1229"]
DROP = {"9938": "連續兩季 EPS 年減：26Q2 0.49 vs 25Q2 0.67；26Q1 0.87 vs 25Q1 1.54",
        "7780": "連續兩季 EPS 年減：26Q2 0.16 vs 25Q2 0.65；26Q1 0.13 vs 25Q1 1.75",
        "2504": "連續兩季 EPS 年減：26Q2 0.77 vs 25Q2 0.87；26Q1 0.70 vs 25Q1 0.71",
        "1210": "連續兩季 EPS 年減：26Q2 0.53 vs 25Q2 0.68；26Q1 0.94 vs 25Q1 1.05"}
# 7、8 月單月營收年增率（HiStock 每月營收頁，照原文）；9 月用證交所／櫃買 OpenAPI
REV78 = {"2204": (13.6, -3.0), "1307": (11.0, 10.8), "9958": (91.2, 91.1), "9904": (-0.6, 4.3),
         "1722": (9.8, -11.3), "3413": (30.1, 23.5), "2439": (-0.3, -6.7), "1227": ("負債比 40%、殖利率 4.7%；近四季營業現金流 27.5 億",
          "連續兩季 EPS 年增（Q2 +115%、Q1 +33%），9 月營收年增 9%",
          "本益比約 17.8 倍；Q2 營業現金流為負、投資現金流 -23.8 億，近四季自由現金流為負"),
 "9910": ("近四季自由現金流 54.6 億（名單最高），ROE 14%、殖利率 5.9%",
          "Q2 EPS 1.03 元、年增 41%",
          "淨值比 2.9 倍偏高；Q1 EPS 年減 41%；8、9 月營收小幅年減"),
 "1229": ("負債比 20%、近四季自由現金流 48.6 億、殖利率 4.9%",
          "7 月營收年增 115%",
          "Q2 EPS 年減 16%、8 月營收年減 13%；本益比約 16.6 倍"),
 "4114": (59.8, 49.9),
         "1227": (7.7, 10.7), "9910": (1.0, -2.8), "1229": (115.0, -13.1)}

# 投資論點／催化劑／風險：只根據表內數字寫成的「分析判斷」，不是新聞或公司說法
NOTE = {
 "2204": ("本益比約 8.5 倍、淨值比 0.77、殖利率 6.8%，估值在名單中最便宜之一；負債比 24%、近四季自由現金流為正",
          "Q2 EPS 2.02 元、年增 58%，若下半年維持，近四季 EPS 可續升",
          "汽車業景氣循環；Q1 營業現金流為負，現金流季度波動大"),
 "1307": ("本益比約 9.4 倍、殖利率 7.0%；負債比 47%，近四季營業現金流為正",
          "上半年 EPS 年增 52%（去年 Q2 有虧損，基期低）",
          "Q2 EPS 季減 49%、Q2 營業現金流為負；近四季自由現金流僅約打平"),
 "2504": ("本益比約 10 倍、殖利率 8.1%（名單最高）；近四季營業現金流 51.5 億、自由現金流為正",
          "近四季營業現金流穩定為正（每季都 > 0），可留意下一次配息政策",
          "營建／建材景氣與房市政策；高殖利率需確認配息能否維持"),
 "1210": ("本益比約 12.7 倍、殖利率 5.8%；近四季營業現金流 64.7 億",
          "9 月營收年增 13%",
          "上半年 EPS 年減 15%、近兩季 EPS 都是年減；近四季自由現金流為負（投資支出大）"),
 "9958": ("股價幾乎貼著 52 週低點（距 0.1%），本益比約 12.4 倍、ROE 17%",
          "9 月營收年增 83%，可留意 Q3 財報是否反映",
          "Q2 投資現金流 -93.7 億，近四季自由現金流 -75 億；Q2 EPS 年減 34%，單季獲利波動大"),
 "9904": ("本益比約 5.6 倍、淨值比 0.42，估值極低；近四季營業現金流 144 億",
          "Q2 EPS 1.61 元、年增 204%",
          "距 52 週低點 13.7%，接近上限；現金流資料只更新到 2026Q1，Q1 營業現金流為負"),
 "1722": ("淨值比 0.78、殖利率 4.8%，資產面便宜",
          "上半年 EPS 已轉正（Q1 0.19、Q2 0.24 元）",
          "本益比約 50 倍，以獲利衡量並不便宜；2025Q4 曾虧損，獲利基礎薄"),
 "3413": ("本益比約 14 倍、殖利率 3.9%；負債比 41%、近四季自由現金流為正",
          "Q2 EPS 4.61 元、年增 35%、季增 8%，獲利止跌回升",
          "半導體設備景氣循環；上半年 EPS 仍年減 12%"),
 "2439": ("本益比約 14.9 倍、淨值比 1.21、殖利率 5.0%",
          "9 月營收年增 4%，股價距 52 週低點 9.5%",
          "近兩季 EPS 連續季減（Q2 0.50 元）；近四季營業現金流僅 2.2 億、自由現金流為負"),
 "1227": ("負債比 40%、殖利率 4.7%；近四季營業現金流 27.5 億",
          "連續兩季 EPS 年增（Q2 +115%、Q1 +33%），9 月營收年增 9%",
          "本益比約 17.8 倍；Q2 營業現金流為負、投資現金流 -23.8 億，近四季自由現金流為負"),
 "9910": ("近四季自由現金流 54.6 億（名單最高），ROE 14%、殖利率 5.9%",
          "Q2 EPS 1.03 元、年增 41%",
          "淨值比 2.9 倍偏高；Q1 EPS 年減 41%；8、9 月營收小幅年減"),
 "1229": ("負債比 20%、近四季自由現金流 48.6 億、殖利率 4.9%",
          "7 月營收年增 115%",
          "Q2 EPS 年減 16%、8 月營收年減 13%；本益比約 16.6 倍"),
 "4114": ("殖利率 5.4%、負債比 35%；9 月營收年增 39%",
          "營收成長若延續，有機會帶動 Q3 獲利",
          "本益比約 18.7 倍偏高；近四季自由現金流 -7.3 億；Q2 營業現金流為負"),
}

wb = Workbook()
F = "Arial"
blue = Font(name=F, color="0000FF"); black = Font(name=F); bold = Font(name=F, bold=True, color="FFFFFF")
hdr_fill = PatternFill("solid", fgColor="1F3864"); thin = Side(style="thin", color="BFBFBF")
box = Border(left=thin, right=thin, top=thin, bottom=thin)
wrap = Alignment(wrap_text=True, vertical="top")

# ================= 工作表 2：季資料（Yahoo 股市逐檔抄錄）=================
q = wb.active; q.title = "季資料"
qh = ["代號","公司","EPS 26Q2","EPS 26Q1","EPS 25Q4","EPS 25Q3","EPS 25Q2","EPS 25Q1",
      "營業CF 最新","營業CF 前1季","營業CF 前2季","營業CF 前3季",
      "自由CF 最新","自由CF 前1季","自由CF 前2季","自由CF 前3季","現金流最新季","來源網址"]
q.append(qh)
qrow = {}
for c in TOP + BACKUP + list(DROP):
    y = Y[c]; tick = f"{c}.TWO" if P[c]["mkt"] == "上櫃" else f"{c}.TW"
    q.append([c, P[c]["name"], *y["eps"], *y["ocf"], *y["fcf"], y["cf_last"],
              f"https://tw.stock.yahoo.com/quote/{tick}/eps ； https://tw.stock.yahoo.com/quote/{tick}/cash-flow-statement"])
    qrow[c] = q.max_row
for row in q.iter_rows(min_row=2):
    for cell in row: cell.font = blue; cell.border = box
    for cell in row[8:16]: cell.number_format = '#,##0;(#,##0)'
q.cell(q.max_row + 2, 1, "單位：EPS 為元（單季）；現金流為仟元（單季）。自由現金流採 Yahoo 股市定義＝營業現金流＋投資現金流。9904 寶成的現金流網頁最新只到 2026Q1，所以它的 4 季是 2025Q2～2026Q1。").font = Font(name=F, italic=True)

# ================= 工作表 1：價值股 Top 10 =================
t = wb.create_sheet("價值股Top10", 0)
cols = ["排名","代號","公司","市場","產業","發行股數(百萬股)","收盤價(10/16)","市值(億元)","52週低點","低點日期",
        "距低點%","近四季EPS(元)","TTM P/E","P/B","殖利率%","營收月份","9月營收年增率","累計營收年增率",
        "26Q2 EPS年增率","26Q1 EPS年增率","7月營收年增率","8月營收年增率","近四季營業現金流(億)","近四季自由現金流(億)","負債比","ROE(上半年年化)",
        "20日均量(張)","價值評分","投資論點（分析判斷）","催化劑（分析判斷）","主要風險（分析判斷）"]
def fill(sheet, codes, start_rank=1):
    sheet.append(cols)
    for i, c in enumerate(codes):
        p = P[c]; r = sheet.max_row + 1; qr = qrow[c]
        lo = p["low52_date"]
        sheet.append([
            start_rank + i, c, p["name"], p["mkt"], p["ind"],
            round(p["shares"] / 1e6, 2), p["close"],
            f"=F{r}*G{r}/100",                                   # 市值 = 股數×股價（億元）
            p["low52"], f"{lo[:4]}/{lo[4:6]}/{lo[6:]}",
            f"=G{r}/I{r}-1",                                     # 距 52 週低點
            f"=SUM(季資料!C{qr}:F{qr})",                          # 近四季 EPS
            f"=G{r}/L{r}",                                       # 本益比
            p["pb"], p["dy"] / 100, f"{p['rev_ym'][:3]}/{p['rev_ym'][3:]}",
            p["rev_yoy"] / 100, (p.get("rev_cum_yoy") or 0) / 100,
            f'=IF(季資料!G{qr}<=0,"去年同季虧損",季資料!C{qr}/季資料!G{qr}-1)',                       # 26Q2 vs 25Q2
            f'=IF(季資料!H{qr}<=0,"去年同季虧損",季資料!D{qr}/季資料!H{qr}-1)',                       # 26Q1 vs 25Q1
            REV78[c][0] / 100, REV78[c][1] / 100,                  # 7、8 月營收年增
            f"=SUM(季資料!I{qr}:L{qr})/100000",                   # 仟元→億元
            f"=SUM(季資料!M{qr}:P{qr})/100000",
            (p.get("debt") or 0) / 100, (p.get("roe") or 0) / 100,
            round(p["vol20"]), p["score"],
            *(NOTE.get(c, ("", "", "")))])
    for row in sheet.iter_rows(min_row=2, max_row=sheet.max_row):
        for cell in row:
            cell.border = box; cell.alignment = wrap
            v = cell.value
            cell.font = black if isinstance(v, str) and v.startswith("=") else blue
        for idx, fmt in {6:'#,##0.00',7:'0.00',8:'#,##0',9:'0.00',11:'0.0%',12:'0.00',13:'0.0"x"',14:'0.00',15:'0.00%',
                         17:'0.0%',18:'0.0%',19:'0.0%',20:'0.0%',21:'0.0%',22:'0.0%',23:'#,##0.0;(#,##0.0)',24:'#,##0.0;(#,##0.0)',25:'0.0%',26:'0.0%',27:'#,##0',28:'0.0'}.items():
            row[idx-1].number_format = fmt
        for idx in [1,2,3,4]: row[idx-1].font = black
    for cell in sheet[1]:
        cell.font = bold; cell.fill = hdr_fill; cell.alignment = Alignment(wrap_text=True, vertical="center", horizontal="center"); cell.border = box
    widths = [5,7,10,6,12,10,9,9,9,11,8,9,8,6,7,8,9,9,9,9,9,9,10,10,8,9,9,8,40,34,40]
    for i, w in enumerate(widths, 1): sheet.column_dimensions[get_column_letter(i)].width = w
    sheet.freeze_panes = "D2"; sheet.row_dimensions[1].height = 45
fill(t, TOP)
t["I1"].comment = Comment("52 週（2025/10/17～2026/10/16）每日最低價中的最低值，用證交所／櫃買每日收盤行情計算", "Claude")
t["L1"].comment = Comment("Yahoo 股市單季 EPS 加總（2025Q3～2026Q2），已和證交所／櫃買本益比反推值交叉比對", "Claude")
t["AB1"].comment = Comment("本益比、淨值比、殖利率、距低點四項在 34 檔通過名單中的百分位平均（0～100，越高越便宜）", "Claude")
n = t.max_row + 2
t.cell(n, 1, "注意：接近 52 週低點不等於買點；本表只是依條件篩出的研究名單，不構成投資建議。投資論點／催化劑／風險欄為根據表內數字的分析判斷，尚未查證新聞與法說內容。").font = Font(name=F, bold=True, color="C00000")
t.cell(n+1, 1, "藍字＝來源數字；黑字＝公式。詳細規則與來源見「篩選規則與來源」工作表。").font = Font(name=F, italic=True)

# ================= 工作表 3：備選與剔除 =================
b = wb.create_sheet("備選與剔除", 1)
b.append(["【備選】通過所有條件、評分排第 11 名"]); b["A1"].font = Font(name=F, bold=True)
start = b.max_row + 1
fill_rows_before = b.max_row
# 備選用同樣欄位
tmp = wb.create_sheet("_tmp"); fill(tmp, BACKUP, 11)
for row in tmp.iter_rows(values_only=False):
    b.append([c.value for c in row])
wb.remove(tmp)
# 修正備選表公式中的列號（從 _tmp 複製過來時列號會偏移）
for r in range(start + 1, b.max_row + 1):
    off = r - (r - start)  # 標題列在 start
    i = r - start          # tmp 中的列號
    for col in range(1, 32):
        cell = b.cell(r, col); v = cell.value
        if isinstance(v, str) and v.startswith("="):
            import re
            cell.value = re.sub(r'(?<![!A-Z])([A-Z])' + str(i + 1) + r'\b', lambda m: m.group(1) + str(r), v)
for row in b.iter_rows(min_row=start, max_row=b.max_row):
    for cell in row:
        cell.border = box; cell.alignment = wrap
        v = cell.value
        if row[0].row > start: cell.font = black if isinstance(v, str) and v.startswith("=") else blue
    for idx, fmt in {6:'#,##0.00',8:'#,##0',11:'0.0%',13:'0.0"x"',15:'0.00%',17:'0.0%',18:'0.0%',19:'0.0%',20:'0.0%',21:'0.0%',22:'0.0%',23:'#,##0.0;(#,##0.0)',24:'#,##0.0;(#,##0.0)',25:'0.0%',26:'0.0%',27:'#,##0'}.items():
        row[idx-1].number_format = fmt
for cell in b[start]:
    cell.font = bold; cell.fill = hdr_fill; cell.alignment = Alignment(wrap_text=True, horizontal="center")
b.append([]); b.append(["【剔除】數字條件都過，但「連續兩季 EPS 比去年同期少」，視為基本面明顯惡化"]); b.cell(b.max_row,1).font = Font(name=F, bold=True)
b.append(["代號","公司","剔除原因"])
for c, why in DROP.items(): b.append([c, P[c]["name"], why])
for i, w in enumerate([7,10,60], 1): pass
for i, w in enumerate([5,7,10,6,12,10,9,9,9,11,8,9,8,6,7,8,9,9,9,9,9,9,10,10,8,9,9,8,40,34,40], 1):
    b.column_dimensions[get_column_letter(i)].width = w

# ================= 工作表 4：篩選規則與來源 =================
s = wb.create_sheet("篩選規則與來源")
rows = [
 ["台股價值股初步名單：篩選規則、漏斗與資料來源"],
 ["資料截至","2026/10/16（週五）收盤；財報為 2026Q2；月營收為 2026 年 9 月"],
 [],
 ["篩選條件（依序檢查）","門檻","刷掉檔數"],
 ["只看上市櫃普通股、有收盤價與股數","4 碼、非 0 開頭",37],
 ["市值","≥ 100 億元",1261],
 ["處置股／變更交易（全額交割）","排除",6],
 ["股價歷史","52 週內至少 150 個交易日",9],
 ["距 52 週低點","≤ 15%",506],
 ["流動性","近 20 日均量 ≥ 500 張",80],
 ["近四季 EPS","> 0（本益比有值）",6],
 ["負債比（一般產業）","≤ 60%",24],
 ["金融股（銀行、保險、證券、金控）","改看 ROE > 8%（上半年淨利×2 ÷ 母公司權益）",6],
 ["今年上半年 EPS","> 0",2],
 ["營收","9 月年增率與累計年增率都 ≥ -10%",12],
 ["毛利率（一般產業）","最近一季 > 0",0],
 ["→ 通過以上條件","",'34 檔'],
 ["近四季營業現金流或自由現金流","> 0（逐檔查 Yahoo 股市，查了評分前 15 名）","0 檔被刷掉"],
 ["連續兩季 EPS 年減（26Q2 與 26Q1 都比去年同季少）","剔除","4 檔（見「備選與剔除」）"],
 ["最近三個月（7～9 月）有兩個月營收年減超過 10%","剔除","0 檔"],
 ["→ 排序","價值評分（本益比低、淨值比低、殖利率高、離低點近，四項百分位平均）","取前 10 名"],
 [],
 ["資料來源",""],
 ["上市每日收盤行情（52 週高低、均量）","https://www.twse.com.tw/rwd/zh/afterTrading/MI_INDEX?date=YYYYMMDD&type=ALLBUT0999&response=json"],
 ["上市 10/16 行情","https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"],
 ["上市本益比／殖利率／淨值比","https://openapi.twse.com.tw/v1/exchangeReport/BWIBBU_ALL"],
 ["上市公司基本資料（發行股數）","https://openapi.twse.com.tw/v1/opendata/t187ap03_L"],
 ["上市月營收","https://openapi.twse.com.tw/v1/opendata/t187ap05_L"],
 ["上市綜合損益表／資產負債表","https://openapi.twse.com.tw/v1/opendata/t187ap06_L_ci （及 _basi/_bd/_fh/_ins/_mim）；t187ap07_L_*"],
 ["上市營益分析（毛利率）","https://openapi.twse.com.tw/v1/opendata/t187ap17_L"],
 ["上市處置股／變更交易","https://openapi.twse.com.tw/v1/announcement/punish ； https://openapi.twse.com.tw/v1/exchangeReport/TWT85U"],
 ["上櫃每日收盤行情","https://www.tpex.org.tw/www/zh-tw/afterTrading/otc?date=YYYY/MM/DD&type=EW&response=json"],
 ["上櫃行情／本益比","https://www.tpex.org.tw/openapi/v1/tpex_mainboard_quotes ； https://www.tpex.org.tw/openapi/v1/tpex_mainboard_peratio_analysis"],
 ["上櫃基本資料／月營收／財報","https://www.tpex.org.tw/openapi/v1/mopsfin_t187ap03_O ； mopsfin_t187ap05_O ； mopsfin_t187ap06_O_* ； mopsfin_t187ap07_O_*"],
 ["上櫃處置股","https://www.tpex.org.tw/openapi/v1/tpex_disposal_information"],
 ["7、8 月單月營收（逐檔）","https://histock.tw/stock/代號/每月營收"],
 ["單季 EPS、現金流量（逐檔）","https://tw.stock.yahoo.com/quote/代號.TW/eps ； https://tw.stock.yahoo.com/quote/代號.TW/cash-flow-statement（網址逐檔列在「季資料」）"],
 [],
 ["已知限制",""],
 ["1","公開資訊觀測站擋住雲端連線，現金流量改用 Yahoo 股市；Yahoo 的自由現金流定義＝營業＋投資現金流"],
 ["2","現金流、單季 EPS、7～8 月營收只查了評分前 15 名；其餘 19 檔未逐檔檢查"],
 ["3","上櫃全額交割股沒有獨立清單，只排除了處置股"],
 ["4","9904 寶成 Yahoo 現金流只到 2026Q1"],
 ["5","投資論點／催化劑／風險只根據數字判斷，尚未查證新聞、法說會與除權息日程"],
]
for r in rows: s.append(r)
s["A1"].font = Font(name=F, bold=True, size=14)
for r in [4, 22, 37]: 
    for c in s[r]: c.font = Font(name=F, bold=True)
for row in s.iter_rows():
    for c in row:
        if not c.font.bold: c.font = Font(name=F)
        c.alignment = Alignment(wrap_text=True, vertical="top")
s.column_dimensions["A"].width = 38; s.column_dimensions["B"].width = 90; s.column_dimensions["C"].width = 22
wb.save("台股價值股初步名單_20261016.xlsx")
print("ok")
