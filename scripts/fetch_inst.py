# 抓 10/12～10/16 五個交易日的個股三大法人買賣超（上市 T86、上櫃 dailyTrade），存檔備用
import json, time, urllib.request
def get(u):
    return json.loads(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=60).read().decode("utf-8-sig"))
for d in ["20261012", "20261013", "20261014", "20261015", "20261016"]:
    for mk, u in [("L", f"https://wwwc.twse.com.tw/rwd/zh/fund/T86?date={d}&selectType=ALLBUT0999&response=json"),
                  ("O", f"https://www.tpex.org.tw/www/zh-tw/insti/dailyTrade?date={d[:4]}/{d[4:6]}/{d[6:]}&type=Daily&sect=EW&response=json")]:
        for a in range(5):
            try:
                j = get(u); json.dump(j, open(f"data/inst/{mk}_{d}.json", "w"), ensure_ascii=False)
                n = len(j.get("data") or (j.get("tables") or [{}])[0].get("data", []))
                print(mk, d, n, "筆", flush=True); break
            except Exception as e:
                print(mk, d, "重試", e, flush=True); time.sleep(30)
        time.sleep(6)
