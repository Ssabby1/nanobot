"""LLM-backed routing fallback for the fitness MVP."""

from __future__ import annotations

import json
from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, Field

from nanobot.fitness.router import (
    FIELD_LABELS,
    PROFILE_REQUIRED_FIELDS,
    FitnessRuleRouter,
    RouteDecision,
)
from nanobot.fitness.service import FitnessService
from nanobot.providers.base import LLMProvider


FitnessAction = Literal[
    "none",
    "save_profile",
    "update_profile",
    "show_profile",
    "generate_weekly_plan",
    "show_weekly_plan",
    "record_feedback",
    "show_feedback",
    "generate_adjustment",
    "show_adjustment",
]


ACTION_REASONS = {
    "save_profile": "建档",
    "update_profile": "更新档案",
    "show_profile": "查看档案",
    "generate_weekly_plan": "生成周计划",
    "show_weekly_plan": "查看周计划",
    "record_feedback": "记录打卡",
    "show_feedback": "查看打卡",
    "generate_adjustment": "生成调整建议",
    "show_adjustment": "查看调整建议",
}

ACTION_ARGUMENT_HINTS = {
    "save_profile": PROFILE_REQUIRED_FIELDS + ["current_split", "weak_points", "injury_notes"],
    "update_profile": PROFILE_REQUIRED_FIELDS + ["current_split", "weak_points", "injury_notes"],
    "show_profile": [],
    "generate_weekly_plan": ["week_start_date"],
    "show_weekly_plan": [],
    "record_feedback": [
        "feedback_date",
        "trained_today",
        "completed_exercises",
        "completion_rate",
        "fatigue_level",
        "soreness_notes",
        "diet_adherence",
        "extra_notes",
    ],
    "show_feedback": [],
    "generate_adjustment": [],
    "show_adjustment": [],
}

ACTION_EXECUTION_CONFIDENCE = {
    "save_profile": 0.6,
    "update_profile": 0.58,
    "show_profile": 0.5,
    "generate_weekly_plan": 0.58,
    "show_weekly_plan": 0.5,
    "record_feedback": 0.58,
    "show_feedback": 0.5,
    "generate_adjustment": 0.58,
    "show_adjustment": 0.5,
    "none": 1.0,
}

FOLLOWUP_CONFIDENCE = 0.35

_ROUTE_TOOL = [
    {
        "type": "function",
        "function": {
            "name": "route_fitness_request",
            "description": "Route the user's message into a structured fitness action.",
            "parameters": {
                "type": "object",
                "properties": {
                    "is_fitness_request": {
                        "type": "boolean",
                        "description": "Whether the message belongs to the fitness assistant domain.",
                    },
                    "action": {
                        "type": "string",
                        "enum": list(FitnessAction.__args__),  # type: ignore[attr-defined]
                        "description": "The chosen fitness action, or 'none' when the message is not for fitness.",
                    },
                    "confidence": {
                        "type": "number",
                        "description": "Confidence score from 0.0 to 1.0.",
                    },
                    "user_id": {
                        "type": ["string", "null"],
                        "description": "Resolved user identifier if present or inferred.",
                    },
                    "arguments": {
                        "type": "object",
                        "description": "Structured arguments for the chosen action.",
                        "additionalProperties": True,
                    },
                    "missing_fields": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Still-missing required fields if the action cannot run yet.",
                    },
                    "needs_followup": {
                        "type": "boolean",
                        "description": "Whether the assistant should ask a follow-up instead of executing immediately.",
                    },
                    "assistant_reply": {
                        "type": "string",
                        "description": "Concise Chinese reply shown when follow-up is needed or the request should not execute yet.",
                    },
                },
                "required": [
                    "is_fitness_request",
                    "action",
                    "confidence",
                    "needs_followup",
                    "assistant_reply",
                ],
            },
        },
    }
]

_SYSTEM_PROMPT = """You are the LLM routing layer for a Chinese fitness assistant.

Your job is NOT to answer with free-form coaching. Your job is to convert the user's latest message into one structured routing decision by calling the tool.

Rules:
1. Only choose from the allowed actions.
2. If the message is not about the fitness assistant domain, set is_fitness_request=false and action='none'.
3. Reuse the resolved user_id when the user is clearly continuing the same fitness task.
4. If there is a pending profile/create-update flow, treat short continuation messages as part of that flow unless the user clearly changed topics.
5. Normalize natural Chinese fitness phrasing when possible, such as:
   - 140斤 -> 70
   - 练了五年 / 老手 / 训练老手 -> 中级
   - 健身房训练 -> 健身房
   - 自己做饭 / 在家做饭 -> 自己做饭
   - 还行 / 基本达标 -> 基本达标
   - 有点累 -> 4
6. For save_profile, the required fields are:
   gender, age, height, weight, goal, experience_level, training_days_per_week, session_duration, environment, diet_constraint
7. For record_feedback, the required fields are:
   completion_rate, fatigue_level, diet_adherence
8. If required fields are missing, set needs_followup=true and list missing_fields.
9. assistant_reply must be concise Chinese. If follow-up is needed, keep it short and action-oriented.
10. Do not invent unsupported arguments. Only use arguments relevant to the chosen action.
"""


