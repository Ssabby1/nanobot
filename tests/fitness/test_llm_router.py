import pytest

from nanobot.fitness.llm_router import FitnessLLMRouter
from nanobot.fitness.service import FitnessService
from nanobot.providers.base import LLMProvider, LLMResponse, ToolCallRequest


class DummyProvider(LLMProvider):
    def __init__(self, responses: list[LLMResponse]):
        super().__init__()
        self._responses = list(responses)

    async def chat(self, *args, **kwargs) -> LLMResponse:
        if self._responses:
            return self._responses.pop(0)
        return LLMResponse(content="", tool_calls=[])

    def get_default_model(self) -> str:
        return "test-model"


@pytest.mark.asyncio
async def test_llm_router_can_fallback_to_update_profile(tmp_path):
    service = FitnessService(tmp_path)
    service.save_profile(
        user_id="sasa",
        gender="男",
        age=23,
        height=176,
        weight=70,
        goal="减脂",
        experience_level="初级",
        training_days_per_week=4,
        session_duration=60,
        environment="商业健身房",
        diet_constraint="外卖为主",
    )

    provider = DummyProvider(
        [
            LLMResponse(
                content="",
                tool_calls=[
                    ToolCallRequest(
                        id="fit1",
                        name="route_fitness_request",
                        arguments={
                            "is_fitness_request": True,
                            "action": "update_profile",
                            "confidence": 0.92,
                            "user_id": "sasa",
                            "arguments": {
                                "environment": "家里",
                                "diet_constraint": "自己做饭",
                            },
                            "missing_fields": [],
                            "needs_followup": False,
                            "assistant_reply": "",
                        },
                    )
                ],
            )
        ]
    )

    router = FitnessLLMRouter(service=service, provider=provider, model="test-model")
    result = await router.handle("我叫sasa，把我的资料改成在家练，自己做饭")

    assert result is not None
    assert "已更新画像" in result
    assert "家里 / 自己做饭" in result


@pytest.mark.asyncio
async def test_llm_router_can_continue_pending_profile_completion(tmp_path):
    service = FitnessService(tmp_path)
    from nanobot.fitness.router import FitnessRuleRouter

    base_router = FitnessRuleRouter(service)
    first = base_router.handle("我叫sasa，男，23岁，176cm，目标减脂")
    assert "我先需要你补充" in first
    assert "体重" in first
    assert "训练经验" in first

    provider = DummyProvider(
        [
            LLMResponse(
                content="",
                tool_calls=[
                    ToolCallRequest(
                        id="fit2",
                        name="route_fitness_request",
                        arguments={
                            "is_fitness_request": True,
                            "action": "save_profile",
                            "confidence": 0.95,
                            "user_id": "sasa",
                            "arguments": {
                                "weight": 70,
                                "experience_level": "中级",
                                "training_days_per_week": 4,
                                "session_duration": 60,
                                "environment": "商业健身房",
                                "diet_constraint": "自己做饭",
                            },
                            "missing_fields": [],
                            "needs_followup": False,
                            "assistant_reply": "",
                        },
                    )
                ],
            )
        ]
    )

    router = FitnessLLMRouter(
        service=service,
        provider=provider,
        model="test-model",
        rule_router=base_router,
    )
    result = await router.handle("体重140斤，训练老手，每周练4次，每次60分钟，健身房训练，自己在家做饭")

    assert result is not None
    assert "已完成建档" in result
    assert "用户: sasa" in result


@pytest.mark.asyncio
async def test_llm_router_asks_for_clarification_when_confidence_is_low(tmp_path):
    service = FitnessService(tmp_path)
    provider = DummyProvider(
        [
            LLMResponse(
                content="",
                tool_calls=[
                    ToolCallRequest(
                        id="fit3",
                        name="route_fitness_request",
                        arguments={
                            "is_fitness_request": True,
                            "action": "update_profile",
                            "confidence": 0.42,
                            "user_id": "sasa",
                            "arguments": {
                                "environment": "家里",
                            },
                            "missing_fields": [],
                            "needs_followup": False,
                            "assistant_reply": "",
                        },
                    )
                ],
            )
        ]
    )

    router = FitnessLLMRouter(service=service, provider=provider, model="test-model")
    result = await router.handle("我想改一下我的情况")

    assert result is not None
    assert "把握还不够高" in result


@pytest.mark.asyncio
async def test_llm_router_can_continue_pending_feedback_completion(tmp_path):
    service = FitnessService(tmp_path)
    service.save_profile(
        user_id="sasa",
        gender="男",
        age=23,
        height=176,
        weight=70,
        goal="减脂",
        experience_level="初级",
        training_days_per_week=4,
        session_duration=60,
        environment="商业健身房",
        diet_constraint="外卖为主",
    )
    from nanobot.fitness.router import FitnessRuleRouter

    base_router = FitnessRuleRouter(service)
    first = base_router.handle("我今天练了卧推和深蹲")
    assert "完成度" in first
    assert "疲劳程度" in first

    provider = DummyProvider(
        [
            LLMResponse(
                content="",
                tool_calls=[
                    ToolCallRequest(
                        id="fit4",
                        name="route_fitness_request",
                        arguments={
                            "is_fitness_request": True,
                            "action": "record_feedback",
                            "confidence": 0.91,
                            "user_id": "sasa",
                            "arguments": {
                                "completion_rate": 0.8,
                                "fatigue_level": 4,
                                "diet_adherence": "基本达标",
                            },
                            "missing_fields": [],
                            "needs_followup": False,
                            "assistant_reply": "",
                        },
                    )
                ],
            )
        ]
    )

    router = FitnessLLMRouter(
        service=service,
        provider=provider,
        model="test-model",
        rule_router=base_router,
    )
    result = await router.handle("完成度80%，有点累，饮食还行")

    assert result is not None
    assert "已记录今日打卡" in result
    assert "80%" in result


def test_rule_router_adapts_profile_followup_based_on_missing_context(tmp_path):
    from nanobot.fitness.router import FitnessRuleRouter

    router = FitnessRuleRouter(FitnessService(tmp_path))
    message = router.handle("我叫sasa，男，23岁，176cm")

    assert "建档" in message
    assert "体重" in message
    assert "目标" in message


def test_rule_router_does_not_ask_completion_rate_when_rest_day_feedback(tmp_path):
    from nanobot.fitness.router import FitnessRuleRouter

    service = FitnessService(tmp_path)
    service.save_profile(
        user_id="sasa",
        gender="男",
        age=23,
        height=176,
        weight=70,
        goal="减脂",
        experience_level="初级",
        training_days_per_week=4,
        session_duration=60,
        environment="商业健身房",
        diet_constraint="外卖为主",
    )
    router = FitnessRuleRouter(service)
    message = router.handle("我叫sasa，今天没练")

    assert "疲劳程度" in message
    assert "饮食达标情况" in message
    assert "完成度" not in message
