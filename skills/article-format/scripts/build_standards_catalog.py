# -*- coding: utf-8 -*-
"""build_standards_catalog.py — 把调研产出的 jsonl 规范条目合并为技能内的规范库。

用途：把 .tmp/standards/s*.jsonl（六路调研产物）归一化合并为
`references/standards/` 下的三层结构：

    standards/standards.jsonl      全量结构化数据（机器可查，脚本按域/关键词过滤）
    standards/index.md             分域索引表（每条一行，便于快速浏览与 grep）
    standards/domain-<slug>.md     分域详表（含完整可执行规格，按需加载）

归一化内容：统一字段、补 domain（14 个大域）、补 profile 映射（该条规范
支撑哪个排版 profile）、去重、按域与置信度排序。

用法：
    python build_standards_catalog.py --src <jsonl 目录> [--out <技能 references 目录>]
    python build_standards_catalog.py --src ... --dry-run     # 只统计不写盘
"""
import argparse
import collections
import json
import os
import re
import sys

# 46 个调研子类 → 14 个规范大域。键为 category 原文。
DOMAIN_MAP = {
    # 公文与政务
    "党政机关公文格式": "gov",
    "法定公文15文种": "gov",
    "公文格式细节": "gov",
    # 办公与企业文书
    "企业文书": "office",
    "事务性文书": "office",
    "规章制度文体": "office",
    "WPS官方模板与排版常识": "office",
    # 学术与科研
    "学术论文与学位论文": "academic",
    "参考文献与著录": "academic",
    "期刊投稿须知": "academic",
    "摘要与关键词规范": "academic",
    "学术伦理与声明": "academic",
    # 语言文字基础
    "标点符号与数字用法": "language",
    "图表规范": "academic",
    # 财经与披露
    "财务报表与披露": "finance",
    "审计与鉴证报告": "finance",
    "证券发行与信息披露": "finance",
    "资产评估与估值报告": "finance",
    "ESG与可持续披露": "finance",
    "内控与风险管理": "finance",
    # 法律与合规
    "法律文书": "legal",
    "法律意见书与律师文书": "legal",
    # 工程与质量
    "工程咨询": "engineering",
    "质量管理体系": "engineering",
    "检验检测与实验室": "engineering",
    "标准化与技术标准文书": "engineering",
    "专利与技术文献": "engineering",
    # 技术与数据文档
    "技术文档国际标准": "tech",
    "中文技术文档": "tech",
    "产品与工程文档": "tech",
    "数据与算法文档": "tech",
    # 新闻与媒体
    "通讯社与报纸": "media",
    "国际英文新闻风格": "media",
    "新媒体平台": "media",
    # 营销与品牌
    "营销与广告": "marketing",
    "品牌与公关": "marketing",
    # 出版与文学
    "出版编辑": "publishing",
    "出版与版权": "publishing",
    "文学与创作": "publishing",
    "影视与短剧剧本": "publishing",
    # 医疗卫生
    "医学科研写作": "medical",
    "临床与药政文书": "medical",
    # 教育与教学
    "教育与教学文档": "edu",
    "语文与写作教学文体": "edu",
    # 综合实务
    "其他实务文体": "misc",
    "其他专业文体": "misc",
}

# 大域元信息：slug → (中文名, 一句话说明, 对应 profile 或空)
DOMAINS = {
    "gov": ("公文与政务", "党政机关公文 15 文种、格式要素、企业行文参照", "gov-official, enterprise-doc"),
    "office": ("办公与企业文书", "通知报告总结、制度规程、WPS 办公模板惯例", "enterprise-doc, regulation"),
    "academic": ("学术与科研", "学位论文、期刊论文、著录规则、摘要关键词、图表、学术伦理", "thesis, academic-paper"),
    "language": ("语言文字基础", "标点符号、数字用法、量与单位——全部文体通用底座", "全部 profile"),
    "finance": ("财经与披露", "财务报表、审计报告、证券披露、评估报告、ESG、内控", "business-report"),
    "legal": ("法律与合规", "诉讼文书、合同、法律意见书、尽调报告", "legal-doc"),
    "engineering": ("工程与质量", "可行性研究、质量体系、检验检测、标准化、专利", "business-report, regulation"),
    "tech": ("技术与数据文档", "使用说明、软件文档、PRD、API、数据集与模型文档", "tech-doc"),
    "media": ("新闻与媒体", "通讯社规范、英文新闻风格、各平台发布规范", "press-release"),
    "marketing": ("营销与品牌", "广告法禁令、平台文案、品牌公关、SEO", "social-media"),
    "publishing": ("出版与文学", "图书编辑、版权页、文学创作、剧本格式", ""),
    "medical": ("医疗卫生", "IMRaD、报告规范、临床试验与药政文书", "medical-paper"),
    "edu": ("教育与教学", "教案、说课、试卷编制、开题报告、教研论文", "teaching-doc"),
    "misc": ("综合实务", "主持词、致辞、年鉴、地方志、解说词等专门文体", ""),
}

