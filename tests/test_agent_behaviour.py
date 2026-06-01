from pathlib import Path
import tempfile
import unittest

from agent.action import ActionModule
from agent.agent import StudyPlanningAgent
from agent.memory import MemoryModule
from agent.perception import PerceptionModule


class PerceptionModuleTests(unittest.TestCase):
    def test_topic_ignores_leading_duration_request(self) -> None:
        parsed = PerceptionModule().parse_goal(
            "I need three days to study everything about derivatives in Thomas's Calculus. "
            "Please help me create a study plan."
        )

        self.assertEqual(parsed.focus_area, "Derivatives in Thomas's Calculus")
        self.assertEqual(parsed.duration_days, 3)

    def test_feedback_duration_prefers_new_target(self) -> None:
        perception = PerceptionModule()
        parsed = perception.parse_goal("Prepare for a calculus quiz in 3 days.")
        revised = perception.revise_with_feedback(parsed, "Change this from 3 days to 5 days.")

        self.assertEqual(revised.duration_days, 5)


class StudyPlanningAgentTests(unittest.TestCase):
    def test_feedback_duration_regenerates_daily_plan(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            memory = MemoryModule(plans_js_path=Path(temp_dir) / "plans.js")
            agent = StudyPlanningAgent()
            agent.memory_module = memory
            agent.action_module = ActionModule(memory_module=memory)

            record = agent.create_study_plan(
                "I need three days to study everything about derivatives in Thomas's Calculus. "
                "Please help me create a study plan."
            )
            updated = agent.update_plan_by_id(
                str(record["id"]),
                "I now need to extend my study time to five days. Please help me update the plan.",
            )

        self.assertIsNotNone(updated)
        assert updated is not None
        self.assertEqual(updated["perceived_state"]["topic"], "Derivatives in Thomas's Calculus")
        self.assertEqual(updated["perceived_state"]["days"], 5)
        self.assertEqual(updated["plan"]["duration_days"], 5)
        self.assertEqual(len(updated["plan"]["daily_tasks"]), 5)


if __name__ == "__main__":
    unittest.main()
