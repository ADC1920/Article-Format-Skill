# -*- coding: utf-8 -*-
"""test_output_path.py — 输出路径语义测试。

历史行为：只取 basename 强制落 cwd，`sub/out.docx` 静默变成 `./out.docx`。
现行为：保留子目录，只拒绝逃出 BASE 的路径。
"""
import os

import pytest

from md2docx import _resolve_out


def test_subdir_preserved(tmp_path, monkeypatch):
    monkeypatch.setenv("ARTICLE_OUT_DIR", str(tmp_path))
    import md2docx
    monkeypatch.setattr(md2docx, "BASE", str(tmp_path))
    target = _resolve_out("sub/out.docx")
    assert target == os.path.join(str(tmp_path), "sub", "out.docx")
    assert os.path.isdir(os.path.dirname(target)), "子目录应被自动创建"


def test_deep_subdir_created(tmp_path, monkeypatch):
    import md2docx
    monkeypatch.setattr(md2docx, "BASE", str(tmp_path))
    target = _resolve_out("a/b/c/out.docx")
    assert os.path.isdir(os.path.dirname(target))


def test_plain_name_lands_in_base(tmp_path, monkeypatch):
    import md2docx
    monkeypatch.setattr(md2docx, "BASE", str(tmp_path))
    assert _resolve_out("out.docx") == os.path.join(str(tmp_path), "out.docx")


def test_escape_rejected(tmp_path, monkeypatch):
    import md2docx
    monkeypatch.setattr(md2docx, "BASE", str(tmp_path))
    with pytest.raises(ValueError) as exc:
        _resolve_out("../escape.docx")
    assert "逃出" in str(exc.value)


def test_nested_escape_rejected(tmp_path, monkeypatch):
    import md2docx
    monkeypatch.setattr(md2docx, "BASE", str(tmp_path))
    with pytest.raises(ValueError):
        _resolve_out("sub/../../escape.docx")


def test_absolute_inside_base_accepted(tmp_path, monkeypatch):
    import md2docx
    monkeypatch.setattr(md2docx, "BASE", str(tmp_path))
    target = os.path.join(str(tmp_path), "sub", "abs.docx")
    assert _resolve_out(target) == target


def test_absolute_outside_base_rejected(tmp_path, monkeypatch):
    import md2docx
    monkeypatch.setattr(md2docx, "BASE", str(tmp_path))
    with pytest.raises(ValueError) as exc:
        _resolve_out(os.path.join(str(tmp_path.parent), "elsewhere.docx"))
    assert "必须位于输出目录内" in str(exc.value)
