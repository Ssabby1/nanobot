"""Fitness MVP module for nanobot."""

from nanobot.fitness.eval import FITNESS_EVAL_CASES, FitnessEvalCase, FitnessEvalResult, build_eval_summary, run_fitness_eval
from nanobot.fitness.models import AdjustmentSuggestion, DailyFeedback, UserProfile, WeeklyPlan
from nanobot.fitness.llm_router import FitnessLLMRouter, FitnessLLMRouteResult
from nanobot.fitness.router import FitnessRuleRouter
from nanobot.fitness.service import FitnessService

__all__ = [
    "AdjustmentSuggestion",
    "DailyFeedback",
    "FitnessEvalCase",
    "FitnessEvalResult",
    "FitnessLLMRouter",
    "FitnessLLMRouteResult",
    "FitnessRuleRouter",
    "FitnessService",
    "FITNESS_EVAL_CASES",
    "UserProfile",
    "WeeklyPlan",
    "build_eval_summary",
    "run_fitness_eval",
]
