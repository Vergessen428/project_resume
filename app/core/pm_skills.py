"""Explicit PM coaching rubrics used by review and long-term memory."""

import hashlib
import re
from typing import Any, Dict, List


PM_SKILLS: List[Dict[str, str]] = [
    {
        "id": "product_sense",
        "name": "产品判断",
        "focus": "用户问题、目标定义、方案取舍与优先级。",
    },
    {
        "id": "story_ownership",
        "name": "项目主导力",
        "focus": "个人职责边界、关键动作、结果与复盘，而非团队泛泛叙述。",
    },
    {
        "id": "metrics_experiment",
        "name": "指标与实验",
        "focus": "指标定义、拆解、归因、实验设计和量化结果。",
    },
    {
        "id": "execution_collaboration",
        "name": "推进与协作",
        "focus": "跨团队分歧、资源约束、风险取舍和落地闭环。",
    },
    {
        "id": "structured_communication",
        "name": "结构化表达",
        "focus": "结论先行、信息层次、追问应对与表达简洁度。",
    },
    {
        "id": "business_context",
        "name": "业务与岗位理解",
        "focus": "将个人经历连接到 JD、公司业务和具体岗位场景。",
    },
]

ROLE_FAMILIES = {
    "ai_product": {"ai", "人工智能", "大模型", "aigc", "智能体", "算法产品", "ai产品"},
    "general_product": {"产品经理", "产品岗", "用户产品", "产品设计"},
    "growth": {"增长", "用户增长", "商业化", "运营增长"},
    "b2b": {"b2b", "企业服务", "saas", "to b", "客户成功"},
    "platform": {"平台", "中台", "基础平台", "开放平台"},
    "data_strategy": {"数据产品", "数据策略", "分析", "数仓", "bi"},
    "operations": {"运营", "内容产品", "社区", "活动运营"},
}


def derive_role_family(role: str = "", analysis: Dict[str, Any] = None) -> str:
    """Return a conservative finite role family; empty means not inferable."""
    analysis = analysis if isinstance(analysis, dict) else {}
    text = " ".join(
        str(value)
        for value in (role, analysis.get("role_title", ""), analysis.get("keywords", []))
    ).strip().lower()
    if not text:
        return ""
    for family, keywords in ROLE_FAMILIES.items():
        if any(keyword.lower() in text for keyword in keywords):
            return family
    if "产品" in text or "product" in text:
        return "general_product"
    # Unknown is intentionally left empty so validation cannot bind two
    # unrelated interviews merely because their free-text roles match.
    return ""


