# -*- coding: utf-8 -*-
"""conftest.py — 测试夹具：技能路径与临时输出目录。"""
import os
import sys

import pytest

SKILL_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(SKILL_ROOT, "scripts")
sys.path.insert(0, SCRIPTS)

# 样例稿件目录
SAMPLES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "samples")


@pytest.fixture(scope="session")
def skill_root():
    return SKILL_ROOT


@pytest.fixture(scope="session")
def scripts_dir():
    return SCRIPTS


@pytest.fixture
def out_dir(tmp_path, monkeypatch):
    """每个测试独立的输出目录，并把它设为 md2docx 的 BASE。"""
    monkeypatch.setenv("ARTICLE_OUT_DIR", str(tmp_path))
    return tmp_path


@pytest.fixture(scope="session")
def samples_dir():
    return SAMPLES
