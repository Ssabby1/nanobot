"""Typed models for the fitness MVP."""

from __future__ import annotations

from datetime import date, datetime
import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator


GoalType = Literal["薄肌增肌", "减脂保肌", "新手入门", "增肌", "减脂", "维持"]
ExperienceLevel = Literal["新手", "初级", "中级"]
EnvironmentType = Literal["商业健身房", "校园健身房", "宿舍", "家里"]
DietConstraintType = Literal["无", "食堂为主", "外卖为主", "自己做饭", "忌口"]
DietAdherenceType = Literal["达标", "基本达标", "未达标"]


def _compact(value: str) -> str:
    return value.strip().lower().replace(" ", "")


def _normalize_goal(value: str) -> str:
    raw = value.strip()
    key = _compact(raw)
    aliases = {
        "薄肌增肌": "薄肌增肌",
        "薄肌": "薄肌增肌",
        "薄肌+增肌": "薄肌增肌",
        "薄肌和增肌": "薄肌增肌",
        "精瘦增肌": "薄肌增肌",
        "leanbulk": "薄肌增肌",
        "减脂保肌": "减脂保肌",
        "薄肌和减脂": "减脂保肌",
        "减脂和薄肌": "减脂保肌",
        "减脂增肌": "减脂保肌",
        "边减脂边增肌": "减脂保肌",
        "边减脂边练壮": "减脂保肌",
        "减脂同时保肌": "减脂保肌",
        "recomp": "减脂保肌",
        "新手入门": "新手入门",
        "入门": "新手入门",
        "新手": "新手入门",
        "刚开始健身": "新手入门",
        "增肌": "增肌",
        "减脂": "减脂",
        "维持": "维持",
        "保持": "维持",
    }
    if key in aliases:
        return aliases[key]
    if "减脂" in raw and ("保肌" in raw or "薄肌" in raw or "增肌" in raw):
        return "减脂保肌"
    if "新手" in raw or "入门" in raw:
        return "新手入门"
    if "薄肌" in raw and "减脂" not in raw:
        return "薄肌增肌"
    if "增肌" in raw:
        return "增肌"
    if "减脂" in raw:
        return "减脂"
    if "维持" in raw or "保持" in raw:
        return "维持"
    return raw


def _normalize_experience(value: str) -> str:
    raw = value.strip()
    key = _compact(raw)
    aliases = {
        "新手": "新手",
        "小白": "新手",
        "刚开始": "新手",
        "刚开始健身": "新手",
        "零基础": "新手",
        "入门": "新手",
        "初级": "初级",
        "系统健身三个月": "初级",
        "系统训练三个月": "初级",
        "练了三个月": "初级",
        "健身三个月": "初级",
        "有一点基础": "初级",
        "中级": "中级",
        "练了一年": "中级",
        "系统健身一年": "中级",
        "有一定基础": "中级",
    }
    if key in aliases:
        return aliases[key]
    if "新手" in raw or "入门" in raw or "零基础" in raw:
        return "新手"
    if "三个月" in raw or "几个月" in raw or "初级" in raw or "一点基础" in raw:
        return "初级"
    if "半年" in raw or "一年" in raw or "中级" in raw or "一定基础" in raw:
        return "中级"
    return raw


def _normalize_environment(value: str) -> str:
    raw = value.strip()
    key = _compact(raw)
    aliases = {
        "商业健身房": "商业健身房",
        "健身房": "商业健身房",
        "商健": "商业健身房",
        "校园健身房": "校园健身房",
        "学校": "校园健身房",
        "学校健身房": "校园健身房",
        "校园": "校园健身房",
        "宿舍": "宿舍",
        "寝室": "宿舍",
        "家里": "家里",
        "在家": "家里",
        "家": "家里",
    }
    if key in aliases:
        return aliases[key]
    if "学校" in raw or "校园" in raw:
        return "校园健身房"
    if "宿舍" in raw or "寝室" in raw:
        return "宿舍"
    if "家" in raw:
        return "家里"
    if "健身房" in raw:
        return "商业健身房"
    return raw


def _normalize_diet_constraint(value: str) -> str:
    raw = value.strip()
    key = _compact(raw)
    aliases = {
        "无": "无",
        "没有": "无",
        "无特殊限制": "无",
        "食堂为主": "食堂为主",
        "学校食堂": "食堂为主",
        "食堂": "食堂为主",
        "学校食堂为主": "食堂为主",
        "外卖为主": "外卖为主",
        "外卖": "外卖为主",
        "经常点外卖": "外卖为主",
        "自己做饭": "自己做饭",
        "自己做": "自己做饭",
        "家里吃饭": "自己做饭",
        "在家吃饭": "自己做饭",
        "家里做饭": "自己做饭",
        "自己下厨": "自己做饭",
        "忌口": "忌口",
        "有忌口": "忌口",
    }
    if key in aliases:
        return aliases[key]
    if "食堂" in raw:
        return "食堂为主"
    if "外卖" in raw:
        return "外卖为主"
    if "做饭" in raw or "下厨" in raw or "家里吃" in raw:
        return "自己做饭"
    if "忌口" in raw:
        return "忌口"
    if raw in {"无", "没有"}:
        return "无"
    return raw