class FitnessLLMRouteResult(BaseModel):
    """Structured output from the LLM fitness router."""

    is_fitness_request: bool
    action: FitnessAction = "none"
    confidence: float = Field(ge=0.0, le=1.0)
    user_id: str | None = None
    arguments: dict[str, Any] = Field(default_factory=dict)
    missing_fields: list[str] = Field(default_factory=list)
    needs_followup: bool = False
    assistant_reply: str = ""


class FitnessLLMRouter:
    """LLM fallback router that emits structured action decisions."""

    def __init__(
        self,
        service: FitnessService,
        provider: LLMProvider,
        model: str,
        rule_router: FitnessRuleRouter | None = None,
    ):
        self.service = service
        self.provider = provider
        self.model = model
        self.rule_router = rule_router or FitnessRuleRouter(service)

    async def route(
        self,
        message: str,
        user_id: str | None = None,
        fallback_rule_decision: RouteDecision | None = None,
    ) -> FitnessLLMRouteResult | None:
        clean = (message or "").strip()
        if not clean:
            return None

        resolved_user_id = self.rule_router.infer_user_id(clean, explicit_user_id=user_id)
        pending = self.rule_router._load_state().get("pending_route")
        profile = self.service.get_profile(resolved_user_id) if resolved_user_id != "default" else None
        profile_summary = self.service.format_profile(profile) if profile else "无现有档案"

        fallback_summary = {
            "action": fallback_rule_decision.action if fallback_rule_decision else None,
            "reason": fallback_rule_decision.reason if fallback_rule_decision else "",
            "params": fallback_rule_decision.params if fallback_rule_decision else {},
            "missing_fields": fallback_rule_decision.missing_fields if fallback_rule_decision else [],
        }

        allowed_arguments = {action: fields for action, fields in ACTION_ARGUMENT_HINTS.items()}
        user_prompt = (
            f"今天日期: {date.today().isoformat()}\n"
            f"用户消息: {clean}\n"
            f"当前推断 user_id: {resolved_user_id}\n"
            f"当前档案摘要: {profile_summary}\n"
            f"待续流程: {json.dumps(pending, ensure_ascii=False) if pending else '无'}\n"
            f"规则路由结果: {json.dumps(fallback_summary, ensure_ascii=False)}\n"
            f"允许 action -> arguments: {json.dumps(allowed_arguments, ensure_ascii=False)}\n"
            f"字段中文标签: {json.dumps(FIELD_LABELS, ensure_ascii=False)}"
        )

        response = await self.provider.chat_with_retry(
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            tools=_ROUTE_TOOL,
            tool_choice={"type": "function", "function": {"name": "route_fitness_request"}},
            model=self.model,
            max_tokens=900,
            temperature=0.0,
        )
        if not response.has_tool_calls:
            return None

        args = response.tool_calls[0].arguments or {}
        result = FitnessLLMRouteResult.model_validate(args)
        return self._post_process(result, resolved_user_id)

    async def handle(
        self,
        message: str,
        user_id: str | None = None,
        fallback_rule_decision: RouteDecision | None = None,
    ) -> str | None:
        result = await self.route(message, user_id=user_id, fallback_rule_decision=fallback_rule_decision)
        if result is None or not result.is_fitness_request or result.action == "none":
            return None
        if result.confidence < FOLLOWUP_CONFIDENCE:
            return self._build_clarification_reply(result)

        effective_user_id = (result.user_id or self.rule_router.infer_user_id(message, explicit_user_id=user_id)).strip()
        if not effective_user_id:
            effective_user_id = "default"
        pending = self.rule_router._load_state().get("pending_route")
        followup_turn = 0
        if (
            isinstance(pending, dict)
            and pending.get("action") == result.action
            and str(pending.get("user_id", "")).strip() == effective_user_id
        ):
            followup_turn = int(pending.get("followup_turn", 0)) + 1

        decision = RouteDecision(
            action=result.action,
            params=result.arguments,
            missing_fields=list(result.missing_fields),
            reason=ACTION_REASONS.get(result.action, "LLM路由"),
            stateful=result.action in {"save_profile", "update_profile", "record_feedback"},
            user_id_override=effective_user_id,
            followup_turn=followup_turn,
        )

        if result.needs_followup or decision.missing_fields:
            self.rule_router._save_pending_route(decision, effective_user_id)
            if decision.missing_fields:
                return self.rule_router._format_missing_message(decision)
            return result.assistant_reply.strip()

        threshold = ACTION_EXECUTION_CONFIDENCE.get(result.action, 0.6)
        if result.confidence < threshold:
            if decision.stateful:
                self.rule_router._save_pending_route(decision, effective_user_id)
            return self._build_clarification_reply(result, decision=decision)

        reply = self.rule_router.execute(decision, user_id=effective_user_id)
        self.rule_router._clear_pending_route()
        self.rule_router._save_last_user_id(effective_user_id)
        return reply

    def _post_process(
        self,
        result: FitnessLLMRouteResult,
        resolved_user_id: str,
    ) -> FitnessLLMRouteResult:
        pending = self.rule_router._load_state().get("pending_route")
        pending_action = pending.get("action") if isinstance(pending, dict) else None
        pending_params = pending.get("params", {}) if isinstance(pending, dict) else {}

        if result.user_id is None:
            result.user_id = None if resolved_user_id == "default" else resolved_user_id

        if pending_action in {"save_profile", "update_profile", "record_feedback"}:
            if result.action == "none" and result.is_fitness_request:
                result.action = pending_action
            if result.action == pending_action:
                merged = dict(pending_params)
                merged.update(result.arguments)
                result.arguments = merged

        if result.action in {"save_profile", "update_profile"}:
            allowed = set(ACTION_ARGUMENT_HINTS[result.action])
            result.arguments = {k: v for k, v in result.arguments.items() if k in allowed}
            if result.action == "save_profile":
                recomputed_missing = [
                    field for field in PROFILE_REQUIRED_FIELDS if result.arguments.get(field) in (None, "")
                ]
                if recomputed_missing and not result.missing_fields:
                    result.missing_fields = recomputed_missing
                    result.needs_followup = True
        elif result.action == "record_feedback":
            allowed = set(ACTION_ARGUMENT_HINTS[result.action])
            result.arguments = {k: v for k, v in result.arguments.items() if k in allowed}
            recomputed_missing = [
                field
                for field in ("completion_rate", "fatigue_level", "diet_adherence")
                if result.arguments.get(field) in (None, "")
            ]
            if recomputed_missing and not result.missing_fields:
                result.missing_fields = recomputed_missing
                result.needs_followup = True
        else:
            allowed = set(ACTION_ARGUMENT_HINTS.get(result.action, []))
            result.arguments = {k: v for k, v in result.arguments.items() if k in allowed} if allowed else {}

        result.missing_fields = [field for field in result.missing_fields if field in FIELD_LABELS]
        return result

    def _build_followup_reply(self, action: str, missing_fields: list[str]) -> str:
        decision = RouteDecision(
            action=action,
            params={},
            missing_fields=list(missing_fields),
            reason=ACTION_REASONS.get(action, "当前这个需求"),
            stateful=action in {"save_profile", "update_profile", "record_feedback"},
            followup_turn=0,
        )
        return self.rule_router._format_missing_message(decision)

    def _build_clarification_reply(
        self,
        result: FitnessLLMRouteResult,
        decision: RouteDecision | None = None,
    ) -> str:
        if result.assistant_reply.strip():
            return result.assistant_reply.strip()
        if decision and decision.missing_fields:
            return self._build_followup_reply(decision.action or "none", decision.missing_fields)
        action_label = ACTION_REASONS.get(result.action, "这个需求")
        action_prompts = {
            "save_profile": "我猜你的意思是想先把档案建起来",
            "update_profile": "我猜你的意思是想改一下现在的档案",
            "record_feedback": "我猜你的意思是在补今天的训练反馈",
            "generate_weekly_plan": "我猜你的意思是想让我生成这周计划",
            "generate_adjustment": "我猜你的意思是想让我给你调一下计划",
        }
        prefix = action_prompts.get(result.action, f"我大概理解你是在说{action_label}")
        return (
            f"{prefix}，但把握还不够高。\n"
            "你可以再具体一点，直接补充你想改什么、缺什么，或者希望我帮你做什么。"
        )
