# 每週一鍵執行：下載資料 → 篩選 → 計算盤勢與風險 → 產生第二階段待查清單
# 用法：python3 scripts/run_weekly.py
#   要重跑過去某一週：WEEK_END=20261016 python3 scripts/run_weekly.py --skip-download
# 執行完之後，排程中的 Claude 要：
#   1. 依 results/<W>/stage2_todo.json 逐檔上網查，寫進 results/<W>/stage2_input.json
#   2. 跑 python3 scripts/finalize.py（結束代碼 2＝還要查下一批，照畫面列出的代號繼續查）
import subprocess, sys, time
from common import *

PY = sys.executable
skip_download = "--skip-download" in sys.argv


def run(script, *args, check=True):
    """執行一支程式並把畫面輸出印出來；check=True 時失敗就停止"""
    print(f"\n========== {script} {' '.join(args)} ==========", flush=True)
    r = subprocess.run([PY, f"scripts/{script}", *args])
    if check and r.returncode != 0:
        raise SystemExit(f"{script} 失敗（結束代碼 {r.returncode}）")
    return r.returncode


if not skip_download:
    run("update_prices.py")
    run("fetch_basic.py")
    # 證交所常限速：有失敗項目就等 2 分鐘再跑一次（已抓到的會自動跳過），最多 3 輪
    for i in range(3):
        run("fetch_week.py", check=False)
        failed = load_json("data/market/fetch_status.json", {}).get("failed", [])
        if not failed:
            break
        print(f"第 {i + 1} 輪仍有失敗：{failed}，2 分鐘後重試", flush=True)
        time.sleep(120)
    run("fetch_us.py")

W = week_end()
P = prev_week_end(W)
print(f"\n本週最後交易日 W={W}，上週最後交易日 P={P}", flush=True)
run("screen_value.py")
run("screen_momentum.py")
pdir = f"results/{P[:4]}-{P[4:6]}-{P[6:]}"
if not os.path.exists(f"{pdir}/momentum_all.json"):
    # 上週的結果沒存到時，用上週的資料重算一次通過檔數（市場廣度用）
    run("screen_momentum.py", P)
run("market.py")
run("stage2_prep.py")

status = load_json("data/market/fetch_status.json", {})
print("\n========== 完成 ==========")
print(f"抓取失敗項目：{status.get('failed') or '無'}")
print(f"下一步：依 results/{W[:4]}-{W[4:6]}-{W[6:]}/stage2_todo.json 逐檔查資料，然後跑 scripts/finalize.py")