def normalise_jd_profile(
    job_description: str = "",
    analysis: Dict[str, Any] = None,
    role: str = "",
    existing: Dict[str, Any] = None,
) -> Dict[str, Any]:
    """Build the small shared JD contract without adding another service."""
    analysis = analysis if isinstance(analysis, dict) else {}
    existing = existing if isinstance(existing, dict) else {}
    jd = str(job_description or "").strip()
    jd_hash = hashlib.sha256(jd.encode("utf-8")).hexdigest()[:24] if jd else ""
    role_family = str(existing.get("role_family", "") or analysis.get("role_family", "")).strip()
    if role_family not in set(ROLE_FAMILIES) | {"other"}:
        role_family = derive_role_family(role, analysis)

    source_items = []
    for key in ("requirements", "responsibilities", "interview_focus", "keywords"):
        values = analysis.get(key) if isinstance(analysis.get(key), list) else []
        source_items.extend(str(item).strip() for item in values if str(item).strip())
    text = " ".join(source_items + [jd]).lower()
    capability_hints = {
        "metrics_experiment": ("指标", "数据", "实验", "归因", "量化", "验证"),
        "execution_collaboration": ("协作", "推进", "跨团队", "项目", "落地", "资源"),
        "product_sense": ("用户", "需求", "产品", "方案", "优先级", "场景"),
        "structured_communication": ("结构化", "拆解", "表达", "沟通", "分析"),
        "business_context": ("业务", "市场", "行业", "岗位", "商业"),
        "story_ownership": ("负责", "主导", "项目", "结果", "复盘"),
    }
    expected = {
        "metrics_experiment": ["指标定义", "归因", "验证方法"],
        "execution_collaboration": ["个人推进动作", "分歧处理", "落地结果"],
        "product_sense": ["用户问题", "目标定义", "方案取舍"],
        "structured_communication": ["结论先行", "结构化拆解", "追问应对"],
        "business_context": ["业务目标", "岗位连接", "结果影响"],
        "story_ownership": ["个人职责", "关键决策", "结果复盘"],
    }
    core = []
    existing_core = existing.get("core_capabilities") if isinstance(existing.get("core_capabilities"), list) else []
    for item in existing_core:
        if not isinstance(item, dict) or str(item.get("skill_id", "")) not in PM_SKILL_DIMENSIONS:
            continue
        skill_id = str(item["skill_id"])
        core.append({
            "skill_id": skill_id,
            "importance": str(item.get("importance", "should_have")) if str(item.get("importance", "")) in {"must_have", "should_have"} else "should_have",
            "jd_evidence": str(item.get("jd_evidence", ""))[:500],
            "evidence_expected": [str(value)[:120] for value in item.get("evidence_expected", []) if str(value).strip()][:5],
        })
    if not core:
        for skill_id, keywords in capability_hints.items():
            if any(keyword in text for keyword in keywords):
                core.append({
                    "skill_id": skill_id,
                    "importance": "must_have" if skill_id in {"metrics_experiment", "product_sense"} else "should_have",
                    "jd_evidence": next((item for item in source_items if any(keyword in item.lower() for keyword in keywords)), "" )[:500],
                    "evidence_expected": expected[skill_id],
                })
    if not core and jd:
        core = [{
            "skill_id": "product_sense",
            "importance": "should_have",
            "jd_evidence": "JD 信息不足，暂以通用产品判断作为准备入口。",
            "evidence_expected": expected["product_sense"],
        }]
    topics = []
    for key in ("question_topics", "interview_focus", "search_topics", "search_synonyms"):
        values = existing.get(key) if key in existing else analysis.get(key)
        if isinstance(values, list):
            topics.extend(str(item).strip()[:160] for item in values if str(item).strip())
    topics = list(dict.fromkeys(topics))[:12]
    return {
        "profile_version": "jd-profile-1.0",
        "jd_hash": jd_hash,
        "role_family": role_family,
        "core_capabilities": core[:6],
        "question_topics": topics[:8],
        "search_topics": topics[:8],
    }

# Each PM skill is scored through four observable signals. The model may describe
# the signal, but the backend owns the IDs and weights so scores remain comparable
# across reviews and across the long-term memory view.
PM_SKILL_DIMENSIONS: Dict[str, List[Dict[str, Any]]] = {
    "product_sense": [
        {"id": "user_problem", "label": "用户问题", "weight": 30},
        {"id": "goal_definition", "label": "目标定义", "weight": 20},
        {"id": "tradeoff", "label": "方案取舍", "weight": 30},
        {"id": "prioritization", "label": "优先级判断", "weight": 20},
    ],
    "story_ownership": [
        {"id": "scope", "label": "职责边界", "weight": 30},
        {"id": "decision", "label": "关键决策", "weight": 30},
        {"id": "collaboration", "label": "协作推进", "weight": 15},
        {"id": "result_learning", "label": "结果复盘", "weight": 25},
    ],
    "metrics_experiment": [
        {"id": "definition", "label": "指标定义", "weight": 25},
        {"id": "decomposition", "label": "指标拆解", "weight": 20},
        {"id": "attribution", "label": "归因意识", "weight": 30},
        {"id": "experiment_quantify", "label": "实验与量化", "weight": 25},
    ],
    "execution_collaboration": [
        {"id": "planning", "label": "计划与风险", "weight": 25},
        {"id": "alignment", "label": "跨团队对齐", "weight": 25},
        {"id": "resource_tradeoff", "label": "资源取舍", "weight": 20},
        {"id": "closure", "label": "落地闭环", "weight": 30},
    ],
    "structured_communication": [
        {"id": "structure", "label": "表达结构", "weight": 30},
        {"id": "directness", "label": "结论先行", "weight": 20},
        {"id": "precision", "label": "信息精确度", "weight": 25},
        {"id": "probe_response", "label": "追问应对", "weight": 25},
    ],
    "business_context": [
        {"id": "jd_link", "label": "JD 连接", "weight": 30},
        {"id": "user_business", "label": "用户与业务", "weight": 25},
        {"id": "market_context", "label": "市场语境", "weight": 20},
        {"id": "role_fit", "label": "岗位适配", "weight": 25},
    ],
}

