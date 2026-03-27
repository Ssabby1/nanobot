"""Rule-based natural language routing for the fitness MVP."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from nanobot.fitness.service import FitnessService


PROFILE_REQUIRED_FIELDS = [
    "gender",
    "age",
    "height",
    "weight",
    "goal",
    "experience_level",
    "training_days_per_week",
    "session_duration",
    "environment",
    "diet_constraint",
]

FIELD_LABELS = {
    "gender": "\u6027\u522b",
    "age": "\u5e74\u9f84",
    "height": "\u8eab\u9ad8",
    "weight": "\u4f53\u91cd",
    "goal": "\u76ee\u6807",
    "experience_level": "\u8bad\u7ec3\u7ecf\u9a8c",
    "training_days_per_week": "\u6bcf\u5468\u8bad\u7ec3\u5929\u6570",
    "session_duration": "\u5355\u6b21\u8bad\u7ec3\u65f6\u957f",
    "environment": "\u8bad\u7ec3\u73af\u5883",
    "diet_constraint": "\u996e\u98df\u6761\u4ef6",
    "completion_rate": "\u5b8c\u6210\u5ea6",
    "fatigue_level": "\u75b2\u52b3\u7a0b\u5ea6",
    "diet_adherence": "\u996e\u98df\u8fbe\u6807\u60c5\u51b5",
}


@dataclass
class RouteDecision:
    """Routing result before execution."""

    action: str | None
    params: dict[str, Any] = field(default_factory=dict)
    missing_fields: list[str] = field(default_factory=list)
    reason: str = ""


class FitnessRuleRouter:
    """Keyword and regex driven natural language router."""

    def __init__(self, service: FitnessService):
        self.service = service
        self.state_path = Path(self.service.repo.base_dir) / "router_state.json"

    def handle(self, text: str, user_id: str | None = None) -> str:
        clean = (text or "").strip()
        if not clean:
            raise ValueError(
                "\u8bf7\u8f93\u5165\u4e00\u6bb5\u5065\u8eab\u76f8\u5173\u9700\u6c42\uff0c"
                "\u4f8b\u5982\u201c\u5e2e\u6211\u5efa\u6863\u201d\u6216"
                "\u201c\u6211\u4eca\u5929\u7ec3\u4e86\u5367\u63a8\u548c\u5212\u8239\u201d\u3002"
            )

        resolved_user_id = self.infer_user_id(clean, explicit_user_id=user_id)
        decision = self.route(clean, user_id=resolved_user_id)
        if not decision.action:
            return (
                "\u6682\u65f6\u6ca1\u8bc6\u522b\u51fa\u4f60\u7684\u610f\u56fe\u3002"
                "\u5f53\u524d\u89c4\u5219\u8def\u7531\u5df2\u652f\u6301\uff1a"
                "\u5efa\u6863\u3001\u66f4\u65b0\u753b\u50cf\u3001\u67e5\u770b\u753b\u50cf\u3001"
                "\u751f\u6210/\u67e5\u770b\u8ba1\u5212\u3001\u6253\u5361/\u67e5\u770b\u6253\u5361\u3001"
                "\u751f\u6210/\u67e5\u770b\u5efa\u8bae\u3002"
            )
        if decision.missing_fields:
            missing = "\u3001".join(FIELD_LABELS.get(field, field) for field in decision.missing_fields)
            return (
                f"\u5df2\u8bc6\u522b\u4e3a\u201c{decision.reason}\u201d\uff0c"
                f"\u4f46\u8fd8\u7f3a\u5c11\u8fd9\u4e9b\u4fe1\u606f\uff1a{missing}\u3002"
            )

        result = self.execute(decision, user_id=resolved_user_id)
        self._save_last_user_id(resolved_user_id)
        return result

    @staticmethod
    def resolve_user_id(text: str, explicit_user_id: str | None = None) -> str:
        if explicit_user_id and explicit_user_id.strip():
            return explicit_user_id.strip()

        patterns = (
            r"\u6211\u53eb\s*([A-Za-z0-9_-]{2,32}|[\u4e00-\u9fff]{2,16})",
            r"\u6211\u7684\u540d\u5b57\u662f\s*([A-Za-z0-9_-]{2,32}|[\u4e00-\u9fff]{2,16})",
            r"\u53eb\u6211\s*([A-Za-z0-9_-]{2,32}|[\u4e00-\u9fff]{2,16})",
        )
        for pattern in patterns:
            if match := re.search(pattern, text):
                candidate = match.group(1).strip()
                if candidate not in {
                    "\u7537",
                    "\u5973",
                    "\u7537\u6027",
                    "\u5973\u6027",
                    "\u65b0\u624b",
                    "\u521d\u7ea7",
                    "\u4e2d\u7ea7",
                }:
                    return candidate
        return "default"

    def infer_user_id(self, text: str, explicit_user_id: str | None = None) -> str:
        parsed = self.resolve_user_id(text, explicit_user_id=explicit_user_id)
        if parsed != "default":
            return parsed
        if saved := self._load_last_user_id():
            return saved
        profile_ids = self.service.list_profile_ids()
        if len(profile_ids) == 1:
            return profile_ids[0]
        return "default"

    def route(self, text: str, user_id: str = "default") -> RouteDecision:
        lower = text.lower()

        if self._is_show_adjustment_request(lower):
            return RouteDecision(action="show_adjustment", reason="\u67e5\u770b\u5efa\u8bae")

        if self._is_adjustment_request(lower):
            return RouteDecision(action="generate_adjustment", reason="\u751f\u6210\u5efa\u8bae")

        if self._is_show_feedback_request(lower):
            return RouteDecision(action="show_feedback", reason="\u67e5\u770b\u6253\u5361")

        if self._is_feedback_request(lower):
            params = self._extract_feedback_params(text)
            missing = [
                field
                for field in ("completion_rate", "fatigue_level", "diet_adherence")
                if params.get(field) in (None, "")
            ]
            return RouteDecision(
                action="record_feedback",
                params=params,
                missing_fields=missing,
                reason="\u6253\u5361",
            )

        if self._is_show_plan_request(lower):
            return RouteDecision(action="show_weekly_plan", reason="\u67e5\u770b\u8ba1\u5212")

        if self._is_plan_request(lower):
            params = self._extract_plan_params(text)
            return RouteDecision(action="generate_weekly_plan", params=params, reason="\u751f\u6210\u8ba1\u5212")

        if self._is_show_profile_request(lower):
            return RouteDecision(action="show_profile", reason="\u67e5\u770b\u753b\u50cf")

        if self._is_profile_update_request(lower):
            params = self._extract_profile_params(text)
            if not params:
                return RouteDecision(
                    action="update_profile",
                    missing_fields=["weight", "goal", "training_days_per_week", "session_duration", "environment"],
                    reason="\u66f4\u65b0\u753b\u50cf",
                )
            return RouteDecision(action="update_profile", params=params, reason="\u66f4\u65b0\u753b\u50cf")

        if self._is_profile_create_request(lower):
            params = self._extract_profile_params(text)
            missing = [field for field in PROFILE_REQUIRED_FIELDS if params.get(field) in (None, "")]
            return RouteDecision(
                action="save_profile",
                params=params,
                missing_fields=missing,
                reason="\u5efa\u6863",
            )

        return RouteDecision(action=None)

    def execute(self, decision: RouteDecision, user_id: str = "default") -> str:
        params = dict(decision.params)

        if decision.action == "save_profile":
            profile = self.service.save_profile(user_id=user_id, **params)
            return "\u5df2\u5b8c\u6210\u5efa\u6863\u3002\n" + self.service.format_profile(profile)

        if decision.action == "update_profile":
            profile = self.service.update_profile(user_id=user_id, **params)
            return "\u5df2\u66f4\u65b0\u753b\u50cf\u3002\n" + self.service.format_profile(profile)

        if decision.action == "show_profile":
            profile = self.service.get_profile(user_id=user_id)
            if not profile:
                return f"\u8fd8\u6ca1\u6709\u627e\u5230\u7528\u6237 {user_id} \u7684\u753b\u50cf\u3002"
            return "\u8fd9\u662f\u4f60\u5f53\u524d\u7684\u753b\u50cf\uff1a\n" + self.service.format_profile(profile)

        if decision.action == "generate_weekly_plan":
            plan = self.service.generate_weekly_plan(user_id=user_id, week_start_date=params.get("week_start_date"))
            return "\u5df2\u751f\u6210\u672c\u5468\u8ba1\u5212\u3002\n" + self.service.format_plan(plan)

        if decision.action == "show_weekly_plan":
            plan = self.service.get_latest_plan(user_id=user_id)
            if not plan:
                return f"\u8fd8\u6ca1\u6709\u627e\u5230\u7528\u6237 {user_id} \u7684\u8ba1\u5212\u3002"
            return "\u8fd9\u662f\u4f60\u6700\u8fd1\u7684\u8bad\u7ec3\u8ba1\u5212\uff1a\n" + self.service.format_plan(plan)

        if decision.action == "record_feedback":
            feedback = self.service.record_feedback(
                user_id=user_id,
                feedback_date=params["feedback_date"],
                trained_today=params["trained_today"],
                completed_exercises=params.get("completed_exercises", []),
                completion_rate=params["completion_rate"],
                fatigue_level=params["fatigue_level"],
                soreness_notes=params.get("soreness_notes", ""),
                diet_adherence=params["diet_adherence"],
                extra_notes=params.get("extra_notes", ""),
            )
            return "\u5df2\u8bb0\u5f55\u4eca\u65e5\u6253\u5361\u3002\n" + self.service.format_feedback([feedback])

        if decision.action == "show_feedback":
            items = self.service.list_feedback(user_id=user_id, limit=7)
            return "\u8fd9\u662f\u4f60\u6700\u8fd1\u7684\u6253\u5361\u8bb0\u5f55\uff1a\n" + self.service.format_feedback(items)

        if decision.action == "generate_adjustment":
            suggestion = self.service.generate_adjustment(user_id=user_id)
            return "\u5df2\u751f\u6210\u8c03\u6574\u5efa\u8bae\u3002\n" + self.service.format_adjustment(suggestion)

        if decision.action == "show_adjustment":
            suggestion = self.service.get_latest_adjustment(user_id=user_id)
            if not suggestion:
                return f"\u8fd8\u6ca1\u6709\u627e\u5230\u7528\u6237 {user_id} \u7684\u8c03\u6574\u5efa\u8bae\u3002"
            return "\u8fd9\u662f\u4f60\u6700\u8fd1\u7684\u8c03\u6574\u5efa\u8bae\uff1a\n" + self.service.format_adjustment(suggestion)

        raise ValueError(f"Unknown action: {decision.action}")

    @staticmethod
    def _is_profile_create_request(text: str) -> bool:
        keywords = (
            "\u5efa\u6863",
            "\u5efa\u4e2a\u6863",
            "\u5efa\u7acb\u6863\u6848",
            "\u521b\u5efa\u6863\u6848",
            "\u521b\u5efa\u753b\u50cf",
            "\u4fdd\u5b58\u753b\u50cf",
        )
        profile_signals = (
            "\u5e74\u9f84",
            "\u5c81",
            "cm",
            "kg",
            "\u6bcf\u5468",
            "\u5206\u949f",
            "\u5065\u8eab\u623f",
            "\u76ee\u6807",
        )
        return any(keyword in text for keyword in keywords) or sum(token in text for token in profile_signals) >= 4

    @staticmethod
    def _is_profile_update_request(text: str) -> bool:
        keywords = (
            "\u66f4\u65b0\u753b\u50cf",
            "\u4fee\u6539\u753b\u50cf",
            "\u66f4\u65b0\u6863\u6848",
            "\u4fee\u6539\u6863\u6848",
            "\u4f53\u91cd\u53d8\u6210",
            "\u6211\u60f3\u66f4\u65b0",
        )
        return any(keyword in text for keyword in keywords)

    @staticmethod
    def _is_show_profile_request(text: str) -> bool:
        keywords = (
            "\u67e5\u770b\u753b\u50cf",
            "\u6211\u7684\u753b\u50cf",
            "\u770b\u770b\u753b\u50cf",
            "\u6211\u7684\u6863\u6848",
            "\u770b\u770b\u6863\u6848",
        )
        return any(keyword in text for keyword in keywords)

    @staticmethod
    def _is_plan_request(text: str) -> bool:
        keywords = (
            "\u751f\u6210\u8ba1\u5212",
            "\u8bad\u7ec3\u8ba1\u5212",
            "\u8fd9\u5468\u600e\u4e48\u7ec3",
            "\u672c\u5468\u600e\u4e48\u7ec3",
            "\u5b89\u6392\u4e00\u4e0b",
            "\u672c\u5468\u5b89\u6392",
        )
        return any(keyword in text for keyword in keywords)

    @staticmethod
    def _is_show_plan_request(text: str) -> bool:
        keywords = (
            "\u67e5\u770b\u8ba1\u5212",
            "\u770b\u770b\u8ba1\u5212",
            "\u6211\u7684\u8ba1\u5212",
            "\u8fd9\u5468\u7684\u8ba1\u5212",
            "\u4e0a\u6b21\u7684\u8ba1\u5212",
        )
        return any(keyword in text for keyword in keywords)

    @staticmethod
    def _is_feedback_request(text: str) -> bool:
        keywords = (
            "\u6253\u5361",
            "\u6211\u4eca\u5929\u7ec3",
            "\u4eca\u5929\u7ec3\u4e86",
            "\u4eca\u5929\u6ca1\u7ec3",
            "\u672a\u8bad\u7ec3",
            "\u5b8c\u6210\u5ea6",
            "\u75b2\u52b3",
            "\u6709\u70b9\u7d2f",
            "\u5f88\u7d2f",
        )
        return any(keyword in text for keyword in keywords)

    @staticmethod
    def _is_show_feedback_request(text: str) -> bool:
        keywords = (
            "\u67e5\u770b\u6253\u5361",
            "\u770b\u770b\u6253\u5361",
            "\u6253\u5361\u8bb0\u5f55",
            "\u6211\u7684\u8bb0\u5f55",
            "\u6700\u8fd1\u7684\u6253\u5361",
        )
        return any(keyword in text for keyword in keywords)

    @staticmethod
    def _is_adjustment_request(text: str) -> bool:
        keywords = (
            "\u8c03\u6574\u5efa\u8bae",
            "\u600e\u4e48\u8c03",
            "\u600e\u4e48\u8c03\u6574",
            "\u7ed9\u6211\u5efa\u8bae",
            "\u6700\u8fd1\u5f88\u7d2f",
            "\u6062\u590d\u5efa\u8bae",
            "\u91cd\u65b0\u5b89\u6392",
        )
        return any(keyword in text for keyword in keywords)

    @staticmethod
    def _is_show_adjustment_request(text: str) -> bool:
        keywords = (
            "\u67e5\u770b\u5efa\u8bae",
            "\u770b\u770b\u5efa\u8bae",
            "\u4e0a\u6b21\u7684\u5efa\u8bae",
            "\u6700\u8fd1\u7684\u5efa\u8bae",
            "\u8c03\u6574\u8bb0\u5f55",
        )
        return any(keyword in text for keyword in keywords)

    def _extract_profile_params(self, text: str) -> dict[str, Any]:
        params: dict[str, Any] = {}
        if match := re.search("(\u7537|\u5973)", text):
            params["gender"] = match.group(1)
        if match := re.search("(\\d{1,2})\\s*\u5c81", text):
            params["age"] = match.group(1)
        if match := re.search("(\\d{3})\\s*(?:cm|\u5398\u7c73)", text, flags=re.IGNORECASE):
            params["height"] = match.group(1)
        if match := re.search("(\\d{2,3}(?:\\.\\d+)?)\\s*(?:kg|\u516c\u65a4)", text, flags=re.IGNORECASE):
            params["weight"] = match.group(1)
        if match := re.search("\u6bcf\u5468\\s*(\\d(?:\\s*-\\s*\\d)?)\\s*\u6b21", text):
            params["training_days_per_week"] = match.group(1).replace(" ", "")
        if match := re.search("\u6bcf\u6b21\\s*(\\d{2,3}(?:\\s*-\\s*\\d{2,3})?)\\s*\u5206\u949f", text):
            params["session_duration"] = match.group(1).replace(" ", "")

        for raw in (
            "\u51cf\u8102\u4fdd\u808c",
            "\u51cf\u8102\u548c\u589e\u808c",
            "\u8fb9\u51cf\u8102\u8fb9\u589e\u808c",
            "\u7626\u808c\u589e\u808c",
            "\u589e\u808c",
            "\u51cf\u8102",
            "\u65b0\u624b\u5165\u95e8",
            "\u65b0\u624b",
            "\u7ef4\u6301",
        ):
            if raw in text:
                params["goal"] = raw
                break

        for raw in (
            "\u65b0\u624b",
            "\u521d\u7ea7",
            "\u4e2d\u7ea7",
            "\u96f6\u57fa\u7840",
            "\u7cfb\u7edf\u5065\u8eab\u4e09\u4e2a\u6708",
            "\u7ec3\u4e86\u4e00\u5e74",
        ):
            if raw in text:
                params["experience_level"] = raw
                break

        for raw in (
            "\u5546\u4e1a\u5065\u8eab\u623f",
            "\u6821\u56ed\u5065\u8eab\u623f",
            "\u5b66\u6821\u5065\u8eab\u623f",
            "\u5b66\u6821",
            "\u5bbf\u820d",
            "\u5bdd\u5ba4",
            "\u5bb6\u91cc",
            "\u5728\u5bb6",
        ):
            if raw in text:
                params["environment"] = raw
                break

        for raw in (
            "\u98df\u5802\u4e3a\u4e3b",
            "\u5b66\u6821\u98df\u5802",
            "\u5916\u5356\u4e3a\u4e3b",
            "\u5916\u5356",
            "\u81ea\u5df1\u505a\u996d",
            "\u81ea\u5df1\u4e0b\u53a8",
            "\u5fcc\u53e3",
            "\u65e0",
        ):
            if raw in text:
                params["diet_constraint"] = raw
                break

        if match := re.search("\u8584\u5f31(?:\u90e8\u4f4d)?[\u662f\u4e3a:\uff1a ]*([^\n\uff0c\u3002,;\uff1b]+)", text):
            params["weak_points"] = match.group(1).strip()
        if match := re.search("(?:\u4f24\u75c5|\u53d7\u4f24|\u53d7\u9650)[\u662f\u4e3a:\uff1a ]*([^\n\uff0c\u3002,;\uff1b]+)", text):
            params["injury_notes"] = match.group(1).strip()
        if match := re.search("(?:\u5f53\u524d\u5206\u5316|\u5206\u5316)[\u662f\u4e3a:\uff1a ]*([^\n\uff0c\u3002,;\uff1b]+)", text):
            params["current_split"] = match.group(1).strip()

        return params

    def _extract_plan_params(self, text: str) -> dict[str, Any]:
        params: dict[str, Any] = {}
        week_date = None
        if match := re.search("(\\d{4}-\\d{2}-\\d{2})", text):
            week_date = date.fromisoformat(match.group(1))
        elif any(token in text for token in ("\u4eca\u5929", "\u8fd9\u5468", "\u672c\u5468")):
            week_date = date.today()
        elif "\u4e0b\u5468" in text:
            week_date = date.today() + timedelta(days=7)
        if week_date is not None:
            params["week_start_date"] = week_date
        return params

    def _extract_feedback_params(self, text: str) -> dict[str, Any]:
        params: dict[str, Any] = {
            "feedback_date": self._extract_relative_date(text),
            "trained_today": True,
            "completed_exercises": [],
            "soreness_notes": "",
            "extra_notes": "",
        }

        if any(
            keyword in text
            for keyword in (
                "\u6ca1\u7ec3",
                "\u672a\u8bad\u7ec3",
                "\u4eca\u5929\u4f11\u606f",
                "\u4eca\u5929\u6ca1\u53bb",
                "\u4eca\u5929\u6ca1\u8bad\u7ec3",
            )
        ):
            params["trained_today"] = False

        if match := re.search("(?:\u5b8c\u6210\u5ea6|\u5b8c\u6210\u4e86|\u505a\u5230\u4e86)\\s*[:\uff1a ]?(\\d+(?:\\.\\d+)?%?)", text):
            params["completion_rate"] = match.group(1)
        elif match := re.search("(\\d+(?:\\.\\d+)?)\\s*%", text):
            params["completion_rate"] = f"{match.group(1)}%"

        if match := re.search("(?:\u75b2\u52b3|\u75b2\u60eb|\u52b3\u7d2f)[\u7b49\u7ea7\u5ea6]?\\s*[:\uff1a ]?([1-5])", text):
            params["fatigue_level"] = match.group(1)
        else:
            for raw in ("\u6709\u70b9\u7d2f", "\u5f88\u7d2f", "\u7206\u7d2f", "\u4e00\u822c", "\u8f7b\u677e"):
                if raw in text:
                    params["fatigue_level"] = raw
                    break

        for raw in (
            "\u57fa\u672c\u8fbe\u6807",
            "\u8fd8\u884c",
            "\u672a\u8fbe\u6807",
            "\u6ca1\u8fbe\u6807",
            "\u996e\u98df\u5d29\u4e86",
            "\u8fbe\u6807",
        ):
            if raw in text:
                params["diet_adherence"] = raw
                break

        if match := re.search("(?:\u9178\u75db|\u75bc)[\u662f\u4e3a:\uff1a ]*([^\n\u3002\uff1b;]+)", text):
            params["soreness_notes"] = match.group(1).strip()

        if params["trained_today"]:
            params["completed_exercises"] = self._extract_exercises(text)

        if match := re.search("(?:\u5907\u6ce8|\u8865\u5145|\u53e6\u5916)[\u662f\u4e3a:\uff1a ]*([^\n]+)", text):
            params["extra_notes"] = match.group(1).strip()

        return params

    @staticmethod
    def _extract_relative_date(text: str) -> date:
        if match := re.search("(\\d{4}-\\d{2}-\\d{2})", text):
            return date.fromisoformat(match.group(1))
        today = date.today()
        if "\u6628\u5929" in text:
            return today - timedelta(days=1)
        if "\u524d\u5929" in text:
            return today - timedelta(days=2)
        return today

    @staticmethod
    def _extract_exercises(text: str) -> list[str]:
        match = re.search("(?:\u7ec3\u4e86|\u505a\u4e86|\u5b8c\u6210\u4e86)([^\u3002\uff1b;\n]+)", text)
        if not match:
            return []
        segment = match.group(1)
        segment = re.split(
            "(?:\u5b8c\u6210\u5ea6|\u75b2\u52b3|\u996e\u98df|\u6709\u70b9\u7d2f|\u5f88\u7d2f|\u9178\u75db)",
            segment,
        )[0]
        parts = re.split("[\u3001,\uff0c/+]|\u548c|\u53ca", segment)
        cleaned = []
        for part in parts:
            item = part.strip(" \uff1a:,\uff0c\u3002\uff1b;")
            if not item or item in {"\u4eca\u5929", "\u8bad\u7ec3", "\u52a8\u4f5c"}:
                continue
            cleaned.append(item)
        return cleaned

    def _load_last_user_id(self) -> str | None:
        try:
            if not self.state_path.exists():
                return None
            data = json.loads(self.state_path.read_text(encoding="utf-8"))
            user_id = str(data.get("last_user_id", "")).strip()
            return user_id or None
        except Exception:
            return None

    def _save_last_user_id(self, user_id: str) -> None:
        if not user_id or user_id == "default":
            return
        self.state_path.write_text(
            json.dumps({"last_user_id": user_id}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
