# PM 能力评分规则

六项能力保持稳定。每项能力包含四个可观察子维度，权重合计 100%。字段 ID 保持英文，便于后端校验和旧数据兼容。

| 能力 ID | 中文能力 | 子维度与权重 |
| --- | --- | --- |
| `product_sense` | 产品判断 | `user_problem` 用户问题 30、`goal_definition` 目标定义 20、`tradeoff` 方案取舍 30、`prioritization` 优先级 20 |
| `story_ownership` | 项目主导力 | `scope` 职责边界 30、`decision` 关键决策 30、`collaboration` 协作推进 15、`result_learning` 结果与复盘 25 |
| `metrics_experiment` | 指标与实验 | `definition` 指标定义 25、`decomposition` 指标拆解 20、`attribution` 归因意识 30、`experiment_quantify` 实验与量化 25 |
| `execution_collaboration` | 推进与协作 | `planning` 计划推进 25、`alignment` 目标对齐 25、`resource_tradeoff` 资源取舍 20、`closure` 结果闭环 30 |
| `structured_communication` | 结构化表达 | `structure` 信息结构 30、`directness` 结论先行 20、`precision` 表达精确度 25、`probe_response` 追问应对 25 |
| `business_context` | 业务与岗位理解 | `jd_link` JD 连接 30、`user_business` 用户与业务 25、`market_context` 市场场景 20、`role_fit` 岗位匹配 25 |

## 评分锚点

- `1`：没有展示相关行为，或回答与问题明显不匹配。
- `2`：提到了相关点，但缺少关键定义、动作、取舍或结果。
- `3`：案例基本完整，但有一个重要环节没有闭环。
- `4`：行为具体且能解释取舍，只有少量细节缺口。
- `5`：证据完成闭环，连接了用户/业务、决策、指标、结果和复盘。

只有在转写支持中间行为时，才允许在 2 和 4 之间插值。缺失子维度不能默认给 3 分。
