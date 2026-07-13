# Diagnosis Schema

The normalized review returns `schema_version: "2.0"` and keeps legacy fields.

```json
{
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

The server validates IDs against the catalog, clamps scores to 1–5, caps list lengths and text lengths, verifies quotes against the transcript when available, and lowers confidence when evidence is absent. `evidence_profile` separately evaluates specificity, personal ownership, causality, result quality, reflection, and resilience under follow-up questions. Legacy string `next_practice` is preserved while a normalized `practice_plan` is added.
