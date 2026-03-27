"""Fitness MVP module for nanobot."""

from nanobot.fitness.models import AdjustmentSuggestion, DailyFeedback, UserProfile, WeeklyPlan
from nanobot.fitness.router import FitnessRuleRouter
from nanobot.fitness.service import FitnessService

__all__ = [
    "AdjustmentSuggestion",
    "DailyFeedback",
    "FitnessRuleRouter",
    "FitnessService",
    "UserProfile",
    "WeeklyPlan",
]
