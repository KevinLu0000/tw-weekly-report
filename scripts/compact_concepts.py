# 把總控台的「非凡概念」名單（ustv_concepts_claude.json，約 1.8 MB）精簡成週報要用的快照
# 只留：概念名稱、group_id、成分股代號與名稱（價格、成交量每週會另外從交易所抓，不需要存）
# 用法：python3 scripts/compact_concepts.py <來源json> <來源檔修改時間(ISO)>
import json, sys, datetime
src, mtime = sys.argv[1], (sys.argv[2] if len(sys.argv) > 2 else "")
d = json.load(open(src, encoding="utf-8"))
if len(d) < 100:                                   # 防呆：來源檔壞掉或抓不完整，就不覆蓋舊快照
    sys.exit(f"只有 {len(d)} 個概念，判定來源異常，不更新快照")
snap = {"source": "integrated_system_claude/review/journal/ustv_concepts_claude.json（非凡新聞網 news.ustv.com.tw 概念股）",
        "source_modified": mtime,
        "snapshot_at": datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).strftime("%Y-%m-%d %H:%M"),
        "concepts": [{"group_id": x["group_id"], "concept": x["concept"],
                      "stocks": [[s["stock_id"], s["stock_name"]] for s in x["stocks"] if s.get("stock_id")]} for x in d]}
json.dump(snap, open("data/concepts/ustv_concepts.json", "w", encoding="utf-8"), ensure_ascii=False, indent=0)
print(f"快照完成：{len(snap['concepts'])} 個概念、{sum(len(c['stocks']) for c in snap['concepts'])} 筆個股")