DIAGNOSTIC_STATUSES = {"observed", "missing", "contradicted", "not_applicable", "unverified"}

EVIDENCE_PROFILE_FIELDS = {
    "specificity": "是否有具体场景、对象、时间或数字",
    "ownership": "是否能区分个人动作与团队动作",
    "causality": "是否说明判断依据、因果假设或验证方式",
    "result_quality": "是否有口径清楚的结果和影响",
    "reflection": "是否能说明复盘、边界和下一次调整",
    "probe_resilience": "面对追问是否补充完整而不改口或跳题",
}


# Controlled vocabulary of recurring weakness tags, so long-term memory can count
# "the same problem" across interviews even when the model phrases the title differently.
# id is globally unique via "<skill_id>__<slug>". Anything the model cannot map lands on "other".
PM_GAP_TAGS: List[Dict[str, str]] = [
    {"id": "product_sense__user_problem", "skill_id": "product_sense", "name": "用户问题定义不清"},
    {"id": "product_sense__tradeoff", "skill_id": "product_sense", "name": "方案取舍/优先级薄弱"},
    {"id": "story_ownership__scope", "skill_id": "story_ownership", "name": "个人职责边界模糊"},
    {"id": "story_ownership__result", "skill_id": "story_ownership", "name": "结果与复盘缺失"},
    {"id": "metrics_experiment__definition", "skill_id": "metrics_experiment", "name": "指标定义/口径不清"},
    {"id": "metrics_experiment__attribution", "skill_id": "metrics_experiment", "name": "缺乏归因意识"},
    {"id": "metrics_experiment__quantify", "skill_id": "metrics_experiment", "name": "结果缺乏量化"},
    {"id": "execution_collaboration__conflict", "skill_id": "execution_collaboration", "name": "跨团队分歧处理弱"},
    {"id": "execution_collaboration__closure", "skill_id": "execution_collaboration", "name": "落地闭环不完整"},
    {"id": "structured_communication__structure", "skill_id": "structured_communication", "name": "表达缺乏结构/结论后置"},
    {"id": "structured_communication__probe", "skill_id": "structured_communication", "name": "追问应对不稳"},
    {"id": "business_context__jd_link", "skill_id": "business_context", "name": "经历与岗位/业务脱节"},
]

GAP_TAG_OTHER = "other"

# Behaviourally anchored rating scale (BARS): explicit 1/3/5 anchors per skill so the
# model rates against a stable reference instead of an ungrounded "give a 1-5".
PM_SCORE_ANCHORS: Dict[str, Dict[int, str]] = {
    "product_sense": {
        1: "说不清用户是谁、要解决什么问题。",
        3: "能描述用户问题，但目标定义和方案取舍较模糊。",
        5: "能清晰定义用户问题、目标与优先级，并解释取舍理由。",
    },
    "story_ownership": {
        1: "只讲团队做了什么，看不出个人贡献。",
        3: "能说出个人动作，但职责边界或结果复盘不完整。",
        5: "清楚界定个人职责、关键决策、结果与复盘。",
    },
    "metrics_experiment": {
        1: "完全无指标意识，只讲功能不讲衡量。",
        3: "能说出指标，但讲不清口径与归因。",
        5: "能定义北极星+护栏指标，并说清归因与验证方式。",
    },
    "execution_collaboration": {
        1: "回避分歧，说不清如何推进。",
        3: "能描述协作过程，但风险取舍或闭环不清。",
        5: "能讲清跨团队分歧、资源约束下的取舍与落地闭环。",
    },
    "structured_communication": {
        1: "表达发散、无结论、抓不住重点。",
        3: "基本有条理，但结论后置或追问应对不稳。",
        5: "结论先行、层次清晰、追问应对沉稳简洁。",
    },
    "business_context": {
        1: "经历与岗位、业务完全脱节。",
        3: "能关联到岗位，但对业务场景理解偏浅。",
        5: "能把个人经历精准连接到 JD、公司业务和具体岗位场景。",
    },
}

