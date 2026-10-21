# 共用工具：下載網頁（含重試）、數字轉換、判斷「本週」是哪一週
# 其他程式用 `from common import *` 載入
import json, os, re, time, glob, datetime, urllib.request, urllib.parse

UA = {"User-Agent": "Mozilla/5.0"}            # 假裝成一般瀏覽器，部分網站不接受程式預設的標頭
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # 儲存庫根目錄
os.chdir(ROOT)                                 # 之後所有路徑都從根目錄算起


def num(s):
    """把 '1,234.5'、' 12 ' 這類文字轉成數字；'--'、空白、轉不了的回傳 None"""
    try:
        return float(str(s).replace(",", "").strip())
    except (TypeError, ValueError):
        return None


def get(url, data=None, as_json=True, tries=5, wait=30):
    """下載網址；data 有值時用 POST。失敗會等 wait 秒再試，最多 tries 次。
    證交所太快連續抓會回 HTTP 307（暫時限速），所以等待時間設長一點。"""
    body = urllib.parse.urlencode(data).encode() if data else None
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, data=body, headers=UA)
            raw = urllib.request.urlopen(req, timeout=60).read()
            text = raw.decode("utf-8-sig", "ignore")
            return json.loads(text) if as_json else text
        except Exception as e:                 # 任何錯誤都先記下來，等一下再試
            last = e
            print(f"  重試 {i + 1}/{tries}：{url[:90]} → {e}", flush=True)
            time.sleep(wait)
    raise RuntimeError(f"下載失敗：{url} → {last}")


def save_json(path, obj):
    """存 JSON（自動建立資料夾，中文不轉碼）"""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    json.dump(obj, open(path, "w"), ensure_ascii=False)


def load_json(path, default=None):
    """讀 JSON；檔案不存在時回傳 default"""
    return json.load(open(path)) if os.path.exists(path) else default


def trading_days():
    """有成交資料的交易日清單（依上市股價檔判斷；休市日的檔案是空的 {}）"""
    out = []
    for f in sorted(glob.glob("data/prices/L/*.json")):
        if os.path.getsize(f) > 10:            # 空檔 "{}" 只有 2 個字元
            out.append(os.path.basename(f)[:8])
    return out


def week_end():
    """本週的最後一個交易日 W。
    預設＝資料中最新的交易日（週六執行時就是週五）；
    要重跑過去某一週時，設定環境變數 WEEK_END=YYYYMMDD。"""
    days = trading_days()
    force = os.environ.get("WEEK_END")
    if force:
        days = [d for d in days if d <= force]
    return days[-1]


def ymd(s):
    """'20261016' → date 物件"""
    return datetime.datetime.strptime(s, "%Y%m%d").date()


def iso_week(s):
    """回傳 (年, 第幾週)，用來判斷兩個日期是不是同一週"""
    return ymd(s).isocalendar()[:2]


def week_days(W):
    """W 那一週（週一到週五）有開盤的交易日"""
    return [d for d in trading_days() if iso_week(d) == iso_week(W) and d <= W]


def prev_week_end(W):
    """上週的最後一個交易日 P（例如 W 是 10/16，P 就是 10/8，因為 10/9 國慶休市）"""
    return [d for d in trading_days() if iso_week(d) < iso_week(W)][-1]


def days_back(W, n):
    """W 往前數第 n 個交易日（n=5 → 5 個交易日前；W 本身算第 0 個）"""
    days = [d for d in trading_days() if d <= W]
    return days[-1 - n]


def last_n_days(W, n):
    """到 W 為止（含）最近 n 個交易日"""
    return [d for d in trading_days() if d <= W][-n:]


def roc(d):
    """'20261016' → '115/10/16'（民國年，櫃買中心部分網址要用）"""
    return f"{int(d[:4]) - 1911}/{d[4:6]}/{d[6:]}"


def slash(d):
    """'20261016' → '2026/10/16'"""
    return f"{d[:4]}/{d[4:6]}/{d[6:]}"


def results_dir(W):
    """這一週的結果資料夾，例如 results/2026-10-16/"""
    p = f"results/{W[:4]}-{W[4:6]}-{W[6:]}"
    os.makedirs(p, exist_ok=True)
    return p


def load_prices(end=None):
    """讀全部日股價 → {代號: [(日期, 收盤, 最高, 最低, 成交股數), ...]}，只取到 end（含）"""
    series = {}
    for m in "LO":
        for f in sorted(glob.glob(f"data/prices/{m}/*.json")):
            d = os.path.basename(f)[:8]
            if end and d > end:
                continue
            for c, v in json.load(open(f)).items():
                series.setdefault(c, []).append((d, *v))
    return series


def load_raw(name):
    """讀 data/raw/ 下的 OpenAPI 檔"""
    return json.load(open(f"data/raw/{name}.json"))
