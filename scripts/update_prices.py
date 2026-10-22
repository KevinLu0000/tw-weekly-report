# 每週增量更新歷史股價：只補抓「最近 375 天內（52 週＝364 天，再多留幾天）、還沒有檔案」的平日
# 上市：證交所 MI_INDEX，每一次重試輪流換 www／wwwc 主機（某個主機被限速時另一個常常還能用）
# 上櫃：櫃買中心每日收盤行情
# 存檔格式：data/prices/{L或O}/YYYYMMDD.json = {代號: [收盤, 最高, 最低, 成交股數]}；休市日存空檔 {}
# 結束前會檢查上市、上櫃是否「同一天一邊有資料、另一邊沒有」，有的話結束代碼 1（run_weekly.py 會再跑一次）
import json, os, sys, time, datetime, urllib.request
import common        # 載入共用設定（工作目錄切到儲存庫根目錄）

num = common.num


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    return json.loads(urllib.request.urlopen(req, timeout=60).read().decode("utf-8-sig"))


def parse_L(j):
    """解析證交所 MI_INDEX（新版 tables 格式與舊版 dataN 格式都支援）"""
    out = {}
    for t in j.get("tables", []):
        if "每日收盤行情" in t.get("title", ""):
            for r in t["data"]: out[r[0]] = [num(r[8]), num(r[6]), num(r[7]), num(r[2])]
    for k, v in j.items():
        if k.startswith("data") and isinstance(v, list) and v and "收盤價" in (j.get("fields" + k[4:]) or []):
            for r in v: out[r[0]] = [num(r[8]), num(r[6]), num(r[7]), num(r[2])]
    return out


def parse_O(j):
    """解析櫃買中心每日收盤行情"""
    out = {}
    for t in j.get("tables", []):
        for r in t.get("data", []): out[r[0]] = [num(r[2]), num(r[5]), num(r[6]), num(r[7])]
    return out


URL = {
    "L": ["https://www.twse.com.tw/rwd/zh/afterTrading/MI_INDEX?date={ymd}&type=ALLBUT0999&response=json",
          "https://wwwc.twse.com.tw/rwd/zh/afterTrading/MI_INDEX?date={ymd}&type=ALLBUT0999&response=json"],
    "O": ["https://www.tpex.org.tw/www/zh-tw/afterTrading/otc?date={y}/{m}/{d}&type=EW&response=json"],
}
PACE = {"L": 8, "O": 1.5}          # 每抓一天之後休息幾秒


def path(m, d):
    return f"data/prices/{m}/{d:%Y%m%d}.json"


def has_data(m, d):
    """這一天的檔案存在而且不是空的（空檔＝休市）"""
    p = path(m, d)
    return os.path.exists(p) and os.path.getsize(p) > 10


def todo_days(market):
    """要抓的日子：沒有檔案的平日；或本市場是空檔、另一個市場卻有資料（代表上次抓錯，要重抓）"""
    other = "O" if market == "L" else "L"
    today = datetime.date.today()
    d, out = today - datetime.timedelta(days=375), []
    while d <= today:
        if d.weekday() < 5:
            if not os.path.exists(path(market, d)) or (not has_data(market, d) and has_data(other, d)):
                out.append(d)
        d += datetime.timedelta(days=1)
    return out[::-1]          # 最新的先抓


def fetch_day(market, day):
    """抓一天；最多 10 次，每次換主機，等待時間逐次拉長（20、40、60…秒，最多 120 秒）"""
    tpls = URL[market]
    for attempt in range(10):
        tpl = tpls[attempt % len(tpls)]
        try:
            j = get(tpl.format(ymd=f"{day:%Y%m%d}", y=day.year, m=f"{day.month:02d}", d=f"{day.day:02d}"))
            out = parse_L(j) if market == "L" else parse_O(j)
            # 今天的資料若還沒出來（空的）就不存，下次再抓；過去的空資料代表休市，存空檔避免重抓
            if out or day < datetime.date.today():
                json.dump(out, open(path(market, day), "w"))
            print(market, day, len(out), "筆", flush=True)
            return True
        except Exception as e:
            wait = min(120, 20 * (attempt + 1))
            print(market, day, f"重試 {attempt + 1}/10（{wait} 秒後）", e, flush=True)
            time.sleep(wait)
    print("❌", market, day, "10 次都失敗", flush=True)
    return False


for market in ["O", "L"]:                    # 先抓上櫃（不太會被擋），上市判斷是否該重抓時才有依據
    os.makedirs(f"data/prices/{market}", exist_ok=True)
    days = todo_days(market)
    print(market, "需要補抓", len(days), "天", flush=True)
    for day in days:
        fetch_day(market, day)
        time.sleep(PACE[market])

# ---------- 完整性檢查：同一天上市、上櫃要一致（都有資料或都休市）----------
problems = []
today = datetime.date.today()
d = today - datetime.timedelta(days=375)
while d < today:                              # 今天的資料可能還沒公布，不檢查
    if d.weekday() < 5:
        a, b = has_data("L", d), has_data("O", d)
        if a != b or not os.path.exists(path("L", d)) or not os.path.exists(path("O", d)):
            problems.append(f"{d:%Y%m%d}（上市{'有' if a else '缺'}、上櫃{'有' if b else '缺'}）")
    d += datetime.timedelta(days=1)
if problems:
    print("❌ 股價資料不完整：", "、".join(problems), flush=True)
    sys.exit(1)
print("完成，股價資料完整", flush=True)