PM_SCORE_GUIDE: Dict[int, str] = {
    1: "未展示：没有可核对的行为或理解，或回答与问题明显不匹配。",
    2: "偏弱：提到相关点，但缺少关键定义、个人动作、取舍或结果。",
    3: "合格：能给出基本完整的例子和判断，但仍有一处重要环节不完整。",
    4: "较强：行为具体，能解释取舍、协作和结果，只有少量细节缺口。",
    5: "优秀：证据具体且闭环，能连接用户/业务、指标、取舍、结果和复盘。",
}


def prompt_rubric() -> str:
    return "\n".join("- %s (%s): %s" % (item["id"], item["name"], item["focus"]) for item in PM_SKILLS)


def dimension_prompt() -> str:
    lines = []
    for skill in PM_SKILLS:
        dimensions = PM_SKILL_DIMENSIONS[skill["id"]]
        rendered = "; ".join(
            "%s=%s（%s%%）" % (item["id"], item["label"], item["weight"])
            for item in dimensions
        )
        lines.append("- %s（%s）: %s" % (skill["id"], skill["name"], rendered))
    return "\n".join(lines)


def evidence_profile_prompt() -> str:
    return "; ".join("%s=%s（0-3）" % (key, label) for key, label in EVIDENCE_PROFILE_FIELDS.items())


def public_skills() -> List[Dict[str, Any]]:
    return [
        {
            "id": item["id"],
            "name": item["name"],
            "focus": item["focus"],
            "dimensions": [dict(dimension) for dimension in PM_SKILL_DIMENSIONS[item["id"]]],
            "score_anchors": {str(level): text for level, text in PM_SCORE_ANCHORS[item["id"]].items()},
            "score_guide": {str(level): text for level, text in PM_SCORE_GUIDE.items()},
        }
        for item in PM_SKILLS
    ]


def gap_tag_ids() -> set:
    """All valid canonical_gap_id values, including the "other" fallback."""
    return {tag["id"] for tag in PM_GAP_TAGS} | {GAP_TAG_OTHER}


def canonicalize_gap_id(value: Any) -> str:
    """Force any model-provided gap id back into the controlled vocabulary."""
    text = str(value or "").strip()
    return text if text in gap_tag_ids() else GAP_TAG_OTHER


def gap_tags_prompt() -> str:
    """Render the controlled weakness tags for the review prompt."""
    skill_names = {item["id"]: item["name"] for item in PM_SKILLS}
    lines = [
        "- %s: %s（属于「%s」）" % (tag["id"], tag["name"], skill_names.get(tag["skill_id"], tag["skill_id"]))
        for tag in PM_GAP_TAGS
    ]
    lines.append("- %s: 归不进以上任何一类时使用" % GAP_TAG_OTHER)
    return "\n".join(lines)


def anchors_prompt() -> str:
    """Render the 1/3/5 behaviour anchors for the review prompt."""
    skill_names = {item["id"]: item["name"] for item in PM_SKILLS}
    blocks = []
    for skill_id, anchors in PM_SCORE_ANCHORS.items():
        header = "%s (%s):" % (skill_id, skill_names.get(skill_id, skill_id))
        levels = "; ".join("%d=%s" % (level, anchors[level]) for level in sorted(anchors))
        blocks.append("- %s %s" % (header, levels))
    return "\n".join(blocks)
