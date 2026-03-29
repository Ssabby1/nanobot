from datetime import date

from nanobot.fitness.router import FitnessRuleRouter
from nanobot.fitness.service import FitnessService


def _build_profile(service: FitnessService, user_id: str = "demo"):
    return service.save_profile(
        user_id=user_id,
        gender="\u7537",
        age=24,
        height=178,
        weight=72,
        goal="\u51cf\u8102\u4fdd\u808c",
        experience_level="\u521d\u7ea7",
        training_days_per_week=3,
        session_duration=60,
        environment="\u6821\u56ed\u5065\u8eab\u623f",
        diet_constraint="\u98df\u5802\u4e3a\u4e3b",
        current_split="\u4e0a/\u4e0b\u80a2",
        weak_points="\u6838\u5fc3",
        injury_notes="",
    )


def test_generate_plan_and_adjustment(tmp_path):
    service = FitnessService(tmp_path)
    _build_profile(service)

    plan = service.generate_weekly_plan("demo", date(2026, 3, 25))

    assert plan.user_id == "demo"
    assert len(plan.plan_content) == 7
    assert sum(1 for day in plan.plan_content if day.is_training_day) == 3
    assert any(day.focus == "\u5168\u8eab\u4ee3\u8c22" for day in plan.plan_content)

    service.record_feedback(
        user_id="demo",
        feedback_date=date(2026, 3, 24),
        trained_today=True,
        completed_exercises=["\u5367\u63a8", "\u5212\u8239"],
        completion_rate=0.5,
        fatigue_level=4,
        soreness_notes="\u4e0b\u80a2\u9178\u75db\u660e\u663e",
        diet_adherence="\u672a\u8fbe\u6807",
        extra_notes="\u7761\u7720\u4e00\u822c",
    )
    service.record_feedback(
        user_id="demo",
        feedback_date=date(2026, 3, 25),
        trained_today=False,
        completed_exercises=[],
        completion_rate=0.0,
        fatigue_level=5,
        soreness_notes="",
        diet_adherence="\u672a\u8fbe\u6807",
        extra_notes="\u8d76\u8bba\u6587",
    )

    suggestion = service.generate_adjustment("demo")

    assert "deload" in suggestion.adjustment_type
    assert "diet" in suggestion.adjustment_type
    assert "simplify" in suggestion.adjustment_type
    assert "\u8fde\u7eed\u4e24\u6b21\u4e3b\u89c2\u75b2\u52b3\u8f83\u9ad8" in suggestion.trigger_reason
    assert "\u4e0b\u8c03 20%" in suggestion.suggestion_content


def test_generate_plan_requires_profile(tmp_path):
    service = FitnessService(tmp_path)

    try:
        service.generate_weekly_plan("missing")
    except ValueError as exc:
        assert "profile set" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_rule_router_end_to_end(tmp_path):
    service = FitnessService(tmp_path)
    router = FitnessRuleRouter(service)

    profile_result = router.handle(
        "\u5e2e\u6211\u5efa\u6863\uff0c\u6211\u662f\u7537\uff0c23\u5c81\uff0c176cm\uff0c70kg\uff0c"
        "\u76ee\u6807\u662f\u589e\u808c\uff0c\u521d\u7ea7\uff0c\u6bcf\u54684\u6b21\uff0c"
        "\u6bcf\u6b2160\u5206\u949f\uff0c\u5728\u5bb6\u8bad\u7ec3\uff0c\u5916\u5356\u4e3a\u4e3b",
        user_id="demo",
    )
    assert "\u5df2\u5b8c\u6210\u5efa\u6863" in profile_result
    assert "demo" in profile_result

    plan_result = router.handle("\u7ed9\u6211\u751f\u6210\u8fd9\u5468\u8bad\u7ec3\u8ba1\u5212", user_id="demo")
    assert "\u5df2\u751f\u6210\u672c\u5468\u8ba1\u5212" in plan_result
    assert "\u5468\u4e00" in plan_result

    feedback_result = router.handle(
        "\u6211\u4eca\u5929\u7ec3\u4e86\u5367\u63a8\u548c\u5212\u8239\uff0c\u5b8c\u6210\u5ea680%\uff0c"
        "\u6709\u70b9\u7d2f\uff0c\u996e\u98df\u8fd8\u884c\uff0c"
        "\u9178\u75db\u662f\u624b\u81c2\u6709\u70b9\u7d27",
        user_id="demo",
    )
    assert "\u5df2\u8bb0\u5f55\u4eca\u65e5\u6253\u5361" in feedback_result
    assert "80%" in feedback_result

    show_feedback = router.handle("\u770b\u770b\u6253\u5361\u8bb0\u5f55", user_id="demo")
    assert "\u6253\u5361\u8bb0\u5f55" in show_feedback

    adjustment_result = router.handle("\u7ed9\u6211\u4e00\u70b9\u8c03\u6574\u5efa\u8bae", user_id="demo")
    assert "\u5df2\u751f\u6210\u8c03\u6574\u5efa\u8bae" in adjustment_result

    show_adjustment = router.handle("\u770b\u770b\u6700\u8fd1\u7684\u5efa\u8bae", user_id="demo")
    assert "\u8c03\u6574\u5efa\u8bae" in show_adjustment


