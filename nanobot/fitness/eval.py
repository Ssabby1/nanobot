"""Deterministic evaluation helpers for the fitness routing project."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from nanobot.fitness.router import FitnessRuleRouter
from nanobot.fitness.service import FitnessService


@dataclass
class FitnessEvalCase:
    """One deterministic fitness routing evaluation case."""

    case_id: str
    category: str
    description: str
    messages: list[str]
    expected_substrings: list[str] = field(default_factory=list)
    expected_absent_substrings: list[str] = field(default_factory=list)


@dataclass
class FitnessEvalResult:
    """Single evaluation result."""

    case_id: str
    category: str
    description: str
    passed: bool
    transcript: list[str]
    checks: list[str]


FITNESS_EVAL_CASES: list[FitnessEvalCase] = [
    FitnessEvalCase(
        case_id="profile_full_natural",
        category="demo",
        description="完整自然语言建档应直接成功",
        messages=[
            "我叫彭于晏，男，23岁，176cm，体重140斤，目标减脂，训练老手，已经锻炼五年了，每周练4次，每次60分钟，健身房训练，每天自己在家做饭吃"
        ],
        expected_substrings=["已完成建档", "用户: 彭于晏"],
    ),
    FitnessEvalCase(
        case_id="profile_followup_multi_turn",
        category="followup",
        description="建档补槽应支持多轮续填并完成建档",
        messages=[
            "我叫sasa，男，23岁，176cm",
            "体重140斤",
            "目标减脂，练了五年，每周练4次，每次60分钟，健身房训练，自己做饭",
        ],
        expected_substrings=["基础信息我先记下了", "我们接着把剩下的补完", "已完成建档", "用户: sasa"],
    ),
    FitnessEvalCase(
        case_id="recent_user_reuse",
        category="memory",
        description="最近活跃用户应在查看档案时自动复用",
        messages=[
            "我叫sasa，男，23岁，176cm，70kg，目标增肌，初级，每周练4次，每次60分钟，在家训练，外卖为主",
            "看看我的档案",
        ],
        expected_substrings=["已完成建档", "用户: sasa"],
    ),
    FitnessEvalCase(
        case_id="plan_generation",
        category="demo",
        description="建档后应能生成周计划",
        messages=[
            "我叫sasa，男，23岁，176cm，70kg，目标增肌，初级，每周练4次，每次60分钟，在家训练，外卖为主",
            "给我生成这周训练计划",
        ],
        expected_substrings=["已生成本周计划", "周一"],
    ),
    FitnessEvalCase(
        case_id="rest_day_feedback_followup",
        category="followup",
        description="休息日打卡应优先追问疲劳和饮食，并能续填完成",
        messages=[
            "我叫sasa，男，23岁，176cm，70kg，目标减脂，初级，每周练4次，每次60分钟，在家训练，自己做饭",
            "我今天没练",
            "有点累，饮食还行",
        ],
        expected_substrings=["休息日也可以记一下状态", "已记录今日打卡"],
    ),
    FitnessEvalCase(
        case_id="adjustment_after_feedback",
        category="loop",
        description="完成建档和打卡后应能生成调整建议",
        messages=[
            "我叫demo，男，25岁，180cm，75kg，目标减脂，中级，每周练4次，每次60分钟，健身房训练，自己做饭",
            "我今天练了卧推和深蹲，完成度80%，有点累，饮食还行",
            "给我生成调整建议",
        ],
        expected_substrings=["已记录今日打卡", "已生成调整建议"],
    ),
]


def run_fitness_eval(workspace: Path | str) -> tuple[list[FitnessEvalResult], Path]:
    """Run the built-in deterministic evaluation suite."""

    workspace_path = Path(workspace)
    run_id = datetime.now().strftime("%Y%m%d-%H%M%S")
    report_root = workspace_path / "fitness_eval_reports"
    run_root = report_root / run_id
    run_root.mkdir(parents=True, exist_ok=True)

    results: list[FitnessEvalResult] = []
    for case in FITNESS_EVAL_CASES:
        case_workspace = run_root / case.case_id
        case_workspace.mkdir(parents=True, exist_ok=True)
        router = FitnessRuleRouter(FitnessService(case_workspace))

        transcript: list[str] = []
        checks: list[str] = []
        for message in case.messages:
            transcript.append(router.handle(message))

        passed = True
        combined = "\n".join(transcript)
        for needle in case.expected_substrings:
            if needle in combined:
                checks.append(f"PASS contains: {needle}")
            else:
                passed = False
                checks.append(f"FAIL missing: {needle}")

        for needle in case.expected_absent_substrings:
            if needle in combined:
                passed = False
                checks.append(f"FAIL unexpected: {needle}")
            else:
                checks.append(f"PASS absent: {needle}")

        results.append(
            FitnessEvalResult(
                case_id=case.case_id,
                category=case.category,
                description=case.description,
                passed=passed,
                transcript=transcript,
                checks=checks,
            )
        )

    report_path = run_root / "fitness_eval_report.json"
    report = {
        "generated_at": datetime.now().isoformat(),
        "summary": build_eval_summary(results),
        "results": [asdict(item) for item in results],
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return results, report_path


def build_eval_summary(results: list[FitnessEvalResult]) -> dict[str, Any]:
    """Build a compact summary for display and reports."""

    total = len(results)
    passed = sum(1 for item in results if item.passed)
    failed = total - passed
    by_category: dict[str, dict[str, int]] = {}
    for item in results:
        bucket = by_category.setdefault(item.category, {"total": 0, "passed": 0})
        bucket["total"] += 1
        if item.passed:
            bucket["passed"] += 1
    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "pass_rate": round((passed / total) * 100, 1) if total else 0.0,
        "by_category": by_category,
    }
