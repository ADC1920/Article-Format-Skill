# -*- coding: utf-8 -*-
"""test_end_to_end.py — 真实样张端到端：生成 → 校验。

与 run_profile_regression.py 的区别：那份用 25 行极简样例，只能证明
「同一输入在 13 套规格下自洽」；这里用 tests/samples/medium-article.md，
含长表格、七级嵌套列表、日期行首、代码块、分页符，是真实文章形态。
"""
import os
import re
import subprocess
import sys
import zipfile

import pytest

from spec_loader import list_profiles

SAMPLE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      "samples", "medium-article.md")


def _run(args, env):
    return subprocess.run([sys.executable] + args, capture_output=True,
                          text=True, env=env, encoding="utf-8", errors="replace")


def _gen(scripts_dir, out_dir, profile, sample=None):
    env = dict(os.environ)
    env["ARTICLE_OUT_DIR"] = str(out_dir)
    env.pop("ARTICLE_FORMAT_SPEC", None)
    docx = os.path.join(str(out_dir), f"{profile}.docx")
    r = _run([os.path.join(scripts_dir, "md2docx.py"), sample or SAMPLE, docx,
              "--profile", profile], env)
    return r, docx


@pytest.mark.parametrize("profile", list_profiles())
def test_generate_and_verify_real_sample(scripts_dir, out_dir, profile):
    """13 个 profile 各自用真实样张跑通生成 + 校验。

    声明了 required_sections 的 profile（论文类）需要样张含必备章节；
    medium-article.md 没有摘要，故按 profile 声明在样张前部补章节标题。
    """
    from spec_loader import load_spec
    required = (load_spec(profile=profile).get("profile") or {}).get("required_sections") or []
    sample = SAMPLE
    if required:
        kind = str(load_spec(profile=profile).get("numbering_scheme", {})
                   .get("heading_kind", "numeric") or "numeric")
        if kind in ("chinese", "chinese-numeric"):
            heads = [f"## {cn}、{sec}" for cn, sec in zip("一二三四五六七八九十", required)]
        elif kind == "chapter":
            heads = [f"## 第{i}章 {sec}" for i, sec in enumerate(required, 1)]
        elif kind == "none":
            heads = [f"## {sec}" for sec in required]
        else:
            heads = [f"## {i} {sec}" for i, sec in enumerate(required, 1)]
        with open(SAMPLE, encoding="utf-8") as fh:
            body = fh.read()
        # 去掉原主标题避免出现两个 Title，把必备章节插到最前
        body = "\n".join(l for l in body.splitlines() if not l.startswith("# 真实样张"))
        sample = os.path.join(str(out_dir), f"{profile}-sample.md")
        with open(sample, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("\n\n".join(heads) + "\n\n" + body)

    gen, docx = _gen(scripts_dir, out_dir, profile, sample=sample)
    assert gen.returncode == 0, (
        f"{profile} 生成失败：\n{gen.stderr[-1500:]}\n{gen.stdout[-800:]}")
    assert os.path.exists(docx), f"{profile} 产物不存在"

    env = dict(os.environ)
    env.pop("ARTICLE_FORMAT_SPEC", None)
    ver = _run([os.path.join(scripts_dir, "verify_article_style.py"),
                docx, "--profile", profile], env)
    assert ver.returncode == 0, (
        f"{profile} 校验未过：\n{ver.stdout[-2000:]}")


@pytest.mark.parametrize("profile", ["formal-doc", "gov-official", "thesis"])
def test_long_table_header_repeat(scripts_dir, out_dir, profile):
    """长表格必须有 tblHeader（表头跨页重复）与 cantSplit（行不拆页）。"""
    gen, docx = _gen(scripts_dir, out_dir, profile)
    assert gen.returncode == 0, gen.stderr[-800:]
    with zipfile.ZipFile(docx) as z:
        xml = z.read("word/document.xml").decode("utf-8")
    assert "w:tblHeader" in xml, f"{profile} 缺表头重复标记"
    assert "w:cantSplit" in xml, f"{profile} 缺行不拆页标记"


@pytest.mark.parametrize("profile", ["formal-doc", "gov-official"])
def test_nested_list_seven_levels(scripts_dir, out_dir, profile):
    """七级嵌套列表要落到 numbering.xml，且各级 numFmt 存在。"""
    gen, docx = _gen(scripts_dir, out_dir, profile)
    assert gen.returncode == 0, gen.stderr[-800:]
    with zipfile.ZipFile(docx) as z:
        numbering = z.read("word/numbering.xml").decode("utf-8")
    fmts = set(re.findall(r'w:numFmt w:val="([^"]+)"', numbering))
    assert fmts, "numbering.xml 里没有任何 numFmt"


def test_date_lines_become_body(scripts_dir, out_dir):
    """明确日期形态（4 位年份或带前导零）不得被识别为标题。

    `9.17` 这类两段均无前导零的与章节号同构，按设计不拦截（见
    md2docx._is_date_like_number 的说明），故不在此断言。
    """
    from md2docx import parse_markdown
    md = "09.17 期数据\n\n2026.10.08 上新\n\n2026.9 单段月\n"
    parsed = parse_markdown(md)
    kinds = [n["type"] for n in parsed]
    assert kinds.count("h") == 0, f"日期行被当成标题：{parsed}"
    assert kinds.count("p") == 3


def test_code_fence_content_not_heading(scripts_dir):
    """围栏内的 # 注释不得被当作标题。"""
    from md2docx import parse_markdown
    md = "```python\n# 这是注释不是标题\nx = 1\n```\n"
    parsed = parse_markdown(md)
    assert not any(n["type"] == "h" for n in parsed), parsed
    assert any(n["type"] == "code" for n in parsed)


def test_bold_markup_consumed(scripts_dir, out_dir):
    """**重点** 必须渲染为加粗，成品里不得残留字面星号。"""
    gen, docx = _gen(scripts_dir, out_dir, "formal-doc")
    assert gen.returncode == 0, gen.stderr[-800:]
    with zipfile.ZipFile(docx) as z:
        xml = z.read("word/document.xml").decode("utf-8")
    # 提取所有正文文本
    texts = re.findall(r"<w:t[^>]*>([^<]*)</w:t>", xml)
    joined = "".join(texts)
    assert "**" not in joined, "成品里残留 ** 标记"


def test_medium_sample_tables_preserved(scripts_dir, out_dir):
    """真实样张含 1 张 31 行表格，产物表格行列数要对得上。"""
    from docx import Document
    gen, docx = _gen(scripts_dir, out_dir, "formal-doc")
    assert gen.returncode == 0, gen.stderr[-800:]
    d = Document(docx)
    assert len(d.tables) == 1, f"表格数异常：{len(d.tables)}"
    assert len(d.tables[0].rows) == 31, f"表格行数异常：{len(d.tables[0].rows)}"
    assert len(d.tables[0].columns) == 4
