# Article-Format-Skill

中文文章类文档的排版规范与生成工具。把 Markdown 草稿转成符合规范的 Word docx，按文体切换整套排版规格，并附带 490 条可检索的行业规范库。

**没有默认排版**——每份文档都必须先按性质选定文体，脚本不指定就报错。这样不会出现「判不出文体就随便套一套」的情况。

写作里最费时的不是想内容，是应付格式：公文要求三号仿宋加上 37mm 天头、学位论文要求章标题「第1章」配三线表、期刊论文要求五号正文配双倍行距。这些规矩散在各部国标、投稿须知和单位模板里，每次动手都要重查一遍。这个仓库把规范变成配置——选一个文体，剩下的交给脚本。

## 最近更新（v2.2.0）

- **底模注入**：`--base-template 模板.docx --keep-until 锚点` 把正文灌进单位模板，封面、红头、原创性声明页原样保留。
- **结构要件门禁**：profile 可声明 `required_sections`，交付前校验必备章节（论文缺摘要会报 FAIL，不再只查版式）。
- **配置可信**：profile 写错键在加载时直接报错并列出可疑键。此前把 `list.formats` 改成任何值都不会生效，且一声不响。
- **工程基线**：`pyproject.toml` 锁依赖版本；`pytest` 58 项测试（含篡改字体验门禁真会拦的负向用例）；三平台 × 三 Python 版本 CI。

## 能力

**13 种文体 profile**（12 个行业文体 + 1 个通用档），每套独立规定字体、字号、行距、页边距、章节编号体系与表格样式：

| profile | 适用文体 | 关键差异 |
| --- | --- | --- |
| `formal-doc` | 方案、总结、汇报、调研报告、说明书等通用正式文章 | 黑体标题 / 宋体小四 / 1.3 倍行距 / 数字式七级编号 |
| `gov-official` | 党政机关公文 15 文种 | 上 3.7 下 3.5 左 2.8 右 2.6cm、3 号仿宋、固定行距 28.9 磅、「一、」「（一）」层次序数 |
| `enterprise-doc` | 企业通知、请示、报告、纪要 | 小四宋体、1.5 倍行距、公文式层次序数（信息密度优先） |
| `thesis` | 本科至博士学位论文 | 页边距 3/2.5cm、章标题「第1章」、三线表 |
| `academic-paper` | 期刊论文、学报、会议论文 | 五号正文、章节编号不超过 4 级、三线表 |
| `medical-paper` | 医学论文、病例报告、系统综述 | 双倍行距、IMRaD 无编号标题、Vancouver 引文 |
| `tech-doc` | 用户手册、API 文档、PRD、运维手册 | 正文左对齐无缩进、标题不加编号、Arial 西文 |
| `legal-doc` | 起诉状、合同、法律意见书 | 三号仿宋、公文式版心、层次标题不加粗 |
| `press-release` | 新闻稿、通稿、公关声明 | 标题左对齐、小标题不加编号 |
| `business-report` | 可行性研究、商业计划、ESG、尽调 | 章标题居中、章节不超过 5 级 |
| `regulation` | 管理办法、操作规程、SOP、质量手册 | 章标题居中、条款式列举 |
| `teaching-doc` | 教案、教学设计、开题报告、教研论文 | 四号标题、五号表格（教学过程表） |
| `social-media` | 公众号、小红书、知乎、短视频脚本 | 正文不缩进左对齐、1.75 倍行距、无页码 |

**490 条规范库**，覆盖 14 个领域 46 个子类。每条含名称、可执行规格、适用文体与置信度（high 304 / medium 176 / low 10）。`query_standards.py --audit` 可查可溯源性：其中 172 条无标准号且非 high 置信度，只能当写作提示，不作排版依据。

| 领域 | 条数 | 领域 | 条数 |
| --- | --- | --- | --- |
| 财经与披露 | 62 | 技术与数据文档 | 42 |
| 学术与科研 | 60 | 出版与文学 | 37 |
| 办公与企业文书 | 53 | 新闻与媒体 | 32 |
| 工程与质量 | 47 | 教育与教学 | 23 |
| 公文与政务 | 46 | 综合实务 | 21 |
| 营销与品牌 | 20 | 医疗卫生 | 20 |
| 法律与合规 | 19 | 语言文字基础 | 8 |

## 快速开始

```bash
git clone https://github.com/ADC1920/Article-Format-Skill.git

# 拷入本地技能目录
cp -r Article-Format-Skill/skills/article-format ~/.agents/skills/
# Claude Code 用户：cp -r skills/article-format ~/.claude/skills/
```

依赖只有 `python-docx` 与 `PyYAML`：

```bash
python -m pip install python-docx pyyaml
```

生成文档（`--profile` 必填，不指定会报错并列出可选文体）：

```bash
# 公文
python skills/article-format/scripts/md2docx.py 通知.md 成品.docx --profile gov-official

# 方案 / 总结等通用正式文章
python skills/article-format/scripts/md2docx.py 方案.md 成品.docx --profile formal-doc

# 查看全部可选文体
python skills/article-format/scripts/md2docx.py --list-profiles
```

也可用环境变量 `ARTICLE_FORMAT_PROFILE=thesis` 指定。

`md2docx.py` 内部已调用样式套用，一步出成品。也可对已有 docx 重排：

