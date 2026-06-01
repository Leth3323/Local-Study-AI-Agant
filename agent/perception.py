from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any


@dataclass(frozen=True)
class ParsedGoal:
    raw_goal: str
    focus_area: str
    duration_days: int
    difficulty: str
    task_type: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "topic": self.focus_area,
            "days": self.duration_days,
            "difficulty": self.difficulty,
            "task_type": self.task_type,
        }


class PerceptionModule:
    DEFAULT_DAYS = 7
    TOPIC_MAX_WORDS = 8
    TOPIC_MAX_CHARS = 48
    TITLE_MAX_CHARS = 60
    NUMBER_WORDS = {
        "one": 1,
        "two": 2,
        "three": 3,
        "four": 4,
        "five": 5,
        "six": 6,
        "seven": 7,
        "eight": 8,
        "nine": 9,
        "ten": 10,
        "eleven": 11,
        "twelve": 12,
        "thirteen": 13,
        "fourteen": 14,
        "fifteen": 15,
        "sixteen": 16,
        "seventeen": 17,
        "eighteen": 18,
        "nineteen": 19,
        "twenty": 20,
    }

    def parse_goal(self, goal_text: str) -> ParsedGoal:
        normalized_goal = " ".join(goal_text.split())
        duration_days = self._extract_duration_days(normalized_goal)
        focus_area = self._extract_focus_area(normalized_goal)
        task_type = self._classify_task_type(normalized_goal)
        difficulty = self._estimate_difficulty(normalized_goal, duration_days, task_type)
        return ParsedGoal(
            raw_goal=normalized_goal,
            focus_area=focus_area,
            duration_days=duration_days,
            difficulty=difficulty,
            task_type=task_type,
        )

    def revise_with_feedback(self, parsed_goal: ParsedGoal, feedback_text: str) -> ParsedGoal:
        revised_duration = self.extract_duration_days(
            feedback_text,
            default=None,
            prefer_last=True,
        )
        if revised_duration is None:
            return parsed_goal

        combined_text = f"{parsed_goal.raw_goal} {feedback_text}".strip()
        task_type = self._classify_task_type(combined_text)
        if task_type == "general study planning":
            task_type = parsed_goal.task_type

        return ParsedGoal(
            raw_goal=parsed_goal.raw_goal,
            focus_area=parsed_goal.focus_area,
            duration_days=revised_duration,
            difficulty=self._estimate_difficulty(combined_text, revised_duration, task_type),
            task_type=task_type,
        )

    def _extract_duration_days(self, goal_text: str) -> int:
        return self.extract_duration_days(goal_text, default=self.DEFAULT_DAYS) or self.DEFAULT_DAYS

    def extract_duration_days(
        self,
        goal_text: str,
        default: int | None = DEFAULT_DAYS,
        prefer_last: bool = False,
    ) -> int | None:
        matches = self._duration_matches(goal_text)
        if not matches:
            return default
        return matches[-1] if prefer_last else matches[0]

    def _duration_matches(self, text: str) -> list[int]:
        matches: list[int] = []
        for match in re.finditer(self._duration_regex(), text or "", re.IGNORECASE):
            raw_value = match.group("value").lower()
            unit = match.group("unit").lower()
            if raw_value.isdigit():
                value = int(raw_value)
            else:
                value = self.NUMBER_WORDS.get(raw_value, 0)
            if value <= 0:
                continue
            if unit.startswith("week"):
                value *= 7
            matches.append(max(1, value))
        return matches

    def _duration_regex(self) -> str:
        words = "|".join(sorted(self.NUMBER_WORDS, key=len, reverse=True))
        return rf"\b(?P<value>\d+|{words})\b(?:\s*-\s*|\s+)(?P<unit>days?|weeks?)\b"

    def _extract_focus_area(self, goal_text: str) -> str:
        focus = re.sub(
            r"^\s*(i\s+(need|want|have)\s+to\s+|please\s+|help\s+me\s+)?",
            "",
            goal_text,
            flags=re.IGNORECASE,
        )
        focus = re.sub(
            r"^\s*(prepare|study|revise|review|build|create|plan)\s+(for\s+)?",
            "",
            focus,
            flags=re.IGNORECASE,
        )
        focus = re.sub(
            r"^\s*(a|an|the)\s+",
            "",
            focus,
            flags=re.IGNORECASE,
        )
        focus = re.sub(
            r"\s+(in|within|over)\s+(\d+|\w+)\s+(day|days|week|weeks)\.?\s*$",
            "",
            focus,
            flags=re.IGNORECASE,
        )
        focus = self.build_topic(focus or goal_text, fallback=goal_text)
        return focus or goal_text.strip()

    def build_topic(self, goal_text: str, fallback: str | None = None) -> str:
        text = " ".join((goal_text or "").split())
        backup = " ".join((fallback or goal_text or "").split())
        if not text:
            return self._fallback_topic(backup)

        text = re.split(r"[.!?]\s+", text, maxsplit=1)[0]
        text = self._strip_leading_duration_intent(text)
        text = re.sub(
            r"^\s*(i\s+(need|want|have)\s+(to\s+|a\s+|an\s+|the\s+)|please\s+|help\s+me\s+|can\s+you\s+|could\s+you\s+)",
            "",
            text,
            flags=re.IGNORECASE,
        )
        text = re.sub(
            r"^\s*(help\s+me\s+|please\s+|can\s+you\s+|could\s+you\s+)",
            "",
            text,
            flags=re.IGNORECASE,
        )
        text = re.sub(
            r"^\s*(temporary|quick|concise|focused)\s+",
            "",
            text,
            flags=re.IGNORECASE,
        )
        text = re.sub(
            r"^\s*(create|make|build)\s+(a\s+)?(study\s+|revision\s+|learning\s+)?plan\s+(for\s+)?",
            "",
            text,
            flags=re.IGNORECASE,
        )
        text = re.sub(
            r"^\s*(prepare|study|revise|review|learn|build|create|make|plan)\s+(for\s+)?",
            "",
            text,
            flags=re.IGNORECASE,
        )
        text = re.sub(
            r"^\s*(everything|all)\s+(about|on|for)\s+",
            "",
            text,
            flags=re.IGNORECASE,
        )
        text = re.sub(
            r"^\s*(about|on|for)\s+",
            "",
            text,
            flags=re.IGNORECASE,
        )
        text = re.sub(
            r"\b(a|an|the|temporary|quick|concise|focused)\s+(study\s+plan|plan)\b",
            "",
            text,
            flags=re.IGNORECASE,
        )
        text = re.sub(
            r"\b(study\s+plan|revision\s+plan|learning\s+plan)\b",
            "",
            text,
            flags=re.IGNORECASE,
        )
        text = re.sub(
            r"\bplease\s+provide.*$",
            "",
            text,
            flags=re.IGNORECASE,
        )
        text = re.sub(
            r"\bthat\s+(can\s+be\s+completed|i\s+can\s+complete).*$",
            "",
            text,
            flags=re.IGNORECASE,
        )
        text = re.sub(
            r"\bwith\s+\d+\s+hours?(\s+of\s+study)?\s+(a|per)\s+day\b",
            "",
            text,
            flags=re.IGNORECASE,
        )
        text = re.sub(
            r"\b(in|within|over)\s+(\d+|\w+)\s+(day|days|week|weeks)\b",
            "",
            text,
            flags=re.IGNORECASE,
        )
        text = re.sub(
            r"\bfor\s+(modal|ui|layout)\s+testing\b",
            "",
            text,
            flags=re.IGNORECASE,
        )
        text = re.sub(r"\s*[,;:-]\s*", " ", text)
        text = re.sub(r"\s+", " ", text).strip(" .")

        exam_like_match = re.search(
            r"([A-Za-z0-9+/&()\- ]{2,}?\b(?:exam|midterm|final|quiz|test|assignment|project|presentation)\b)",
            text,
            re.IGNORECASE,
        )
        if exam_like_match:
            text = exam_like_match.group(1).strip()

        text = self._limit_words(text, self.TOPIC_MAX_WORDS, self.TOPIC_MAX_CHARS)
        if text:
            return self._format_display_text(text)
        return self._fallback_topic(backup)

    def _strip_leading_duration_intent(self, text: str) -> str:
        duration = self._duration_regex()
        value = text
        patterns = [
            rf"^\s*i\s+(now\s+)?(need|have|want)\s+(only\s+|about\s+|around\s+)?{duration}\s+(to\s+)?",
            rf"^\s*(in|within|over)\s+{duration}\s*,?\s*(i\s+)?(need|have|want)\s+(to\s+)?",
        ]
        for pattern in patterns:
            value = re.sub(pattern, "", value, flags=re.IGNORECASE)
        return value

    def build_plan_title(self, topic: str, duration_days: int, task_type: str) -> str:
        compact_topic = self._format_display_text(self._limit_words(topic, 6, 34) or "Study")
        duration_prefix = f"{duration_days}-Day " if duration_days > 0 else ""

        candidates = [
            f"{compact_topic} {duration_prefix}Study Plan".strip(),
            f"{compact_topic} {duration_prefix}Plan".strip(),
            compact_topic,
        ]

        if task_type == "assignment preparation":
            candidates.insert(0, f"{compact_topic} {duration_prefix}Assignment Plan".strip())
        elif task_type == "presentation preparation":
            candidates.insert(0, f"{compact_topic} {duration_prefix}Presentation Plan".strip())
        elif "exam" in compact_topic.lower() or task_type == "exam preparation":
            candidates.insert(0, f"{compact_topic} {duration_prefix}Study Plan".strip())

        for candidate in candidates:
            shortened = self._limit_chars(candidate, self.TITLE_MAX_CHARS)
            if shortened:
                return shortened

        return "Study Plan"

    def _fallback_topic(self, text: str) -> str:
        fallback = re.sub(
            r"\b(in|within|over)\s+(\d+|\w+)\s+(day|days|week|weeks)\b",
            "",
            text,
            flags=re.IGNORECASE,
        )
        fallback = re.sub(r"\s+", " ", fallback).strip(" .")
        limited = self._limit_words(fallback, self.TOPIC_MAX_WORDS, self.TOPIC_MAX_CHARS) or "Study Topic"
        return self._format_display_text(limited)

    def _limit_words(self, text: str, max_words: int, max_chars: int) -> str:
        words = [word for word in text.split() if word]
        if not words:
            return ""

        candidate_words: list[str] = []
        for word in words:
            next_candidate = " ".join(candidate_words + [word]).strip()
            if len(candidate_words) >= max_words or len(next_candidate) > max_chars:
                break
            candidate_words.append(word)

        candidate = " ".join(candidate_words).strip(" .,-")
        return candidate or self._limit_chars(text.strip(" .,-"), max_chars)

    def _limit_chars(self, text: str, max_chars: int) -> str:
        value = text.strip()
        if len(value) <= max_chars:
            return value
        trimmed = value[: max_chars - 1].rstrip(" ,;:-")
        return f"{trimmed}…" if trimmed else value[:max_chars]

    def _format_display_text(self, text: str) -> str:
        words = [word for word in text.split() if word]
        formatted: list[str] = []
        small_words = {"a", "an", "and", "as", "at", "for", "from", "in", "of", "on", "or", "the", "to", "with"}
        for index, word in enumerate(words):
            lowered = word.lower()
            if index > 0 and lowered in small_words:
                formatted.append(lowered)
                continue
            if any(character.isupper() for character in word[1:]) or word.isupper():
                formatted.append(word)
                continue
            if len(word) <= 4 and word.lower() in {"llm", "nlp", "rl", "ml", "ai"}:
                formatted.append(word.upper())
                continue
            formatted.append(word[:1].upper() + word[1:])
        return " ".join(formatted)

    def _classify_task_type(self, goal_text: str) -> str:
        lowered = goal_text.lower()
        if any(keyword in lowered for keyword in ("exam", "midterm", "final", "quiz", "test")):
            return "exam preparation"
        if any(keyword in lowered for keyword in ("assignment", "project", "coursework")):
            return "assignment preparation"
        if any(keyword in lowered for keyword in ("presentation", "talk")):
            return "presentation preparation"
        return "general study planning"

    def _estimate_difficulty(self, goal_text: str, duration_days: int, task_type: str) -> str:
        lowered = goal_text.lower()
        high_pressure = any(keyword in lowered for keyword in ("reinforcement learning", "exam", "final", "midterm"))

        if duration_days <= 5 or high_pressure:
            return "High"
        if duration_days <= 10 or task_type == "exam preparation":
            return "Medium"
        return "Low"
