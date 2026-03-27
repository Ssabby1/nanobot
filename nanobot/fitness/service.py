"""Business logic for the fitness MVP."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Iterable
from uuid import uuid4

from nanobot.fitness.models import AdjustmentSuggestion, DailyFeedback, ExercisePlan, PlanDay, UserProfile, WeeklyPlan
from nanobot.fitness.storage import FitnessRepository


DAY_LABELS = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]


class FitnessService:
    """High-level API for profile, plan, feedback, and adjustment flows."""

    def __init__(self, workspace):
        self.repo = FitnessRepository(workspace)

    def save_profile(self, **profile_data) -> UserProfile:
        now = datetime.now()
        existing = self.repo.get_profile(profile_data["user_id"])
        incoming_created_at = profile_data.pop("created_at", None)
        profile_data.pop("updated_at", None)
        created_at = (
            incoming_created_at
            or (existing.created_at if existing and existing.created_at else None)
            or now
        )
        profile = UserProfile(**profile_data, created_at=created_at, updated_at=now)
        return self.repo.upsert_profile(profile)

    def update_profile(self, user_id: str = "default", **partial_data) -> UserProfile:
        existing = self._require_profile(user_id)
        merged = existing.model_dump()
        for key, value in partial_data.items():
            if value is None:
                continue
            merged[key] = value
        merged["user_id"] = user_id
        return self.save_profile(**merged)

    def get_profile(self, user_id: str = "default") -> UserProfile | None:
        return self.repo.get_profile(user_id)

    def generate_weekly_plan(self, user_id: str = "default", week_start_date: date | None = None) -> WeeklyPlan:
        profile = self._require_profile(user_id)
        week_start = self._normalize_week_start(week_start_date or date.today())
        training_indices = set(self._pick_training_days(profile.training_days_per_week))
        focus_sequence = self._pick_focus_sequence(profile, len(training_indices))
        focus_iter = iter(focus_sequence)
        plan_days: list[PlanDay] = []

        for idx, label in enumerate(DAY_LABELS):
            is_training = idx in training_indices
            if is_training:
                focus = next(focus_iter)
                exercises = self._build_exercises(profile, focus)
                notes = self._build_day_notes(profile, focus)
                diet_tip = self._training_day_diet_tip(profile)
            else:
                focus = "休息/恢复"
                exercises = []
                notes = ["安排 20-30 分钟轻松步行、拉伸或泡沫轴放松。"]
                diet_tip = self._rest_day_diet_tip(profile)
            plan_days.append(
                PlanDay(
                    day_index=idx,
                    label=label,
                    is_training_day=is_training,
                    focus=focus,
                    exercises=exercises,
                    notes=notes,
                    diet_tip=diet_tip,
                )
            )

        reason = (
            f"依据 {profile.goal}、{profile.experience_level} 经验、"
            f"每周 {profile.training_days_per_week} 练、{profile.environment} 场地与 "
            f"{profile.session_duration} 分钟时长生成。"
        )
        plan = WeeklyPlan(
            plan_id=str(uuid4()),
            user_id=user_id,
            week_start_date=week_start,
            goal_type=profile.goal,
            plan_content=plan_days,
            version=1,
            generated_reason=reason,
            created_at=datetime.now(),
        )
        return self.repo.save_weekly_plan(plan)

    def get_latest_plan(self, user_id: str = "default") -> WeeklyPlan | None:
        return self.repo.get_latest_plan(user_id)

    def record_feedback(
        self,
        *,
        user_id: str,
        feedback_date: date,
        trained_today: bool,
        completed_exercises: Iterable[str],
        completion_rate: float,
        fatigue_level: int,
        soreness_notes: str,
        diet_adherence: str,
        extra_notes: str,
    ) -> DailyFeedback:
        self._require_profile(user_id)
        feedback = DailyFeedback(
            feedback_id=str(uuid4()),
            user_id=user_id,
            date=feedback_date,
            trained_today=trained_today,
            completed_exercises=[item.strip() for item in completed_exercises if item.strip()],
            completion_rate=completion_rate,
            fatigue_level=fatigue_level,
            soreness_notes=soreness_notes.strip(),
            diet_adherence=diet_adherence,
            extra_notes=extra_notes.strip(),
            created_at=datetime.now(),
        )
        return self.repo.save_feedback(feedback)

    def list_feedback(self, user_id: str = "default", limit: int = 7) -> list[DailyFeedback]:
        return self.repo.list_feedback(user_id, limit=limit)

    def generate_adjustment(self, user_id: str = "default", lookback_days: int = 7) -> AdjustmentSuggestion:
        profile = self._require_profile(user_id)
        feedback_items = list(reversed(self.repo.list_feedback(user_id, limit=lookback_days)))
        if not feedback_items:
            raise ValueError("生成调整建议前，至少需要一条反馈记录。")

        reasons: list[str] = []
        actions: list[str] = []
        adjustment_types: list[str] = []

        if len(feedback_items) >= 2 and all(item.fatigue_level >= 4 for item in feedback_items[-2:]):
            reasons.append("最近连续两次主观疲劳较高")
            actions.append("下一次训练将总组数下调 20%，复合动作保留，孤立动作酌情减少。")
            adjustment_types.append("deload")

        soreness_feedback = next((item for item in reversed(feedback_items) if item.soreness_notes.strip()), None)
        if soreness_feedback:
            reasons.append(f"最近反馈存在明显酸痛：{soreness_feedback.soreness_notes}")
            actions.append("优先避开酸痛部位的大重量动作，改为轻负荷、控制节奏或恢复性训练。")
            adjustment_types.append("exercise_swap")

        low_completion_count = sum(
            1 for item in feedback_items if (not item.trained_today) or item.completion_rate < 0.7
        )
        if low_completion_count >= 2:
            reasons.append("近期多次未完成计划或训练缺席")
            actions.append("将单次训练控制在 45-60 分钟，优先保留 4-5 个关键动作，先恢复连续性。")
            adjustment_types.append("simplify")

        recent_diet = feedback_items[-2:]
        if len(recent_diet) >= 2 and all(item.diet_adherence == "未达标" for item in recent_diet):
            reasons.append("饮食连续两次未达标")
            actions.append(self._diet_replacement_tip(profile))
            adjustment_types.append("diet")

        if len(feedback_items) >= 3 and all(not item.trained_today for item in feedback_items[-3:]):
            reasons.append("连续多日未训练")
            actions.append("建议用一次低门槛重启训练：全身 3-4 个动作，每个动作 2-3 组即可。")
            adjustment_types.append("restart")

        if not actions:
            reasons.append("近期反馈整体稳定")
            actions.append("维持本周计划，优先保证睡眠、蛋白摄入和训练完成度。")
            adjustment_types.append("maintain")

        feedback_range = f"{feedback_items[0].date.isoformat()} ~ {feedback_items[-1].date.isoformat()}"
        content = "调整建议：\n" + "\n".join(f"- {action}" for action in actions)
        suggestion = AdjustmentSuggestion(
            suggestion_id=str(uuid4()),
            user_id=user_id,
            based_on_feedback_range=feedback_range,
            adjustment_type="、".join(dict.fromkeys(adjustment_types)),
            suggestion_content=content,
            trigger_reason="；".join(reasons),
            created_at=datetime.now(),
        )
        return self.repo.save_adjustment(suggestion)

    def get_latest_adjustment(self, user_id: str = "default") -> AdjustmentSuggestion | None:
        return self.repo.get_latest_adjustment(user_id)

    @staticmethod
    def format_profile(profile: UserProfile) -> str:
        return "\n".join(
            [
                f"用户: {profile.user_id}",
                f"基础信息: {profile.gender}，{profile.age} 岁，{profile.height} cm，{profile.weight} kg",
                f"目标与经验: {profile.goal} / {profile.experience_level}",
                f"训练安排: 每周 {profile.training_days_per_week} 练，每次 {profile.session_duration} 分钟",
                f"场地与饮食: {profile.environment} / {profile.diet_constraint}",
                f"当前分化: {profile.current_split or '未填写'}",
                f"薄弱部位: {profile.weak_points or '未填写'}",
                f"伤病限制: {profile.injury_notes or '未填写'}",
            ]
        )

    @staticmethod
    def format_plan(plan: WeeklyPlan) -> str:
        lines = [
            f"用户: {plan.user_id}",
            f"周起始日期: {plan.week_start_date.isoformat()}",
            f"目标: {plan.goal_type}",
            f"生成依据: {plan.generated_reason}",
            "",
        ]
        for day in plan.plan_content:
            lines.append(f"{day.label} | {day.focus}")
            if day.is_training_day:
                for exercise in day.exercises:
                    detail = f"{exercise.name} {exercise.sets} 组 x {exercise.reps}"
                    if exercise.note:
                        detail += f" | {exercise.note}"
                    lines.append(f"- {detail}")
            else:
                lines.append("- 休息或主动恢复")
            for note in day.notes:
                lines.append(f"- 注意: {note}")
            lines.append(f"- 饮食提示: {day.diet_tip}")
            lines.append("")
        return "\n".join(lines).strip()

    @staticmethod
    def format_feedback(items: list[DailyFeedback]) -> str:
        if not items:
            return "暂无反馈记录。"
        lines = []
        for item in items:
            status = "已训练" if item.trained_today else "未训练"
            exercises = "、".join(item.completed_exercises) if item.completed_exercises else "无"
            lines.append(
                f"{item.date.isoformat()} | {status} | 完成度 {int(item.completion_rate * 100)}% | "
                f"疲劳 {item.fatigue_level}/5 | 饮食 {item.diet_adherence} | 动作 {exercises}"
            )
            if item.soreness_notes:
                lines.append(f"  酸痛: {item.soreness_notes}")
            if item.extra_notes:
                lines.append(f"  备注: {item.extra_notes}")
        return "\n".join(lines)

    @staticmethod
    def format_adjustment(suggestion: AdjustmentSuggestion) -> str:
        return "\n".join(
            [
                f"用户: {suggestion.user_id}",
                f"反馈区间: {suggestion.based_on_feedback_range}",
                f"调整类型: {suggestion.adjustment_type}",
                f"触发原因: {suggestion.trigger_reason}",
                suggestion.suggestion_content,
            ]
        )

    def _require_profile(self, user_id: str) -> UserProfile:
        profile = self.repo.get_profile(user_id)
        if not profile:
            raise ValueError(f"未找到用户 {user_id} 的画像，请先执行 profile set。")
        return profile

    @staticmethod
    def _normalize_week_start(day: date) -> date:
        return day - timedelta(days=day.weekday())

    @staticmethod
    def _pick_training_days(days_per_week: int) -> list[int]:
        presets = {
            1: [0],
            2: [0, 3],
            3: [0, 2, 4],
            4: [0, 1, 3, 5],
            5: [0, 1, 2, 4, 5],
            6: [0, 1, 2, 3, 5, 6],
            7: [0, 1, 2, 3, 4, 5, 6],
        }
        return presets[days_per_week]

    @staticmethod
    def _pick_focus_sequence(profile: UserProfile, training_days: int) -> list[str]:
        goal = profile.goal
        exp = profile.experience_level
        if goal == "新手入门" or exp == "新手":
            return ["全身适应"] * training_days
        if goal == "减脂保肌":
            patterns = {
                2: ["全身代谢", "全身代谢"],
                3: ["上肢推拉", "下肢核心", "全身代谢"],
                4: ["上肢", "下肢", "上肢", "下肢核心"],
                5: ["上肢", "下肢", "全身代谢", "上肢", "下肢核心"],
            }
            return patterns.get(
                training_days,
                ["上肢", "下肢", "全身代谢", "上肢", "下肢核心", "全身恢复"][:training_days],
            )
        patterns = {
            2: ["上肢", "下肢"],
            3: ["推", "拉", "腿"],
            4: ["上肢", "下肢", "推", "拉腿补强"],
            5: ["推", "拉", "腿", "上肢补强", "下肢核心"],
            6: ["推", "拉", "腿", "推", "拉", "腿"],
            7: ["推", "拉", "腿", "上肢补强", "下肢核心", "全身泵感", "恢复训练"],
        }
        return patterns.get(training_days, ["推", "拉", "腿"][:training_days])

    def _build_exercises(self, profile: UserProfile, focus: str) -> list[ExercisePlan]:
        home = profile.environment in {"宿舍", "家里"}
        rep_scheme = self._rep_scheme(profile.goal, focus)
        library = {
            "全身适应": [
                "高脚杯深蹲" if not home else "徒手深蹲",
                "哑铃卧推" if not home else "俯卧撑",
                "高位下拉" if not home else "弹力带划船",
                "罗马尼亚硬拉" if not home else "臀桥",
                "平板支撑",
            ],
            "全身代谢": [
                "哑铃杯式深蹲" if not home else "徒手深蹲",
                "哑铃卧推" if not home else "上斜俯卧撑",
                "坐姿划船" if not home else "弹力带划船",
                "壶铃摆动" if not home else "波比简化版",
                "登山跑",
            ],
            "上肢": [
                "卧推" if not home else "俯卧撑",
                "坐姿划船" if not home else "弹力带划船",
                "哑铃肩推",
                "高位下拉" if not home else "弹力带下拉",
                "哑铃弯举",
            ],
            "下肢": [
                "深蹲" if not home else "保加利亚分腿蹲",
                "罗马尼亚硬拉" if not home else "臀桥",
                "箭步蹲",
                "提踵",
                "死虫",
            ],
            "下肢核心": [
                "腿举" if not home else "杯式深蹲",
                "腿弯举" if not home else "臀桥",
                "台阶踏步",
                "侧桥",
                "卷腹",
            ],
            "推": [
                "杠铃卧推" if not home else "俯卧撑",
                "上斜哑铃卧推" if not home else "跪姿俯卧撑",
                "哑铃肩推",
                "哑铃侧平举",
                "绳索下压" if not home else "椅上臂屈伸",
            ],
            "拉": [
                "引体辅助或高位下拉" if not home else "弹力带下拉",
                "单臂哑铃划船",
                "俯身飞鸟",
                "哑铃弯举",
                "面拉" if not home else "弹力带面拉",
            ],
            "腿": [
                "杠铃深蹲" if not home else "高脚杯深蹲",
                "罗马尼亚硬拉",
                "箭步蹲",
                "腿屈伸" if not home else "靠墙静蹲",
                "悬垂举腿" if not home else "仰卧抬腿",
            ],
            "上肢推拉": [
                "卧推" if not home else "俯卧撑",
                "坐姿划船" if not home else "弹力带划船",
                "哑铃肩推",
                "高位下拉" if not home else "弹力带下拉",
                "哑铃弯举 + 臂屈伸",
            ],
            "上肢补强": [
                profile.weak_points or "肩部稳定训练",
                "哑铃侧平举",
                "面拉" if not home else "弹力带面拉",
                "俯卧撑",
                "哑铃弯举",
            ],
            "拉腿补强": [
                "单臂划船",
                "硬拉变式" if not home else "臀桥",
                "分腿蹲",
                "侧桥",
                "拉伸放松",
            ],
            "全身泵感": [
                "循环训练 1",
                "循环训练 2",
                "俯卧撑 + 侧平举",
                "划船 + 深蹲",
                "平板支撑",
            ],
            "恢复训练": [
                "步行或单车 20 分钟",
                "髋屈肌拉伸",
                "胸椎旋转",
                "呼吸训练",
                "泡沫轴或按摩球",
            ],
        }

        result: list[ExercisePlan] = []
        for name in library.get(focus, library["全身适应"])[: self._exercise_count(profile.session_duration)]:
            result.append(
                ExercisePlan(
                    name=name,
                    sets=rep_scheme["sets"],
                    reps=rep_scheme["reps"],
                    note=rep_scheme["note"],
                )
            )
        return result

    @staticmethod
    def _exercise_count(session_duration: int) -> int:
        if session_duration < 45:
            return 4
        if session_duration < 75:
            return 5
        return 6

    @staticmethod
    def _rep_scheme(goal: str, focus: str) -> dict[str, str | int]:
        if goal == "减脂保肌" or focus in {"全身代谢", "全身泵感"}:
            return {"sets": 3, "reps": "10-15", "note": "组间休息控制在 45-75 秒"}
        if goal == "新手入门":
            return {"sets": 2, "reps": "10-12", "note": "优先动作标准，保留 2 次余力"}
        return {"sets": 4, "reps": "6-12", "note": "采用渐进超负荷，最后一组接近力竭"}

    @staticmethod
    def _build_day_notes(profile: UserProfile, focus: str) -> list[str]:
        notes = [
            f"本次训练时长控制在 {profile.session_duration} 分钟内。",
            "先做 5-8 分钟热身，再进入主训练。",
        ]
        if profile.injury_notes:
            notes.append(f"注意避开伤病限制相关动作：{profile.injury_notes}")
        if profile.weak_points:
            notes.append(f"可在结束前增加 1 个薄弱部位补强动作：{profile.weak_points}")
        if focus == "全身适应":
            notes.append("以动作学习和节奏稳定为主，不追求高强度。")
        return notes

    @staticmethod
    def _training_day_diet_tip(profile: UserProfile) -> str:
        base = {
            "薄肌增肌": "训练前后保证蛋白质和主食摄入，优先保证当天总热量略有盈余。",
            "增肌": "训练日优先保证蛋白质、主食和补水，晚餐别省碳水。",
            "减脂保肌": "训练日前后保留主食与蛋白质，避免因为减脂把训练质量吃没。",
            "新手入门": "训练前吃易消化主食，训练后补蛋白和一份正常正餐。",
            "减脂": "优先高蛋白与高饱腹感食物，避免额外零食和含糖饮料。",
            "维持": "维持规律三餐和足量蛋白，训练后正常补餐即可。",
        }
        tip = base.get(profile.goal, "训练日优先保证蛋白质、主食和补水。")
        if profile.diet_constraint == "食堂为主":
            return tip + " 食堂优先双蛋白 + 一份米饭 + 一份蔬菜。"
        if profile.diet_constraint == "外卖为主":
            return tip + " 外卖优先点轻食饭、卤肉饭去酱或盖饭加蛋白。"
        if profile.diet_constraint == "自己做饭":
            return tip + " 自己做饭时优先保证一份蛋白质、一份主食和一份蔬菜，备餐尽量简单可重复。"
        return tip

    @staticmethod
    def _rest_day_diet_tip(profile: UserProfile) -> str:
        if profile.goal in {"薄肌增肌", "增肌"}:
            return "休息日保持蛋白质不断档，主食可略降但不要极端节食。"
        if profile.goal in {"减脂保肌", "减脂"}:
            return "休息日控制额外零食，保证蛋白质和蔬菜摄入，维持轻微热量缺口。"
        return "休息日正常饮食即可，重点是规律作息和补水。"

    @staticmethod
    def _diet_replacement_tip(profile: UserProfile) -> str:
        if profile.diet_constraint == "食堂为主":
            return "饮食不稳定时，食堂至少保证 1 份肉/蛋白 + 1 份主食 + 1 份蔬菜，不必追求完美。"
        if profile.diet_constraint == "外卖为主":
            return "外卖难控制时，优先选择鸡腿饭、轻食碗、粥+蛋+卤牛肉这类高蛋白组合。"
        if profile.diet_constraint == "自己做饭":
            return "自己做饭时先把菜单固定成 2-3 套简单组合，比如鸡蛋+鸡胸/牛肉+米饭+冷冻蔬菜，降低执行成本。"
        if profile.diet_constraint == "忌口":
            return "在忌口前提下优先保证蛋白质来源稳定，必要时用酸奶、鸡蛋、豆制品补足。"
        return "这两天先把饮食目标简化为：每餐有蛋白、饮料尽量无糖、夜宵减少。"
