# 抓取全市場基本資料：上市（證交所 OpenAPI）與上櫃（櫃買 OpenAPI），存成 JSON 檔備用
# OpenAPI 只提供「最新一期」資料，所以要在週六（週五收盤後）執行
import common        # 載入共用設定（工作目錄切到儲存庫根目錄）
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
  "L_notice":f"{TW}/announcement/notice",              # 注意股
  "L_exdiv": f"{TW}/exchangeReport/TWT48U_ALL",        # 除權除息預告
  # --- 上櫃 ---
  "O_quote": f"{TP}/tpex_mainboard_quotes",
  "O_val":   f"{TP}/tpex_mainboard_peratio_analysis",
  "O_info":  f"{TP}/mopsfin_t187ap03_O",
  "O_rev":   f"{TP}/mopsfin_t187ap05_O",
  "O_margin":f"{TP}/mopsfin_187ap17_O",
  "O_punish":f"{TP}/tpex_disposal_information",
  "O_notice":f"{TP}/tpex_trading_warning_information", # 注意股
  "O_exdiv": f"{TP}/tpex_exright_prepost",             # 除權除息預告
}
# 財報：損益表(ap06)、資產負債表(ap07)，各分 6 種產業格式
for kind in ["06", "07"]:
    for ind in ["ci", "basi", "bd", "fh", "ins", "mim"]:
        targets[f"L_ap{kind}_{ind}"] = f"{TW}/opendata/t187ap{kind}_L_{ind}"
        targets[f"O_ap{kind}_{ind}"] = f"{TP}/mopsfin_t187ap{kind}_O_{ind}"

import sys
snapshot_only = "--snapshot-only" in sys.argv          # 只重做月營收快照、不重新下載（測試用）
for name, url in ({} if snapshot_only else targets).items():
    for attempt in range(3):  # 失敗最多重試 3 次
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"})
            data = json.loads(urllib.request.urlopen(req, timeout=60).read().decode("utf-8-sig"))
            json.dump(data, open(f"data/raw/{name}.json", "w"), ensure_ascii=False)
            print(f"{name}: {len(data)} 筆")
            break
        except Exception as e:
            print(f"{name}: 失敗 {e}"); time.sleep(3)
    else:
        print(f"❌ {name}: 3 次都失敗")          # for 迴圈沒有 break 才會跑到這裡
    time.sleep(0.5)  # 放慢速度，避免被伺服器擋

# ---------- 月營收快照：每個月存一份，累積起來就能算「近三個月」營收年增 ----------
# OpenAPI 只給最新一個月，所以每週把它存成 data/rev/{L或O}_{西元年月}.json
# 內容：{代號: [當月營收, 去年同月營收, 年增率%, 累計年增率%]}（營收單位：仟元）
num = common.num
for mk in ["L", "O"]:
    path = f"data/raw/{mk}_rev.json"
    if not os.path.exists(path):
        continue
    snap = {}
    for r in json.load(open(path)):
        ym = str(r.get("資料年月", "")).strip()          # 民國年月，例如 11509
        if len(ym) < 4:
            continue
        key = f"{int(ym[:-2]) + 1911}{ym[-2:]}"
        snap.setdefault(key, {})[r.get("公司代號")] = [
            num(r.get("營業收入-當月營收")), num(r.get("營業收入-去年當月營收")),
            num(r.get("營業收入-去年同月增減(%)")), num(r.get("累計營業收入-前期比較增減(%)"))]
    for key, rows in snap.items():
        out = f"data/rev/{mk}_{key}.json"
        old = common.load_json(out, {})
        old.update(rows)                                # 同一個月份後來才公布的公司會補進去
        common.save_json(out, old)
        print(f"月營收快照 {out}：{len(old)} 家")
