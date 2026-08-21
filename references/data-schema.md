# 研究包数据结构

标准研究包包含 `report.md`、`data.csv`、`evidence.csv`，有确定性计算时增加输入文件 `calculations.json` 和输出文件 `calculation-results.json`。所有文件使用 UTF-8；CSV 推荐使用 UTF-8 with BOM，以便中文 Excel 兼容。

## report.md

关键定量结论使用指标标记：

```markdown
2025 年目标市场规模为 128 亿元，同比增长 9.4% [M001][M002]。
```

指标标记必须能在 `data.csv` 中找到。年份、章节编号和来源发布日期不需要指标标记；影响结论的金额、比例、数量、工资、营收、利润和预测需要标记。

## data.csv

每个最终指标一行，`metric_id` 唯一。

| 字段 | 必填 | 说明 |
|---|---|---|
| `metric_id` | 是 | `M` 加至少三位数字，如 `M001` |
| `metric_name` | 是 | 清晰指标名称 |
| `value` | 条件 | 数值或简短区间；不可获得时留空 |
| `unit` | 条件 | 元、亿元、%、人、家等 |
| `geography` | 条件 | 指标适用地区 |
| `data_period` | 条件 | 年、季度、财年或截至日期 |
| `definition` | 是 | 分母、范围和关键口径 |
| `evidence_type` | 是 | `direct`、`calculated`、`estimated`、`unavailable` |
| `confidence` | 是 | `A`、`B`、`C`、`D` |
| `calculation_operation_id` | 条件 | 数值计算对应的脚本 operation ID |
| `calculation_result_path` | 条件 | 结果文件中的路径，如 `result.percent` |
| `notes` | 否 | 修订、限制或展示说明 |

除 `unavailable` 外，`value`、`unit`、`geography` 和 `data_period` 必填。数值型 `calculated` 或 `estimated` 指标应填写计算映射；严格校验会把缺少映射视为失败，并核对 `data.csv` 的值是否等于 `calculation-results.json` 中的结果。

## evidence.csv

一项指标可对应多条证据，因此 `metric_id` 可以重复，`record_id` 必须唯一。

| 字段 | 必填 | 说明 |
|---|---|---|
| `record_id` | 是 | `E` 加至少三位数字 |
| `metric_id` | 是 | 对应 `data.csv` |
| `source_title` | 条件 | 来源标题；直接证据必填 |
| `publisher` | 条件 | 发布机构；直接证据必填 |
| `url` | 条件 | `http` 或 `https` URL；直接证据必填 |
| `publication_date` | 否 | 来源发布日期 |
| `accessed_date` | 条件 | 网络来源访问日期 |
| `source_location` | 否 | 页码、表号、章节或段落 |
| `source_metric_ids` | 条件 | 计算或估算输入，使用分号分隔 |
| `calculation_formula` | 条件 | 计算或估算公式 |
| `assumptions` | 条件 | 估算关键假设 |
| `notes` | 否 | 转载关系、限制和冲突说明 |

规则：

- `direct` 指标至少有一条包含标题、发布者、URL 和访问日期的证据。
- `calculated` 指标必须记录 `source_metric_ids` 和 `calculation_formula`。
- `estimated` 指标必须记录 `source_metric_ids`、`calculation_formula` 和 `assumptions`。
- `unavailable` 指标在 `notes` 中记录搜索范围和缺失原因。

证据类型和可信度保存在 `data.csv`，避免多来源行产生矛盾等级。

## calculations.json

供 `scripts/calculate_market_metrics.py` 使用：

```json
{
  "schema_version": "1.0",
  "operations": [
    {
      "id": "market_cagr",
      "type": "cagr",
      "start_value": 100,
      "end_value": 146.41,
      "periods": 4
    },
    {
      "id": "brand_share",
      "type": "market_share",
      "market_total": 1000,
      "top_n_complete": 2,
      "entities": [
        {"name": "品牌 A", "value": 260},
        {"name": "品牌 B", "value": 180}
      ]
    }
  ]
}
```

支持的操作类型：

- `cagr`
- `market_share`
- `margin`
- `product`：自上而下或自下而上乘法，输入为带名称的非负因子
- `summary`
- `scenario_forecast`

脚本输出包含输入回显和计算结果，保存为 `calculation-results.json`。报告指标通过 `data.csv` 关联最终采用的结果。

`market_share.top_n_complete` 表示输入已完整覆盖前 N 名品牌。省略时，市场覆盖不完整的 CR3/CR5/CR10 只输出 `known_lower_bound`；只有全市场覆盖或已明确覆盖相应前 N 名时才输出正式 CRn。

## research-matrix（可选工作文件）

检索矩阵用于管理过程，不属于强制交付物。需要保留时可使用 Markdown 或 CSV，字段至少包括：`research_question`、`metric`、`geography_period`、`preferred_primary_source`、`cross_source`、`status`、`notes`。状态限定为 `待检索`、`已获得`、`口径冲突`、`需估算`、`不可获得`。
