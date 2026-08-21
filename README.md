# industry-market-research（行业市场调研 Skill）

![status](https://img.shields.io/badge/status-v1.0-blue)
![language](https://img.shields.io/badge/language-简体中文优先-green)
![evidence](https://img.shields.io/badge/research-证据可追溯-brightgreen)
![output](https://img.shields.io/badge/output-Markdown%20%7C%20PDF%20%7C%20CSV-orange)
![agents](https://img.shields.io/badge/agents-Claude%20Code%20%7C%20Codex%20%7C%20WorkBuddy-grey)

面向 Claude Code、Codex 与 WorkBuddy 的开源行业市场调研 Skill：采集和分析公开互联网数据，生成**有来源、可复算、可审查**的行业或细分市场报告，并在 PDF 前部的核心结论后附上核心指标信息图。

它适合市场规模、区域发展、品牌份额、竞争格局、发展趋势、工资、营收和利润分析。它不是证券研究终端，也不会绕过付费墙、登录、验证码或访问限制；证据不足时会明确降级可信度或标记“无可靠公开数据”。

## 设计理念

**事实有出处，计算可复算，估算有边界，结论能复核。**

- 事实、计算、估算和判断分开表达，不把模型推断伪装成公开披露。
- 每个关键定量结论使用 `[Mxxx]` 指标标记，并连接到数据表与证据台账。
- CAGR、份额、集中度和情景测算由确定性脚本执行，不在正文中手算关键指标。
- 优先采用政府、监管机构、国际组织、行业协会和公司定期报告，并识别转载关系。
- 市场口径、期间、地域、单位、币种和分母不一致时分别呈现，不做简单平均。
- 信息图只压缩报告已有的 A—C 级指标，不新增未经证据支持的数字或预测。

## ✅ 会做的 / ⛔ 不做的

| ✅ 会做的 | ⛔ 不做的 |
| --- | --- |
| 调研市场规模、历史增长、区域与竞争格局 | 输出证券买卖、持仓或估值建议 |
| 比较企业营收、利润率、工资与就业指标 | 绕过登录、付费墙、验证码或网站条款 |
| 建立 `data.csv` 与 `evidence.csv` 证据链 | 把新闻转载当成独立交叉来源 |
| 计算 CAGR、CRn、HHI、利润率与情景区间 | 混用品牌、公司、集团或业务分部口径 |
| 生成 Markdown、PDF 和核心指标信息图 | 用集团利润冒充品牌利润 |
| 为现成 PDF 追加可核验的信息图页 | 在证据不足时编造精确市场份额或预测 |

## 你会拿到什么

标准研究包默认写入 `market-research/<主题>-<日期>/`：

| 文件 | 用途 |
| --- | --- |
| `report.md` | 完整报告；关键数字带 `[Mxxx]` 标记 |
| `report.pdf` | 可交付 PDF；核心结论后附信息图 |
| `core-metrics-infographic.png` | 5—8 个核心指标的可视化摘要 |
| `data.csv` | 最终指标、定义、期间、地域、证据类型与可信度 |
| `evidence.csv` | 来源、URL、原文位置与计算链路台账 |
| `calculations.json` | 确定性计算输入；无计算时可省略 |
| `calculation-results.json` | 计算脚本输出；无计算时可省略 |

如果输入的是现成 PDF，原文件不会被覆盖；默认输出 `<原文件名>-with-infographic.pdf`，并另存信息图源文件。

## 快速开始

安装完成后，直接告诉代理研究对象即可：

```text
使用 $industry-market-research 调研中国连锁超市零售业，市场口径采用商品销售额，
覆盖最近 5 个完整年度，并输出标准研究包和带核心指标信息图的 PDF。
```

也可以处理已有报告：

```text
使用 $industry-market-research 读取这份 PDF 调研报告，提取报告中已有的核心指标，
在核心结论后追加一页信息图；保留原文件，不补充外部数据。
```

## 安装

这是一个独立 Skill 仓库。将仓库完整克隆到对应宿主的用户级 Skills 目录；不要只复制 `SKILL.md`，`scripts/` 与 `references/` 也是运行所需内容。

### Codex

```text
帮我把 https://github.com/cxtx/industry-market-research 安装到
~/.codex/skills/industry-market-research，并保留仓库内的 SKILL.md、agents/、
scripts/、references/ 和 tests/。同名目录存在时先告诉我将覆盖哪些文件，安装后验证 Skill。
```

### Claude Code

```text
帮我把 https://github.com/cxtx/industry-market-research 安装到
~/.claude/skills/industry-market-research，并完整保留仓库目录结构。安装后验证 Skill。
```

### WorkBuddy

```text
帮我把 https://github.com/cxtx/industry-market-research 安装到
~/.workbuddy/skills/industry-market-research，并完整保留仓库目录结构。安装后验证 Skill。
```

安装或更新后请新开一个会话，让宿主重新加载 Skill。项目级安装时，把目标路径替换为该宿主在项目根目录下的 Skills 目录。

## 工作方式

```text
锁定行业、地域与市场口径
          ↓
建立指标清单与检索矩阵
          ↓
采集公开证据并记录原文位置
          ↓
统一口径、交叉验证、确定性计算
          ↓
生成报告、数据表、证据台账与信息图
          ↓
结构校验 + 原始来源抽查 + PDF 逐页检查
```

可信度分为 A—D：A、B、C 可用于执行摘要，D 只作线索或缺口记录。结构校验能发现文件、字段和引用链错误，但不能自动证明网页内容真实或来源相互独立，因此交付前仍要求人工打开核心来源复核。

## 确定性计算与校验

从研究包目录运行：

```text
python <skill-dir>/scripts/calculate_market_metrics.py calculations.json -o calculation-results.json
python <skill-dir>/scripts/validate_research_package.py . --strict --require-pdf-visual
```

`calculate_market_metrics.py` 支持 CAGR、市场份额、CRn、HHI、利润率、加权平均和情景计算。`validate_research_package.py` 检查指标标记、证据链、计算结果关联、可信度约束，以及 PDF/PNG 是否存在且信息图位于执行摘要章节内。

## 仓库结构

| 路径 | 用途 |
| --- | --- |
| [`SKILL.md`](SKILL.md) | Skill 入口、核心工作流与不可破坏的证据规则 |
| [`agents/`](agents/) | 宿主 UI 展示与默认调用提示 |
| [`references/`](references/) | 范围锁定、指标定义、证据政策、估算方法、数据结构与报告模板 |
| [`scripts/`](scripts/) | 确定性计算和研究包校验脚本 |
| [`tests/`](tests/) | 计算与校验器测试 |

## 开发与验证

脚本仅使用 Python 标准库。运行全部测试：

```text
python -m unittest discover -s tests -v
```

检查 Skill 结构：

```text
python <skill-creator-dir>/scripts/quick_validate.py .
```

## 已知边界

- 公开数据覆盖度因行业、地域和年份而异；报告会保留缺口，不承诺每个指标都能获得。
- 公司财报通常披露集团或业务分部，不一定能支持品牌级利润结论。
- 招聘样本工资不等于官方行业平均工资，两者会分开呈现。
- 预测是带假设的情景结果，不是确定事实。
- 现成 PDF 模式只使用报告及用户提供的证据；除非用户明确要求，不自动补充外部调研。

## 安全与合规

本 Skill 面向公开互联网资料，不应上传机密、个人敏感信息或无权处理的数据。不绕过网站限制，不批量采集个人信息，并尊重来源的访问条件。生成内容用于研究与决策支持，不构成证券投资、法律、税务或会计专业建议。
