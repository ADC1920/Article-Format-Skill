---
name: article-format
description: |
  文章类文档排版规范与生成工具（全局默认）：把 Markdown 或草稿转成符合中文文章排版规范的 Word docx，并可按文体切换排版规格（公文/学位论文/学术论文/技术文档/法律文书/新闻稿/企业报告/教案/新媒体/规章制度等 13 种 profile）。
  Article formatting standard: produce Chinese article-style Word docx with heading styles, auto-numbered body lists, and navigation pane outline; supports per-genre profiles.
  **触发分支**：文章排版、排版规范、格式要求、生成 docx 文档、Word 排版、制度/论文/报告排版、md 转 Word、写方案、写总结、写制度、写通知、汇报材料、调研报告、实施方案、工作总结、说明书、操作手册、规章制度、公文格式、红头文件、学位论文格式、期刊投稿格式、技术文档排版、法律文书格式、新闻稿格式、教案格式、新媒体排版。
metadata:
  trigger: 文章类文档排版（按文体强制选 profile，无默认）
  language: zh-CN
  scope: 全局
  version: "2.2.0"
---

# 文章排版规范（全局默认 · 多文体）

文章、制度、论文、报告、方案、总结、通知、汇报材料等「文章类」文档默认按本规范排版并输出 docx。会议纪要自 2026-09-09 起同样走本规范（公文体已退役，见末节分工）。

**v2.2（2026-11-22）新增**：①profile 未知键校验（写错键立刻报错，不再静默失效）；②`--base-template` / `--keep-until` 底模注入（红头、封面、声明页可保留）；③profile 可声明 `required_sections` 必备章节，交付前校验结构完整性；④pytest 测试套件 + 三平台 CI；⑤输出路径保留子目录（原先静默丢弃目录成分）。

**v2.1（2026-11-21）起无默认排版**：必须按文章性质选定文体 profile，不指定则脚本报错。v2.0 新增三层能力：①12 种文体 profile（另 formal-doc 通用档），按文体切换整套排版规格；②490 条规范库（14 个领域），可检索各行业文章规范的具体参数与结构要件；③三线表、固定行网格、中文层次序数、分边页边距等此前缺失的版式能力。

## 文体 profile 速选（先看这张表）

| profile | 适用文体 | 关键版式特征 |
|---|---|---|
| `formal-doc` | 方案、总结、汇报、调研报告、说明书等通用正式文章 | 黑体标题/宋体小四/1.3 倍行距/首行缩进 2 字/数字式七级编号 |
| `gov-official` | 党政机关公文 15 文种 | A4、上 3.7 下 3.5 左 2.8 右 2.6cm、3 号仿宋、固定行距 28.9 磅、「一、」「（一）」「1.」「（1）」、层次字体黑体/楷体/仿宋 |
| `enterprise-doc` | 企业通知/请示/报告/总结/纪要 | 小四宋体、1.5 倍行距、公文式层次序数（密度优先） |
| `thesis` | 本科/硕士/博士学位论文 | 页边距 3/2.5cm、1.5 倍行距、章标题「第1章」、三线表 |
| `academic-paper` | 期刊论文、学报、会议论文 | 五号正文、三线表、章节编号≤4 级、GB/T 7714 著录 |
| `medical-paper` | 医学论文、病例报告、综述 | 双倍行距、IMRaD 无编号标题、三线表、Vancouver 引文 |
| `tech-doc` | 用户手册、API 文档、PRD、运维手册 | 正文左对齐无缩进、标题不加编号、五号正文、Arial 西文 |
| `legal-doc` | 起诉状/答辩状/合同/法律意见书 | 三号仿宋、公文式版心、层次标题不加粗 |
| `press-release` | 新闻稿、通稿、公关声明 | 标题左对齐、1.5 倍行距、小标题不加编号 |
| `business-report` | 可行性研究/商业计划/ESG/尽调 | 章标题居中、章节≤5 级、五号表格 |
| `regulation` | 管理办法/操作规程/SOP/质量手册 | 章标题居中、1.5 倍行距、条款式列举 |
| `teaching-doc` | 教案/教学设计/开题报告/教研论文 | 四号标题、五号表格（教学过程表）、1.5 倍行距 |
| `social-media` | 公众号/小红书/知乎/短视频脚本 | 正文不缩进左对齐、1.75 倍行距、段距 0.3 行、无页码 |

