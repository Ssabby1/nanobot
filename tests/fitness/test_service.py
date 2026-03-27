from datetime import date

from nanobot.fitness.service import FitnessService


def _build_profile(service: FitnessService, user_id: str = "demo"):
    return service.save_profile(
        user_id=user_id,
        gender="男",
        age=24,
        height=178,
        weight=72,
        goal="减脂保肌",
        experience_level="初级",
        training_days_per_week=3,
        session_duration=60,
        environment="校园健身房",
        diet_constraint="食堂为主",
        current_split="上/下肢",
        weak_points="核心",
        injury_notes="",
    )


def test_generate_plan_and_adjustment(tmp_path):
    service = FitnessService(tmp_path)
    _build_profile(service)

    plan = service.generate_weekly_plan("demo", date(2026, 3, 25))

    assert plan.user_id == "demo"
    assert len(plan.plan_content) == 7
    assert sum(1 for day in plan.plan_content if day.is_training_day) == 3
    assert any(day.focus == "全身代谢" for day in plan.plan_content)

    service.record_feedback(
        user_id="demo",
        feedback_date=date(2026, 3, 24),
        trained_today=True,
        completed_exercises=["卧推", "划船"],
        completion_rate=0.5,
        fatigue_level=4,
        soreness_notes="下肢酸痛明显",
        diet_adherence="未达标",
        extra_notes="睡眠一般",
    )
    service.record_feedback(
        user_id="demo",
        feedback_date=date(2026, 3, 25),
        trained_today=False,
        completed_exercises=[],
        completion_rate=0.0,
        fatigue_level=5,
        soreness_notes="",
        diet_adherence="未达标",
        extra_notes="赶论文",
    )

    suggestion = service.generate_adjustment("demo")

    assert "deload" in suggestion.adjustment_type
    assert "diet" in suggestion.adjustment_type
    assert "simplify" in suggestion.adjustment_type
    assert "连续两次主观疲劳较高" in suggestion.trigger_reason
    assert "下调 20%" in suggestion.suggestion_content


def test_generate_plan_requires_profile(tmp_path):
    service = FitnessService(tmp_path)

    try:
        service.generate_weekly_plan("missing")
    except ValueError as exc:
        assert "请先执行 profile set" in str(exc)
    else:
        raise AssertionError("expected ValueError")
