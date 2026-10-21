# 台股週報：價值、動量與風險

每週六上午約 8:00（台北）由雲端排程自動產出的台股週報所需的程式、資料與每週結果。
排程的完整工作步驟寫在 `PROMPT.md`；所有篩選與判斷規則寫在 `RULES.md`。

## 每週流程
```bash
python3 scripts/run_weekly.py      # 1. 下載資料、篩選、計算盤勢與風險、列出第二階段待查清單
# 2. 依 results/<日期>/stage2_todo.json 逐檔查 EPS、現金流、月營收，寫進 stage2_input.json
python3 scripts/finalize.py        # 3. 套用第二階段規則，產生前 10 名、表格、圖表、試算表
# 4. 查證前 5 名、研究本週事件 → 建立 Claude 文件 → 匯出 report.md → commit
```
重跑過去某一週：`WEEK_END=20261016 python3 scripts/run_weekly.py --skip-download`

## 程式
| 程式 | 做什麼 |
|---|---|
| `scripts/common.py` | 共用工具：下載（含重試）、判斷本週最後交易日 W 與上週 P |
| `scripts/run_weekly.py` | 一鍵依序執行下面的步驟 |
| `scripts/update_prices.py` | 只補抓缺少的交易日股價（上市證交所 MI_INDEX、上櫃櫃買中心） |
| `scripts/fetch_basic.py` | 上市櫃基本資料、估值、月營收、財報、處置／注意／全額交割、除權息（OpenAPI，只有最新一期）；並累積月營收快照 |
| `scripts/fetch_week.py` | 本週與上週的指數、法人、融資融券、借券、台指期與未平倉、成交值、類股成交 |
| `scripts/fetch_us.py` | 美股、美元、台幣、10 年期美債、油價、黃金（Yahoo 財經，近 6 個月） |
| `scripts/screen_value.py` | 價值股第一階段篩選與價值評分 |
| `scripts/screen_momentum.py` | 動量股篩選與排名（可指定結束日，用來算上週通過檔數） |
| `scripts/market.py` | 盤勢、產業強弱、美股宏觀數字與風險偏好計分 |
| `scripts/stage2_prep.py` | 列出第二階段要逐檔查的項目，能自動取得的先填好 |
| `scripts/finalize.py` | 第二階段規則、前 10 名、融資 5 日增減與券資比、`tables.md` |
| `scripts/widgets.py` | 產生兩張圖表的程式碼 |
| `scripts/build_xlsx.py` | 產生每週資料試算表 |
| `scripts/compact_concepts.py` | 把總控台的概念股名單精簡成快照（由 Mac 上傳排程使用） |

## 資料
| 位置 | 內容 |
|---|---|
| `data/prices/L/`、`data/prices/O/` | 上市、上櫃每日收盤行情（一天一檔，`{代號: [收盤, 最高, 最低, 成交股數]}`；休市日為空檔） |
| `data/inst/` | 個股三大法人買賣超（上市 T86、上櫃 dailyTrade，原始格式） |
| `data/market/{日期}.json` | 指數、融資融券、借券、台指期與三大法人未平倉 |
| `data/market/week_{週一}.json` | 三大法人一週買賣金額（BFI82U） |
| `data/market/twse_daily.json`、`tpex_daily.json` | 加權指數／櫃買指數收盤與成交金額 |
| `data/market/bfiamu/` | 上市各類股每日成交金額 |
| `data/margin/` | 個股融資、融券餘額（張） |
| `data/rev/` | 每月營收快照（每週累積，用來算近三個月營收） |
| `data/concepts/` | 非凡概念快照與產業對應表（由 Mac 排程上傳，週報不修改） |
| `data/raw/` | OpenAPI 原始下載檔（每週重抓，不進版控） |
| `results/YYYY-MM-DD/` | 每週結果：候選與前 10 名 json、`market.json`、`tables.md`、圖表程式碼、試算表、`report.md`（週報備份） |

## 注意
- 證交所網站會限速（HTTP 307），程式已放慢速度、輪流使用 www 與 wwwc 兩個主機，失敗會自動重試。
- 公開資訊觀測站擋雲端連線：單季 EPS、上櫃股現金流改從 Yahoo 股市逐檔查；上市股現金流用 Yahoo 財經 API；前幾個月營收用 HiStock 或 `data/rev/` 快照。