def _normalize_diet_adherence(value: str) -> str:
    raw = value.strip()
    key = _compact(raw)
    aliases = {
        "达标": "达标",
        "完成": "达标",
        "吃得很好": "达标",
        "基本达标": "基本达标",
        "差不多达标": "基本达标",
        "一般": "基本达标",
        "还行": "基本达标",
        "未达标": "未达标",
        "没达标": "未达标",
        "没控制住": "未达标",
        "饮食崩了": "未达标",
    }
    if key in aliases:
        return aliases[key]
    if "达标" in raw and "基本" in raw:
        return "基本达标"
    if "未达标" in raw or "没达标" in raw:
        return "未达标"
    return raw


def _normalize_numeric_like(value: object, *, prefer: str = "upper") -> int | float | object:
    if isinstance(value, (int, float)):
        return value
    raw = str(value).strip()
    if not raw:
        return value
    compact = raw.lower().replace(" ", "")
    numbers = re.findall(r"\d+(?:\.\d+)?", compact)
    if not numbers:
        return value
    if len(numbers) == 1:
        number = float(numbers[0])
    else:
        picked = numbers[-1] if prefer == "upper" else numbers[0]
        number = float(picked)
    return int(number) if number.is_integer() else number


class ExercisePlan(BaseModel):
    name: str
    sets: int
    reps: str
    note: str = ""


class PlanDay(BaseModel):
    day_index: int = Field(ge=0, le=6)
    label: str
    is_training_day: bool
    focus: str
    exercises: list[ExercisePlan] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    diet_tip: str


class UserProfile(BaseModel):
    user_id: str = "default"
    gender: str
    age: int = Field(ge=12, le=80)
    height: float = Field(gt=100, lt=250)
    weight: float = Field(gt=30, lt=250)
    goal: GoalType
    experience_level: ExperienceLevel
    training_days_per_week: int = Field(ge=1, le=7)
    session_duration: int = Field(ge=20, le=180)
    environment: EnvironmentType
    diet_constraint: DietConstraintType
    current_split: str = ""
    weak_points: str = ""
    injury_notes: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @field_validator("user_id")
    @classmethod
    def _normalize_user_id(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("user_id 不能为空")
        return value

    @field_validator("goal", mode="before")
    @classmethod
    def _normalize_goal_value(cls, value: str) -> str:
        return _normalize_goal(str(value))

    @field_validator("experience_level", mode="before")
    @classmethod
    def _normalize_experience_value(cls, value: str) -> str:
        return _normalize_experience(str(value))

    @field_validator("environment", mode="before")
    @classmethod
    def _normalize_environment_value(cls, value: str) -> str:
        return _normalize_environment(str(value))

    @field_validator("diet_constraint", mode="before")
    @classmethod
    def _normalize_diet_constraint_value(cls, value: str) -> str:
        return _normalize_diet_constraint(str(value))

    @field_validator("age", mode="before")
    @classmethod
    def _normalize_age_value(cls, value: object) -> object:
        return _normalize_numeric_like(value, prefer="upper")

    @field_validator("height", mode="before")
    @classmethod
    def _normalize_height_value(cls, value: object) -> object:
        return _normalize_numeric_like(value, prefer="upper")

    @field_validator("weight", mode="before")
    @classmethod
    def _normalize_weight_value(cls, value: object) -> object:
        return _normalize_numeric_like(value, prefer="upper")

    @field_validator("training_days_per_week", mode="before")
    @classmethod
    def _normalize_training_days_value(cls, value: object) -> object:
        return _normalize_numeric_like(value, prefer="upper")

    @field_validator("session_duration", mode="before")
    @classmethod
    def _normalize_session_duration_value(cls, value: object) -> object:
        return _normalize_numeric_like(value, prefer="upper")


class WeeklyPlan(BaseModel):
    plan_id: str
    user_id: str
    week_start_date: date
    goal_type: str
    plan_content: list[PlanDay]
    version: int = 1
    generated_reason: str
    created_at: datetime | None = None


class DailyFeedback(BaseModel):
    feedback_id: str
    user_id: str
    date: date
    trained_today: bool
    completed_exercises: list[str] = Field(default_factory=list)
    completion_rate: float = Field(ge=0.0, le=1.0)
    fatigue_level: int = Field(ge=1, le=5)
    soreness_notes: str = ""
    diet_adherence: DietAdherenceType
    extra_notes: str = ""
    created_at: datetime | None = None

    @field_validator("diet_adherence", mode="before")
    @classmethod
    def _normalize_diet_adherence_value(cls, value: str) -> str:
        return _normalize_diet_adherence(str(value))

    @field_validator("completion_rate", mode="before")
    @classmethod
    def _normalize_completion_rate_value(cls, value: object) -> object:
        if isinstance(value, (int, float)):
            return value
        raw = str(value).strip()
        if raw.endswith("%"):
            normalized = _normalize_numeric_like(raw[:-1], prefer="upper")
            if isinstance(normalized, (int, float)):
                return float(normalized) / 100.0
        normalized = _normalize_numeric_like(raw, prefer="upper")
        if isinstance(normalized, (int, float)) and normalized > 1:
            return float(normalized) / 100.0
        return normalized

    @field_validator("fatigue_level", mode="before")
    @classmethod
    def _normalize_fatigue_level_value(cls, value: object) -> object:
        raw = str(value).strip()
        aliases = {
            "很轻松": 1,
            "轻松": 2,
            "一般": 3,
            "有点累": 4,
            "很累": 5,
            "爆累": 5,
        }
        if raw in aliases:
            return aliases[raw]
        return _normalize_numeric_like(value, prefer="upper")


class AdjustmentSuggestion(BaseModel):
    suggestion_id: str
    user_id: str
    based_on_feedback_range: str
    adjustment_type: str
    suggestion_content: str
    trigger_reason: str
    created_at: datetime | None = None
