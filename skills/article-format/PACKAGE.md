# article-format

中文文章类文档的排版规范与生成工具。把 Markdown 草稿转成符合规范的 Word docx，按文体切换整套排版规格。

13 种文体 profile，每套独立规定字体、字号、行距、页边距、章节编号体系与表格样式：

- `formal-doc` 通用正式文章（方案、总结、汇报、调研报告）
- `gov-official` 党政机关公文（GB/T 9704-2012）
- `enterprise-doc` 企业公文与事务文书
- `thesis` 学位论文（GB/T 7713.1-2025）
- `academic-paper` 期刊论文（GB/T 7713.2-2022）
- `medical-paper` 医学论文（ICMJE、IMRaD）
- `tech-doc` 技术文档（ISO/IEC/IEEE 82079-1）
- `legal-doc` 法律文书
- `press-release` 新闻稿
- `business-report` 企业报告
- `regulation` 规章制度（GB/T 1.1-2020）
- `teaching-doc` 教育教学文档
- `social-media` 新媒体文案

另含 490 条可检索的行业规范库，覆盖 14 个领域。

## 用法

```bash
python scripts/md2docx.py 输入.md 成品.docx --profile gov-official
python scripts/md2docx.py --list-profiles
python scripts/verify_article_style.py 成品.docx --profile gov-official
```

`--profile` 必填，不指定会报错并列出可选文体。详细用法见 `SKILL.md`。

## 依赖

`python-docx>=1.1,<2` 与 `PyYAML>=6.0,<7`。

## 说明

本包不做真正的安装分发（`scripts/` 不是 Python 包，无 `__init__.py`），`pyproject.toml` 仅用于声明依赖版本约束与运行测试。使用时把整个 `article-format` 目录拷入技能目录即可。
