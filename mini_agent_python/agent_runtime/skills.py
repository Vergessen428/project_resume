import os
from typing import List


class SkillLoader:
    def __init__(self, skills_root: str) -> None:
        self.skills_root = skills_root

    def load_for_goal(self, goal: str) -> List[str]:
        lowered = goal.lower()
        keywords = [
            "面试",
            "项目",
            "star",
            "追问",
            "复盘",
            "interview",
            "resume",
            "project",
        ]

        if any(keyword in lowered for keyword in keywords):
            skill = self._read_skill("interview_prep.md")
            return [skill] if skill else []

        return []

    def _read_skill(self, filename: str) -> str:
        path = os.path.join(self.skills_root, filename)
        if not os.path.isfile(path):
            return ""

        with open(path, "r", encoding="utf-8") as f:
            return f.read()