**用法**：`--profile <名>`；或设环境变量 `ARTICLE_FORMAT_PROFILE`。**本技能不使用默认排版**：两者都没有时脚本报错退出（exit 2）并列出可选文体，不会静默套一套规格。列出全部：`python scripts/md2docx.py --list-profiles`。

## 规范库（490 条，14 个领域）

`references/standards/` 收录各行业文章规范，用于查证「这类文体通常怎么写、版式参数是多少」：

| 领域 | 条数 | 内容 |
|---|---|---|
| 公文与政务 | 46 | GB/T 9704 全套要素、15 法定文种、企业行文参照 |
| 办公与企业文书 | 53 | 通知报告总结、制度规程、WPS 办公模板惯例 |
| 学术与科研 | 60 | 学位论文、期刊论文、GB/T 7714 著录、摘要关键词、三线表、学术伦理 |
| 语言文字基础 | 8 | GB/T 15834 标点、GB/T 15835 数字用法 |
| 财经与披露 | 62 | 财务报表、审计报告、证券披露、评估报告、ESG、内控 |
| 法律与合规 | 19 | 诉讼文书、合同、法律意见书、尽调报告 |
| 工程与质量 | 47 | 可行性研究、ISO 9001/IATF 16949、检验检测、标准化、专利 |
| 技术与数据文档 | 42 | ISO/IEC/IEEE 82079、GB/T 8567、PRD、API、模型卡 |
| 新闻与媒体 | 32 | 新华社禁用词、AP/Reuters/BBC 风格、各平台发布规范 |
| 营销与品牌 | 20 | 广告法禁令、平台文案、品牌公关、SEO |
| 出版与文学 | 37 | 图书编辑、CIP 数据、文学创作、剧本格式 |
| 医疗卫生 | 20 | IMRaD、CONSORT/PRISMA、临床试验与药政文书 |
| 教育与教学 | 23 | 教案、说课、试卷编制、教研论文 |
| 综合实务 | 21 | 主持词、致辞、年鉴、地方志、解说词 |

三层结构：`index.md`（全部条目一行式索引）、`domain-<slug>.md`（分域详表含完整规格）、`standards.jsonl`（机器可查）。

**检索**：

```bash
python scripts/query_standards.py --list-domains              # 领域与条数
python scripts/query_standards.py --domain academic           # 某领域全部
python scripts/query_standards.py --keyword 三线表            # 关键词
python scripts/query_standards.py --profile thesis            # 某 profile 关联条目
python scripts/query_standards.py --domain gov --min-conf high --full
python scripts/query_standards.py --audit                     # 可溯源性审计（置信度/出处/不可依据清单）
```

置信度三档：`high` 已核对官方原文；`medium` 行业通行做法或二次资料；`low` 仅见转述、口径存疑。**low 不作为排版依据。**

**查文体结构骨架**：规范库里 56 条的 `specs` 字段直接写了章节骨架（含「依次」「节次」「必备节」等字样），例如审计报告必备要素、专利说明书五部分、PRD 九节、学位论文三部分。查法：

```bash
python scripts/query_standards.py --keyword 必备 --domain finance --full
python scripts/query_standards.py --keyword 依次 --domain gov --full
```

`--full` 输出完整 specs 全文，可直接用作写稿结构清单（规范库的 source 字段已清空，出处以条目名称中的标准号为准）。**注意**：脚本只做关键词匹配，不解析结构语义，命中的条目要自己读一遍再决定是否采用。

## 适用性保证（两层机制）

