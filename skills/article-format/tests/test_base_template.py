# -*- coding: utf-8 -*-
"""test_base_template.py — 底模注入（--base-template / --keep-until）。

解决的问题：公文红头、学位论文封面与原创性声明页、单位发文机关标志这类
部件脚本无法凭空生成，只能让用户提供含这些部件的模板，脚本把正文接上。
"""
import os
import subprocess
import sys

import pytest
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt


def _make_template(path, cover_texts, anchor_text=None):
    """造一份带「封面」的底模：几段大标题，末尾可留锚点。"""
    doc = Document()
    for text in cover_texts:
        par = doc.add_paragraph()
        run = par.add_run(text)
        run.font.size = Pt(22)
        par.alignment = WD_ALIGN_PARAGRAPH.CENTER
    if anchor_text:
        doc.add_paragraph(anchor_text)
    # 锚点之后故意留垃圾内容，验证会被清掉
    doc.add_paragraph("模板里原有的旧正文，应被清除。")
    doc.add_paragraph("模板里原有的第二段旧正文，也应被清除。")
    doc.save(path)
    return path


def _run(scripts_dir, out_dir, md_text, extra_args):
    src = os.path.join(str(out_dir), "src.md")
    with open(src, "w", encoding="utf-8") as fh:
        fh.write(md_text)
    out = os.path.join(str(out_dir), "out.docx")
    env = dict(os.environ)
    env["ARTICLE_OUT_DIR"] = str(out_dir)
    env.pop("ARTICLE_FORMAT_SPEC", None)
    r = subprocess.run(
        [sys.executable, os.path.join(scripts_dir, "md2docx.py"),
         src, out, "--profile", "formal-doc"] + extra_args,
        capture_output=True, text=True, env=env, encoding="utf-8", errors="replace")
    return r, out


MD = "# 正文标题\n\n## 1 一章\n\n正文第一段。\n\n## 2 二章\n\n正文第二段。\n"


def test_base_template_keeps_cover(scripts_dir, out_dir):
    """底模的封面段落必须保留，正文接在后面。"""
    tpl = _make_template(os.path.join(str(out_dir), "tpl.docx"),
                         ["某某大学", "学位论文", "作者：张三"])
    r, out = _run(scripts_dir, out_dir, MD, ["--base-template", tpl])
    assert r.returncode == 0, r.stderr[-800:]
    d = Document(out)
    texts = [p.text for p in d.paragraphs if p.text.strip()]
    assert "某某大学" in texts, f"封面丢失：{texts[:8]}"
    assert "学位论文" in texts
    assert "作者：张三" in texts
    assert any("正文标题" in t for t in texts)
    assert any("正文第一段" in t for t in texts)


def test_keep_until_truncates_template(scripts_dir, out_dir):
    """--keep-until 锚点之后的内容应被清除，锚点本身保留。"""
    tpl = _make_template(os.path.join(str(out_dir), "tpl.docx"),
                         ["某某大学", "学位论文"], anchor_text="【正文开始】")
    r, out = _run(scripts_dir, out_dir, MD,
                  ["--base-template", tpl, "--keep-until", "【正文开始】"])
    assert r.returncode == 0, r.stderr[-800:]
    d = Document(out)
    texts = [p.text for p in d.paragraphs if p.text.strip()]
    assert "【正文开始】" in texts, "锚点行应保留"
    assert not any("旧正文" in t for t in texts), f"锚点后旧内容未清除：{texts}"
    assert any("正文第一段" in t for t in texts)


def test_keep_until_missing_anchor_errors(scripts_dir, out_dir):
    """锚点文字不存在时必须报错退出，不能静默追加。"""
    tpl = _make_template(os.path.join(str(out_dir), "tpl.docx"), ["封面"])
    r, _ = _run(scripts_dir, out_dir, MD,
                ["--base-template", tpl, "--keep-until", "不存在的锚点文字"])
    assert r.returncode == 2
    assert "找不到锚点" in r.stderr


def test_missing_template_errors(scripts_dir, out_dir):
    r, _ = _run(scripts_dir, out_dir, MD,
                ["--base-template", os.path.join(str(out_dir), "nope.docx")])
    assert r.returncode == 2
    assert "底模不存在" in r.stderr


def test_keep_until_without_template_warns(scripts_dir, out_dir):
    """单独的 --keep-until 应被忽略并提示，不影响出稿。"""
    r, out = _run(scripts_dir, out_dir, MD, ["--keep-until", "x"])
    assert r.returncode == 0
    assert "已忽略" in r.stderr
    assert os.path.exists(out)


def test_template_output_passes_verify(scripts_dir, out_dir):
    """底模产物的正文版式仍须过门禁（封面部件不参与版式断言）。"""
    tpl = _make_template(os.path.join(str(out_dir), "tpl.docx"),
                         ["封面标题"], anchor_text="【正文】")
    r, out = _run(scripts_dir, out_dir, MD,
                  ["--base-template", tpl, "--keep-until", "【正文】"])
    assert r.returncode == 0, r.stderr[-800:]
    env = dict(os.environ)
    env.pop("ARTICLE_FORMAT_SPEC", None)
    ver = subprocess.run(
        [sys.executable, os.path.join(scripts_dir, "verify_article_style.py"),
         out, "--profile", "formal-doc"],
        capture_output=True, text=True, env=env, encoding="utf-8", errors="replace")
    assert ver.returncode == 0, ver.stdout[-2000:]
