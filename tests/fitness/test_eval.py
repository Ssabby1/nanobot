from nanobot.fitness.eval import build_eval_summary, run_fitness_eval


def test_run_fitness_eval_generates_passing_report(tmp_path):
    results, report_path = run_fitness_eval(tmp_path)

    assert results
    assert all(item.passed for item in results)
    assert report_path.exists()

    summary = build_eval_summary(results)
    assert summary["failed"] == 0
    assert summary["passed"] == summary["total"]
