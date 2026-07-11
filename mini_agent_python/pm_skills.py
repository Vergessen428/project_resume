"""Explicit PM coaching rubrics used by review and long-term memory."""

from typing import Dict, List


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


def prompt_rubric() -> str:
    return "\n".join("- %s (%s): %s" % (item["id"], item["name"], item["focus"]) for item in PM_SKILLS)


def public_skills() -> List[Dict[str, str]]:
    return [{"id": item["id"], "name": item["name"], "focus": item["focus"]} for item in PM_SKILLS]
