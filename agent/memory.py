from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
from typing import Any

from .decision import StudyPlan
from .perception import PerceptionModule


PLANS_JS_PREFIX = "window.STUDY_PLAN_RECORDS = "
VALID_TASK_STATUSES = {"todo", "in_progress", "done"}


def _now_timestamp() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _normalize_status(value: Any) -> str:
    status = str(value or "todo").strip().lower()
    if status not in VALID_TASK_STATUSES:
        return "todo"
    return status


def _timestamp_stamp(timestamp: str) -> str:
    if not timestamp:
        return "unknown"

    date_part, _, time_part = timestamp.partition("T")
    compact_date = "".join(character for character in date_part if character.isdigit())
    compact_time = "".join(character for character in time_part if character.isdigit())[:6]
    if compact_date and compact_time:
        return f"{compact_date}_{compact_time}"
    if compact_date:
        return compact_date
    return "unknown"


class MemoryModule:
    def __init__(self, plans_js_path: Path | None = None) -> None:
        project_root = Path(__file__).resolve().parent.parent
        self.project_root = project_root
        self.web_data_dir = project_root / "web" / "data"
        self.plans_js_path = plans_js_path or self.web_data_dir / "plans.js"
        self.legacy_memory_path = project_root / "data" / "memory.json"
        self.perception_module = PerceptionModule()
        self.web_data_dir.mkdir(parents=True, exist_ok=True)
        self._ensure_plans_file()

    def load_records(self) -> list[dict[str, Any]]:
        records, parsed_ok = self._read_records_from_store()
        if not parsed_ok:
            records = self._load_legacy_records()

        normalized_records = self._normalize_records(records)
        if not parsed_ok or records != normalized_records:
            self.save_records(normalized_records)
        return normalized_records

    def save_records(self, records: list[dict[str, Any]]) -> None:
        normalized_records = self._normalize_records(records)
        payload = json.dumps(normalized_records, ensure_ascii=False, indent=2)
        self.plans_js_path.write_text(f"{PLANS_JS_PREFIX}{payload};\n", encoding="utf-8")

    def add_record(self, record: dict[str, Any]) -> None:
        records = self.load_records()
        records.append(record)
        self.save_records(records)

    def update_record(self, record_id: str, updated_record: dict[str, Any]) -> dict[str, Any] | None:
        records = self.load_records()
        target_id = record_id.strip()
        for index, record in enumerate(records):
            if str(record.get("id", "")) != target_id:
                continue
            records[index] = updated_record
            self.save_records(records)
            return self.get_record_by_id(target_id)
        return None

    def replace_record(self, record_id: str, record: dict[str, Any]) -> dict[str, Any] | None:
        return self.update_record(record_id, record)

    def get_latest_plan(self) -> dict[str, Any] | None:
        records = self.get_history(limit=1)
        if not records:
            return None
        return records[0]

    def get_history(self, limit: int | None = None, offset: int = 0) -> list[dict[str, Any]]:
        records = sorted(
            self.load_records(),
            key=lambda record: (
                str(record.get("updated_at") or record.get("created_at") or ""),
                str(record.get("created_at") or ""),
            ),
            reverse=True,
        )
        start = max(offset, 0)
        if limit is None:
            return records[start:]
        if limit <= 0:
            return []
        return records[start : start + limit]

    def get_record_by_id(self, record_id: str) -> dict[str, Any] | None:
        target_id = record_id.strip()
        if not target_id:
            return None

        for record in self.load_records():
            if str(record.get("id", "")) == target_id:
                return record
        return None

    def count_records(self) -> int:
        return len(self.load_records())

    def delete_record(self, record_id: str) -> bool:
        target_id = record_id.strip()
        if not target_id:
            return False

        records = self.load_records()
        remaining_records = [
            record
            for record in records
            if str(record.get("id", "")) != target_id
        ]
        if len(remaining_records) == len(records):
            return False

        self.save_records(remaining_records)
        return True

    def update_task_status(self, record_id: str, task_id: str, status: str) -> dict[str, Any] | None:
        normalized_status = _normalize_status(status)
        records = self.load_records()
        target_id = record_id.strip()
        target_task_id = task_id.strip()

        for record in records:
            if str(record.get("id", "")) != target_id:
                continue

            plan = record.get("plan")
            if not isinstance(plan, dict):
                return None

            daily_tasks = plan.get("daily_tasks")
            if not isinstance(daily_tasks, list):
                return None

            for day in daily_tasks:
                if not isinstance(day, dict):
                    continue
                tasks = day.get("tasks")
                if not isinstance(tasks, list):
                    continue
                for task in tasks:
                    if not isinstance(task, dict):
                        continue
                    if str(task.get("id", "")) != target_task_id:
                        continue
                    task["status"] = normalized_status
                    record["updated_at"] = _now_timestamp()
                    self.save_records(records)
                    return self.get_record_by_id(target_id)
            return None
        return None

    def _ensure_plans_file(self) -> None:
        if not self.plans_js_path.exists():
            migrated_records = self._load_legacy_records()
            self.save_records(migrated_records)
            return

        records, parsed_ok = self._read_records_from_store()
        if not parsed_ok:
            self.save_records(self._load_legacy_records())
            return

        normalized_records = self._normalize_records(records)
        if records != normalized_records:
            self.save_records(normalized_records)

    def _read_records_from_store(self) -> tuple[list[Any], bool]:
        try:
            raw_text = self.plans_js_path.read_text(encoding="utf-8")
        except OSError:
            return [], False

        stripped = raw_text.strip()
        if not stripped or not stripped.startswith(PLANS_JS_PREFIX):
            return [], False

        payload_text = stripped[len(PLANS_JS_PREFIX) :].strip()
        if payload_text.endswith(";"):
            payload_text = payload_text[:-1].rstrip()

        try:
            parsed = json.loads(payload_text)
        except json.JSONDecodeError:
            return [], False

        if not isinstance(parsed, list):
            return [], False
        return parsed, True

    def _load_legacy_records(self) -> list[dict[str, Any]]:
        if not self.legacy_memory_path.exists():
            return []

        try:
            payload = json.loads(self.legacy_memory_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []

        raw_records = payload.get("records") if isinstance(payload, dict) else None
        if not isinstance(raw_records, list):
            return []
        return raw_records

    def _normalize_records(self, records: list[Any]) -> list[dict[str, Any]]:
        raw_records = [record for record in records if isinstance(record, dict)]
        grouped_records = self._group_records(raw_records)
        normalized_records = [
            self._normalize_record_group(group, index)
            for index, group in enumerate(grouped_records, start=1)
            if group
        ]

        used_ids: set[str] = set()
        for index, record in enumerate(normalized_records, start=1):
            record["id"] = self._ensure_unique_plan_id(record, used_ids, index)
            used_ids.add(record["id"])

        return normalized_records

    def _group_records(self, raw_records: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
        grouped: dict[str, list[dict[str, Any]]] = {}
        order: list[str] = []
        records_by_id = {
            str(record.get("id", "")).strip(): record
            for record in raw_records
            if str(record.get("id", "")).strip()
        }

        for index, record in enumerate(raw_records, start=1):
            group_key = self._group_key(record, records_by_id, index)
            if group_key not in grouped:
                grouped[group_key] = []
                order.append(group_key)
            grouped[group_key].append(record)

        return [grouped[key] for key in order]

    def _group_key(
        self,
        record: dict[str, Any],
        records_by_id: dict[str, dict[str, Any]],
        index: int,
    ) -> str:
        if self._is_current_record_shape(record):
            record_id = str(record.get("id", "")).strip()
            if record_id:
                return f"plan:{record_id}"
            created_at = str(record.get("created_at") or record.get("updated_at") or "")
            return f"plan:{_timestamp_stamp(created_at)}:{index}"

        source_id = str(record.get("source_plan_id", "")).strip()
        if source_id:
            return f"legacy:{self._resolve_root_source_id(source_id, records_by_id)}"

        record_id = str(record.get("id", "")).strip()
        if record_id:
            return f"legacy:{record_id}"

        timestamp = str(record.get("timestamp") or record.get("created_at") or "")
        goal = str(record.get("goal") or f"plan_{index}")
        return f"legacy:{_timestamp_stamp(timestamp)}:{goal}"

    def _resolve_root_source_id(
        self,
        source_id: str,
        records_by_id: dict[str, dict[str, Any]],
    ) -> str:
        root_id = source_id
        visited: set[str] = set()

        while root_id in records_by_id and root_id not in visited:
            visited.add(root_id)
            parent_id = str(records_by_id[root_id].get("source_plan_id", "")).strip()
            if not parent_id:
                break
            root_id = parent_id

        return root_id

    def _normalize_record_group(self, group: list[dict[str, Any]], index: int) -> dict[str, Any]:
        ordered_group = sorted(
            group,
            key=lambda record: (
                str(record.get("updated_at") or record.get("timestamp") or record.get("created_at") or ""),
                str(record.get("created_at") or record.get("timestamp") or ""),
            ),
        )
        base_record = ordered_group[0]
        latest_record = ordered_group[-1]

        created_at = str(
            base_record.get("created_at")
            or base_record.get("timestamp")
            or latest_record.get("created_at")
            or latest_record.get("timestamp")
            or ""
        )
        updated_at = str(
            latest_record.get("updated_at")
            or latest_record.get("timestamp")
            or latest_record.get("created_at")
            or created_at
        )
        goal = str(latest_record.get("goal") or base_record.get("goal") or "")
        perceived_state = latest_record.get("perceived_state")
        if not isinstance(perceived_state, dict):
            perceived_state = base_record.get("perceived_state")
        if not isinstance(perceived_state, dict):
            perceived_state = {
                "topic": goal,
                "days": 0,
                "difficulty": "Unknown",
                "task_type": "general study planning",
            }
        perceived_state = dict(perceived_state)
        perceived_state["topic"] = self.perception_module.build_topic(
            goal,
            fallback=str(perceived_state.get("topic") or goal),
        )

        plan_payload = latest_record.get("plan") if isinstance(latest_record.get("plan"), dict) else {}
        normalized_plan = self._normalize_plan(
            plan_payload,
            goal=goal,
            perceived_state=perceived_state,
        )

        update_history = self._collect_update_history(ordered_group)
        latest_feedback = update_history[-1]["feedback"] if update_history else None
        if latest_feedback is None:
            latest_feedback = latest_record.get("latest_feedback") or latest_record.get("feedback")

        return {
            "id": "",
            "created_at": created_at,
            "updated_at": updated_at or created_at,
            "goal": goal,
            "latest_feedback": latest_feedback,
            "update_history": update_history,
            "perceived_state": dict(perceived_state),
            "plan": normalized_plan,
        }

    def _collect_update_history(self, ordered_group: list[dict[str, Any]]) -> list[dict[str, str]]:
        history_entries: list[dict[str, str]] = []
        seen_entries: set[tuple[str, str]] = set()
        seen_feedback: set[str] = set()

        for record in ordered_group:
            raw_history = record.get("update_history")
            if isinstance(raw_history, list):
                for item in raw_history:
                    if not isinstance(item, dict):
                        continue
                    timestamp = str(item.get("timestamp") or record.get("updated_at") or record.get("timestamp") or "")
                    feedback = str(item.get("feedback") or "").strip()
                    if not feedback:
                        continue
                    feedback_key = " ".join(feedback.lower().split())
                    if feedback_key in seen_feedback:
                        continue
                    key = (timestamp, feedback)
                    if key in seen_entries:
                        continue
                    seen_entries.add(key)
                    seen_feedback.add(feedback_key)
                    history_entries.append({"timestamp": timestamp, "feedback": feedback})

            feedback = str(record.get("latest_feedback") or record.get("feedback") or "").strip()
            if not feedback:
                continue

            timestamp = str(record.get("updated_at") or record.get("timestamp") or record.get("created_at") or "")
            feedback_key = " ".join(feedback.lower().split())
            if feedback_key in seen_feedback:
                continue
            key = (timestamp, feedback)
            if key in seen_entries:
                continue
            seen_entries.add(key)
            seen_feedback.add(feedback_key)
            history_entries.append({"timestamp": timestamp, "feedback": feedback})

        history_entries.sort(key=lambda entry: str(entry.get("timestamp") or ""))
        return history_entries

    def _normalize_plan(
        self,
        payload: dict[str, Any],
        goal: str = "",
        perceived_state: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        plan = StudyPlan.from_dict(payload).to_dict()
        normalized_daily_tasks: list[dict[str, Any]] = []

        raw_daily_tasks = payload.get("daily_tasks")
        if not isinstance(raw_daily_tasks, list):
            raw_daily_tasks = plan.get("daily_tasks", [])
        for day_index, day in enumerate(raw_daily_tasks, start=1):
            if not isinstance(day, dict):
                continue

            raw_day = day.get("day", day.get("day_number", day_index))
            try:
                day_number = int(raw_day)
            except (TypeError, ValueError):
                day_number = day_index

            if "title" in day or "day_number" in day:
                focus = str(day.get("title") or day.get("focus") or f"Day {day_number}")
                objective = str(day.get("focus") or day.get("objective") or "")
            else:
                focus = str(day.get("focus") or f"Day {day_number}")
                objective = str(day.get("objective") or "")

            raw_tasks = day.get("tasks")
            if not isinstance(raw_tasks, list):
                raw_tasks = []

            tasks: list[dict[str, str]] = []
            seen_task_ids: set[str] = set()
            for task_index, task in enumerate(raw_tasks, start=1):
                task_object = self._normalize_task_object(task, day_number, task_index)
                task_object["id"] = self._ensure_unique_task_id(task_object["id"], seen_task_ids)
                seen_task_ids.add(task_object["id"])
                tasks.append(task_object)

            normalized_daily_tasks.append(
                {
                    "day": day_number,
                    "focus": focus,
                    "objective": objective,
                    "tasks": tasks,
                }
            )
        state = perceived_state if isinstance(perceived_state, dict) else {}
        topic = self.perception_module.build_topic(
            str(state.get("topic") or goal or plan.get("title") or "Study Topic"),
            fallback=str(goal or state.get("topic") or plan.get("title") or "Study Topic"),
        )
        duration_days = int(plan.get("duration_days", len(normalized_daily_tasks) or 0))
        title = self.perception_module.build_plan_title(
            topic=topic,
            duration_days=duration_days,
            task_type=str(state.get("task_type") or "general study planning"),
        )
        return {
            "title": title,
            "summary": str(plan.get("summary", "")),
            "duration_days": duration_days,
            "strategy": str(plan.get("strategy") or plan.get("planning_strategy") or ""),
            "priority_list": [str(item) for item in plan.get("priority_list", [])],
            "study_notes": [str(item) for item in plan.get("study_notes") or plan.get("tips", [])],
            "risk_warning": str(plan.get("risk_warning", "")),
            "daily_tasks": normalized_daily_tasks,
        }

    def _normalize_task_object(self, task: Any, day_number: int, task_index: int) -> dict[str, str]:
        if isinstance(task, dict):
            text = str(task.get("text") or task.get("task") or "")
            task_id = str(task.get("id") or f"day{day_number}_task{task_index}")
            status = _normalize_status(task.get("status"))
        else:
            text = str(task)
            task_id = f"day{day_number}_task{task_index}"
            status = "todo"

        return {"id": task_id, "text": text, "status": status}

    def _ensure_unique_task_id(self, task_id: str, used_ids: set[str]) -> str:
        candidate = task_id or "task"
        if candidate not in used_ids:
            return candidate

        suffix = 2
        unique_id = f"{candidate}_{suffix}"
        while unique_id in used_ids:
            suffix += 1
            unique_id = f"{candidate}_{suffix}"
        return unique_id

    def _ensure_unique_plan_id(
        self,
        record: dict[str, Any],
        used_ids: set[str],
        index: int,
    ) -> str:
        candidate = str(record.get("id") or "").strip()
        if candidate and candidate not in used_ids and candidate.startswith("plan_"):
            return candidate

        base_id = f"plan_{_timestamp_stamp(str(record.get('created_at') or record.get('updated_at') or ''))}"
        if base_id == "plan_unknown":
            base_id = f"{base_id}_{index}"
        unique_id = base_id
        suffix = 2
        while unique_id in used_ids:
            unique_id = f"{base_id}_{suffix}"
            suffix += 1
        return unique_id

    def _is_current_record_shape(self, record: dict[str, Any]) -> bool:
        return any(key in record for key in ("created_at", "updated_at", "latest_feedback", "update_history"))