1. **常驻规则**（保证层）：ZCode 侧由 `~/.zcode/scripts/article-default.js` 挂在 SessionStart，每会话注入
   「文章类文档一律默认用本技能排版」并说明 13 种 profile 的用法（2026-11-21 起该钩子正式注册进
   `~/.zcode/cli/config.json` 的 SessionStart，此前文档声称已挂、实际未挂，靠全局 `AGENTS.md` 的
   「文章排版默认规则」节兜底）。文案优先读 `~/.zcode/AGENTS-annex.md` 的同名节，缺失时用脚本内置文案。
   **DSH 侧（2026-11-07 起）**：DSH 没有 SessionStart 钩子，`article-default.js` 不会被调用；对应保证改由
   `~/.dsh/AGENTS.md` 末尾「排版指路」段常驻承担（该段已写明文章类走本技能）。此处不再依赖 ZCode 脚本。
2. **触发提示**（提醒层）：ZCode 侧由 `skill-trigger.js`（UserPromptSubmit hook）读 `SKILL-TRIGGERS.md` 的 article-format 行做关键词匹配，命中时注入「必须立即加载本技能」的 nudge；无该表消费者的平台（含 DSH），触发由本文件 front-matter 的 `description` 随技能清单常驻、靠语义匹配承担。

**唯一例外**：用户明确指定其他格式、给出自定义模板或具体排版要求（字体字号等）时，以用户指定为准。

## 执行步骤

### 1. 定 profile

先判文体。命中下表的直接取对应 profile。**判不出时不许随便挑一个**：先用 `query_standards.py` 查该文体在规范库里的定位，仍不确定就问用户——按错 profile 出的成品（如把学位论文按公文排）比多问一句代价大得多。交付时说明实际用了哪个 profile。

- 公文/红头文件/请示/批复/通知（机关行文）→ `gov-official`
- 企业内部通知/报告/总结/纪要/请示 → `enterprise-doc`
- 学位论文/毕业论文 → `thesis`
- 期刊论文/学报投稿/会议论文 → `academic-paper`
- 医学论文/病例报告/系统综述 → `medical-paper`
- 用户手册/操作手册/API 文档/PRD/测试报告 → `tech-doc`
- 起诉状/答辩状/合同/律师函/法律意见书 → `legal-doc`
- 新闻稿/通稿/媒体声明 → `press-release`
- 可行性研究/商业计划/尽调/ESG 报告 → `business-report`
- 管理办法/操作规程/SOP/质量手册 → `regulation`
- 教案/教学设计/开题报告/教研论文 → `teaching-doc`
- 公众号/小红书/短视频脚本/营销文案 → `social-media`
- 方案、总结、汇报、调研报告、说明书等通用正式文章 → `formal-doc`
- 确实不属于以上任何一类 → 查规范库确认文体归属，再决定；仍无法归类时问用户

**易混文体的判据**（只看关键词会判错，按这些特征区分）：

| 疑似 | 关键区分点 | 结论 |
|---|---|---|
| 函 | 收文方是本机关内部部门 → 企业行文；是外部单位 → 公文式 | `enterprise-doc` / `gov-official` |
| 论文 | 有「第一章/第二章」章回体系 → 学位论文；有「摘要+关键词+中图分类号」投稿格式 → 期刊论文 | `thesis` / `academic-paper` |
| 论文 | 有 IMRaD（方法/结果/讨论）且需英文摘要、报告规范清单 → 医学论文 | `medical-paper` |
| 报告 | 写给人看的技术说明（操作步骤、接口参数）→ 技术文档；写给决策者看的论证（投资、可行性、尽调）→ 企业报告 | `tech-doc` / `business-report` |
| 报告 | 事故复盘、季度总结、工作汇报 → 内部行文；对外披露或立项论证 → 企业报告 | `enterprise-doc`/`formal-doc` / `business-report` |
| 制度 | 面向全员、条款式（第一条/第二条）、有罚则 → 规章制度；技术操作步骤 → 技术文档 | `regulation` / `tech-doc` |
| 稿 | 发给媒体、有「本报讯」或媒体联络 → 新闻稿；发自有账号、有话题标签 → 新媒体 | `press-release` / `social-media` |
| 申请材料 | 资质认定、项目立项、补贴申报 → 企业报告；学位相关 → 学位论文 | `business-report` / `thesis` |

