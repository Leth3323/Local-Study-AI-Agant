from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .perception import ParsedGoal, PerceptionModule


@dataclass
class StudyDay:
    day_number: int
    title: str
    focus: str
    tasks: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "day": self.day_number,
            "focus": self.title,
            "objective": self.focus,
            "tasks": [
                {
                    "id": f"day{self.day_number}_task{index}",
                    "text": task,
                    "status": "todo",
                }
                for index, task in enumerate(self.tasks, start=1)
            ],
        }


@dataclass
class StudyPlan:
    title: str
    summary: str
    duration_days: int
    planning_strategy: str
    priority_list: list[str] = field(default_factory=list)
    risk_warning: str = ""
    daily_tasks: list[StudyDay] = field(default_factory=list)
    tips: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "summary": self.summary,
            "duration_days": self.duration_days,
            "strategy": self.planning_strategy,
            "priority_list": list(self.priority_list),
            "risk_warning": self.risk_warning,
            "daily_tasks": [day.to_dict() for day in self.daily_tasks],
            "study_notes": list(self.tips),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "StudyPlan":
        daily_tasks: list[StudyDay] = []
        for index, day in enumerate(payload.get("daily_tasks", []), start=1):
            if not isinstance(day, dict):
                continue

            raw_day = day.get("day", day.get("day_number", index))
            try:
                day_number = int(raw_day)
            except (TypeError, ValueError):
                day_number = index

            if "day_number" in day or "title" in day:
                title = str(day.get("title") or day.get("focus") or f"Day {day_number}")
                focus = str(day.get("focus") or day.get("objective") or "")
            else:
                title = str(day.get("focus") or f"Day {day_number}")
                focus = str(day.get("objective") or "")

            daily_tasks.append(
                StudyDay(
                    day_number=day_number,
                    title=title,
                    focus=focus,
                    tasks=[
                        str(task.get("text") or task.get("task") or "")
                        if isinstance(task, dict)
                        else str(task)
                        for task in day.get("tasks", [])
                    ],
                )
            )

        return cls(
            title=payload.get("title", "Study Plan"),
            summary=payload.get("summary", ""),
            duration_days=int(payload.get("duration_days", len(daily_tasks) or 0)),
            planning_strategy=payload.get("strategy") or payload.get("planning_strategy", ""),
            priority_list=[str(item) for item in payload.get("priority_list", [])],
            risk_warning=payload.get("risk_warning", ""),
            daily_tasks=daily_tasks,
            tips=[str(tip) for tip in payload.get("study_notes") or payload.get("tips", [])],
        )


