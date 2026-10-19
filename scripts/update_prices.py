# 每週增量更新歷史股價：只補抓「最近 400 天內、還沒有檔案」的平日
# 上市用證交所兩個主機輪流抓（降低被限速機率）；上櫃用櫃買中心
# 存檔格式：data/prices/{L或O}/YYYYMMDD.json = {代號: [收盤, 最高, 最低, 成交股數]}
import json, os, time, datetime, threading, urllib.request

def num(s):
    """'1,234.5' → 1234.5；'--' 或空白 → None"""
    try: return float(str(s).replace(",", "").strip())
    except: return None

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
    "L": ["https://wwwc.twse.com.tw/rwd/zh/afterTrading/MI_INDEX?date={ymd}&type=ALLBUT0999&response=json",
          "https://www.twse.com.tw/exchangeReport/MI_INDEX?response=json&date={ymd}&type=ALLBUT0999"],
    "O": ["https://www.tpex.org.tw/www/zh-tw/afterTrading/otc?date={y}/{m}/{d}&type=EW&response=json"],
}

def todo_days(market):
    today = datetime.date.today()
    d, out = today - datetime.timedelta(days=400), []
    while d <= today:
        if d.weekday() < 5 and not os.path.exists(f"data/prices/{market}/{d:%Y%m%d}.json"): out.append(d)
        d += datetime.timedelta(days=1)
    return out[::-1]          # 最新的先抓

def worker(market, tpl, queue, lock, delay):
    while True:
        with lock:
            if not queue: return
            day = queue.pop(0)
        for attempt in range(8):
            try:
                j = get(tpl.format(ymd=f"{day:%Y%m%d}", y=day.year, m=f"{day.month:02d}", d=f"{day.day:02d}"))
                out = parse_L(j) if market == "L" else parse_O(j)
                # 今天的資料若還沒出來（空的）就不存，下次再抓；過去的空資料代表休市，存空檔避免重抓
                if out or day < datetime.date.today():
                    json.dump(out, open(f"data/prices/{market}/{day:%Y%m%d}.json", "w"))
                print(market, day, len(out), "筆", flush=True)
                break
            except Exception as e:
                print(market, day, "重試", e, flush=True); time.sleep(30)
        time.sleep(delay)

threads = []
for market, tpls in URL.items():
    os.makedirs(f"data/prices/{market}", exist_ok=True)
    q, lock = todo_days(market), threading.Lock()
    print(market, "需要補抓", len(q), "天", flush=True)
    for tpl in tpls:
        threads.append(threading.Thread(target=worker, args=(market, tpl, q, lock, 6 if market == "L" else 1.5)))
[t.start() for t in threads]; [t.join() for t in threads]
print("完成", flush=True)