判据优先级：**文稿实际体裁 > 用户措辞**。用户说「写个报告」而内容是操作步骤时，按技术文档排。

**超出本技能范围的文档**（不要硬选一个 profile）：

| 类型 | 为什么不适合 | 应怎么答复 |
|---|---|---|
| 招股说明书、债券募集说明书、年报半年报 | 有法定披露准则与固定章节，还含财务报表、承销商信息、审计意见等本技能不生成的部件 | 说明属证券披露文档，本技能只能帮正文部分按 `business-report` 排版，完整文件需按证监会格式准则制作 |
| 上市公司公告、权益变动报告书 | 同上，且需与交易所披露系统对接 | 同上 |
| 家书、日记、私人信件 | 无行业规范，也不属办公文档 | 说明本技能面向正式文档；如只是要个 docx 可给 `formal-doc` |
| 期刊/学位论文的**完整投稿包** | 除正文外还含投稿信、作者贡献声明、图表单独文件、补充材料 | 正文按对应 profile，其余部件需另行准备 |
| 需盖章/签发的正式公文（红头文件） | 版式可排，但发文机关标志、印章、成文日期位置需按单位模板 | 版式按 `gov-official`，并提示这些部件需人工处理 |

判断口径：**如果这份文档的核心价值来自法定格式、专用部件或外部系统对接，而不是文章本身的组织与版式，就属于超范围。** 此时要说清能帮到哪一步，而不是默默套一个 profile 交出半成品。

确实判不出时：①先 `query_standards.py --keyword <文体名>` 查该文体在规范库的定位与结构要件；②仍不确定就问用户「这份文件要按什么文体排版」，并给出 2-3 个候选及差异；③**不要硬套一个看起来像的**——按错 profile 出的是整套版式不对，返工成本高于问一句。

需要核对某文体的具体参数时，先 `query_standards.py` 查规范库，再决定是否偏离 profile 默认值。

### 2. 准备 Markdown 源稿

按以下约定写 md，脚本据此识别层级（**层级以「数字编号段数」为准，`#` 前缀数不参与定级**）：

- 主标题用 `# `（不带编号；渲染为 Title 样式——不进目录树、不参与章节编号）
- 标题序号必须「数字 空格 题名」：`## 1 绪论`（一级）、`### 1.1 实验装置`（二级）、`#### 1.1.1 参数校正`（三级）——1 段编号→H1、2 段→H2、……、7 段→H7
- 也可省略 `#` 前缀，编号独立成行：`1 绪论`、`1.1 实验装置` …… `1.1.1.1.1.1.1`（七级）
- **中文式编号（v2.0）**：`一、总体要求`、`（一）工作目标`、`第一章 绪论` 在 profile 的
  `numbering_scheme.heading_kind` 为 `chinese` / `chapter` / `chinese-numeric` 时按形态定级
  （一、→H1，（一）→H2，第一章→H1）；`formal-doc` 与 `academic-paper` 等 numeric 体系下这些行不按标题处理，避免正文列举误判
- 无编号的 `##`~`#######` 前缀行按「# 数 - 1」兜底定级（`## 概述` → 一级）
- **标题编号自动重排（v1.5，v2.0 扩展四种体系）**：章节编号由 Word 自动多级编号显示，脚本渲染标题时
  自动剥离源稿手写编号前缀（如 `## 1.1 实验装置` → docx 显示「1.1 实验装置」，编号来自 Word 而非文字），
  增删章节编号自动重排；源稿编号仅作层级提示，写错数值不影响成品编号，但**层级跳级（如 1 级下直接
  3 级）默认报错退出**（yaml `numbering_scheme.heading_gap_check`：error / warn / off）
  - `numeric`：1 / 1.1 / 1.1.1（formal-doc、academic-paper、business-report 等）
  - `chinese`：一、/（一）/ 1. /（1）（gov-official、enterprise-doc、legal-doc）
  - `chapter`：第1章 / 1.1 / 1.1.1（thesis）
  - `none`：标题不加编号（tech-doc、medical-paper、social-media、press-release）