def test_rule_router_extracts_user_id_from_message(tmp_path):
    service = FitnessService(tmp_path)
    router = FitnessRuleRouter(service)

    profile_result = router.handle(
        "\u6211\u53ebsasa\uff0c\u6211\u662f\u7537\uff0c23\u5c81\uff0c176cm\uff0c70kg\uff0c"
        "\u76ee\u6807\u662f\u589e\u808c\uff0c\u521d\u7ea7\uff0c\u6bcf\u54684\u6b21\uff0c"
        "\u6bcf\u6b2160\u5206\u949f\uff0c\u5728\u5bb6\u8bad\u7ec3\uff0c\u5916\u5356\u4e3a\u4e3b"
    )
    assert "\u7528\u6237: sasa" in profile_result


def test_rule_router_remembers_last_user(tmp_path):
    service = FitnessService(tmp_path)
    router = FitnessRuleRouter(service)

    router.handle(
        "\u6211\u53ebsasa\uff0c\u6211\u662f\u7537\uff0c23\u5c81\uff0c176cm\uff0c70kg\uff0c"
        "\u76ee\u6807\u662f\u589e\u808c\uff0c\u521d\u7ea7\uff0c\u6bcf\u54684\u6b21\uff0c"
        "\u6bcf\u6b2160\u5206\u949f\uff0c\u5728\u5bb6\u8bad\u7ec3\uff0c\u5916\u5356\u4e3a\u4e3b"
    )
    show_profile = router.handle("\u770b\u770b\u6211\u7684\u753b\u50cf")
    assert "\u7528\u6237: sasa" in show_profile


def test_rule_router_handles_natural_profile_phrasing(tmp_path):
    service = FitnessService(tmp_path)
    router = FitnessRuleRouter(service)

    result = router.handle(
        "\u6211\u53eb\u5f6d\u4e8e\u664f\uff0c\u7537\uff0c23\u5c81\uff0c176cm\uff0c\u4f53\u91cd140\u65a4\uff0c"
        "\u76ee\u6807\u51cf\u8102\uff0c\u8bad\u7ec3\u8001\u624b\uff0c\u5df2\u7ecf\u953b\u70bc\u4e94\u5e74\u4e86\uff0c"
        "\u6bcf\u5468\u7ec34\u6b21\uff0c\u6bcf\u6b2160\u5206\u949f\uff0c\u5065\u8eab\u623f\u8bad\u7ec3\uff0c"
        "\u6bcf\u5929\u81ea\u5df1\u5728\u5bb6\u505a\u996d\u5403"
    )

    assert "\u5df2\u5b8c\u6210\u5efa\u6863" in result
    assert "\u7528\u6237: \u5f6d\u4e8e\u664f" in result
    assert "70.0kg" in result or "70kg" in result


def test_rule_router_can_continue_pending_profile_completion(tmp_path):
    service = FitnessService(tmp_path)
    router = FitnessRuleRouter(service)

    first = router.handle("\u6211\u53ebsasa\uff0c\u7537\uff0c23\u5c81\uff0c176cm\uff0c\u76ee\u6807\u51cf\u8102")
    assert "\u4f53\u91cd" in first
    assert "\u8bad\u7ec3\u7ecf\u9a8c" in first

    second = router.handle(
        "\u4f53\u91cd140\u65a4\uff0c\u8bad\u7ec3\u8001\u624b\uff0c\u6bcf\u5468\u7ec34\u6b21\uff0c"
        "\u6bcf\u6b2160\u5206\u949f\uff0c\u5065\u8eab\u623f\u8bad\u7ec3\uff0c\u81ea\u5df1\u5728\u5bb6\u505a\u996d"
    )
    assert "\u5df2\u5b8c\u6210\u5efa\u6863" in second
    assert "\u7528\u6237: sasa" in second
