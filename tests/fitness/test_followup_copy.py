from nanobot.fitness.router import FitnessRuleRouter, RouteDecision
from nanobot.fitness.service import FitnessService


def test_rule_router_uses_natural_question_for_profile_followup(tmp_path):
    router = FitnessRuleRouter(FitnessService(tmp_path))

    message = router._format_missing_message(
        RouteDecision(
            action="save_profile",
            params={"gender": "男", "age": 23, "height": 176},
            missing_fields=["weight", "goal", "experience_level"],
            reason="建档",
            stateful=True,
        )
    )

    assert "你现在体重大概多少" in message
    assert "更偏向减脂还是增肌" in message
    assert "体重140斤，目标减脂" in message


def test_rule_router_uses_rest_day_feedback_question(tmp_path):
    router = FitnessRuleRouter(FitnessService(tmp_path))

    message = router._format_missing_message(
        RouteDecision(
            action="record_feedback",
            params={"trained_today": False},
            missing_fields=["fatigue_level", "diet_adherence"],
            reason="打卡",
            stateful=True,
        )
    )

    assert "今天整体状态感觉累不累" in message
    assert "饮食大概达标了吗" in message
    assert "有点累，饮食还行" in message


def test_rule_router_uses_contextual_lead_for_partial_profile(tmp_path):
    router = FitnessRuleRouter(FitnessService(tmp_path))

    message = router._format_missing_message(
        RouteDecision(
            action="save_profile",
            params={"gender": "男", "age": 23, "height": 176},
            missing_fields=["weight", "goal", "experience_level"],
            reason="建档",
            stateful=True,
        )
    )

    assert "基础信息我先记下了" in message


def test_rule_router_uses_rest_day_contextual_lead(tmp_path):
    router = FitnessRuleRouter(FitnessService(tmp_path))

    message = router._format_missing_message(
        RouteDecision(
            action="record_feedback",
            params={"trained_today": False},
            missing_fields=["fatigue_level", "diet_adherence"],
            reason="打卡",
            stateful=True,
        )
    )

    assert "休息日也可以记一下状态" in message


def test_rule_router_uses_continuation_lead_on_second_followup(tmp_path):
    router = FitnessRuleRouter(FitnessService(tmp_path))

    first = router.handle("我叫sasa，男，23岁，176cm")
    second = router.handle("体重140斤")

    assert "基础信息我先记下了" in first
    assert "我们接着把剩下的补完" in second