- 正文标号手写为 `1. ` / `1) ` / `(1) ` / `① ` / `a. ` / `(a) ` / `i. `（七级形式依层级），脚本会剥离前缀并挂接 Word 自动编号；公共文类 profile 可整体替换为「一、」「（一）」
- 嵌套标号行**行首不留空格**；不得出现 `2))` 这类多余右括号（会导致该行掉出自动编号）
- 表格用标准 md 表格；**三线表（v2.0）**：profile 的 `table.style: three-line` 时自动改为三线表
  （顶线 1.5 磅、栏目线 0.75 磅、底线 1.5 磅、无竖线与内横线），学术/学位/医学论文默认启用
- 分隔线用单独一行 `---`（`***` / `___` 同义，输出横线不留字面）；代码用成对 ``` 围栏包住（块内文本按原样输出，`#` 注释不当作标题）；分页用单独一行 `[[PAGEBREAK]]`（生成硬分页符，不留字面文字）
- `**重点**` 渲染为真加粗：正文段、引文（`>`）、编号列表条目、表格单元格统一解析
  （v1.5.1 前列表条目不解析，星号会字面出现在成品里）
- 行首日期形态（`09.17` / `2026.10.08` 等）不按标题识别，自动落为正文段、不挂
  章节编号（v1.5.2 起内置防护——日期与数字编号形态同构，此前会误判为二级标题；
  两段均无前导零的 `9.17` 与章节号无法区分，如作标题请加 `#` 前缀）

### 3. 生成 docx

```bash
python "<skill_dir>/scripts/md2docx.py" 输入.md 中间.docx [--profile <文体>]
python "<skill_dir>/scripts/article_style.py" 中间.docx 最终.docx [--profile <文体>]
```

`<skill_dir>` 为本技能目录（技能实体位于 `%USERPROFILE%\.agents\skills\article-format`）。脚本仅依赖 `python-docx` 与 `PyYAML`，版本区间见 `pyproject.toml`。

`md2docx.py` 内部已调用 `apply_article_style`，单跑第一条即可出成品；第二条用于对已有 docx 重新套样式（如换 profile 重排）。

**输出路径**（v2.2 修正）：相对路径按 `ARTICLE_OUT_DIR` 或当前工作目录解析，**保留子目录**——`sub/out.docx` 会落到 `sub/` 下，父目录自动创建。逃出基准目录的路径（`../x.docx`、基线外的绝对路径）会报错退出（exit 2），不再静默改道。此前版本只取 basename 强制落 cwd，脚本化调用会以为产物在子目录里。

**底模注入**（v2.2 新增）：公文红头、学位论文封面与原创性声明页、单位发文机关标志这类部件脚本无法凭空生成，用底模承接：

```bash
python "<skill_dir>/scripts/md2docx.py" 正文.md out.docx --profile thesis \
  --base-template 学校模板.docx \
  --keep-until 目录
```

- `--base-template`：以该 docx 为底模，正文接在其后，封面等前置部件原样保留。
- `--keep-until 文字`：删掉底模中该文字所在段落之后的所有内容，正文从该处续写。按段落文本**包含匹配**，找不到即报错（exit 2），不会静默追加。
- 不传 `--keep-until` 时正文追加到模板末尾。
- 底模产物的正文仍走本技能版式并需通过 `verify_article_style.py`；封面部件使用模板自带样式，不受影响。
- 底模须为有效 `.docx`（`.doc`/`.dot` 先另存为 docx）。

### 4. 交付前抽查

```bash
python "<skill_dir>/scripts/verify_article_style.py" 最终.docx [--profile <文体>]
```

核验项随 profile 的规格变化（约 100 项，标点/字体/字号/段距/纸型/页边距/编号体系/页码/三线表/表格跨页/OOXML schema 顺序）。exit 0 = 全部通过。

**结构要件校验**（v2.2 新增）：profile 可用 `profile.required_sections` 声明必备章节关键词，verify 按标题与正文文本做存在性检查。已在 academic-paper（摘要/关键词/参考文献）、thesis（同）、medical-paper（摘要/关键词/方法/结果/讨论/参考文献）声明。缺项报 `[FAIL] 结构 必备章节齐全` 并列出缺什么；未声明的 profile 该项直接通过。**只判有无，不判质量与顺序。**

