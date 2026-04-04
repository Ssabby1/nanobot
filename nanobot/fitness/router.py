"""Rule-based natural language routing for the fitness MVP."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
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

FOLLOWUP_FIELD_LIMIT = 2

ACTION_FIELD_PRIORITIES = {
    "save_profile": [
        "weight",
        "experience_level",
        "training_days_per_week",
        "session_duration",
        "environment",
        "diet_constraint",
        "goal",
        "gender",
        "age",
        "height",
    ],
    "update_profile": [
        "weight",
        "goal",
        "experience_level",
        "training_days_per_week",
        "session_duration",
        "environment",
        "diet_constraint",
        "gender",
        "age",
        "height",
    ],
    "record_feedback": [
        "completion_rate",
        "fatigue_level",
        "diet_adherence",
    ],
}

FIELD_REPLY_EXAMPLES = {
    "weight": "\u4f53\u91cd140\u65a4",
    "experience_level": "\u7ec3\u4e86\u4e94\u5e74",
    "training_days_per_week": "\u6bcf\u5468\u7ec34\u6b21",
    "session_duration": "\u6bcf\u6b2160\u5206\u949f",
    "environment": "\u5065\u8eab\u623f\u8bad\u7ec3",
    "diet_constraint": "\u81ea\u5df1\u505a\u996d",
    "goal": "\u76ee\u6807\u51cf\u8102",
    "gender": "\u7537",
    "age": "23\u5c81",
    "height": "176cm",
    "completion_rate": "\u5b8c\u6210\u5ea680%",
    "fatigue_level": "\u6709\u70b9\u7d2f",
    "diet_adherence": "\u996e\u98df\u8fd8\u884c",
}

FIELD_QUESTION_PROMPTS = {
    "gender": "\u4f60\u662f\u7537\u751f\u8fd8\u662f\u5973\u751f\uff1f",
    "age": "\u4f60\u4eca\u5e74\u591a\u5927\uff1f",
    "height": "\u4f60\u8eab\u9ad8\u5927\u6982\u591a\u5c11\uff1f",
    "weight": "\u4f60\u73b0\u5728\u4f53\u91cd\u5927\u6982\u591a\u5c11\uff1f",
    "goal": "\u4f60\u8fd9\u6b21\u66f4\u504f\u5411\u51cf\u8102\uff0c\u589e\u808c\uff0c\u8fd8\u662f\u4fdd\u6301\u4f53\u80fd\uff1f",
    "experience_level": "\u4f60\u5e73\u65f6\u8bad\u7ec3\u5927\u6982\u662f\u65b0\u624b\uff0c\u521d\u7ea7\uff0c\u8fd8\u662f\u5df2\u7ecf\u7ec3\u4e86\u51e0\u5e74\uff1f",
    "training_days_per_week": "\u4f60\u73b0\u5728\u4e00\u822c\u6bcf\u5468\u80fd\u7ec3\u51e0\u5929\uff1f",
    "session_duration": "\u4f60\u6bcf\u6b21\u8bad\u7ec3\u5927\u6982\u80fd\u62ff\u51fa\u591a\u5c11\u65f6\u95f4\uff1f",
    "environment": "\u4f60\u4e3b\u8981\u662f\u5728\u5bb6\u7ec3\uff0c\u5065\u8eab\u623f\u7ec3\uff0c\u8fd8\u662f\u5176\u4ed6\u73af\u5883\uff1f",
    "diet_constraint": "\u4f60\u5e73\u65f6\u5403\u996d\u66f4\u63a5\u8fd1\u81ea\u5df1\u505a\uff0c\u5916\u5356\u4e3a\u4e3b\uff0c\u8fd8\u662f\u6709\u5176\u4ed6\u996e\u98df\u9650\u5236\uff1f",
    "completion_rate": "\u4eca\u5929\u8fd9\u6b21\u8bad\u7ec3\u5927\u6982\u5b8c\u6210\u4e86\u591a\u5c11\uff1f",
    "fatigue_level": "\u7ec3\u5b8c\u6216\u8005\u4eca\u5929\u6574\u4f53\u611f\u89c9\u7d2f\u4e0d\u7d2f\uff1f",
    "diet_adherence": "\u4eca\u5929\u996e\u98df\u5927\u6982\u8fbe\u6807\u4e86\u5417\uff1f",
}


@dataclass
class RouteDecision:
    """Routing result before execution."""

    action: str | None
    params: dict[str, Any] = field(default_factory=dict)
    missing_fields: list[str] = field(default_factory=list)
    reason: str = ""
    stateful: bool = False
    user_id_override: str | None = None
    followup_turn: int = 0


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
        pending = self._continue_pending_route(clean, resolved_user_id)
        if pending:
            effective_user_id = pending.user_id_override or resolved_user_id
            if pending.missing_fields:
                self._save_pending_route(pending, effective_user_id)
                return self._format_missing_message(pending)
            result = self.execute(pending, user_id=effective_user_id)
            self._clear_pending_route()
            self._save_last_user_id(effective_user_id)
            return result

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
            self._save_pending_route(decision, resolved_user_id)
            return self._format_missing_message(decision)

        result = self.execute(decision, user_id=resolved_user_id)
        self._clear_pending_route()
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
        if pending_user_id := self._load_pending_user_id():
            return pending_user_id
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
                stateful=True,
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
                stateful=True,
            )

        inferred_profile = self._extract_profile_params(text)
        has_profile_intro = any(token in text for token in ("\u6211\u53eb", "\u6211\u7684\u540d\u5b57\u662f", "\u53eb\u6211"))
        if len(inferred_profile) >= 4 or (has_profile_intro and len(inferred_profile) >= 3):
            missing = [field for field in PROFILE_REQUIRED_FIELDS if inferred_profile.get(field) in (None, "")]
            return RouteDecision(
                action="save_profile",
                params=inferred_profile,
                missing_fields=missing,
                reason="\u5efa\u6863",
                stateful=True,
            )

        return RouteDecision(action=None)

    def _continue_pending_route(self, text: str, user_id: str) -> RouteDecision | None:
        state = self._load_state()
        pending = state.get("pending_route")
        if not isinstance(pending, dict):
            return None

        action = pending.get("action")
        if action not in {"save_profile", "update_profile", "record_feedback"}:
            return None

        pending_user_id = str(pending.get("user_id", "")).strip() or user_id
        if user_id not in {"default", pending_user_id} and pending_user_id != user_id:
            return None

        current = self.route(text, user_id=user_id)
        if current.action and current.action != action:
            return None

        if action == "record_feedback":
            new_params = self._extract_feedback_params(text)
        else:
            new_params = self._extract_profile_params(text)
        if not new_params and current.action != action:
            return None

        merged = dict(pending.get("params", {}))
        merged.update(new_params)
        if action == "record_feedback":
            missing = [
                field
                for field in ("completion_rate", "fatigue_level", "diet_adherence")
                if merged.get(field) in (None, "")
            ]
        else:
            missing = [field for field in PROFILE_REQUIRED_FIELDS if merged.get(field) in (None, "")]
        return RouteDecision(
            action=action,
            params=merged,
            missing_fields=missing if action in {"save_profile", "record_feedback"} else [],
            reason=(
                "\u8865\u5145\u5efa\u6863\u4fe1\u606f"
                if action == "save_profile"
                else "\u8865\u5145\u6253\u5361\u4fe1\u606f"
                if action == "record_feedback"
                else "\u8865\u5145\u66f4\u65b0\u4fe1\u606f"
            ),
            stateful=True,
            user_id_override=pending_user_id,
            followup_turn=int(pending.get("followup_turn", 0)) + 1,
        )

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
        elif match := re.search("(\\d{2,3}(?:\\.\\d+)?)\\s*\u65a4", text):
            params["weight"] = str(round(float(match.group(1)) / 2, 1))
        if match := re.search("\u6bcf\u5468(?:\u8bad\u7ec3|\u7ec3)?\\s*(\\d(?:\\s*-\\s*\\d)?)\\s*\u6b21", text):
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

        experience_aliases = (
            ("\u65b0\u624b", "\u65b0\u624b"),
            ("\u521d\u7ea7", "\u521d\u7ea7"),
            ("\u4e2d\u7ea7", "\u4e2d\u7ea7"),
            ("\u8001\u624b", "\u4e2d\u7ea7"),
            ("\u8001\u9e1f", "\u4e2d\u7ea7"),
            ("\u6709\u7ecf\u9a8c", "\u4e2d\u7ea7"),
            ("\u96f6\u57fa\u7840", "\u65b0\u624b"),
            ("\u7cfb\u7edf\u5065\u8eab\u4e09\u4e2a\u6708", "\u521d\u7ea7"),
            ("\u7ec3\u4e86\u4e00\u5e74", "\u4e2d\u7ea7"),
        )
        for raw, normalized in experience_aliases:
            if raw in text:
                params["experience_level"] = normalized
                break
        if "experience_level" not in params:
            if re.search("(?:\u7ec3|\u9501\u70bc|\u5065\u8eab).{0,4}(\\d+)\\s*\u5e74", text):
                params["experience_level"] = "\u4e2d\u7ea7"
            elif "\u4e94\u5e74" in text or "\u591a\u5e74" in text:
                params["experience_level"] = "\u4e2d\u7ea7"

        for raw in (
            "\u5546\u4e1a\u5065\u8eab\u623f",
            "\u5065\u8eab\u623f",
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
            "\u5728\u5bb6\u505a\u996d",
            "\u5bb6\u91cc\u505a\u996d",
            "\u81ea\u5df1\u5728\u5bb6\u505a\u996d",
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
            params["completion_rate"] = 0.0

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

    def _format_missing_message(self, decision: RouteDecision) -> str:
        missing_labels = [FIELD_LABELS.get(field, field) for field in decision.missing_fields]
        all_missing = "\u3001".join(missing_labels)
        focus_fields = self._pick_focus_missing_fields(
            decision.action,
            decision.missing_fields,
            decision.params,
        )
        lead = self._build_followup_lead(decision, focus_fields)
        question = self._build_followup_question(decision.action, focus_fields, decision.params)
        example = self._build_followup_example(focus_fields)

        if len(decision.missing_fields) <= FOLLOWUP_FIELD_LIMIT:
            return (
                f"{lead}\n"
                f"\u8fd8\u5dee {all_missing} \u8fd9\u4e9b\u4fe1\u606f\u3002\n"
                f"{question}\n"
                f"\u4f60\u76f4\u63a5\u8865\u5145\u5c31\u884c\uff0c\u6bd4\u5982\uff1a{example}"
            )

        rest_fields = [field for field in decision.missing_fields if field not in focus_fields]
        rest_labels = "\u3001".join(FIELD_LABELS.get(field, field) for field in rest_fields)
        return (
            f"{lead}\n"
            f"{question}\n"
            f"\u4f60\u53ef\u4ee5\u76f4\u63a5\u8fd9\u6837\u56de\uff1a{example}\n"
            f"\u5176\u4ed6\u8fd8\u7f3a\uff1a{rest_labels}\uff0c\u540e\u9762\u53ef\u4ee5\u63a5\u7740\u8865\u3002"
        )

    def _pick_focus_missing_fields(
        self,
        action: str | None,
        missing_fields: list[str],
        params: dict[str, Any] | None = None,
    ) -> list[str]:
        params = params or {}
        adaptive = self._pick_adaptive_focus_fields(action, missing_fields, params)
        if adaptive:
            return adaptive[:FOLLOWUP_FIELD_LIMIT]

        priorities = ACTION_FIELD_PRIORITIES.get(action or "", [])
        ordered: list[str] = []
        for field in priorities:
            if field in missing_fields and field not in ordered:
                ordered.append(field)
        for field in missing_fields:
            if field not in ordered:
                ordered.append(field)
        return ordered[:FOLLOWUP_FIELD_LIMIT]

    def _pick_adaptive_focus_fields(
        self,
        action: str | None,
        missing_fields: list[str],
        params: dict[str, Any],
    ) -> list[str]:
        if not missing_fields:
            return []

        if action == "save_profile":
            basics_missing = [f for f in ("weight", "height", "age", "gender", "goal") if f in missing_fields]
            schedule_missing = [f for f in ("experience_level", "training_days_per_week", "session_duration") if f in missing_fields]
            context_missing = [f for f in ("environment", "diet_constraint") if f in missing_fields]

            if "goal" in missing_fields and "weight" in missing_fields:
                return ["weight", "goal"]
            if basics_missing and not any(params.get(k) in (None, "") for k in ("gender", "age", "height")):
                return basics_missing[:FOLLOWUP_FIELD_LIMIT]
            if schedule_missing and {"gender", "age", "height", "weight", "goal"}.issubset(set(params.keys())):
                return schedule_missing[:FOLLOWUP_FIELD_LIMIT]
            if context_missing and not basics_missing and not schedule_missing:
                return context_missing[:FOLLOWUP_FIELD_LIMIT]

        if action == "record_feedback":
            if params.get("trained_today") is False:
                preferred = [f for f in ("fatigue_level", "diet_adherence") if f in missing_fields]
                if preferred:
                    return preferred
            return [f for f in ("completion_rate", "fatigue_level", "diet_adherence") if f in missing_fields]

        return []

    def _build_followup_example(self, fields: list[str]) -> str:
        parts = [FIELD_REPLY_EXAMPLES.get(field, f"{FIELD_LABELS.get(field, field)}...") for field in fields]
        return "\uff0c".join(parts)

    def _build_followup_lead(self, decision: RouteDecision, focus_fields: list[str]) -> str:
        action = decision.action or ""
        params = decision.params or {}
        followup_turn = max(decision.followup_turn, 0)

        if followup_turn >= 1:
            if action == "save_profile":
                return "\u6211\u4eec\u63a5\u7740\u628a\u5269\u4e0b\u7684\u8865\u5b8c\uff0c\u8fd9\u6b21\u5148\u786e\u8ba4\u4e24\u4e2a\u5173\u952e\u7684\u3002"
            if action == "update_profile":
                return "\u521a\u624d\u90a3\u6bb5\u6211\u63a5\u4f4f\u4e86\uff0c\u6211\u4eec\u7ee7\u7eed\u628a\u8fd9\u6b21\u66f4\u65b0\u8865\u5b8c\u3002"
            if action == "record_feedback":
                if params.get("trained_today") is False:
                    return "\u4f11\u606f\u65e5\u8fd9\u5757\u6211\u5df2\u7ecf\u8ddf\u4e0a\u4e86\uff0c\u518d\u8865\u4e24\u4e2a\u72b6\u6001\u4fe1\u606f\u5c31\u884c\u3002"
                return "\u8fd9\u6b21\u6253\u5361\u6211\u63a5\u7740\u5e2e\u4f60\u8865\uff0c\u518d\u786e\u8ba4\u4e24\u4e2a\u70b9\u5c31\u80fd\u8bb0\u4e0b\u6765\u3002"

        if action == "save_profile":
            if {"gender", "age", "height"}.issubset(set(params.keys())):
                return "\u57fa\u7840\u4fe1\u606f\u6211\u5148\u8bb0\u4e0b\u4e86\uff0c\u518d\u8865\u4e24\u4e2a\u5173\u952e\u7684\u5c31\u80fd\u7ee7\u7eed\u3002"
            return "\u5df2\u7ecf\u5f00\u59cb\u7ed9\u4f60\u5efa\u6863\u4e86\uff0c\u6211\u5148\u95ee\u4f60\u4e24\u4e2a\u5173\u952e\u7684\u3002"

        if action == "update_profile":
            if params:
                return "\u4f60\u8fd9\u6b21\u60f3\u8c03\u6574\u7684\u65b9\u5411\u6211\u5927\u6982\u660e\u767d\u4e86\uff0c\u518d\u786e\u8ba4\u4e24\u4e2a\u70b9\u5c31\u884c\u3002"
            return "\u6211\u5148\u5e2e\u4f60\u628a\u8fd9\u6b21\u66f4\u65b0\u7406\u987a\uff0c\u5148\u786e\u8ba4\u4e24\u4e2a\u5173\u952e\u4fe1\u606f\u3002"

        if action == "record_feedback":
            if params.get("trained_today") is False:
                return "\u4f11\u606f\u65e5\u4e5f\u53ef\u4ee5\u8bb0\u4e00\u4e0b\u72b6\u6001\uff0c\u6211\u5148\u95ee\u4f60\u4e24\u4e2a\u6700\u5173\u952e\u7684\u3002"
            if params.get("completed_exercises"):
                return "\u4eca\u5929\u7ec3\u4e86\u4ec0\u4e48\u6211\u8bb0\u4f4f\u4e86\uff0c\u518d\u8865\u4e24\u4e2a\u611f\u53d7\u7c7b\u4fe1\u606f\u5c31\u884c\u3002"
            return "\u8fd9\u6b21\u6253\u5361\u6211\u5148\u63a5\u4f4f\u4e86\uff0c\u518d\u8865\u4e24\u4e2a\u5173\u952e\u4fe1\u606f\u5c31\u80fd\u8bb0\u4e0b\u6765\u3002"

        focus_labels = "\u3001".join(FIELD_LABELS.get(field, field) for field in focus_fields)
        return f"\u5df2\u8bc6\u522b\u4e3a\u201c{decision.reason}\u201d\uff0c\u6211\u5148\u786e\u8ba4 {focus_labels} \u3002"

    def _build_followup_question(
        self,
        action: str | None,
        fields: list[str],
        params: dict[str, Any] | None = None,
    ) -> str:
        fields = [field for field in fields if field in FIELD_LABELS]
        if not fields:
            return "\u4f60\u76f4\u63a5\u628a\u8fd8\u7f3a\u7684\u4fe1\u606f\u8865\u5145\u4e00\u4e0b\u5c31\u884c\u3002"

        pair = tuple(fields[:2])
        pair_templates = {
            ("weight", "goal"): "\u4f60\u73b0\u5728\u4f53\u91cd\u5927\u6982\u591a\u5c11\uff1f\u53e6\u5916\u4f60\u8fd9\u6b21\u66f4\u504f\u5411\u51cf\u8102\u8fd8\u662f\u589e\u808c\uff1f",
            ("weight", "experience_level"): "\u4f60\u73b0\u5728\u4f53\u91cd\u5927\u6982\u591a\u5c11\uff1f\u53e6\u5916\u4f60\u5e73\u65f6\u8bad\u7ec3\u5927\u6982\u5728\u4ec0\u4e48\u9636\u6bb5\uff1f",
            ("training_days_per_week", "session_duration"): "\u4f60\u73b0\u5728\u4e00\u822c\u6bcf\u5468\u80fd\u7ec3\u51e0\u5929\uff1f\u6bcf\u6b21\u5927\u6982\u80fd\u7ec3\u591a\u4e45\uff1f",
            ("environment", "diet_constraint"): "\u4f60\u73b0\u5728\u4e3b\u8981\u662f\u5728\u54ea\u91cc\u8bad\u7ec3\uff1f\u996e\u98df\u4e0a\u66f4\u63a5\u8fd1\u81ea\u5df1\u505a\u8fd8\u662f\u5916\u5356\u4e3a\u4e3b\uff1f",
            ("completion_rate", "fatigue_level"): "\u4eca\u5929\u8fd9\u6b21\u8bad\u7ec3\u5927\u6982\u5b8c\u6210\u4e86\u591a\u5c11\uff1f\u7ec3\u5b8c\u611f\u89c9\u7d2f\u4e0d\u7d2f\uff1f",
            ("fatigue_level", "diet_adherence"): "\u4eca\u5929\u6574\u4f53\u72b6\u6001\u611f\u89c9\u7d2f\u4e0d\u7d2f\uff1f\u996e\u98df\u5927\u6982\u8fbe\u6807\u4e86\u5417\uff1f",
        }
        if pair in pair_templates:
            return pair_templates[pair]

        prompts = [FIELD_QUESTION_PROMPTS.get(field, f"\u8bf7\u8865\u5145{FIELD_LABELS.get(field, field)}\u3002") for field in fields[:2]]
        if len(prompts) == 1:
            return prompts[0]
        return "\u53e6\u5916\uff0c".join((prompts[0], prompts[1]))

    def _load_state(self) -> dict[str, Any]:
        try:
            if not self.state_path.exists():
                return {}
            data = json.loads(self.state_path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _save_state(self, data: dict[str, Any]) -> None:
        self.state_path.write_text(
            json.dumps(self._to_json_safe(data), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _save_pending_route(self, decision: RouteDecision, user_id: str) -> None:
        if not decision.action or decision.action not in {"save_profile", "update_profile", "record_feedback"}:
            return
        state = self._load_state()
        state["pending_route"] = {
            "action": decision.action,
            "user_id": user_id,
            "params": decision.params,
            "followup_turn": decision.followup_turn,
        }
        self._save_state(state)

    def _clear_pending_route(self) -> None:
        state = self._load_state()
        if "pending_route" in state:
            state.pop("pending_route", None)
            self._save_state(state)

    @staticmethod
    def _to_json_safe(value: Any) -> Any:
        if isinstance(value, (date, datetime)):
            return value.isoformat()
        if isinstance(value, dict):
            return {k: FitnessRuleRouter._to_json_safe(v) for k, v in value.items()}
        if isinstance(value, list):
            return [FitnessRuleRouter._to_json_safe(item) for item in value]
        return value

    def _load_last_user_id(self) -> str | None:
        try:
            data = self._load_state()
            user_id = str(data.get("last_user_id", "")).strip()
            return user_id or None
        except Exception:
            return None

    def _load_pending_user_id(self) -> str | None:
        try:
            pending = self._load_state().get("pending_route")
            if not isinstance(pending, dict):
                return None
            user_id = str(pending.get("user_id", "")).strip()
            return user_id or None
        except Exception:
            return None

    def _save_last_user_id(self, user_id: str) -> None:
        if not user_id or user_id == "default":
            return
        state = self._load_state()
        state["last_user_id"] = user_id
        self._save_state(state)
