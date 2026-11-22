# -*- coding: utf-8 -*-
"""run_profile_regression.py — article-format 全部 profile 的端到端回归。

用法：
    python run_profile_regression.py [--keep]

对 profiles/ 下每个文体 profile：用该 profile 生成一份样例文档，
跑 verify_article_style.py 按同一 profile 口径核验，汇总 PASS/FAIL 与退出码。

--keep 保留生成的 docx 供人工打开检查；默认跑完删除。
输出目录：环境变量 ARTICLE_OUT_DIR 或当前工作目录下的 .profile-regression/
"""
import argparse
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL_ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from spec_loader import list_profiles  # noqa: E402

SAMPLE_MD = """# 样例文档标题

## {h1} 第一部分

这是用于回归测试的正文段落，用于核验字体、字号、行距与首行缩进。

### {h2} 子节说明

- 列举项甲
- 列举项乙

| 项目 | 数值 |
| --- | --- |
| 甲 | 100 |
| 乙 | 200 |

## {h1} 第二部分

正文第二段，用于验证多章节下的编号连续与样式一致性。
"""


def _sample(profile):
    """按 profile 的编号体系选择标题前缀，避免跳级告警。

    若 profile 声明了 required_sections（结构要件门禁），把缺的章节补成
    一级标题插到正文前——回归只验版式与通道，不该因样例缺「摘要」而红。
    """
    kind = "numeric"
    required = []
    try:
        from spec_loader import load_spec
        spec = load_spec(profile=profile)
        kind = str(spec.get("numbering_scheme", {})
                   .get("heading_kind", "numeric") or "numeric")
        required = (spec.get("profile") or {}).get("required_sections") or []
    except Exception:
        pass

    if kind == "chinese":
        base = SAMPLE_MD.format(h1="一、", h2="（一）")
    elif kind == "chapter":
        base = SAMPLE_MD.format(h1="第1章", h2="1.1")
    elif kind == "chinese-numeric":
        base = SAMPLE_MD.format(h1="一", h2="一.一")
    else:
        base = SAMPLE_MD.format(h1="1", h2="1.1")

    if not required:
        return base
    # 按当前体系的编号风格铺必备章节，标题层级为一级，不制造跳级
    if kind in ("chinese", "chinese-numeric"):
        lines = [f"## {cn}、{sec}" for cn, sec in
                 zip("一二三四五六七八九十", required)]
    elif kind == "chapter":
        lines = [f"## 第{i}章 {sec}" for i, sec in enumerate(required, 1)]
    elif kind == "none":
        lines = [f"## {sec}" for sec in required]
    else:
        lines = [f"## {i} {sec}" for i, sec in enumerate(required, 1)]
    return "\n\n".join(lines) + "\n\n" + base


def run_one(profile, out_dir):
    name = profile
    md_path = os.path.join(out_dir, f"{name}.md")
    docx_path = os.path.join(out_dir, f"{name}.docx")
    with open(md_path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(_sample(profile))

    env = dict(os.environ)
    env["ARTICLE_OUT_DIR"] = out_dir
    gen_cmd = [sys.executable, os.path.join(HERE, "md2docx.py"),
               md_path, docx_path, "--profile", profile]
    gen = subprocess.run(gen_cmd, capture_output=True, text=True, env=env,
                         encoding="utf-8", errors="replace")
    if gen.returncode != 0:
        return (profile, "GEN_FAIL", gen.returncode,
                (gen.stderr or gen.stdout).strip()[-400:], docx_path)

    ver_cmd = [sys.executable, os.path.join(HERE, "verify_article_style.py"),
               docx_path, "--profile", profile]
    ver = subprocess.run(ver_cmd, capture_output=True, text=True, env=env,
                         encoding="utf-8", errors="replace")
    tail = [ln for ln in (ver.stdout or "").splitlines() if ln.strip()]
    summary = next((ln for ln in reversed(tail) if ln.startswith("合计")), "")
    fails = [ln.strip() for ln in tail if ln.strip().startswith("- ")]
    detail = summary
    if fails:
        detail += " | " + "; ".join(fails[:4])
    return (profile, "OK" if ver.returncode == 0 else "VERIFY_FAIL",
            ver.returncode, detail, docx_path)


def main(argv=None):
    ap = argparse.ArgumentParser(description="article-format 全 profile 回归")
    ap.add_argument("--keep", action="store_true", help="保留生成的 docx")
    ns = ap.parse_args(argv if argv is not None else sys.argv[1:])

    out_dir = os.path.join(os.environ.get("ARTICLE_OUT_DIR") or os.getcwd(),
                           ".profile-regression")
    os.makedirs(out_dir, exist_ok=True)

    profiles = list_profiles()
    results = [run_one(p, out_dir) for p in profiles]

    width = max(len(r[0]) for r in results) + 2
    bad = 0
    for profile, status, code, detail, _ in results:
        if status != "OK":
            bad += 1
        print(f"{profile:<{width}} {status:<12} exit={code}  {detail}")
    print()
    print(f"合计 {len(results)} 个 profile：通过 {len(results) - bad}，失败 {bad}")

    if not ns.keep:
        shutil.rmtree(out_dir, ignore_errors=True)
    else:
        print(f"产物保留在 {out_dir}")
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