也可直接跑全部 profile 的端到端回归：

```bash
python "<skill_dir>/scripts/run_profile_regression.py"          # 13 个 profile 全跑一遍
python "<skill_dir>/scripts/run_profile_regression.py" --keep   # 保留产物供目检
python -m pytest tests/ -q                                      # 单元 + 真实样张端到端 + 负向门禁
```

`tests/` 与 `run_profile_regression.py` 的分工：后者用 25 行极简样例验「同一输入在 13 套规格下自洽」；前者用 `tests/samples/medium-article.md`（31 行表格、七级嵌套列表、日期行首、代码块、分页符）验真实文章形态，并含**负向门禁测试**——篡改字体/字号后确认 verify 真的报 FAIL，防止门禁空转。

人工核对要点：标题黑体、正文宋体小四、正文标号顶格且为自动编号、页脚页码、标题编号连续。属公文/学位论文等有封面与声明页的文体，封面、页眉章名、印章、成文日期位置仍需按单位模板人工处理——脚本不代劳（可用 `--base-template` 承接）。

## 规格配置（唯一权威源）

文体规格写在 **`<skill_dir>/profiles/<文体>.yaml`**。改配置即改规格，**不需要改任何 Python 代码**。

`<skill_dir>/article-format.yaml` 是**字段级基线**（供各 profile 继承未写字段），不是可选文体，也不对外暴露。

```yaml
fonts:      {heading: 黑体, body: 宋体, western: Times New Roman}
sizes_pt:   {doc_title: 18, h1: 15, h2: 14, h3: 14, h4: 12, h5: 12, h6: 10.5, h7: 10.5, body: 12, table: 12, footer: 12}
spacing:    {line: 1.3, h1_before_after_pt: 17, h2_before_after_pt: 13, h4_before_after_pt: 6, h6_before_after_pt: 3, body_before_after_lines: 0.1}
page:       {size: A4, width_cm: 21.0, height_cm: 29.7, margin_cm: 2.54}
indent:     {body_first_line_chars: 2, list_left: 0, list_hanging: 0}
color:      {text: "000000"}
table:      {font_size_pt: 12, header_bold: true, shading: false, first_line_indent: false, line_spacing: 1.3}
```

profile 文件只写与该默认值的差异，未写字段自动继承。可选高级字段：

| 字段 | 作用 | 取值示例 |
|---|---|---|
| `fonts.heading_by_level` | 按标题层级分别指定中文字体 | `{1: 黑体, 2: 楷体_GB2312}`（公文层次字体） |
| `spacing.line_rule` / `line_pt` | 固定行距（行网格）替代倍数行距 | `exact` / `28.9`（公文每页 22 行） |
| `page.margin_top_cm` 等四项 | 分边页边距覆盖 `margin_cm` | `3.7` / `3.5` / `2.8` / `2.6` |
| `table.style` | 表格样式 | `three-line`（三线表） |
| `list.level_defs` | 正文列举七级编号定义（**唯一有效键**） | `[{fmt: chineseCounting, text: "%1、"}]` |
| `numbering_scheme.heading_kind` | 章节编号体系 | `numeric`/`chinese`/`chapter`/`chinese-numeric`/`none` |
| `footer.number_format` | 页码格式 | `dash`（- N -）/ `plain`（N）/ `none` |
| `profile.required_sections` | 必备章节关键词（verify 做存在性检查） | `[摘要, 关键词, 参考文献]` |

**未知键会被拦截**（v2.2）：profile 里写错键（如把 `list.level_defs` 写成 `list.formats`）在加载时直接抛错并列出可疑键，不再被静默吞掉。已废弃的 `heading_style` / `body_list_style` / `use_gongwen` / `list.formats` 已从全部 13 个 profile 与基线移除，回流会被 `check_skill_consistency.py` 拦下。

