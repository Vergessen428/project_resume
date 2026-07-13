"""Explicit PM coaching rubrics used by review and long-term memory."""

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


def prompt_rubric() -> str:
    return "\n".join("- %s (%s): %s" % (item["id"], item["name"], item["focus"]) for item in PM_SKILLS)


def public_skills() -> List[Dict[str, str]]:
    return [{"id": item["id"], "name": item["name"], "focus": item["focus"]} for item in PM_SKILLS]


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
