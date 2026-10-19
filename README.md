# 台股週報：價值、動量與風險

每週日台北時間 10:00 自動產出的台股週報所需的資料與程式。

## 資料夾
| 位置 | 內容 |
|---|---|
| `data/prices/L/` | 上市每日收盤行情（一天一檔，`{代號: [收盤, 最高, 最低, 成交股數]}`），來源：證交所 MI_INDEX |
| `data/prices/O/` | 上櫃每日收盤行情，來源：櫃買中心每日收盤行情 |
| `data/raw/` | 每週重新下載的基本資料、月營收、財報（不進版控） |
| `scripts/update_prices.py` | 只補抓缺少的交易日（每週約 5 天） |
| `scripts/fetch_basic.py` | 下載上市櫃基本資料、估值、月營收、財報 |
| `scripts/screen_value.py` | 價值股篩選（條件寫在程式第 8 段） |
| `results/YYYY-MM-DD/` | 每週篩選結果 |

## 每週執行順序
```bash
python3 scripts/update_prices.py   # 補抓本週股價
python3 scripts/fetch_basic.py     # 下載最新基本資料與財報
python3 scripts/screen_value.py    # 跑價值股篩選
```

## 注意
- 證交所網站會限速，抓太快會被暫時封鎖（HTTP 307）。`update_prices.py` 已放慢並輪流使用兩個主機。
- 公開資訊觀測站擋雲端連線，現金流量改從 Yahoo 股市逐檔查。