- 配置文件缺失、字段缺失或 PyYAML 未安装 → 自动回落到脚本内置默认值（与上表一致），脚本照常运行。
- 临时套用别的规格：`ARTICLE_FORMAT_SPEC=/path/to/other.yaml python scripts/article_style.py in.docx out.docx`。
- 指定文体：`ARTICLE_FORMAT_PROFILE=thesis` 环境变量，或 `--profile thesis` 参数。
- **版本号单一来源**：`article-format.yaml` 的 `version` 与 `spec_loader.DEFAULT_SPEC["version"]` 必须一致，由 `check_skill_consistency.py` 校验；`pyproject.toml` 同步。

## 排版规格（formal-doc 参考值）

| 元素 | 字体字号 | 段落格式 |
|---|---|---|
| 文档主标题 | 黑体 小二（18pt）加粗 | 居中，1.3 倍行距 |
| 一级标题 `1 绪论` | 黑体 小三（15pt）加粗 | 居中，段前段后 17 磅，1.3 倍行距 |
| 二级标题 `1.1 …` | 黑体 四号（14pt）加粗 | 两端对齐，段前段后 13 磅，1.3 倍行距 |
| 三级标题 `1.1.1 …` | 黑体 四号（14pt）加粗 | 两端对齐，段前段后 13 磅，1.3 倍行距 |
| 四级标题 `1.1.1.1 …` | 黑体 小四（12pt）加粗 | 两端对齐，段前段后 6 磅，1.3 倍行距 |
| 五级标题 `1.1.1.1.1 …` | 黑体 小四（12pt）加粗 | 两端对齐，段前段后 6 磅，1.3 倍行距 |
| 六级标题 `1.1.1.1.1.1 …` | 黑体 五号（10.5pt）加粗 | 两端对齐，段前段后 3 磅，1.3 倍行距 |
| 七级标题 `1.1.1.1.1.1.1 …` | 黑体 五号（10.5pt）加粗 | 两端对齐，段前段后 3 磅，1.3 倍行距 |
| 正文 | 宋体 小四（12pt） | 两端对齐，首行缩进 2 字符，段前段后 0.1 行，1.3 倍行距 |
| 正文标号 `1.` `1)` `(1)` `①` `a.` `(a)` `i.` | 同正文 | **顶格**（缩进归零），Word 程序自动编号（七级形式依层级），每列表块从 1 重排 |
| 表格 | 宋体 小四 12pt，表头加粗 | 去底色；单元格左对齐、无缩进、1.3 倍行距；跨页时表头自动重复、行不跨页拆断、表头行与标题行不孤立页底 |
| 页脚页码 | 宋体 小四（12pt）黑色 | 底端居中，页码格式 `- N -` |
| 页面 | A4（21×29.7cm） | 四边页边距 2.54cm |

英文与数字一律 Times New Roman（标题处加粗）。标题序号与题名间空一格。

其他 profile 的完整参数见 `profiles/<名>.yaml`，文件头注释写明依据的标准与来源。

**标题编号自动重排**：章节编号由 Word 自动多级编号驱动（abstractNum 90，样式级绑定 Heading 1-7），源稿手写编号前缀渲染时剥离——成品编号永远连续、增删章节自动重排。

**顶格**指编号缩进与文本缩进在编号定义层与段落级双层归零（`w:ind left=0 hanging=0`），保证 Word/WPS 打开同样顶格。

**左侧导航目录**：一~七级标题自动套用 Word 内置 Heading 1-7（样式自带 outlineLvl 0~6），Word/WPS「视图→导航窗格（WPS 为『导航』）」即可可见可点击跳转；主标题不套用。

## 分工红线

