from __future__ import annotations

from typing import Any

from .action import ActionModule
from .decision import DecisionModule, StudyPlan
from .memory import MemoryModule
from .perception import PerceptionModule


class StudyPlanningAgent:
    def __init__(self) -> None:
        self.memory_module = MemoryModule()
        self.perception_module = PerceptionModule()
        self.decision_module = DecisionModule()
        self.action_module = ActionModule(memory_module=self.memory_module)

    def create_study_plan(self, goal_text: str) -> dict[str, Any]:
        parsed_goal = self.perception_module.parse_goal(goal_text)
        plan = self.decision_module.create_plan(parsed_goal)
        record = self.action_module.store_created_plan(
            goal=goal_text,
            perceived_state=parsed_goal.to_dict(),
            plan=plan,
        )
        return record

    def update_latest_plan(self, feedback_text: str) -> dict[str, Any] | None:
        latest_record = self.memory_module.get_latest_plan()
        if latest_record is None:
            return None

        return self.update_plan_by_id(str(latest_record.get("id", "")), feedback_text)

    def update_plan_by_id(self, record_id: str, feedback_text: str) -> dict[str, Any] | None:
        target_record = self.memory_module.get_record_by_id(record_id)
        if target_record is None:
            return None

        parsed_goal = self.perception_module.parse_goal(str(target_record.get("goal", "")))
        parsed_goal = self.perception_module.revise_with_feedback(parsed_goal, feedback_text)
        previous_plan = StudyPlan.from_dict(target_record.get("plan", {}))
        updated_plan = self.decision_module.create_plan(
            parsed_goal,
            feedback=feedback_text,
            previous_plan=previous_plan,
        )
        record = self.action_module.store_updated_plan(
            existing_record=target_record,
            goal=str(target_record.get("goal", "")),
            perceived_state=parsed_goal.to_dict(),
            plan=updated_plan,
            feedback=feedback_text,
        )
        return record

    def get_history(self, limit: int | None = None, offset: int = 0) -> list[dict[str, Any]]:
        return self.memory_module.get_history(limit=limit, offset=offset)

    def get_latest_plan(self) -> dict[str, Any] | None:
        return self.memory_module.get_latest_plan()

    def get_record_by_id(self, record_id: str) -> dict[str, Any] | None:
        return self.memory_module.get_record_by_id(record_id)

    def update_task_status(self, record_id: str, task_id: str, status: str) -> dict[str, Any] | None:
        return self.memory_module.update_task_status(record_id, task_id, status)

    def delete_plan(self, record_id: str) -> bool:
        return self.memory_module.delete_record(record_id)
