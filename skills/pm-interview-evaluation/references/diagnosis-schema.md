# 诊断 Schema

归一化后的复盘返回 `schema_version: "2.1"`，并保留旧字段。`2.0` 及更早版本的数据仍可读取；缺失的来源信息用 `legacy_unknown` 表示。

```json
{
  "schema_version": "2.1",
  "scored_by": {"provider": "gemini", "model": "gemini-3.1-flash-lite", "prompt_version": "2.1", "rubric_version": "pm-rubric-2.0", "scored_at": "2026-09-18T10:00:00+00:00"},
  "score_summary": {"coach_score": 68, "score_scale": 100, "strongest_skill": "story_ownership", "priority_skills": ["metrics_experiment"], "training_band": "需要针对性训练"},
  "review_quality": {"transcript_chars": 420, "answered_questions": 4, "evidence_coverage": 0.78, "confidence": "medium", "data_quality": "部分结果缺少量化证据"},
  "skill_diagnosis": [{
    "skill_id": "metrics_experiment", "score": 2, "exact_score": 2.1, "confidence": "high", "anchor_match": 2,
    "evidence_profile": {"specificity": 1, "ownership": 2, "causality": 1, "result_quality": 0, "reflection": 0, "probe_resilience": 1},
    "dimensions": [{"id": "attribution", "label": "归因意识", "weight": 30, "score": 2, "status": "observed", "evidence": "原文", "rationale": "评分原因"}],
    "gaps": [{"gap_id": "metrics_experiment__attribution", "severity": "high", "evidence": "原文", "impact": "影响"}],
    "diagnosis": "结论",
    "next_practice": "重写一次指标定义",
    "practice_plan": {"action": "重写一次指标定义", "prompt": "如何验证归因？", "success_criteria": ["定义指标", "说明假设", "给出验证"], "follow_up_question": "如果指标不变怎么办？"}
  }]
}
```

归一化后的复盘还包含 `action_plan` 数组。每个行动项都有稳定的
`id`/`action_key`、有边界的训练生命周期和明确的来源元数据：

```json
{
  "action_plan": [{
    "id": "action-4c8d...",
    "action_key": "action-4c8d...",
    "action": "重写指标归因段落",
    "priority": "高",
    "reason": "本场缺少因果验证",
    "success_criteria": ["定义核心指标", "说明验证方法"],
    "next_validation": "下一场先说指标口径",
    "source_skill_ids": ["metrics_experiment"],
    "source_gap_ids": ["metrics_experiment__attribution"],
    "source_interview_id": "interview-id",
    "source_interview_date": "2026-09-18",
    "source_company": "示例公司",
    "source_role": "产品经理",
    "source_round_name": "一面",
    "done": false,
    "completed_at": "",
    "acceptance_status": "pending",
    "acceptance_note": "",
    "training_progress": {"pre_test": false, "rewrite": false, "post_test": false, "attempt_count": 0},
    "attempts": []
  }]
}
```

对于相同的来源 ID 或行动文本，`action_key` 必须确定性生成。重新生成复盘时，数据存储会保留已有的行动 ID、训练尝试、验收状态、备注和完成时间，同时允许新的诊断文本替换旧文本。旧记录如果没有 action key，则使用有长度上限的文本签名作为迁移兜底。
这样可以避免模型重跑破坏 `diagnosis -> practice -> validation` 训练链路。

服务端按目录顺序输出六项受控 PM 能力。未覆盖的能力或子维度会得到 `score: null`、能力层 `exact_score: null`、`status: "missing"` 和明确的低置信度说明；缺失子维度的模型分数会被丢弃，不能静默转换为 1 分。V2 能力层分数不能替代缺失的加权子维度计算。没有子维度的旧记录仍可读取，并保留历史能力分以兼容旧数据，但会标记为旧来源，不能被当成新证据直接比较。

每个 `action_plan` 还带有 `training_progress` 和 `attempts`。一次训练尝试包含有边界的 `phase`（`pre_test`、`rewrite` 或 `post_test`）、用户回答、可选自评、验收标准和备注。本地存储强制执行 `pre_test -> rewrite -> post_test` 顺序；没有 `post_test` 时，API 拒绝将行动标记为 `passed`。这些记录是训练证据，不是招聘分数。

在面试记录层，`outcome` 是可选的用户自报值：`passed`、`failed`、`pending` 或空字符串。它只表示训练反馈。长期记忆在 4 场记录后才展示描述性结果分组，至少 6 场且每组至少 2 场后才展示更稳定的方向性观察；它永远不预测招聘结果。

长期记忆还会暴露 `comparability`、`mixed_scoring`、`scoring_providers` 和 `scoring_models`。模型或 rubric 元数据混用或缺失时，趋势会标记为不可直接比较。

服务端会根据能力目录校验 ID，将分数限制在 1–5，限制列表和文本长度，并在有转写时核对引用；证据缺失时降低置信度。`evidence_profile` 会独立评估具体性、个人归因、因果意识、结果质量、复盘迁移和追问韧性。旧的字符串 `next_practice` 会保留，同时新增归一化的 `practice_plan`。

研究上下文与面试证据严格分开。公开来源预审最多包含四条 `question_leads`，每条包含 `question`、`topic`、`evidence` 和 `evidence_status`。Prompt 上下文还会暴露 `status`、`citation_allowed` 和 `source_role`：只有人工确认的 `approved` 来源允许 `citation_allowed: true`；`auto_approved`、candidate 和未核实来源只能作为 `question_lead_only`。只有已核实摘录才能携带证据；这些线索可以影响下一道问题，但不能支撑分数，也不能改写面试中实际发生的事情。保存面试时，受限研究快照会保留查询、相关度拆解、来源状态、预审摘要和线索主题，但排除公开原帖正文。