- **文章/制度/论文/报告/方案/总结/通知/汇报材料/公文/技术文档/法律文书/教案/新媒体文案** → 本技能（按文体选 profile）
- **表格按载体分工**（2026-11-21 明确）：**文档内表格**归本技能，按 `article-format.yaml` 的 `table` 节排版（宋体小四/无底色/跨页规则；学术类 profile 走三线表）。**独立成件的表格文件**归 `table-format`（深蓝表头 + 黑体 10 号 + 隔行底纹 + 冻结表头，交付 xlsx）。两者的样式规格不同且不能混用——同一份文档里不要出现 table-format 的深蓝表头。触发侧由 `skill-trigger.js` 的载体分流自动判定：句中含文章/报告/论文/制度/方案/总结/通知/公文/文档/word/docx 等载体词且无电子表格信号时，「表格」归本技能；含 xlsx/Excel/公式/数据清洗等信号时仍按表格文件处理。
- **会议纪要公文体已退役**（2026-09-09 用户确认）：原 `tools/fangong_style.py` 不再实现「宋体二号/三号 + 固定 28 磅 + 一、→（一）编号」的公文样式。会议纪要今后走 `enterprise-doc` profile（企业场景）或 `gov-official`（机关场景）。
- 全库统一一套样式体系：黑体标题 / 宋体（或仿宋）正文 / 自动编号 / Heading 导航；差异通过 profile 表达，不在代码里分叉。

## 规格外置与单通道

**多套规格、单条输出通道**，规格唯一权威源 = `article-format.yaml` + `profiles/*.yaml`：

| 通道 | 入口 | 用途 |
|---|---|---|
| Python（精确） | `scripts/md2docx.py` → `scripts/article_style.py` | 精确排版（Word 自动编号、标号顶格、Heading 导航、三线表） |
| 底模注入 | `scripts/md2docx.py --base-template` | 正文灌入单位模板，保留封面/红头/声明页 |
| 规范查询（只读） | `scripts/query_standards.py` | 查各行业文章规范的具体参数；`--audit` 审计可溯源性 |
| 回归（只读） | `scripts/run_profile_regression.py` + `pytest tests/` | 13 个 profile 端到端核验 + 真实样张 + 负向门禁 |

通道从 `spec_loader.load_spec()` 读 yaml；改规格只改 yaml，不改代码。（pandoc 通用通道已于 2026-09-11 按用户指令移除。）

## 触发覆盖（100% 保证，两层机制）

1. **常驻层（保证）**：ZCode 侧由 `~/.zcode/scripts/article-default.js` 挂 SessionStart（2026-11-21 已正式注册），每会话注入「文章类文档一律默认用本技能排版」——不依赖关键词，因此中文表述再多也覆盖（实测 20 例模糊说法命中 18，剩 2 例由本层兜底）。
2. **触发层（提醒）**：ZCode 侧是 `SKILL-TRIGGERS.md` 的 article-format 行（2026-11-21 扩到 130+ 复合词，补入学位论文/公文/技术文档/法律文书/教案/期刊论文等文体词）经 `skill-trigger.js` 正则匹配后 nudge；无该表消费者的平台，改由 front-matter `description` 的触发分支随技能清单常驻，靠语义匹配命中。

**唯一例外**：用户明确指定其他格式、给出自定义模板或具体排版要求时，以用户要求为准。

## 已知限制

- 公文/法律/学位论文的**封面、发文机关标志、红色分隔线、印章、成文日期位置、原创性声明页、页眉章名、罗马数字前置页码**不由脚本生成，需按单位模板人工处理；v2.2 起可用 `--base-template` 把正文灌进含这些部件的模板，但模板本身仍要人工准备。脚本只保证正文版式与层次序数合规。
- `social-media` profile 的平台限流词、`press-release` 的禁用词与慎用词、法律与财经文书的实体条款合规性，脚本不做词表扫描，需人工对照规范库核校。
- 规范库中 `low` 置信度条目（10 条）来自二手转述、口径存疑，不作为排版依据。用 `python scripts/query_standards.py --audit` 可查看置信度分布与不可依据条目清单：当前 490 条中 `source` 字段全空、172 条无标准号且非 high 置信度，这些只能当写作提示，不能当排版依据。
- `required_sections` 只做关键词存在性匹配，不判章节顺序、层级正确性与内容质量；同名词出现在正文任意位置也会算命中。
- 底模注入的 `--keep-until` 用的是「段落文本包含匹配」，模板里若有多个段落含同一文字，取第一个匹配项。
