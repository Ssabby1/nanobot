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
async def test_llm_router_uses_contextual_clarification_copy(tmp_path):
    service = FitnessService(tmp_path)
    provider = DummyProvider(
        [
            LLMResponse(
                content="",
                tool_calls=[
                    ToolCallRequest(
                        id="fit-copy-1",
                        name="route_fitness_request",
                        arguments={
                            "is_fitness_request": True,
                            "action": "update_profile",
                            "confidence": 0.32,
                            "user_id": "sasa",
                            "arguments": {"environment": "家里"},
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
    result = await router.handle("我想改一下最近训练情况")

    assert result is not None
    assert "我猜你的意思是想改一下现在的档案" in result
    assert "但把握还不够高" in result


@pytest.mark.asyncio
async def test_llm_router_reuses_rule_router_natural_followup_copy(tmp_path):
    service = FitnessService(tmp_path)
    provider = DummyProvider(
        [
            LLMResponse(
                content="",
                tool_calls=[
                    ToolCallRequest(
                        id="fit-copy-2",
                        name="route_fitness_request",
                        arguments={
                            "is_fitness_request": True,
                            "action": "save_profile",
                            "confidence": 0.9,
                            "user_id": "sasa",
                            "arguments": {"gender": "男", "age": 23, "height": 176},
                            "missing_fields": ["weight", "goal", "experience_level"],
                            "needs_followup": True,
                            "assistant_reply": "",
                        },
                    )
                ],
            )
        ]
    )

    router = FitnessLLMRouter(service=service, provider=provider, model="test-model")
    result = await router.handle("我叫sasa，男，23岁，176cm")

    assert result is not None
    assert "基础信息我先记下了" in result
    assert "你现在体重大概多少" in result


@pytest.mark.asyncio
async def test_llm_router_uses_continuation_lead_when_pending_exists(tmp_path):
    service = FitnessService(tmp_path)
    from nanobot.fitness.router import FitnessRuleRouter

    base_router = FitnessRuleRouter(service)
    first = base_router.handle("我叫sasa，男，23岁，176cm")
    assert "基础信息我先记下了" in first

    provider = DummyProvider(
        [
            LLMResponse(
                content="",
                tool_calls=[
                    ToolCallRequest(
                        id="fit-copy-3",
                        name="route_fitness_request",
                        arguments={
                            "is_fitness_request": True,
                            "action": "save_profile",
                            "confidence": 0.9,
                            "user_id": "sasa",
                            "arguments": {"weight": 70},
                            "missing_fields": ["goal", "experience_level"],
                            "needs_followup": True,
                            "assistant_reply": "",
                        },
                    )
                ],
            )
        ]
    )

    router = FitnessLLMRouter(service=service, provider=provider, model="test-model", rule_router=base_router)
    result = await router.handle("体重140斤")

    assert result is not None
    assert "我们接着把剩下的补完" in result
    assert "更偏向减脂还是增肌" in result
