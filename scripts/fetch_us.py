# 下載美股、匯率、利率、商品的近 6 個月日線（Yahoo 財經 chart API），存成 data/raw/us.json
# 6 個月約 125 個交易日，足夠算費半 65 日均線
# 10 年期美債殖利率：FRED（DGS10）從雲端連線會被斷線，改用 Yahoo ^TNX（CBOE 10 年期美債殖利率指數，數值即殖利率 %）
import json, os, time, datetime, urllib.request, urllib.parse
import common        # 載入共用設定（工作目錄切到儲存庫根目錄）
SYMS = {"^SOX": "費城半導體指數", "^IXIC": "NASDAQ", "^GSPC": "S&P 500", "NVDA": "Nvidia", "TSM": "台積電ADR",
        "DX-Y.NYB": "美元指數", "TWD=X": "美元兌新台幣", "^TNX": "美國10年期公債殖利率",
        "CL=F": "WTI原油", "BZ=F": "Brent原油", "GC=F": "黃金"}
os.makedirs("data/raw", exist_ok=True)
out = {}
for s, name in SYMS.items():
    for attempt in range(3):
        try:
            u = f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(s)}?range=6mo&interval=1d"
            j = json.loads(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=30).read())
            r = j["chart"]["result"][0]
            # 日期用交易所當地時區（Yahoo 給的 gmtoffset），避免美股收盤日被算成隔天
            off = r["meta"].get("gmtoffset", 0)
            out[s] = dict(name=name, rows=[(datetime.datetime.fromtimestamp(t + off, datetime.UTC).strftime("%Y%m%d"), c)
                                           for t, c in zip(r["timestamp"], r["indicators"]["quote"][0]["close"]) if c is not None])
            print("OK", name, out[s]["rows"][-1]); break
        except Exception as e:
            print("重試", name, e); time.sleep(5)
    time.sleep(1)
json.dump(out, open("data/raw/us.json", "w"), ensure_ascii=False)
