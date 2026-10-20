# 動量股額外資料：加權指數每日收盤（7～10 月，證交所 FMTQIK）、注意股名單（上市、上櫃）
import json, time, urllib.request
def get(u):
    return json.loads(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=60).read().decode("utf-8-sig"))
taiex = {}
for ym in ["20260601", "20260701", "20260801", "20260901", "20261001"]:
    for a in range(5):
        try:
            j = get(f"https://wwwc.twse.com.tw/rwd/zh/afterTrading/FMTQIK?date={ym}&response=json")
            for r in j["data"]:   # 欄位：日期(民國), 成交股數, 成交金額, 成交筆數, 發行量加權股價指數, 漲跌點數
                y, m, d = r[0].split("/"); taiex[f"{int(y)+1911}{m}{d}"] = float(r[4].replace(",", ""))
            print(ym, "OK", len(j["data"])); break
        except Exception as e:
            print(ym, "重試", e); time.sleep(30)
    time.sleep(6)
json.dump(taiex, open("data/raw/taiex.json", "w"))
for name, u in [("L_notice", "https://openapi.twse.com.tw/v1/announcement/notice"),
                ("O_notice", "https://www.tpex.org.tw/openapi/v1/tpex_trading_warning_information")]:
    d = get(u); json.dump(d, open(f"data/raw/{name}.json", "w"), ensure_ascii=False); print(name, len(d), json.dumps(d[0], ensure_ascii=False)[:200] if d else "")
print("加權指數最後幾天:", sorted(taiex.items())[-3:])