# 条目名关键词 → profile 建议。只在该条目所属 domain 与关键词语义一致时
# 才应用——「通知」「报告」这类通用词在财经/医疗域里指向的是财务报告、医学
# 报告，不是公文（实测事故：财会〔2019〕6 号《财务报表格式的通知》被「通知」
# 命中，误映射成 gov-official）。故 hints 按 domain 分组，不做全局扫描。
PROFILE_HINTS_BY_DOMAIN = {
    "gov": (("公文", "gov-official"), ("请示", "gov-official"),
            ("批复", "gov-official"), ("决定", "gov-official"),
            ("通告", "gov-official"), ("纪要", "gov-official"),
            ("通知", "gov-official"), ("通报", "gov-official")),
    "office": (("制度", "regulation"), ("规程", "regulation"),
               ("SOP", "regulation"), ("质量手册", "regulation"),
               ("通知", "enterprise-doc"), ("总结", "enterprise-doc"),
               ("计划", "enterprise-doc")),
    "academic": (("学位论文", "thesis"), ("毕业论文", "thesis"),
                 ("学术论文", "academic-paper"), ("期刊", "academic-paper"),
                 ("参考文献", "academic-paper"), ("摘要", "academic-paper"),
                 ("三线表", "academic-paper")),
    "medical": (("临床试验", "medical-paper"), ("CONSORT", "medical-paper"),
                ("PRISMA", "medical-paper"), ("IMRaD", "medical-paper"),
                ("病例报告", "medical-paper")),
    "tech": (("使用说明", "tech-doc"), ("用户文档", "tech-doc"),
             ("软件文档", "tech-doc"), ("PRD", "tech-doc"),
             ("README", "tech-doc"), ("API", "tech-doc"),
             ("测试报告", "tech-doc")),
    "legal": (("起诉状", "legal-doc"), ("答辩状", "legal-doc"),
              ("上诉状", "legal-doc"), ("合同", "legal-doc"),
              ("法律意见", "legal-doc"), ("律师函", "legal-doc")),
    "media": (("新闻", "press-release"), ("通讯社", "press-release"),
              ("通稿", "press-release")),
    "marketing": (("广告", "social-media"), ("小红书", "social-media"),
                  ("公众号", "social-media"), ("抖音", "social-media"),
                  ("知乎", "social-media"), ("文案", "social-media")),
    "finance": (("可研", "business-report"), ("可行性", "business-report"),
                ("商业计划", "business-report"), ("尽调", "business-report"),
                ("ESG", "business-report"), ("社会责任报告", "business-report")),
    "edu": (("教案", "teaching-doc"), ("教学设计", "teaching-doc"),
            ("试卷", "teaching-doc"), ("说课", "teaching-doc")),
}

CATEGORY_ORDER_HINT = ("标点符号与数字用法", "参考文献与著录")


def slugify_domain(domain):
    return domain


def normalize(row):
    """补 domain 与 profile 字段，清理空白。"""
    out = dict(row)
    for key in ("id", "category", "name", "specs", "applies_to", "source",
                "confidence"):
        out[key] = str(out.get(key, "")).strip()
    out["specs"] = re.sub(r"\s+", " ", out["specs"])
    out["domain"] = DOMAIN_MAP.get(out["category"], "misc")
    if not out.get("profile"):
        hint = ""
        blob = out["name"] + out["applies_to"]
        for kw, prof in PROFILE_HINTS_BY_DOMAIN.get(out["domain"], ()):
            if kw in blob:
                hint = prof
                break
        out["profile"] = hint
    return out


