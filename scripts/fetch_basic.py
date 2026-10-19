# 抓取全市場基本資料：上市（證交所 OpenAPI）與上櫃（櫃買 OpenAPI），存成 JSON 檔備用
import os; os.makedirs("data/raw", exist_ok=True)
import json, time, urllib.request

TW = "https://openapi.twse.com.tw/v1"
TP = "https://www.tpex.org.tw/openapi/v1"
# 檔名 : 網址
targets = {
  # --- 上市 ---
  "L_quote": f"{TW}/exchangeReport/STOCK_DAY_ALL",     # 每日收盤行情
  "L_val":   f"{TW}/exchangeReport/BWIBBU_ALL",        # 本益比、殖利率、淨值比
  "L_info":  f"{TW}/opendata/t187ap03_L",              # 公司基本資料（產業、股本）
  "L_rev":   f"{TW}/opendata/t187ap05_L",              # 月營收
  "L_margin":f"{TW}/opendata/t187ap17_L",              # 營益分析（毛利率等）
  "L_punish":f"{TW}/announcement/punish",              # 處置股
  "L_change":f"{TW}/exchangeReport/TWT85U",            # 變更交易（全額交割）
  # --- 上櫃 ---
  "O_quote": f"{TP}/tpex_mainboard_quotes",
  "O_val":   f"{TP}/tpex_mainboard_peratio_analysis",
  "O_info":  f"{TP}/mopsfin_t187ap03_O",
  "O_rev":   f"{TP}/mopsfin_t187ap05_O",
  "O_margin":f"{TP}/mopsfin_187ap17_O",
  "O_punish":f"{TP}/tpex_disposal_information",
}
# 財報：損益表(ap06)、資產負債表(ap07)，各分 6 種產業格式
for kind in ["06", "07"]:
    for ind in ["ci", "basi", "bd", "fh", "ins", "mim"]:
        targets[f"L_ap{kind}_{ind}"] = f"{TW}/opendata/t187ap{kind}_L_{ind}"
        targets[f"O_ap{kind}_{ind}"] = f"{TP}/mopsfin_t187ap{kind}_O_{ind}"

for name, url in targets.items():
    for attempt in range(3):  # 失敗最多重試 3 次
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"})
            data = json.loads(urllib.request.urlopen(req, timeout=60).read().decode("utf-8-sig"))
            json.dump(data, open(f"data/raw/{name}.json", "w"), ensure_ascii=False)
            print(f"{name}: {len(data)} 筆")
            break
        except Exception as e:
            print(f"{name}: 失敗 {e}"); time.sleep(3)
    time.sleep(0.5)  # 放慢速度，避免被伺服器擋
