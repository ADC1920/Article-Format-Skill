# -*- coding: utf-8 -*-
"""apply_verification.py — 把标准号核查结果并入规范库条目。

核查结果文件（verification.jsonl）每行：
    {"code":"GB/T 7714-2025","exists":true,"status":"现行","publish_date":"...",
     "implement_date":"...","title":"...","evidence":"URL","note":"..."}

处理规则：
- exists=false 或 status 含「废止/未发布/查无」→ 该条目标记为 `confidence: low`
  并在 specs 末尾追加「【核查】<note>」
- exists=true 且 status 含「现行/即将实施」→ confidence 提到 high（若原为 medium）
  并追加「【核查】<状态>，发布 <日期>，实施 <日期>」
- exists=uncertain → 保持原置信度，追加「【核查】未确认：<note>」
- 找不到对应条目 → 打印出来供人工处理（不静默丢弃）

用法：
    python apply_verification.py --catalog <standards.jsonl> --verif <verification.jsonl>
    python apply_verification.py ... --dry-run
"""
import argparse
import json
import os
import re
import sys


def norm_code(text):
    """标准号归一化：去空格、统一破折号、去「第X部分」。"""
    s = str(text).upper()
    s = s.replace("—", "-").replace("－", "-").replace(" ", "")
    return s


def load_verif(path):
    rows = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def match_rows(code, catalog):
    """在规范库中找提到该标准号的条目。返回匹配的条目索引列表。"""
    target = norm_code(code)
    # 取标准号主干（如 GB/T7714-2025 → 7714-2025）做宽松匹配
    m = re.search(r"([A-Z/]*)(\d+(?:\.\d+)?)-(\d{4})", target)
    core = f"{m.group(2)}-{m.group(3)}" if m else target
    hits = []
    for idx, row in enumerate(catalog):
        blob = norm_code(row.get("name", "") + " " + row.get("specs", "")
                         + " " + row.get("source", ""))
        if target in blob or (core and core in blob):
            hits.append(idx)
    return hits


def main(argv=None):
    ap = argparse.ArgumentParser(description="并入标准号核查结果")
    ap.add_argument("--catalog", required=True)
    ap.add_argument("--verif", required=True)
    ap.add_argument("--dry-run", action="store_true")
    ns = ap.parse_args(argv if argv is not None else sys.argv[1:])

    with open(ns.catalog, encoding="utf-8") as fh:
        catalog = [json.loads(line) for line in fh if line.strip()]
    verifs = load_verif(ns.verif)

    changed = 0
    unmatched = []
    for v in verifs:
        code = v.get("code", "")
        hits = match_rows(code, catalog)
        if not hits:
            unmatched.append(code)
            continue
        exists = v.get("exists")
        status = str(v.get("status", ""))
        note = str(v.get("note", "")).strip()
        tag = ""
        if exists is False or any(k in status for k in ("废止", "未发布", "查无")):
            tag = "【核查】不成立或已失效"
            new_conf = "low"
        elif exists is True and any(k in status for k in ("现行", "即将实施")):
            dates = []
            if v.get("publish_date"):
                dates.append(f"发布 {v['publish_date']}")
            if v.get("implement_date"):
                dates.append(f"实施 {v['implement_date']}")
            tag = "【核查】" + status + ("，" + "，".join(dates) if dates else "")
            new_conf = "high"
        else:
            tag = "【核查】未确认"
            new_conf = None
        for idx in hits:
            row = catalog[idx]
            if tag and tag not in row["specs"]:
                row["specs"] = (row["specs"] + " " + tag
                                + ("：" + note if note else "")).strip()
            if new_conf:
                row["confidence"] = new_conf
            row["verified"] = exists if isinstance(exists, bool) else "uncertain"
            if v.get("evidence"):
                row["verify_evidence"] = v["evidence"]
            changed += 1

    print(f"核查条目 {len(verifs)} 条，命中并更新 {changed} 条规范")
    if unmatched:
        print(f"未匹配到规范条目的核查项（{len(unmatched)} 条，需人工处理）：")
        for code in unmatched:
            print("  -", code)

    if ns.dry_run:
        print("（dry-run，未写盘）")
        return 0

    with open(ns.catalog, "w", encoding="utf-8", newline="\n") as fh:
        for row in catalog:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"已写回 {ns.catalog}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
