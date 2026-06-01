from __future__ import annotations

from datetime import datetime
from typing import Any

from .decision import StudyPlan
from .memory import MemoryModule


class ActionModule:
    def __init__(self, memory_module: MemoryModule | None = None) -> None:
        self.memory_module = memory_module or MemoryModule()

    def store_created_plan(
        self,
        goal: str,
        perceived_state: dict[str, object],
        plan: StudyPlan,
    ) -> dict[str, Any]:
        timestamp = self._timestamp_now()
        record = {
            "id": self._build_plan_id(timestamp),
            "created_at": timestamp,
            "updated_at": timestamp,
            "goal": goal,
            "latest_feedback": None,
            "update_history": [],
            "perceived_state": dict(perceived_state),
            "plan": self._plan_to_record_plan(plan),
        }
        self.memory_module.add_record(record)
        return record

    def store_updated_plan(
        self,
        existing_record: dict[str, Any],
        goal: str,
        perceived_state: dict[str, object],
        plan: StudyPlan,
        feedback: str,
    ) -> dict[str, Any] | None:
        record_id = str(existing_record.get("id", "")).strip()
        if not record_id:
            return None

        timestamp = self._timestamp_now()
        update_history = existing_record.get("update_history")
        if not isinstance(update_history, list):
            update_history = []
        update_history = list(update_history)
        last_feedback = ""
        if update_history and isinstance(update_history[-1], dict):
            last_feedback = str(update_history[-1].get("feedback") or "").strip()
        if last_feedback != feedback:
            update_history.append({"timestamp": timestamp, "feedback": feedback})

        updated_record = {
            "id": record_id,
            "created_at": str(existing_record.get("created_at") or timestamp),
            "updated_at": timestamp,
            "goal": goal,
            "latest_feedback": feedback,
            "update_history": update_history,
            "perceived_state": dict(perceived_state),
            "plan": self._plan_to_record_plan(plan, existing_record=existing_record),
        }
        return self.memory_module.update_record(record_id, updated_record)

    def _timestamp_now(self) -> str:
        return datetime.now().isoformat(timespec="seconds")

    def _build_plan_id(self, timestamp: str) -> str:
        base_id = f"plan_{self._timestamp_stamp(timestamp)}"
        existing_ids = {
            str(record.get("id", ""))
            for record in self.memory_module.load_records()
            if isinstance(record, dict)
        }
        if base_id not in existing_ids:
            return base_id

        suffix = 2
        candidate_id = f"{base_id}_{suffix}"
        while candidate_id in existing_ids:
            suffix += 1
            candidate_id = f"{base_id}_{suffix}"
        return candidate_id

    def _timestamp_stamp(self, timestamp: str) -> str:
        date_part, _, time_part = timestamp.partition("T")
        compact_date = "".join(character for character in date_part if character.isdigit())
        compact_time = "".join(character for character in time_part if character.isdigit())[:6]
        if compact_date and compact_time:
            return f"{compact_date}_{compact_time}"
        if compact_date:
            return compact_date
        return "unknown"

    def _plan_to_record_plan(
        self,
        plan: StudyPlan,
        existing_record: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        plan_payload = plan.to_dict()
        previous_days = self._previous_tasks_by_day(existing_record)
        daily_tasks: list[dict[str, Any]] = []

        for day_index, raw_day in enumerate(plan_payload.get("daily_tasks", []), start=1):
            if not isinstance(raw_day, dict):
                continue

            day_number = int(raw_day.get("day", day_index))
            focus = str(raw_day.get("focus") or f"Day {day_number}")
            objective = str(raw_day.get("objective") or "")
            merged_tasks = self._merge_task_statuses(
                day_number=day_number,
                raw_tasks=raw_day.get("tasks", []),
                previous_tasks=previous_days.get(day_number, []),
            )
            daily_tasks.append(
                {
                    "day": day_number,
                    "focus": focus,
                    "objective": objective,
                    "tasks": merged_tasks,
                }
            )

        return {
            "title": str(plan_payload.get("title", "Study Plan")),
            "summary": str(plan_payload.get("summary", "")),
            "duration_days": int(plan_payload.get("duration_days", len(daily_tasks) or 0)),
            "strategy": str(plan_payload.get("strategy") or ""),
            "priority_list": [str(item) for item in plan_payload.get("priority_list", [])],
            "study_notes": [str(item) for item in plan_payload.get("study_notes", [])],
            "risk_warning": str(plan_payload.get("risk_warning", "")),
            "daily_tasks": daily_tasks,
        }

    def _previous_tasks_by_day(self, record: dict[str, Any] | None) -> dict[int, list[dict[str, Any]]]:
        if not isinstance(record, dict):
            return {}

        plan = record.get("plan")
        if not isinstance(plan, dict):
            return {}

        daily_tasks = plan.get("daily_tasks")
        if not isinstance(daily_tasks, list):
            return {}

        previous_days: dict[int, list[dict[str, Any]]] = {}
        for day_index, raw_day in enumerate(daily_tasks, start=1):
            if not isinstance(raw_day, dict):
                continue
            try:
                day_number = int(raw_day.get("day", day_index))
            except (TypeError, ValueError):
                day_number = day_index
            tasks = raw_day.get("tasks")
            if not isinstance(tasks, list):
                continue
            previous_days[day_number] = [task for task in tasks if isinstance(task, dict)]
        return previous_days

    def _merge_task_statuses(
        self,
        *,
        day_number: int,
        raw_tasks: list[Any],
        previous_tasks: list[dict[str, Any]],
    ) -> list[dict[str, str]]:
        previous_by_text: dict[str, list[dict[str, Any]]] = {}
        for task in previous_tasks:
            normalized_text = self._task_text_key(str(task.get("text") or ""))
            previous_by_text.setdefault(normalized_text, []).append(task)

        merged_tasks: list[dict[str, str]] = []
        for task_index, raw_task in enumerate(raw_tasks, start=1):
            if isinstance(raw_task, dict):
                text = str(raw_task.get("text") or raw_task.get("task") or "")
            else:
                text = str(raw_task)

            previous_match = None
            normalized_text = self._task_text_key(text)
            if normalized_text and previous_by_text.get(normalized_text):
                previous_match = previous_by_text[normalized_text].pop(0)
            elif task_index - 1 < len(previous_tasks):
                previous_match = previous_tasks[task_index - 1]

            merged_tasks.append(
                {
                    "id": str(previous_match.get("id")) if previous_match else f"day{day_number}_task{task_index}",
                    "text": text,
                    "status": self._normalize_status(previous_match.get("status")) if previous_match else "todo",
                }
            )

        return merged_tasks

    def _task_text_key(self, text: str) -> str:
        return " ".join(text.lower().split())

    def _normalize_status(self, value: Any) -> str:
        status = str(value or "todo").strip().lower()
        if status not in {"todo", "in_progress", "done"}:
            return "todo"
        return status