```bash
python skills/article-format/scripts/article_style.py 旧.docx 新.docx --profile thesis
```

## 源稿写法

层级按**数字编号段数**判定，`#` 前缀数量不参与定级：

```markdown
# 文档主标题

## 1 一级标题
### 1.1 二级标题
#### 1.1.1 三级标题

正文段落，`**重点**` 渲染为加粗。

- 列表项（脚本剥离前缀并挂 Word 自动编号）
- 每个列表块独立从 1 重新计数

| 表头 | 表头 |
| --- | --- |
| 单元格 | 单元格 |
```

中文式编号（`一、`、`（一）`、`第一章`）在 `heading_kind` 为中文体系的 profile 下会被识别为标题，`default` 下仍按正文列举处理。

标号会自动剥离，成品编号由 Word 多级列表驱动——增删章节编号自动重排，不需要手改。

## 校验

```bash
# 单个文档
python skills/article-format/scripts/verify_article_style.py 成品.docx --profile thesis

# 全部 profile 端到端回归
python skills/article-format/scripts/run_profile_regression.py

# 技能文档与实物一致性
python skills/article-format/scripts/check_skill_consistency.py
```

`verify_article_style.py` 约 100 项断言（随 profile 与表格数浮动），退出码 0 才可交付。查的是字体、字号、段距、行距、纸型、页边距、编号体系、页码格式、三线表、表格跨页规则与 OOXML schema 顺序。

## 查规范

想知道某行业通常怎么写、参数是多少：

```bash
python skills/article-format/scripts/query_standards.py --list-domains
python skills/article-format/scripts/query_standards.py --domain gov --min-conf high
python skills/article-format/scripts/query_standards.py --keyword 三线表 --full
python skills/article-format/scripts/query_standards.py --profile thesis
```

规范库三层结构：`references/standards/index.md`（全量索引）、`domain-<slug>.md`（14 个分域详表）、`standards.jsonl`（机器可查）。

## 自定义规格

规格唯一权威源是 yaml，改配置不改代码。profile 只写与默认值的差异，未写字段自动继承：

```yaml
# profiles/my-genre.yaml
profile:
  name: my-genre
  title: 我的文体

fonts:
  heading: 黑体
  body: 仿宋_GB2312
  heading_by_level:      # 按层级分别指定字体
    1: 黑体
    2: 楷体_GB2312

page:
  margin_top_cm: 3.7     # 分边页边距
  margin_bottom_cm: 3.5

spacing:
  line_rule: exact       # 固定行距替代倍数行距
  line_pt: 28.9

table:
  style: three-line      # 三线表

numbering_scheme:
  heading_kind: chinese  # numeric / chinese / chapter / chinese-numeric / none
```

临时换规格文件：`ARTICLE_FORMAT_SPEC=/path/to/spec.yaml`。按文体选：`--profile <名>` 或 `ARTICLE_FORMAT_PROFILE=<名>`。

## 已知限制

- 公文、法律文书、学位论文的**封面、发文机关标志、红色分隔线、印章、成文日期位置、原创性声明页、页眉章名、罗马数字前置页码**不由脚本生成，需按单位模板人工处理。脚本只保证正文版式与层次序数合规。
- 规范库中标 `low` 的 10 条来自二手转述、口径存疑，不作为排版依据。
- 平台限流词、公文禁用词、广告法违禁表述**不做词表扫描**，需人工对照规范库核校。
- 本技能只管文档内表格；独立成件的表格文件请用 `table-format`（深蓝表头 + 隔行底纹那套规格），两者样式不同且不宜混用。

## 目录

```
skills/article-format/
├── SKILL.md                    技能主文档（profile 速选表、规范库索引、执行步骤）
├── article-format.yaml         字段级基线规格（供各 profile 继承）
├── pyproject.toml              依赖版本约束（python-docx / PyYAML / pytest）
├── profiles/                   13 个文体 profile
├── references/standards/       490 条规范库（索引 + 14 个分域详表 + jsonl）
├── tests/                      pytest：规格契约 / 路径语义 / 真实样张端到端 / 负向门禁
│   └── samples/                medium-article.md（长表格、七级嵌套、日期行首、代码块）
└── scripts/
    ├── md2docx.py              Markdown → docx 骨架（含 --base-template 底模注入）
    ├── article_style.py        样式内核（标题/正文/编号/表格/页码）
    ├── spec_loader.py          profile 加载、规格合并与未知键校验
    ├── verify_article_style.py 规格核验（约 100 项断言 + 结构要件门禁）
    ├── query_standards.py      规范库检索（--audit 可溯源性审计）
    ├── build_standards_catalog.py  调研数据 → 规范库
    ├── apply_verification.py   标准号核查结果回填
    ├── run_profile_regression.py   全 profile 回归
    └── check_skill_consistency.py  文档与实物一致性（9 项检查）
```

CI 位于仓库根 `.github/workflows/ci.yml`（GitHub Actions 只识别仓库根），矩阵跑 Windows / Ubuntu / macOS × Python 3.9 / 3.11 / 3.12。

## 许可

技能脚本与规范库结构可自由使用。规范库中的标准条文引用其著作权归原标准发布机构，本仓库仅作要点归纳与检索用途，不作为标准原文替代。
