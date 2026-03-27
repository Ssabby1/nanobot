"""SQLite-backed persistence for the fitness MVP."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from nanobot.fitness.models import AdjustmentSuggestion, DailyFeedback, UserProfile, WeeklyPlan
from nanobot.utils.helpers import ensure_dir


class FitnessRepository:
    """Persist structured fitness state separately from chat history."""

    def __init__(self, workspace: Path):
        self.base_dir = ensure_dir(workspace / "fitness")
        self.db_path = self.base_dir / "fitness.db"
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS user_profiles (
                    user_id TEXT PRIMARY KEY,
                    data TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS weekly_plans (
                    plan_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    week_start_date TEXT NOT NULL,
                    goal_type TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    generated_reason TEXT NOT NULL,
                    plan_content TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS daily_feedback (
                    feedback_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    date TEXT NOT NULL,
                    trained_today INTEGER NOT NULL,
                    completion_rate REAL NOT NULL,
                    fatigue_level INTEGER NOT NULL,
                    soreness_notes TEXT NOT NULL,
                    diet_adherence TEXT NOT NULL,
                    extra_notes TEXT NOT NULL,
                    completed_exercises TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS adjustment_suggestions (
                    suggestion_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    based_on_feedback_range TEXT NOT NULL,
                    adjustment_type TEXT NOT NULL,
                    suggestion_content TEXT NOT NULL,
                    trigger_reason TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_weekly_plans_user_week
                    ON weekly_plans(user_id, week_start_date DESC);

                CREATE INDEX IF NOT EXISTS idx_daily_feedback_user_date
                    ON daily_feedback(user_id, date DESC);

                CREATE INDEX IF NOT EXISTS idx_adjustment_user_created
                    ON adjustment_suggestions(user_id, created_at DESC);
                """
            )

    @staticmethod
    def _dump(model: Any) -> str:
        return model.model_dump_json()

    @staticmethod
    def _load_profile(row: sqlite3.Row | None) -> UserProfile | None:
        return UserProfile.model_validate_json(row["data"]) if row else None

    @staticmethod
    def _load_weekly_plan(row: sqlite3.Row | None) -> WeeklyPlan | None:
        if not row:
            return None
        return WeeklyPlan.model_validate(
            {
                "plan_id": row["plan_id"],
                "user_id": row["user_id"],
                "week_start_date": row["week_start_date"],
                "goal_type": row["goal_type"],
                "version": row["version"],
                "generated_reason": row["generated_reason"],
                "plan_content": json.loads(row["plan_content"]),
                "created_at": row["created_at"],
            }
        )

    @staticmethod
    def _load_feedback(row: sqlite3.Row | None) -> DailyFeedback | None:
        if not row:
            return None
        return DailyFeedback.model_validate(
            {
                "feedback_id": row["feedback_id"],
                "user_id": row["user_id"],
                "date": row["date"],
                "trained_today": bool(row["trained_today"]),
                "completion_rate": row["completion_rate"],
                "fatigue_level": row["fatigue_level"],
                "soreness_notes": row["soreness_notes"],
                "diet_adherence": row["diet_adherence"],
                "extra_notes": row["extra_notes"],
                "completed_exercises": json.loads(row["completed_exercises"]),
                "created_at": row["created_at"],
            }
        )

    @staticmethod
    def _load_adjustment(row: sqlite3.Row | None) -> AdjustmentSuggestion | None:
        if not row:
            return None
        return AdjustmentSuggestion.model_validate(dict(row))

    def upsert_profile(self, profile: UserProfile) -> UserProfile:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO user_profiles(user_id, data, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    data = excluded.data,
                    updated_at = excluded.updated_at
                """,
                (
                    profile.user_id,
                    self._dump(profile),
                    profile.created_at.isoformat(),
                    profile.updated_at.isoformat(),
                ),
            )
        return profile

    def get_profile(self, user_id: str) -> UserProfile | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT data FROM user_profiles WHERE user_id = ?",
                (user_id,),
            ).fetchone()
        return self._load_profile(row)

    def save_weekly_plan(self, plan: WeeklyPlan) -> WeeklyPlan:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO weekly_plans(
                    plan_id, user_id, week_start_date, goal_type, version,
                    generated_reason, plan_content, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    plan.plan_id,
                    plan.user_id,
                    plan.week_start_date.isoformat(),
                    plan.goal_type,
                    plan.version,
                    plan.generated_reason,
                    json.dumps([day.model_dump() for day in plan.plan_content], ensure_ascii=False),
                    plan.created_at.isoformat(),
                ),
            )
        return plan

    def get_latest_plan(self, user_id: str) -> WeeklyPlan | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT * FROM weekly_plans
                WHERE user_id = ?
                ORDER BY week_start_date DESC, created_at DESC
                LIMIT 1
                """,
                (user_id,),
            ).fetchone()
        return self._load_weekly_plan(row)

    def save_feedback(self, feedback: DailyFeedback) -> DailyFeedback:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO daily_feedback(
                    feedback_id, user_id, date, trained_today, completion_rate,
                    fatigue_level, soreness_notes, diet_adherence, extra_notes,
                    completed_exercises, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    feedback.feedback_id,
                    feedback.user_id,
                    feedback.date.isoformat(),
                    int(feedback.trained_today),
                    feedback.completion_rate,
                    feedback.fatigue_level,
                    feedback.soreness_notes,
                    feedback.diet_adherence,
                    feedback.extra_notes,
                    json.dumps(feedback.completed_exercises, ensure_ascii=False),
                    feedback.created_at.isoformat(),
                ),
            )
        return feedback

    def list_feedback(self, user_id: str, limit: int = 7) -> list[DailyFeedback]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM daily_feedback
                WHERE user_id = ?
                ORDER BY date DESC, created_at DESC
                LIMIT ?
                """,
                (user_id, limit),
            ).fetchall()
        return [self._load_feedback(row) for row in rows]

    def save_adjustment(self, suggestion: AdjustmentSuggestion) -> AdjustmentSuggestion:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO adjustment_suggestions(
                    suggestion_id, user_id, based_on_feedback_range, adjustment_type,
                    suggestion_content, trigger_reason, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    suggestion.suggestion_id,
                    suggestion.user_id,
                    suggestion.based_on_feedback_range,
                    suggestion.adjustment_type,
                    suggestion.suggestion_content,
                    suggestion.trigger_reason,
                    suggestion.created_at.isoformat(),
                ),
            )
        return suggestion

    def get_latest_adjustment(self, user_id: str) -> AdjustmentSuggestion | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT * FROM adjustment_suggestions
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (user_id,),
            ).fetchone()
        return self._load_adjustment(row)
