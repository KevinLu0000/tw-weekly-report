# 下載本週與上週的「大盤層級」資料，以及近 10 個交易日的個股法人買賣超
# 本週最後交易日 W、上週最後交易日 P 由股價檔自動判斷（見 common.py）
# 原始下載檔存 data/market/raw/（不進版控）；整理後的精簡數字存：
#   data/market/{日期}.json   ：指數、融資融券、借券、台指期與未平倉、上櫃融資（每天一檔）
#   data/market/week_{週一}.json：三大法人一週買賣金額（證交所 BFI82U 週報）
#   data/market/twse_daily.json：加權指數收盤與上市成交金額（FMTQIK，逐月累積）
#   data/market/tpex_daily.json：櫃買指數收盤與上櫃成交金額（逐月累積）
#   data/market/bfiamu/{日期}.json：上市各類股成交金額
#   data/margin/{L或O}_{日期}.json：個股融資、融券餘額（張）
#   data/inst/{L或O}_{日期}.json：個股三大法人買賣超（原始格式）
import re, html
from common import *

W = week_end()
P = prev_week_end(W)
D5 = days_back(W, 5)                    # 5 個交易日前（算個股融資 5 日增減用）
print(f"本週最後交易日 W={W}，上週最後交易日 P={P}，5 日前 D5={D5}", flush=True)

TW = ["https://www.twse.com.tw", "https://wwwc.twse.com.tw"]   # 證交所兩個主機，一個被限速（HTTP 307）就換另一個
PACE = 12                                # 每次抓證交所之後休息幾秒（太快會被暫時封鎖 HTTP 307）


def twse(path):
    """抓證交所 rwd 資料：先試 wwwc 主機，失敗再試 www 主機"""
    for host in TW:
        try:
            j = get(host + path, tries=2, wait=40)
            time.sleep(PACE)
            return j
        except RuntimeError as e:
            print("  換主機", e, flush=True)
    raise RuntimeError("證交所兩個主機都失敗：" + path)


def day_file(d):
    return f"data/market/{d}.json"


def update_day(d, key, value):
    """把整理好的數字寫進 data/market/{d}.json 的某個欄位"""
    rec = load_json(day_file(d), {})
    rec[key] = value
    save_json(day_file(d), rec)


def have(d, key):
    return key in load_json(day_file(d), {})


def step(name, fn):
    """執行一個下載步驟；失敗不中斷整個程式，最後統一列出失敗項目"""
    try:
        fn()
    except Exception as e:
        print(f"❌ {name} 失敗：{e}", flush=True)
        FAILED.append(f"{name}：{e}")


FAILED = []

# ---------- 1. 個股三大法人買賣超（近 10 個交易日，已存在的檔案不重抓）----------
def fetch_inst():
    os.makedirs("data/inst", exist_ok=True)
    for d in last_n_days(W, 10):
        if not os.path.exists(f"data/inst/L_{d}.json"):
            j = twse(f"/rwd/zh/fund/T86?date={d}&selectType=ALLBUT0999&response=json")
            if not j.get("data"):
                raise RuntimeError(f"T86 {d} 沒有資料：{j.get('stat')}")
            save_json(f"data/inst/L_{d}.json", j)
            print("  上市法人", d, len(j["data"]), "筆", flush=True)
        if not os.path.exists(f"data/inst/O_{d}.json"):
            j = get(f"https://www.tpex.org.tw/www/zh-tw/insti/dailyTrade?date={slash(d)}&type=Daily&sect=EW&response=json")
            if not j.get("tables") or not j["tables"][0].get("data"):
                raise RuntimeError(f"上櫃法人 {d} 沒有資料")
            save_json(f"data/inst/O_{d}.json", j)
            print("  上櫃法人", d, len(j["tables"][0]["data"]), "筆", flush=True)
            time.sleep(2)


# ---------- 2. 指數（加權指數與各類股指數）----------
def parse_index(j):
    """從 MI_INDEX 取出所有「價格指數」的收盤 → {指數名稱: 收盤}"""
    out = {}
    for t in j.get("tables", []):
        f = t.get("fields") or []
        if f and f[0] == "指數" and "價格指數" in (t.get("title") or ""):
            for r in t["data"]:
                out[r[0].strip()] = num(r[1])
    return out


def fetch_index():
    for d in sorted({W, P}):
        if have(d, "index"):
            continue
        idx = parse_index(twse(f"/rwd/zh/afterTrading/MI_INDEX?date={d}&type=IND&response=json"))
        if "發行量加權股價指數" not in idx:
            raise RuntimeError(f"{d} 指數表沒有加權指數")
        update_day(d, "index", idx)
        print("  指數", d, len(idx), "項，加權指數", idx["發行量加權股價指數"], flush=True)