def load_rows(src_dir):
    rows = []
    bad = 0
    for fn in sorted(os.listdir(src_dir)):
        if not fn.endswith(".jsonl"):
            continue
        path = os.path.join(src_dir, fn)
        with open(path, encoding="utf-8") as fh:
            for lineno, line in enumerate(fh, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(normalize(json.loads(line)))
                except Exception as exc:
                    bad += 1
                    sys.stderr.write(f"[跳过] {fn}:{lineno} {exc}\n")
    # 去重：先按 id，再按 name（保留置信度更高的一条）
    conf_rank = {"high": 3, "medium": 2, "low": 1, "": 0}
    seen_ids, seen_names, merged = set(), {}, []
    for row in rows:
        if row["id"] in seen_ids:
            continue
        seen_ids.add(row["id"])
        key = row["name"].strip()
        if key in seen_names:
            prev = seen_names[key]
            if conf_rank.get(row["confidence"], 0) > conf_rank.get(prev["confidence"], 0):
                merged[merged.index(prev)] = row
                seen_names[key] = row
            continue
        seen_names[key] = row
        merged.append(row)
    return merged, bad


def group_by_domain(rows):
    buckets = collections.defaultdict(list)
    for row in rows:
        buckets[row["domain"]].append(row)
    for domain in buckets:
        buckets[domain].sort(key=lambda r: (
            -{"high": 3, "medium": 2, "low": 1}.get(r["confidence"], 0),
            r["category"], r["id"]))
    return buckets


def write_jsonl(rows, path):
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_index(buckets, path, total):
    lines = [
        "# 文章规范库索引",
        "",
        f"共收录 **{total}** 条规范条目，覆盖 {len(buckets)} 个领域、46 个子类。",
        "",
        "本文件是索引层，每条一行，便于快速定位。完整可执行规格见同目录",
        "`domain-<slug>.md`（按领域分文件）；机器查询用 `standards.jsonl`。",
        "",
        "置信度标记：`高` = 已核对官方原文或权威来源；`中` = 行业通行做法或二次资料；",
        "`低` = 仅见转述、口径存疑。**低置信度条目不作为排版依据，仅供追溯。**",
        "",
        "## 领域总览",
        "",
        "| 领域 | 条目数 | 说明 | 对应 profile |",
        "| --- | --- | --- | --- |",
    ]
    for domain in DOMAINS:
        rows = buckets.get(domain, [])
        if not rows:
            continue
        cn, desc, prof = DOMAINS[domain]
        lines.append(f"| [{cn}](domain-{domain}.md) | {len(rows)} | {desc} | {prof or '—'} |")
    lines.append("")

    conf_cn = {"high": "高", "medium": "中", "low": "低"}
    for domain in DOMAINS:
        rows = buckets.get(domain, [])
        if not rows:
            continue
        cn, desc, prof = DOMAINS[domain]
        lines.append(f"## {cn}（{len(rows)} 条）")
        lines.append("")
        lines.append("| 编号 | 规范名称 | 适用文体 | 置信度 | 要点 |")
        lines.append("| --- | --- | --- | --- | --- |")
        for row in rows:
            brief = row["specs"]
            if len(brief) > 60:
                brief = brief[:58] + "…"
            name = row["name"].replace("|", "／")
            applies = (row["applies_to"] or "—").replace("|", "／")
            if len(applies) > 18:
                applies = applies[:16] + "…"
            lines.append(
                f"| {row['id']} | {name} | {applies} | "
                f"{conf_cn.get(row['confidence'], row['confidence'])} | {brief} |")
        lines.append("")
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines))


def write_domain_docs(buckets, out_dir):
    conf_cn = {"high": "高", "medium": "中", "low": "低"}
    for domain, rows in buckets.items():
        cn, desc, prof = DOMAINS[domain]
        lines = [
            f"# {cn}",
            "",
            f"{desc}",
            "",
            f"共 {len(rows)} 条。对应 profile：{prof or '无专用 profile，按具体文体选' }",
            "",
        ]
        by_cat = collections.defaultdict(list)
        for row in rows:
            by_cat[row["category"]].append(row)
        for cat, items in by_cat.items():
            lines.append(f"## {cat}（{len(items)} 条）")
            lines.append("")
            for row in items:
                lines.append(f"### {row['name']}")
                lines.append("")
                lines.append(f"- 编号：`{row['id']}`　置信度：{conf_cn.get(row['confidence'], row['confidence'])}")
                if row["applies_to"]:
                    lines.append(f"- 适用：{row['applies_to']}")
                if row["profile"]:
                    lines.append(f"- 关联 profile：`{row['profile']}`")
                lines.append(f"- 规格：{row['specs']}")
                if row.get("source"):
                    lines.append(f"- 来源：{row['source']}")
                lines.append("")
        path = os.path.join(out_dir, f"domain-{domain}.md")
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("\n".join(lines))


def main(argv=None):
    here = os.path.dirname(os.path.abspath(__file__))
    default_out = os.path.join(os.path.dirname(here), "references", "standards")
    ap = argparse.ArgumentParser(description="合并调研 jsonl 为规范库")
    ap.add_argument("--src", required=True, help="调研 jsonl 所在目录")
    ap.add_argument("--out", default=default_out, help="输出目录（默认技能 references/standards）")
    ap.add_argument("--dry-run", action="store_true", help="只统计不写盘")
    ns = ap.parse_args(argv if argv is not None else sys.argv[1:])

    rows, bad = load_rows(ns.src)
    buckets = group_by_domain(rows)
    print(f"读入 {len(rows)} 条（去重后），解析失败 {bad} 条")
    for domain in DOMAINS:
        items = buckets.get(domain, [])
        if items:
            conf = collections.Counter(r["confidence"] for r in items)
            print(f"  {DOMAINS[domain][0]:<12} {len(items):>3} 条  {dict(conf)}")

    if ns.dry_run:
        return 0

    os.makedirs(ns.out, exist_ok=True)
    write_jsonl(rows, os.path.join(ns.out, "standards.jsonl"))
    write_index(buckets, os.path.join(ns.out, "index.md"), len(rows))
    write_domain_docs(buckets, ns.out)
    print(f"\n已写入 {ns.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