class DecisionModule:
    def __init__(self) -> None:
        self.perception_module = PerceptionModule()

    def create_plan(
        self,
        parsed_goal: ParsedGoal,
        feedback: str | None = None,
        previous_plan: StudyPlan | None = None,
    ) -> StudyPlan:
        duration_days = max(1, parsed_goal.duration_days)
        focus_area = parsed_goal.focus_area
        feedback_flags = self._feedback_flags(feedback)

        if previous_plan is None:
            summary = (
                f"This {duration_days}-day plan breaks {focus_area} into daily review, "
                "active recall, and practice checkpoints."
            )
        else:
            summary = (
                f"This revised {duration_days}-day plan keeps the core structure for "
                f"{focus_area} while incorporating the latest feedback."
            )

        if feedback:
            summary += f" Latest feedback: {feedback}"

        daily_tasks = [
            self._build_day_plan(day_number, duration_days, focus_area, feedback_flags)
            for day_number in range(1, duration_days + 1)
        ]

        planning_strategy = self._build_strategy(parsed_goal, feedback_flags, previous_plan is not None)
        priority_list = self._build_priority_list(parsed_goal, feedback_flags)
        risk_warning = self._build_risk_warning(parsed_goal)
        tips = self._build_tips(feedback_flags, feedback)

        return StudyPlan(
            title=self.perception_module.build_plan_title(
                topic=focus_area,
                duration_days=duration_days,
                task_type=parsed_goal.task_type,
            ),
            summary=summary,
            duration_days=duration_days,
            planning_strategy=planning_strategy,
            priority_list=priority_list,
            risk_warning=risk_warning,
            daily_tasks=daily_tasks,
            tips=tips,
        )

    def _build_day_plan(
        self,
        day_number: int,
        total_days: int,
        focus_area: str,
        feedback_flags: dict[str, bool],
    ) -> StudyDay:
        if total_days == 1:
            tasks = [
                f"List the highest-risk topics in {focus_area}.",
                "Do a short diagnostic quiz or a small set of practice questions.",
                "Finish with a condensed summary sheet and a final recall pass.",
            ]
            return StudyDay(
                day_number=1,
                title="Rapid preparation",
                focus="Prioritize the highest-yield material",
                tasks=self._apply_feedback(tasks, feedback_flags, final_day=True),
            )

        if day_number == 1:
            tasks = [
                f"Map the exam scope for {focus_area} and gather resources.",
                "Identify weak areas, required formulas, and core definitions.",
                "Set a realistic session length and a short end-of-day recall check.",
            ]
            return StudyDay(
                day_number=day_number,
                title="Scope and baseline",
                focus="Understand coverage and current gaps",
                tasks=self._apply_feedback(tasks, feedback_flags),
            )

        if day_number == total_days:
            tasks = [
                "Run a timed self-check using mixed questions or prompts.",
                "Review mistakes, unresolved topics, and common traps.",
                "End with a concise recap from memory without notes.",
            ]
            return StudyDay(
                day_number=day_number,
                title="Mock exam and consolidation",
                focus="Verify readiness under exam-like conditions",
                tasks=self._apply_feedback(tasks, feedback_flags, final_day=True),
            )

        progress = day_number / total_days
        if progress <= 0.4:
            tasks = [
                f"Study a core block of {focus_area} in depth.",
                "Convert the material into short notes, flashcards, or recall prompts.",
                "Close the session by explaining the topic aloud without reading.",
            ]
            title = "Core concepts"
            focus = "Build durable understanding"
        elif progress <= 0.75:
            tasks = [
                f"Work through applied problems for {focus_area}.",
                "Review errors immediately and note the pattern behind each miss.",
                "Create a short checkpoint list of what still feels uncertain.",
            ]
            title = "Guided practice"
            focus = "Turn concepts into problem-solving"
        else:
            tasks = [
                "Mix older and newer topics in one session.",
                "Use active recall first, then verify with notes or solutions.",
                "Trim notes into a final quick-review sheet.",
            ]
            title = "Synthesis and review"
            focus = "Strengthen retrieval across topics"

        return StudyDay(
            day_number=day_number,
            title=title,
            focus=focus,
            tasks=self._apply_feedback(tasks, feedback_flags),
        )

    def _feedback_flags(self, feedback: str | None) -> dict[str, bool]:
        lowered = (feedback or "").lower()
        return {
            "more_practice": any(word in lowered for word in ("practice", "problems", "questions", "exam")),
            "more_review": any(word in lowered for word in ("review", "summary", "recap", "notes")),
            "lighter_load": any(word in lowered for word in ("busy", "lighter", "shorter", "less time", "focused")),
            "more_theory": any(word in lowered for word in ("theory", "intuition", "understand", "concept")),
        }

    def _apply_feedback(
        self,
        tasks: list[str],
        feedback_flags: dict[str, bool],
        final_day: bool = False,
    ) -> list[str]:
        revised_tasks = list(tasks)

        if feedback_flags["more_theory"]:
            revised_tasks.append("Add a short intuition pass before moving into exercises.")
        if feedback_flags["more_practice"]:
            revised_tasks.append("Include one extra set of exam-style questions and score it honestly.")
        if feedback_flags["more_review"] and not final_day:
            revised_tasks.append("Reserve the last 10 minutes for a written recap from memory.")
        if feedback_flags["lighter_load"]:
            revised_tasks.append("Keep the session tight by limiting the plan to one primary topic block.")

        return revised_tasks

    def _build_strategy(
        self,
        parsed_goal: ParsedGoal,
        feedback_flags: dict[str, bool],
        is_revision: bool,
    ) -> str:
        article = self._indefinite_article(parsed_goal.task_type)
        strategy = (
            f"Use {article} {parsed_goal.task_type} strategy that front-loads scope mapping, "
            "moves into deliberate practice, and ends with retrieval-heavy review."
        )
        if parsed_goal.difficulty == "High":
            strategy += " Keep sessions tightly focused on high-yield topics because the time window is compressed."
        if feedback_flags["more_practice"]:
            strategy += " Allocate extra time to practice questions in every session."
        if feedback_flags["lighter_load"]:
            strategy += " Reduce context switching and keep each day centered on one primary topic."
        if is_revision:
            strategy += " This version preserves the existing structure and adjusts emphasis based on the latest feedback."
        return strategy

    def _indefinite_article(self, phrase: str) -> str:
        if phrase[:1].lower() in {"a", "e", "i", "o", "u"}:
            return "an"
        return "a"

    def _build_priority_list(
        self,
        parsed_goal: ParsedGoal,
        feedback_flags: dict[str, bool],
    ) -> list[str]:
        priorities = [
            f"Identify the highest-risk areas in {parsed_goal.focus_area}.",
            "Turn notes into active recall prompts instead of passive rereading.",
            "Finish each day with a short self-check to expose gaps early.",
        ]

        if feedback_flags["more_practice"]:
            priorities[1] = "Use exam-style practice questions to validate understanding every day."
        if feedback_flags["lighter_load"]:
            priorities.append("Limit each session to the highest-yield subtopic before expanding scope.")

        return priorities

    def _build_risk_warning(self, parsed_goal: ParsedGoal) -> str:
        if parsed_goal.duration_days <= 5:
            return (
                f"Only {parsed_goal.duration_days} days are available. "
                "Avoid expanding scope late and protect time for practice under pressure."
            )
        if parsed_goal.difficulty == "High":
            return "The topic appears demanding. Track weak areas daily so they do not accumulate."
        return "The main risk is passive review. Keep recall and practice at the center of each session."

    def _build_tips(self, feedback_flags: dict[str, bool], feedback: str | None) -> list[str]:
        tips = [
            "Start each session by recalling yesterday's material before opening your notes.",
            "Track mistakes as categories, not just individual questions.",
            "Protect a short daily review window instead of relying on one long cram session.",
        ]

        if feedback_flags["more_practice"]:
            tips.append("Shift more time into mixed practice once the basics feel stable.")
        if feedback_flags["lighter_load"]:
            tips.append("When time is constrained, drop lower-yield tasks instead of rushing everything.")
        if feedback:
            tips.append(f"Latest revision note: {feedback}")

        return tips