# ---------- 3. 上市融資融券：大盤（W、P）與個股（W、D5）----------
def fetch_margin_L():
    for d in sorted({W, P}):
        if have(d, "margin_L"):
            continue
        j = twse(f"/rwd/zh/marginTrading/MI_MARGN?date={d}&selectType=MS&response=json")
        rows = {r[0]: r for r in j["tables"][0]["data"]}      # 項目 → [項目, 買進, 賣出, 償還, 前日餘額, 今日餘額]
        update_day(d, "margin_L", {
            "融資張": num(rows["融資(交易單位)"][5]),
            "融券張": num(rows["融券(交易單位)"][5]),
            "融資金額億": num(rows["融資金額(仟元)"][5]) / 1e5,   # 仟元 → 億元
        })
        print("  上市大盤融資券", d, flush=True)
    for d in sorted({W, D5}):
        path = f"data/margin/L_{d}.json"
        if os.path.exists(path):
            continue
        j = twse(f"/rwd/zh/marginTrading/MI_MARGN?date={d}&selectType=ALL&response=json")
        out = {}
        for t in j.get("tables", []):
            f = t.get("fields") or []
            if "代號" in f and t.get("data"):
                # 欄位裡有兩個「今日餘額」：第一個是融資、第二個是融券
                pos = [i for i, x in enumerate(f) if x == "今日餘額"]
                for r in t["data"]:
                    out[r[0].strip()] = [num(r[pos[0]]), num(r[pos[1]])]
        if not out:
            raise RuntimeError(f"MI_MARGN ALL {d} 解析不到個股資料")
        save_json(path, out)
        print("  上市個股融資券", d, len(out), "檔", flush=True)


# ---------- 4. 上市借券賣出餘額（TWT93U，全部證券加總）----------
def fetch_sbl():
    for d in sorted({W, P}):
        if have(d, "sbl_L"):
            continue
        j = twse(f"/rwd/zh/marginTrading/TWT93U?date={d}&response=json")
        # 欄位：0 代號、1 名稱、2～7 融券、8～13 借券賣出（8 前日餘額 … 12 當日餘額）、14 備註；單位：股
        # 最後一列是「合計」，不能重複加總，所以只加有證券代號的列
        total = sum(num(r[12]) or 0 for r in j["data"] if r[0].strip() and r[0].strip() != "合計")
        update_day(d, "sbl_L", {"借券賣出餘額張": total / 1000})
        print("  借券賣出餘額", d, round(total / 1000), "張", flush=True)


# ---------- 5. 期交所：台指期行情與三大法人未平倉 ----------
def cells(tr):
    """把一列 HTML 表格 <tr> 轉成文字清單"""
    return [re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", c))).strip()
            for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr, re.S)]


def fetch_taifex():
    for d in sorted({W, P}):
        if have(d, "taifex"):
            continue
        ds = slash(d)
        page = get("https://www.taifex.com.tw/cht/3/futDailyMarketReport",
                   {"queryType": "2", "marketCode": "0", "commodity_id": "TX", "queryDate": ds,
                    "MarketCode": "0", "commodity_idt": "TX"}, as_json=False)
        tx = []
        for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", page, re.S):
            c = cells(tr)
            if len(c) > 5 and c[0] == "TX" and re.fullmatch(r"\d{6}", c[1]):
                tx.append({"月份": c[1], "收盤": num(c[5])})      # 第 6 欄＝最後成交價
        time.sleep(3)
        page = get("https://www.taifex.com.tw/cht/3/futContractsDate",
                   {"queryType": "1", "doQuery": "1", "queryDate": ds, "commodityId": "TXF"}, as_json=False)
        # 表格文字依序為：臺股期貨 → 自營商 12 個數字 → 投信 12 個 → 外資 12 個
        # 12 個數字：交易多方口數、金額、空方口數、金額、淨額口數、金額、未平倉多方口數、金額、空方口數、金額、淨額口數、金額
        # 網頁選單裡也有「臺股期貨」字樣，所以先找表頭「身份別」，再往後找
        i = page.find("臺股期貨", page.find("身份別"))
        text = re.sub(r"<[^>]+>", "|", page[i:i + 12000])
        oi = {}
        for who in ["自營商", "投信", "外資"]:
            k = text.find(who)
            nums = re.findall(r"-?[\d,]+", text[k:k + 3000])
            nums = [num(x) for x in nums if re.search(r"\d", x)][:12]
            oi[who] = nums[10]                                       # 未平倉多空淨額（口）
        if not tx or oi.get("外資") is None:
            raise RuntimeError(f"期交所 {d} 解析失敗")
        update_day(d, "taifex", {"TX": tx, "未平倉淨額口": oi})
        print("  期交所", d, tx[0], oi, flush=True)
        time.sleep(3)


