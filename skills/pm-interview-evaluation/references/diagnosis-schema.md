# Diagnosis Schema

The normalized review returns `schema_version: "2.1"` and keeps legacy fields. Version `2.0` and older records remain readable; missing provenance is represented as `legacy_unknown`.

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

The normalized review also contains an `action_plan` array. Each action has a stable
`id`/`action_key`, a bounded training lifecycle, and explicit origin metadata:

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

`action_key` is deterministic for the same source IDs or action text. When a review is
regenerated, the store keeps the existing action ID, attempts, acceptance state, note and
completion time while allowing the new diagnosis text to replace the old text. If an older
record has no action key, the store uses a bounded text signature as a migration fallback.
This prevents a model rerun from breaking the `diagnosis -> practice -> validation` chain.

The server emits all six controlled PM skills in catalog order. A skill or dimension that was not
covered has `score: null`, `exact_score: null` at skill level, `status: "missing"`, and an explicit
low-confidence explanation; a `missing` dimension's model-supplied score is discarded and it is not
silently converted into a 1. A V2 skill-level score is never
used to replace a missing weighted-dimension calculation. Legacy records without dimensions remain
readable and retain their historical skill score for compatibility, but are marked by their legacy
provenance and are not treated as newly comparable evidence.

Each `action_plan` item also carries `training_progress` and `attempts`. An attempt has a bounded
`phase` (`pre_test`, `rewrite`, or `post_test`), the user's response, optional self-score, criteria
and note. The local store enforces `pre_test -> rewrite -> post_test`; the API rejects `passed`
until a `post_test` exists. These records are training evidence, not hiring scores.

At interview-record level, `outcome` is an optional self-reported value: `passed`, `failed`, `pending`, or an empty string. It is training feedback only. Long-term memory shows descriptive outcome groups after 4 records and a more stable direction only after 6 records with at least 2 records in each group; it never predicts hiring.

Long-term memory also exposes `comparability`, `mixed_scoring`, `scoring_providers`, and `scoring_models`. Trends are marked non-comparable when model/rubric metadata is mixed or missing.

The server validates IDs against the catalog, clamps scores to 1–5, caps list lengths and text lengths, verifies quotes against the transcript when available, and lowers confidence when evidence is absent. `evidence_profile` separately evaluates specificity, personal ownership, causality, result quality, reflection, and resilience under follow-up questions. Legacy string `next_practice` is preserved while a normalized `practice_plan` is added.

Research context is separate from interview evidence. A public-source assessment may contain up to four `question_leads`, each with `question`, `topic`, `evidence`, and `evidence_status`. Prompt context also exposes `status`, `citation_allowed`, and `source_role`: only human-confirmed `approved` sources have `citation_allowed: true`; `auto_approved`, candidates, and unverified sources are `question_lead_only`. Only verified excerpts may carry evidence; these leads can shape the next question, but cannot support a score or rewrite what happened in the interview. When an interview is saved, its bounded research snapshot preserves the query, relevance breakdown, source status, assessment summary and lead topics, while excluding raw public excerpts.