# ---------- 6. 上櫃融資融券：大盤合計（W、P）與個股（W、D5）----------
def fetch_margin_O():
    for d in sorted({W, P, D5}):
        need_total = d in (W, P) and not have(d, "margin_O")
        need_stock = d in (W, D5) and not os.path.exists(f"data/margin/O_{d}.json")
        if not (need_total or need_stock):
            continue
        j = get(f"https://www.tpex.org.tw/www/zh-tw/margin/balance?date={slash(d)}&response=json")
        t = j["tables"][0]
        f = t["fields"]
        ia, ib = f.index("資餘額"), f.index("券餘額")
        stock = {r[0].strip(): [num(r[ia]), num(r[ib])] for r in t["data"]}
        save_json(f"data/margin/O_{d}.json", stock)
        summ = {r[1]: r for r in t.get("summary", [])}
        update_day(d, "margin_O", {
            "融資張": num(summ["合計(張)"][ia]),
            "融券張": num(summ["合計(張)"][ib]),
            "融資金額億": num(summ["融資金(仟元)"][ia]) / 1e5,
        })
        print("  上櫃融資券", d, len(stock), "檔", flush=True)
        time.sleep(2)


# ---------- 7. 三大法人一週買賣金額（BFI82U 週報；本週與上週）----------
def fetch_bfi82u():
    for d in sorted({W, P}):
        monday = week_days(d)[0]
        path = f"data/market/week_{monday}.json"
        if os.path.exists(path):
            continue
        j = twse(f"/rwd/zh/fund/BFI82U?type=week&weekDate={monday}&response=json")
        if not j.get("data"):
            raise RuntimeError(f"BFI82U 週報 {monday} 沒有資料：{j.get('stat')}")
        # 每列：[單位名稱, 買進金額, 賣出金額, 買賣差額]（元）→ 換成億元
        rows = {r[0]: [num(x) / 1e8 for x in r[1:4]] for r in j["data"]}
        save_json(path, {"title": j.get("title"), "億元": rows})
        print("  三大法人週報", j.get("title"), flush=True)


# ---------- 8. 加權指數與上市成交金額（FMTQIK，近 6 個月；已過去的月份不重抓）----------
def fetch_fmtqik():
    path = "data/market/twse_daily.json"
    data = load_json(path, {})
    w = ymd(W)
    months = sorted({(w.year * 12 + w.month - 1 - k) for k in range(6)})
    for m in months:
        y, mo = divmod(m, 12)
        key = f"{y}{mo + 1:02d}"
        done = any(d.startswith(key) for d in data)
        if done and key != W[:6] and key != P[:6]:      # 舊月份已經有了就跳過；本月與上週所在月份每次重抓
            continue
        j = twse(f"/rwd/zh/afterTrading/FMTQIK?date={key}01&response=json")
        for r in j.get("data", []):                     # [日期(民國), 成交股數, 成交金額, 成交筆數, 加權指數, 漲跌點數]
            yy, mm, dd = r[0].split("/")
            data[f"{int(yy) + 1911}{mm}{dd}"] = [num(r[2]), num(r[4])]
        print("  FMTQIK", key, len(j.get("data", [])), "天", flush=True)
    save_json(path, dict(sorted(data.items())))


# ---------- 9. 櫃買指數與上櫃成交金額（本週與上週所在月份）----------
def fetch_tpex_daily():
    path = "data/market/tpex_daily.json"
    data = load_json(path, {})
    for key in sorted({W[:6], P[:6]}):
        j = get(f"https://www.tpex.org.tw/www/zh-tw/afterTrading/tradingIndex?date={key[:4]}/{key[4:]}/01&response=json")
        for r in j["tables"][0]["data"]:                 # [日期(民國), 成交股數(千股), 成交金額(千元), 筆數, 櫃買指數, 漲跌]
            yy, mm, dd = r[0].split("/")
            data[f"{int(yy) + 1911}{mm}{dd}"] = [num(r[2]) * 1000, num(r[4])]
        print("  櫃買每日", key, len(j["tables"][0]["data"]), "天", flush=True)
        time.sleep(2)
    save_json(path, dict(sorted(data.items())))


# ---------- 10. 上市各類股成交金額（BFIAMU，本週與上週每天）----------
def fetch_bfiamu():
    for d in week_days(W) + week_days(P):
        path = f"data/market/bfiamu/{d}.json"
        if os.path.exists(path):
            continue
        j = twse(f"/rwd/zh/afterTrading/BFIAMU?date={d}&response=json")
        if not j.get("data"):
            raise RuntimeError(f"BFIAMU {d} 沒有資料")
        save_json(path, {r[0].strip(): num(r[2]) for r in j["data"]})   # 類股名稱 → 成交金額（元）
        print("  類股成交", d, flush=True)


for name, fn in [("個股法人買賣超", fetch_inst), ("指數", fetch_index), ("上市融資融券", fetch_margin_L),
                 ("借券賣出", fetch_sbl), ("期交所", fetch_taifex), ("上櫃融資融券", fetch_margin_O),
                 ("三大法人週報", fetch_bfi82u), ("加權指數與成交金額", fetch_fmtqik),
                 ("櫃買指數與成交金額", fetch_tpex_daily), ("類股成交", fetch_bfiamu)]:
    print(f"== {name}", flush=True)
    step(name, fn)

save_json("data/market/fetch_status.json", {"W": W, "P": P, "D5": D5, "failed": FAILED})
print("完成。失敗項目：", FAILED or "無", flush=True)
